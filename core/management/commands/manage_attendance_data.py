#!/usr/bin/env python3
"""
Manage existing attendance data without connecting to devices
This command provides various operations on existing attendance data
"""

import os
import sys
import django
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q, Count, Avg
from django.db import transaction

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'attendance_system.settings')
django.setup()

from core.models import CustomUser, Attendance, Device

class Command(BaseCommand):
    help = 'Manage existing attendance data'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--list-users',
            action='store_true',
            help='List all users with their biometric IDs'
        )
        parser.add_argument(
            '--attendance-stats',
            action='store_true',
            help='Show detailed attendance statistics'
        )
        parser.add_argument(
            '--fix-missing-checkouts',
            action='store_true',
            help='Fix records with missing check-out times'
        )
        parser.add_argument(
            '--export-today',
            action='store_true',
            help='Export today\'s attendance data'
        )
        parser.add_argument(
            '--cleanup-duplicates',
            action='store_true',
            help='Clean up duplicate attendance records'
        )
        
    def handle(self, *args, **options):
        if options['list_users']:
            self.list_users()
        elif options['attendance_stats']:
            self.show_attendance_stats()
        elif options['fix_missing_checkouts']:
            self.fix_missing_checkouts()
        elif options['export_today']:
            self.export_todays_attendance()
        elif options['cleanup_duplicates']:
            self.cleanup_duplicates()
        else:
            self.show_help()
            
    def list_users(self):
        """List all users with their biometric IDs"""
        users = CustomUser.objects.all().order_by('username')
        
        self.stdout.write("\n👥 Users in Database")
        self.stdout.write("=" * 80)
        self.stdout.write(f"{'Username':<20} {'Full Name':<25} {'Biometric ID':<12} {'Employee ID':<12} {'Active'}")
        self.stdout.write("-" * 80)
        
        for user in users:
            full_name = user.get_full_name() or user.username
            biometric_id = user.biometric_id or 'N/A'
            employee_id = user.employee_id or 'N/A'
            active = '✅' if user.is_active else '❌'
            
            self.stdout.write(f"{user.username:<20} {full_name:<25} {biometric_id:<12} {employee_id:<12} {active}")
            
    def show_attendance_stats(self):
        """Show detailed attendance statistics"""
        total_records = Attendance.objects.count()
        total_users = CustomUser.objects.count()
        active_users = CustomUser.objects.filter(is_active=True).count()
        
        # Today's stats
        today = timezone.now().date()
        today_records = Attendance.objects.filter(date=today)
        today_present = today_records.filter(status='present').count()
        today_absent = active_users - today_present
        
        # This week's stats
        week_start = today - timedelta(days=today.weekday())
        week_records = Attendance.objects.filter(
            date__gte=week_start,
            date__lte=today
        )
        
        # This month's stats
        month_start = today.replace(day=1)
        month_records = Attendance.objects.filter(
            date__gte=month_start,
            date__lte=today
        )
        
        # Device statistics
        device_stats = Attendance.objects.values('device__name').annotate(
            count=Count('id')
        ).order_by('-count')
        
        self.stdout.write("\n📊 Detailed Attendance Statistics")
        self.stdout.write("=" * 50)
        self.stdout.write(f"Total Users: {total_users}")
        self.stdout.write(f"Active Users: {active_users}")
        self.stdout.write(f"Total Attendance Records: {total_records}")
        self.stdout.write(f"\n📅 Today ({today})")
        self.stdout.write(f"  Present: {today_present}")
        self.stdout.write(f"  Absent: {today_absent}")
        self.stdout.write(f"  Records: {today_records.count()}")
        self.stdout.write(f"\n📅 This Week")
        self.stdout.write(f"  Records: {week_records.count()}")
        self.stdout.write(f"\n📅 This Month")
        self.stdout.write(f"  Records: {month_records.count()}")
        
        if device_stats:
            self.stdout.write(f"\n📱 Device Statistics")
            for stat in device_stats:
                device_name = stat['device__name'] or 'Unknown Device'
                self.stdout.write(f"  {device_name}: {stat['count']} records")
                
    def fix_missing_checkouts(self):
        """Fix records with missing check-out times"""
        # Find records with check-in but no check-out
        incomplete_records = Attendance.objects.filter(
            check_in_time__isnull=False,
            check_out_time__isnull=True,
            date__lt=timezone.now().date()  # Only fix past records
        )
        
        self.stdout.write(f"\n🔧 Fixing {incomplete_records.count()} records with missing check-outs...")
        
        fixed_count = 0
        for record in incomplete_records:
            # Set check-out time to end of working day (18:00) if missing
            if not record.check_out_time:
                # Create a datetime for end of day
                end_of_day = timezone.make_aware(
                    datetime.combine(record.date, datetime.min.time().replace(hour=18))
                )
                record.check_out_time = end_of_day
                record.save()
                fixed_count += 1
                
        self.stdout.write(f"✅ Fixed {fixed_count} records")
        
    def export_todays_attendance(self):
        """Export today's attendance data"""
        today = timezone.now().date()
        attendance_records = Attendance.objects.filter(date=today).order_by('user__username')
        
        self.stdout.write(f"\n📤 Today's Attendance Export ({today})")
        self.stdout.write("=" * 80)
        
        if not attendance_records:
            self.stdout.write("No attendance records for today.")
            return
            
        # CSV-like format
        self.stdout.write("Username,Full Name,Check-in,Check-out,Status,Device")
        for record in attendance_records:
            check_in = record.check_in_time.strftime('%H:%M:%S') if record.check_in_time else 'N/A'
            check_out = record.check_out_time.strftime('%H:%M:%S') if record.check_out_time else 'N/A'
            device = record.device.name if record.device else 'N/A'
            
            self.stdout.write(f"{record.user.username},{record.user.get_full_name()},{check_in},{check_out},{record.status},{device}")
            
    def cleanup_duplicates(self):
        """Clean up duplicate attendance records"""
        # Find potential duplicates (same user, same date, multiple records)
        duplicates = Attendance.objects.values('user', 'date').annotate(
            count=Count('id')
        ).filter(count__gt=1)
        
        self.stdout.write(f"\n🧹 Found {duplicates.count()} potential duplicate groups...")
        
        cleaned_count = 0
        for duplicate in duplicates:
            user_id = duplicate['user']
            date = duplicate['date']
            
            # Get all records for this user and date
            records = Attendance.objects.filter(user_id=user_id, date=date).order_by('check_in_time')
            
            if records.count() > 1:
                # Keep the first record, delete the rest
                first_record = records.first()
                records.exclude(id=first_record.id).delete()
                cleaned_count += records.count() - 1
                
        self.stdout.write(f"✅ Cleaned up {cleaned_count} duplicate records")
        
    def show_help(self):
        """Show help information"""
        self.stdout.write("\n📋 Attendance Data Management Commands")
        self.stdout.write("=" * 50)
        self.stdout.write("--list-users              List all users with biometric IDs")
        self.stdout.write("--attendance-stats        Show detailed statistics")
        self.stdout.write("--fix-missing-checkouts   Fix records missing check-out times")
        self.stdout.write("--export-today            Export today's attendance data")
        self.stdout.write("--cleanup-duplicates      Remove duplicate records")
        self.stdout.write("\nExample usage:")
        self.stdout.write("python manage.py manage_attendance_data --list-users")
        self.stdout.write("python manage.py manage_attendance_data --attendance-stats")
