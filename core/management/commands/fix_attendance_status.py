from django.core.management.base import BaseCommand
from core.models import Attendance
from django.db import transaction


class Command(BaseCommand):
    help = 'Fix attendance status to only show present or absent (not half_day)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update without confirmation',
        )

    def handle(self, *args, **options):
        if not options['force']:
            self.stdout.write(
                self.style.WARNING(
                    'This will update all attendance records. Use --force to proceed.'
                )
            )
            return

        try:
            with transaction.atomic():
                # Get all attendance records with half_day status
                half_day_records = Attendance.objects.filter(status='half_day')
                count = half_day_records.count()
                
                if count == 0:
                    self.stdout.write(
                        self.style.SUCCESS('No records with half_day status found.')
                    )
                    return

                self.stdout.write(f'Found {count} records with half_day status. Updating...')
                
                # Update status to 'present' for all half_day records
                # The day_status will remain 'half_day' to show working hours info
                updated = half_day_records.update(status='present')
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully updated {updated} attendance records. '
                        f'Status is now "present" and day_status shows "half_day" for working hours.'
                    )
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error updating attendance records: {str(e)}')
            )
            raise
