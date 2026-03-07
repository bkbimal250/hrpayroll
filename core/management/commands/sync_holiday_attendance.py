from django.core.management.base import BaseCommand
from core.models import Attendance
from coreapp.models import Holiday


class Command(BaseCommand):
    help = (
        'Sync attendance records on holiday dates:\n'
        '  - Employee came (has check-in)  → Present\n'
        '  - Employee did NOT come (no check-in) → Holiday'
    )

    def handle(self, *args, **options):
        self.stdout.write('Fetching all holidays...')
        holidays = Holiday.objects.all()
        self.stdout.write(f'Found {holidays.count()} holidays.\n')

        total_to_holiday = 0
        total_to_present = 0

        for holiday in holidays:
            # Records with NO check-in on this holiday → mark as holiday
            to_holiday = Attendance.objects.filter(
                date=holiday.date,
                check_in_time__isnull=True
            ).exclude(status='holiday')

            count_holiday = to_holiday.update(status='holiday', day_status='holiday')

            # Records WITH check-in on this holiday → mark as present
            to_present = Attendance.objects.filter(
                date=holiday.date,
                check_in_time__isnull=False
            ).filter(status='holiday')

            count_present = to_present.update(status='present')

            if count_holiday or count_present:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  {holiday.date} ({holiday.name}): '
                        f'{count_holiday} → holiday, {count_present} → present'
                    )
                )
            else:
                self.stdout.write(
                    f'  {holiday.date} ({holiday.name}): no changes needed'
                )

            total_to_holiday += count_holiday
            total_to_present += count_present

        self.stdout.write(
            self.style.SUCCESS(
                f'\nDone! {total_to_holiday} records set to holiday, '
                f'{total_to_present} records set to present.'
            )
        )
