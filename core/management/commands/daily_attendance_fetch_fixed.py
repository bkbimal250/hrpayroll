#!/usr/bin/env python3
"""
Daily Attendance Fetch Command - Fixed Version
Simple command to fetch attendance from all devices one by one
Disables Redis/WebSocket broadcasting to prevent connection issues
"""

import os
import sys
import django
from datetime import datetime, timedelta
import hashlib
import multiprocessing

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'attendance_system.settings')
django.setup()

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import connection, close_old_connections
from core.attendance_processing import record_raw_punch
from core.models import Device, Attendance

# Disable signals to prevent Redis broadcasting
from django.db.models.signals import post_save
from core.signals import attendance_saved

try:
    from zk import ZK
    ZK_AVAILABLE = True
except ImportError:
    ZK_AVAILABLE = False


def _run_daily_device_fetch_worker(device_id, start_date, end_date, limit, result_queue):
    """Fetch one daily device in a separate process so a stuck device can be skipped."""
    try:
        close_old_connections()
        post_save.disconnect(attendance_saved, sender=Attendance)
        device = Device.objects.get(id=device_id)
        command = Command()
        processed, new_records, duplicates = command.fetch_device_attendance(
            device,
            start_date,
            end_date,
            limit,
        )
        result_queue.put({
            'success': True,
            'processed': processed,
            'new_records': new_records,
            'duplicates': duplicates,
        })
    except Exception as exc:
        result_queue.put({
            'success': False,
            'error': str(exc),
        })
    finally:
        close_old_connections()


class Command(BaseCommand):
    help = 'Daily attendance fetch from all devices (one by one) - Fixed version'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=10,
            help='Number of days to fetch (default: 10)'
        )
        parser.add_argument(
            '--device',
            type=str,
            help='Fetch from specific device by name'
        )
        parser.add_argument(
            '--start-date',
            type=str,
            help='Start date for fetch range (YYYY-MM-DD)'
        )
        parser.add_argument(
            '--end-date',
            type=str,
            help='End date for fetch range (YYYY-MM-DD)'
        )
        parser.add_argument(
            '--show-summary',
            action='store_true',
            help='Show summary of fetched data'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=1000,
            help='Limit number of records to process per device (default: 1000)'
        )
        parser.add_argument(
            '--device-timeout',
            type=int,
            default=60,
            help='Maximum seconds allowed for one device fetch before skipping it (default: 60)'
        )
    
    def handle(self, *args, **options):
        if not ZK_AVAILABLE:
            self.stdout.write(
                self.style.ERROR("pyzk library not available. Install with: pip install pyzk")
            )
            return
        
        # Disable attendance signals to prevent Redis broadcasting
        post_save.disconnect(attendance_saved, sender=Attendance)
        
        days = options['days']
        device_name = options['device']
        start_date_option = options.get('start_date')
        end_date_option = options.get('end_date')
        show_summary = options['show_summary']
        limit = options['limit']
        device_timeout = options['device_timeout']
        
        self.stdout.write(
            self.style.SUCCESS(f" Starting daily attendance fetch (last {days} days)")
        )
        self.stdout.write("📡 Redis/WebSocket broadcasting disabled for faster processing")
        
        # Get devices to process
        devices = self.get_devices(device_name)
        if not devices:
            self.stdout.write(
                self.style.WARNING("No active devices found")
            )
            post_save.connect(attendance_saved, sender=Attendance)
            return
        
        # Calculate date range
        if start_date_option and end_date_option:
            try:
                start_date = timezone.make_aware(
                    datetime.strptime(start_date_option, '%Y-%m-%d'),
                    timezone.get_current_timezone()
                )
                end_date = timezone.make_aware(
                    datetime.strptime(end_date_option, '%Y-%m-%d').replace(hour=23, minute=59, second=59),
                    timezone.get_current_timezone()
                )
                if end_date < start_date:
                    raise ValueError('End date must be after start date')
            except ValueError as exc:
                self.stdout.write(self.style.ERROR(f"Invalid date range: {exc}"))
                post_save.connect(attendance_saved, sender=Attendance)
                return
        else:
            end_date = timezone.now()
            start_date = end_date - timedelta(days=days)
        
        self.stdout.write(f"📅 Date range: {start_date.date()} to {end_date.date()}")
        self.stdout.write(f" Processing {len(devices)} devices...\n")
        
        total_processed = 0
        total_new_records = 0
        total_duplicates = 0
        
        # Process each device one by one
        for i, device in enumerate(devices, 1):
            self.stdout.write(
                self.style.SUCCESS(f" [{i}/{len(devices)}] Processing: {device.name}")
            )
            
            try:
                # Ensure fresh database connection for each device
                connection.close()
                
                processed, new_records, duplicates = self.fetch_device_attendance_with_guard(
                    device, start_date, end_date, limit, device_timeout
                )
                
                total_processed += processed
                total_new_records += new_records
                total_duplicates += duplicates
                
                self.stdout.write(
                    f"   {device.name}: {processed} processed, {new_records} new, {duplicates} duplicates"
                )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"   {device.name}: Error - {str(e)}")
                )
                # Close connection on error
                connection.close()
            
            self.stdout.write("")  # Empty line for readability
        
        # Final summary
        self.stdout.write(
            self.style.SUCCESS(" Daily Fetch Summary:")
        )
        self.stdout.write(f"   Devices processed: {len(devices)}")
        self.stdout.write(f"   Total records processed: {total_processed}")
        self.stdout.write(f"   New records created: {total_new_records}")
        self.stdout.write(f"   Duplicates prevented: {total_duplicates}")
        
        if show_summary:
            try:
                self.show_recent_attendance(days)
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f"Could not show summary: {str(e)}")
                )
        
        # Re-enable signals
        post_save.connect(attendance_saved, sender=Attendance)
    
    def get_devices(self, device_name=None):
        """Get devices to process"""
        queryset = Device.objects.filter(is_active=True, device_type='zkteco')
        
        if device_name:
            queryset = queryset.filter(name__icontains=device_name)
        
        return list(queryset)

    def fetch_device_attendance_with_guard(self, device, start_date, end_date, limit, device_timeout):
        """Fetch one device with a hard timeout, then continue with the next device."""
        start_method = 'fork' if 'fork' in multiprocessing.get_all_start_methods() else 'spawn'
        ctx = multiprocessing.get_context(start_method)
        result_queue = ctx.Queue(maxsize=1)
        process = ctx.Process(
            target=_run_daily_device_fetch_worker,
            args=(device.id, start_date, end_date, limit, result_queue),
            daemon=True,
        )

        process.start()
        process.join(device_timeout)

        if process.is_alive():
            self.stdout.write(
                self.style.ERROR(
                    f"   {device.name}: timed out after {device_timeout}s, skipping and continuing"
                )
            )
            process.terminate()
            process.join(timeout=5)
            if process.is_alive():
                process.kill()
                process.join(timeout=2)
            result_queue.close()
            connection.close()
            return 0, 0, 0

        result = None
        try:
            result = result_queue.get(timeout=1)
        except Exception:
            pass
        finally:
            result_queue.close()
            connection.close()

        if not result:
            raise Exception("Device worker ended without a result")

        if not result.get('success'):
            raise Exception(result.get('error', 'Unknown device worker error'))

        return (
            result.get('processed', 0),
            result.get('new_records', 0),
            result.get('duplicates', 0),
        )
    
    def fetch_device_attendance(self, device, start_date, end_date, limit=1000):
        """Fetch attendance from a single device with limit"""
        processed = 0
        new_records = 0
        duplicates = 0
        conn = None
        
        try:
            # Connect to device
            zk = ZK(device.ip_address, port=device.port, timeout=10)
            conn = zk.connect()
            
            if not conn:
                raise Exception(f"Failed to connect to {device.ip_address}:{device.port}")
            
            self.stdout.write(f"   🔗 Connected to {device.name}")
            
            # Get all attendance data
            attendance_logs = conn.get_attendance()
            self.stdout.write(f"    Found {len(attendance_logs)} total logs")
            
            # Filter to date range and limit
            recent_logs = []
            for log in attendance_logs:
                # Make timestamp timezone-aware
                log_timestamp = log.timestamp
                if timezone.is_naive(log_timestamp):
                    log_timestamp = timezone.make_aware(log_timestamp, timezone.get_current_timezone())
                
                if start_date <= log_timestamp <= end_date:
                    recent_logs.append(log)
                    if len(recent_logs) >= limit:
                        break  # Limit processing
            
            self.stdout.write(f"   📅 Found {len(recent_logs)} logs in date range (limited to {limit})")
            
            # Process logs in batches
            batch_size = 50
            for i in range(0, len(recent_logs), batch_size):
                batch = recent_logs[i:i + batch_size]
                batch_processed, batch_new, batch_duplicates = self.process_batch(batch, device)
                
                processed += batch_processed
                new_records += batch_new
                duplicates += batch_duplicates
                
                # Show progress
                if i % (batch_size * 2) == 0:
                    self.stdout.write(f"    Progress: {i}/{len(recent_logs)} records processed")
            
        except Exception as e:
            raise Exception(f"Device error: {str(e)}")
        finally:
            if conn:
                try:
                    conn.disconnect()
                    self.stdout.write(f"   Disconnected from {device.name}")
                except Exception as disconnect_error:
                    self.stdout.write(
                        self.style.WARNING(f"   Disconnect warning for {device.name}: {disconnect_error}")
                    )
            connection.close()
        
        return processed, new_records, duplicates
    
    def process_batch(self, logs, device):
        """Process a batch of attendance logs"""
        processed = 0
        new_records = 0
        duplicates = 0
        
        for log in logs:
            try:
                # Skip invalid logs
                if not hasattr(log, 'user_id') or not hasattr(log, 'timestamp'):
                    continue
                
                # Make timestamp timezone-aware
                timestamp = log.timestamp
                if timezone.is_naive(timestamp):
                    timestamp = timezone.make_aware(timestamp, timezone.get_current_timezone())
                
                # Save raw punch first, then derive final attendance through shared safety rules.
                save_result = self.save_attendance_record(log, timestamp, device)
                if save_result in ['new', 'unmatched']:
                    new_records += 1
                elif save_result == 'duplicate':
                    duplicates += 1
                
                processed += 1
                
            except Exception as e:
                if "MySQL server has gone away" in str(e) or "ConnectionResetError" in str(e):
                    connection.close()
                    connection.ensure_connection()
                    continue
                elif str(e) != "(0, '')":
                    self.stdout.write(f"   ⚠️  Error processing log: {str(e)}")
        
        return processed, new_records, duplicates
    
    def save_attendance_record(self, log, timestamp, device):
        """Save raw punch first, then update final attendance through shared safety rules."""
        try:
            # Ensure database connection is alive
            connection.ensure_connection()

            _raw_log, created, result = record_raw_punch(
                device=device,
                biometric_id=str(log.user_id),
                device_user_id=str(getattr(log, 'uid', None) or log.user_id),
                employee_id=str(getattr(log, 'employee_id', '') or ''),
                punch_time=timestamp,
                punch_type='out' if getattr(log, 'status', 0) == 1 else 'in',
                source='zkteco_fetch',
                raw_payload={
                    'user_id': str(log.user_id),
                    'uid': getattr(log, 'uid', None),
                    'status': getattr(log, 'status', None),
                    'timestamp': timestamp.isoformat(),
                    'source_command': 'daily_attendance_fetch_fixed',
                },
            )
            if result == 'duplicate':
                return 'duplicate'
            if result == 'unmatched':
                self.stdout.write(
                    self.style.WARNING(
                        f"   Unmatched biometric ID {log.user_id} on {device.name} at {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                )
                return 'unmatched'
            return 'new' if created else 'duplicate'
                    
        except Exception as e:
            self.stdout.write(f"   ⚠️  Error saving record: {str(e)}")
            return 'error'
    
    def show_recent_attendance(self, days):
        """Show summary of recent attendance records"""
        self.stdout.write(f"\n📋 Recent Attendance Records (Last {days} Days):")
        
        try:
            end_date = timezone.now()
            start_date = end_date - timedelta(days=days)
            
            recent_attendance = Attendance.objects.filter(
                date__gte=start_date.date(),
                date__lte=end_date.date()
            ).order_by('-date', '-check_in_time')[:10]
            
            count = 0
            for att in recent_attendance:
                try:
                    check_in = att.check_in_time.strftime('%H:%M:%S') if att.check_in_time else 'None'
                    check_out = att.check_out_time.strftime('%H:%M:%S') if att.check_out_time else 'None'
                    self.stdout.write(f"   {att.user.get_full_name()} on {att.date}: {check_in} - {check_out}")
                    count += 1
                except Exception as e:
                    self.stdout.write(f"   Error displaying record: {str(e)}")
            
            if count == 0:
                self.stdout.write("   No recent attendance records found")
                
        except Exception as e:
            self.stdout.write(f"   Error fetching attendance summary: {str(e)}")
