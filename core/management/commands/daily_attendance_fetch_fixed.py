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

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'attendance_system.settings')
django.setup()

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction, connection
from core.models import Device, CustomUser, Attendance

# Disable signals to prevent Redis broadcasting
from django.db.models.signals import post_save
from core.signals import attendance_saved

try:
    from zk import ZK
    ZK_AVAILABLE = True
except ImportError:
    ZK_AVAILABLE = False

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
        show_summary = options['show_summary']
        limit = options['limit']
        
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
            return
        
        # Calculate date range
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
                
                processed, new_records, duplicates = self.fetch_device_attendance(
                    device, start_date, end_date, limit
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
    
    def fetch_device_attendance(self, device, start_date, end_date, limit=1000):
        """Fetch attendance from a single device with limit"""
        processed = 0
        new_records = 0
        duplicates = 0
        
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
            
            conn.disconnect()
            self.stdout.write(f"   🔌 Disconnected from {device.name}")
            
        except Exception as e:
            raise Exception(f"Device error: {str(e)}")
        
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
                
                # Find user by biometric ID
                user = CustomUser.objects.filter(biometric_id=str(log.user_id)).first()
                if not user:
                    continue  # Skip unmapped users
                
                # Make timestamp timezone-aware
                timestamp = log.timestamp
                if timezone.is_naive(timestamp):
                    timestamp = timezone.make_aware(timestamp, timezone.get_current_timezone())
                
                # Save attendance record
                if self.save_attendance_record(user, timestamp, device):
                    new_records += 1
                else:
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
    
    def save_attendance_record(self, user, timestamp, device):
        """Save attendance record with proper check-in/check-out logic"""
        try:
            # Ensure database connection is alive
            connection.ensure_connection()
            
            with transaction.atomic():
                # Get or create attendance record for this user and date
                attendance, created = Attendance.objects.get_or_create(
                    user=user,
                    date=timestamp.date(),
                    defaults={
                        'check_in_time': timestamp,
                        'status': 'present',
                        'device': device
                    }
                )
                
                if created:
                    # First scan of the day - this is the check-in
                    return True
                else:
                    # Update existing record
                    if attendance.check_in_time:
                        # Make existing check-in time timezone-aware
                        check_in_time = attendance.check_in_time
                        if timezone.is_naive(check_in_time):
                            check_in_time = timezone.make_aware(check_in_time, timezone.get_current_timezone())
                        
                        if timestamp < check_in_time:
                            # Earlier timestamp - update check-in time
                            attendance.check_in_time = timestamp
                            attendance.save()
                        elif timestamp > check_in_time:
                            # Later timestamp - update check-out time
                            if not attendance.check_out_time:
                                attendance.check_out_time = timestamp
                                attendance.save()
                            else:
                                # Make existing checkout time timezone-aware
                                existing_checkout = attendance.check_out_time
                                if timezone.is_naive(existing_checkout):
                                    existing_checkout = timezone.make_aware(existing_checkout, timezone.get_current_timezone())
                                
                                if timestamp > existing_checkout:
                                    attendance.check_out_time = timestamp
                                    attendance.save()
                    else:
                        # No check-in time exists - this should be the check-in
                        attendance.check_in_time = timestamp
                        attendance.status = 'present'
                        attendance.save()
                    
                    return True
                    
        except Exception as e:
            self.stdout.write(f"   ⚠️  Error saving record: {str(e)}")
            return False
    
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
