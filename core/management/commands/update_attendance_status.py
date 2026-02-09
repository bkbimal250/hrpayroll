#!/usr/bin/env python3
"""
Management command to update existing attendance records with new status fields
Run this command after adding the new fields to update existing data
"""

import os
import sys
import django
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'attendance_system.settings')
django.setup()

from core.models import Attendance, WorkingHoursSettings


class Command(BaseCommand):
    help = 'Update existing attendance records with new status fields'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update even if fields already exist',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        
        self.stdout.write(
            self.style.SUCCESS(' Starting attendance status update...')
        )
        
        # Check if new fields exist
        try:
            attendance = Attendance.objects.first()
            if hasattr(attendance, 'day_status') and not force:
                self.stdout.write(
                    self.style.WARNING(
                        'New fields already exist. Use --force to update anyway.'
                    )
                )
                return
        except Exception:
            pass
        
        # Get all attendance records
        attendances = Attendance.objects.all()
        total_count = attendances.count()
        
        if total_count == 0:
            self.stdout.write(
                self.style.WARNING('No attendance records found.')
            )
            return
        
        self.stdout.write(f'Found {total_count} attendance records to update')
        
        updated_count = 0
        errors = []
        
        if not dry_run:
            # Create default working hours settings for offices that don't have them
            self._create_default_working_hours()
        
        for attendance in attendances:
            try:
                if dry_run:
                    # Show what would be updated
                    old_status = attendance.status
                    old_total_hours = attendance.total_hours
                    
                    # Simulate the calculation
                    attendance.calculate_attendance_status()
                    
                    self.stdout.write(
                        f' {attendance.user.get_full_name()} - {attendance.date}: '
                        f'Status: {old_status} → {attendance.status}, '
                        f'Day Status: → {attendance.day_status}, '
                        f'Late: → {attendance.is_late}, '
                        f'Hours: {old_total_hours} → {attendance.total_hours}'
                    )
                else:
                    # Actually update the record
                    with transaction.atomic():
                        attendance.calculate_attendance_status()
                        attendance.save()
                        updated_count += 1
                        
                        if updated_count % 100 == 0:
                            self.stdout.write(f'Updated {updated_count}/{total_count} records...')
                            
            except Exception as e:
                error_msg = f'Error updating {attendance.id}: {str(e)}'
                errors.append(error_msg)
                self.stdout.write(
                    self.style.ERROR(f'{error_msg}')
                )
        
        # Summary
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Dry run completed. Would update {total_count} records.'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully updated {updated_count}/{total_count} attendance records!'
                )
            )
        
        if errors:
            self.stdout.write(
                self.style.WARNING(f'{len(errors)} errors occurred during update.')
            )
            for error in errors[:5]:  # Show first 5 errors
                self.stdout.write(f'   • {error}')
            if len(errors) > 5:
                self.stdout.write(f'   ... and {len(errors) - 5} more errors')
    
    def _create_default_working_hours(self):
        """Create default working hours settings for offices that don't have them"""
        from core.models import Office
        
        offices = Office.objects.all()
        created_count = 0
        
        for office in offices:
            if not WorkingHoursSettings.objects.filter(office=office).exists():
                WorkingHoursSettings.objects.create(
                    office=office,
                    standard_hours=9.0,
                    start_time='10:00:00',
                    end_time='19:00:00',
                    late_threshold=15,
                    half_day_threshold=300,  # 5 hours
                    late_coming_threshold='11:30:00'
                )
                created_count += 1
        
        if created_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'Created {created_count} default working hours settings')
            )
