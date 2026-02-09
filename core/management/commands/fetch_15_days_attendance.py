#!/usr/bin/env python3
"""
Django management command to fetch and process attendance data from the last 15 days
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
from django.db import transaction
from core.models import Device, CustomUser, Attendance

try:
    from zk import ZK
    ZK_AVAILABLE = True
except ImportError:
    ZK_AVAILABLE = False

class Command(BaseCommand):
    help = 'Fetch and process attendance data from the last 15 days with duplicate removal'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--remove-duplicates',
            action='store_true',
            help='Remove duplicate attendance records from database'
        )
        parser.add_argument(
            '--show-summary',
            action='store_true',
            help='Show summary of recent attendance records'
        )
    
    def handle(self, *args, **options):
        if not ZK_AVAILABLE:
            self.stdout.write(
                self.style.ERROR("pyzk library not available. Install with: pip install pyzk")
            )
            return
        
        self.stdout.write("Starting 15-day attendance data fetch...")
        
        # Fetch 15 days of data
        self.fetch_15_days_attendance()
        
        # Remove duplicates if requested
        if options['remove_duplicates']:
            self.remove_duplicates()
        
        # Show summary if requested
        if options['show_summary']:
            self.show_summary()
    
    def create_attendance_hash(self, device_id, user_id, timestamp, status):
        """Create a unique hash for attendance record to prevent duplicates"""
        hash_data = f"{device_id}_{user_id}_{timestamp}_{status}"
        return hashlib.md5(hash_data.encode()).hexdigest()
    
    def fetch_15_days_attendance(self):
        """Fetch and process attendance data from the last 15 days"""
        
        # Calculate date range
        end_date = timezone.now()
        start_date = end_date - timedelta(days=15)
        
        self.stdout.write(f"Date range: {start_date.date()} to {end_date.date()}")
        
        # Get active devices
        devices = Device.objects.filter(is_active=True)
        self.stdout.write(f"Found {devices.count()} active devices")
        
        total_processed = 0
        total_duplicates = 0
        total_new_records = 0
        
        # Store processed hashes to prevent duplicates
        processed_hashes = set()
        
        for device in devices:
            self.stdout.write(f"\nProcessing device: {device.name} ({device.device_type})")
            
            if device.device_type == 'zkteco':
                try:
                    # Connect to device
                    zk = ZK(device.ip_address, port=device.port, timeout=10)
                    conn = zk.connect()
                    
                    if conn:
                        self.stdout.write(f"Connected to {device.name}")
                        
                        # Get all attendance data
                        attendance_logs = conn.get_attendance()
                        self.stdout.write(f"Found {len(attendance_logs)} total attendance logs")
                        
                        # Filter to last 15 days
                        recent_logs = []
                        for log in attendance_logs:
                            # Make timestamp timezone-aware
                            log_timestamp = log.timestamp
                            if timezone.is_naive(log_timestamp):
                                log_timestamp = timezone.make_aware(log_timestamp, timezone.get_current_timezone())
                            
                            if start_date <= log_timestamp <= end_date:
                                recent_logs.append(log)
                        
                        self.stdout.write(f"Found {len(recent_logs)} logs in the last 15 days")
                        
                        # Process logs
                        device_processed = 0
                        device_duplicates = 0
                        device_new_records = 0
                        
                        for log in recent_logs:
                            try:
                                # Create unique hash
                                record_hash = self.create_attendance_hash(
                                    device.id, 
                                    log.user_id, 
                                    log.timestamp, 
                                    log.status
                                )
                                
                                # Check for duplicates
                                if record_hash in processed_hashes:
                                    device_duplicates += 1
                                    continue
                                
                                # Find user by biometric ID
                                user = CustomUser.objects.filter(biometric_id=str(log.user_id)).first()
                                if not user:
                                    self.stdout.write(
                                        self.style.WARNING(f"User with biometric ID {log.user_id} not found")
                                    )
                                    continue
                                
                                # Make timestamp timezone-aware
                                timestamp = log.timestamp
                                if timezone.is_naive(timestamp):
                                    timestamp = timezone.make_aware(timestamp, timezone.get_current_timezone())
                                
                                # Process attendance record
                                if self.save_attendance_record(user, timestamp, device):
                                    device_new_records += 1
                                    processed_hashes.add(record_hash)
                                
                                device_processed += 1
                                
                            except Exception as e:
                                self.stdout.write(
                                    self.style.ERROR(f"Error processing log: {str(e)}")
                                )
                        
                        self.stdout.write(
                            f"Device {device.name}: Processed {device_processed}, "
                            f"New records: {device_new_records}, Duplicates: {device_duplicates}"
                        )
                        
                        total_processed += device_processed
                        total_new_records += device_new_records
                        total_duplicates += device_duplicates
                        
                        conn.disconnect()
                        
                    else:
                        self.stdout.write(
                            self.style.ERROR(f"Failed to connect to {device.name}")
                        )
                        
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"Error with device {device.name}: {str(e)}")
                    )
        
        self.stdout.write(f"\nSummary:")
        self.stdout.write(f"Total processed: {total_processed}")
        self.stdout.write(f"New records created: {total_new_records}")
        self.stdout.write(f"Duplicates prevented: {total_duplicates}")
    
    def save_attendance_record(self, user, timestamp, device):
        """Save attendance record with proper check-in/check-out logic"""
        try:
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
                    self.stdout.write(
                        f"  -> Created: {user.get_full_name()} check-in at {timestamp.strftime('%H:%M:%S')}"
                    )
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
                            old_checkin = attendance.check_in_time
                            attendance.check_in_time = timestamp
                            attendance.save()
                            self.stdout.write(
                                f"  -> Updated check-in: {user.get_full_name()} from {old_checkin.strftime('%H:%M:%S')} to {timestamp.strftime('%H:%M:%S')}"
                            )
                        elif timestamp > check_in_time:
                            # Later timestamp - update check-out time
                            if not attendance.check_out_time:
                                attendance.check_out_time = timestamp
                                attendance.save()
                                self.stdout.write(
                                    f"  -> Set check-out: {user.get_full_name()} at {timestamp.strftime('%H:%M:%S')}"
                                )
                            else:
                                # Make existing checkout time timezone-aware
                                existing_checkout = attendance.check_out_time
                                if timezone.is_naive(existing_checkout):
                                    existing_checkout = timezone.make_aware(existing_checkout, timezone.get_current_timezone())
                                
                                if timestamp > existing_checkout:
                                    old_checkout = attendance.check_out_time
                                    attendance.check_out_time = timestamp
                                    attendance.save()
                                    self.stdout.write(
                                        f"  -> Updated check-out: {user.get_full_name()} from {old_checkout.strftime('%H:%M:%S')} to {timestamp.strftime('%H:%M:%S')}"
                                    )
                                else:
                                    # This scan is between check-in and check-out
                                    self.stdout.write(
                                        f"  -> Middle scan: {user.get_full_name()} at {timestamp.strftime('%H:%M:%S')} (ignored)"
                                    )
                    else:
                        # No check-in time exists - this should be the check-in
                        attendance.check_in_time = timestamp
                        attendance.status = 'present'
                        attendance.save()
                        self.stdout.write(
                            f"  -> Fixed check-in: {user.get_full_name()} at {timestamp.strftime('%H:%M:%S')}"
                        )
                    
                    return True
                    
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error saving attendance record: {str(e)}")
            )
            return False
    
    def remove_duplicates(self):
        """Remove duplicate attendance records from database"""
        self.stdout.write("\nChecking for duplicates in database...")
        
        # Get attendance records from last 15 days
        end_date = timezone.now()
        start_date = end_date - timedelta(days=15)
        
        attendance_records = Attendance.objects.filter(
            date__gte=start_date.date(),
            date__lte=end_date.date()
        ).order_by('user', 'date', 'check_in_time')
        
        self.stdout.write(f"Found {attendance_records.count()} attendance records in the last 15 days")
        
        # Group by user and date to find duplicates
        user_date_groups = {}
        for record in attendance_records:
            key = (record.user.id, record.date)
            if key not in user_date_groups:
                user_date_groups[key] = []
            user_date_groups[key].append(record)
        
        duplicates_found = 0
        duplicates_removed = 0
        
        for (user_id, date), records in user_date_groups.items():
            if len(records) > 1:
                duplicates_found += len(records) - 1
                self.stdout.write(
                    f"Found {len(records)} duplicate records for {records[0].user.get_full_name()} on {date}"
                )
                
                # Keep the first record, remove the rest
                for i, record in enumerate(records[1:], 1):
                    self.stdout.write(f"  -> Removing duplicate record {i+1}")
                    record.delete()
                    duplicates_removed += 1
        
        self.stdout.write(f"Duplicates found: {duplicates_found}")
        self.stdout.write(f"Duplicates removed: {duplicates_removed}")
    
    def show_summary(self):
        """Show summary of recent attendance records"""
        self.stdout.write("\nRecent Attendance Records (Last 15 Days):")
        
        end_date = timezone.now()
        start_date = end_date - timedelta(days=15)
        
        recent_attendance = Attendance.objects.filter(
            date__gte=start_date.date(),
            date__lte=end_date.date()
        ).order_by('-date', '-check_in_time')[:20]
        
        for att in recent_attendance:
            check_in = att.check_in_time.strftime('%H:%M:%S') if att.check_in_time else 'None'
            check_out = att.check_out_time.strftime('%H:%M:%S') if att.check_out_time else 'None'
            self.stdout.write(f"{att.user.get_full_name()} on {att.date}: {check_in} - {check_out}")
