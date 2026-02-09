#!/usr/bin/env python3
"""
View and manage existing attendance data
This command works with data already in the database without connecting to devices
"""

import os
import sys
import django
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'attendance_system.settings')
django.setup()

from core.models import CustomUser, Attendance, Device

class Command(BaseCommand):
    help = 'View and manage existing attendance data'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--today',
            action='store_true',
            help='Show today\'s attendance'
        )
        parser.add_argument(
            '--date',
            type=str,
            help='Show attendance for specific date (YYYY-MM-DD)'
        )
        parser.add_argument(
            '--user',
            type=str,
            help='Show attendance for specific user (username or employee_id)'
        )
        parser.add_argument(
            '--summary',
            action='store_true',
            help='Show attendance summary'
        )
        parser.add_argument(
            '--recent',
            type=int,
            default=10,
            help='Show recent N attendance records (default: 10)'
        )
        
    def handle(self, *args, **options):
        if options['today']:
            self.show_todays_attendance()
        elif options['date']:
            self.show_attendance_for_date(options['date'])
        elif options['user']:
            self.show_user_attendance(options['user'])
        elif options['summary']:
            self.show_attendance_summary()
        else:
            self.show_recent_attendance(options['recent'])
            
    def show_todays_attendance(self):
        """Show today's attendance records"""
        today = timezone.now().date()
        attendance_records = Attendance.objects.filter(date=today).order_by('-check_in_time')
        
        self.stdout.write(f"\n📅 Today's Attendance ({today})")
        self.stdout.write("=" * 60)
        
        if not attendance_records:
            self.stdout.write("No attendance records for today.")
            return
            
        for record in attendance_records:
            check_in = record.check_in_time.strftime('%H:%M:%S') if record.check_in_time else 'N/A'
            check_out = record.check_out_time.strftime('%H:%M:%S') if record.check_out_time else 'N/A'
            status = "Present" if record.status == 'present' else f"{record.status}"
            
            self.stdout.write(f"{record.user.get_full_name():<25} | {check_in} - {check_out} | {status}")
            
    def show_attendance_for_date(self, date_str):
        """Show attendance for a specific date"""
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            self.stdout.write("Invalid date format. Use YYYY-MM-DD")
            return
            
        attendance_records = Attendance.objects.filter(date=target_date).order_by('-check_in_time')
        
        self.stdout.write(f"\n📅 Attendance for {target_date}")
        self.stdout.write("=" * 60)
        
        if not attendance_records:
            self.stdout.write(f"No attendance records for {target_date}.")
            return
            
        for record in attendance_records:
            check_in = record.check_in_time.strftime('%H:%M:%S') if record.check_in_time else 'N/A'
            check_out = record.check_out_time.strftime('%H:%M:%S') if record.check_out_time else 'N/A'
            status = "Present" if record.status == 'present' else f"{record.status}"
            
            self.stdout.write(f"{record.user.get_full_name():<25} | {check_in} - {check_out} | {status}")
            
    def show_user_attendance(self, user_identifier):
        """Show attendance for a specific user"""
        # Try to find user by username or employee_id
        user = CustomUser.objects.filter(
            Q(username=user_identifier) | Q(employee_id=user_identifier)
        ).first()
        
        if not user:
            self.stdout.write(f"User '{user_identifier}' not found.")
            return
            
        # Get recent attendance records for this user
        attendance_records = Attendance.objects.filter(
            user=user
        ).order_by('-date', '-check_in_time')[:20]
        
        self.stdout.write(f"\n👤 Attendance for {user.get_full_name()} ({user.username})")
        self.stdout.write("=" * 60)
        
        if not attendance_records:
            self.stdout.write("No attendance records found for this user.")
            return
            
        for record in attendance_records:
            check_in = record.check_in_time.strftime('%H:%M:%S') if record.check_in_time else 'N/A'
            check_out = record.check_out_time.strftime('%H:%M:%S') if record.check_out_time else 'N/A'
            status = "Present" if record.status == 'present' else f"{record.status}"
            
            self.stdout.write(f"{record.date} | {check_in} - {check_out} | {status}")
            
    def show_attendance_summary(self):
        """Show attendance summary statistics"""
        total_records = Attendance.objects.count()
        total_users = CustomUser.objects.count()
        active_users = CustomUser.objects.filter(is_active=True).count()
        
        # Today's stats
        today = timezone.now().date()
        today_present = Attendance.objects.filter(date=today, status='present').count()
        today_absent = total_users - today_present
        
        # This week's stats
        week_start = today - timedelta(days=today.weekday())
        week_records = Attendance.objects.filter(
            date__gte=week_start,
            date__lte=today
        ).count()
        
        self.stdout.write("\n Attendance Summary")
        self.stdout.write("=" * 40)
        self.stdout.write(f"Total Users: {total_users}")
        self.stdout.write(f"Active Users: {active_users}")
        self.stdout.write(f"Total Attendance Records: {total_records}")
        self.stdout.write(f"Today Present: {today_present}")
        self.stdout.write(f"Today Absent: {today_absent}")
        self.stdout.write(f"This Week Records: {week_records}")
        
    def show_recent_attendance(self, count):
        """Show recent attendance records"""
        recent_records = Attendance.objects.order_by('-date', '-check_in_time')[:count]
        
        self.stdout.write(f"\n📋 Recent {count} Attendance Records")
        self.stdout.write("=" * 80)
        
        if not recent_records:
            self.stdout.write("No attendance records found.")
            return
            
        for record in recent_records:
            check_in = record.check_in_time.strftime('%H:%M:%S') if record.check_in_time else 'N/A'
            check_out = record.check_out_time.strftime('%H:%M:%S') if record.check_out_time else 'N/A'
            status = "Present" if record.status == 'present' else f"{record.status}"
            device = record.device.name if record.device else 'N/A'
            
            self.stdout.write(f"{record.date} | {record.user.get_full_name():<25} | {check_in} - {check_out} | {status} | {device}")
