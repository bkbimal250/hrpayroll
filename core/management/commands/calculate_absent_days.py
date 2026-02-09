from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, date, timedelta
from core.models import Attendance, CustomUser, WorkingHoursSettings
import calendar


class Command(BaseCommand):
    help = 'Calculate and create absent records for days when users did not check in'

    def add_arguments(self, parser):
        parser.add_argument(
            '--month',
            type=str,
            help='Month to calculate (YYYY-MM format, e.g., 2024-01)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recalculation even if records exist',
        )

    def handle(self, *args, **options):
        # Determine the month to process
        if options['month']:
            try:
                year, month = map(int, options['month'].split('-'))
                target_date = date(year, month, 1)
            except ValueError:
                self.stdout.write(
                    self.style.ERROR('Invalid month format. Use YYYY-MM (e.g., 2024-01)')
                )
                return
        else:
            # Default to current month
            now = timezone.now()
            target_date = date(now.year, now.month, 1)

        self.stdout.write(
            self.style.SUCCESS(f'Calculating absent days for {target_date.strftime("%B %Y")}')
        )

        # Get all working days in the month (Monday to Friday)
        working_days = self.get_working_days(target_date.year, target_date.month)
        
        # Get all active users
        users = CustomUser.objects.filter(is_active=True)
        
        total_absent_created = 0
        total_absent_updated = 0

        for user in users:
            if not user.office:
                continue

            self.stdout.write(f'Processing user: {user.get_full_name()} ({user.office.name})')
            
            # Get working hours settings for the user's office
            try:
                settings = WorkingHoursSettings.objects.get(office=user.office)
            except WorkingHoursSettings.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f'No working hours settings found for {user.office.name}')
                )
                continue

            for working_day in working_days:
                # Check if attendance record exists for this day
                existing_attendance = Attendance.objects.filter(
                    user=user,
                    date=working_day
                ).first()

                if existing_attendance:
                    # Update existing record if it's marked as absent but should be recalculated
                    if options['force'] and existing_attendance.status == 'absent':
                        existing_attendance.calculate_attendance_status()
                        existing_attendance.save()
                        total_absent_updated += 1
                        self.stdout.write(f'  Updated: {working_day} - {existing_attendance.status}')
                    continue

                # Create absent record for this working day
                absent_attendance = Attendance(
                    user=user,
                    date=working_day,
                    check_in_time=None,
                    check_out_time=None,
                    total_hours=None,
                    status='absent',
                    day_status='absent',
                    is_late=False,
                    late_minutes=0,
                    device=None,
                    notes='Automatically marked as absent'
                )
                
                # Calculate status (this will set it to absent since no check-in time)
                absent_attendance.calculate_attendance_status()
                absent_attendance.save()
                
                total_absent_created += 1
                self.stdout.write(f'  Created absent: {working_day}')

        self.stdout.write(
            self.style.SUCCESS(
                f'Completed! Created {total_absent_created} absent records, '
                f'Updated {total_absent_updated} existing records'
            )
        )

    def get_working_days(self, year, month):
        """Get all working days (Monday to Friday) in the given month"""
        working_days = []
        
        # Get the first day of the month
        first_day = date(year, month, 1)
        
        # Get the last day of the month
        last_day = date(year, month, calendar.monthrange(year, month)[1])
        
        current_date = first_day
        
        while current_date <= last_day:
            # Monday = 0, Tuesday = 1, ..., Friday = 4
            if current_date.weekday() < 5:  # Monday to Friday
                working_days.append(current_date)
            current_date += timedelta(days=1)
        
        return working_days
