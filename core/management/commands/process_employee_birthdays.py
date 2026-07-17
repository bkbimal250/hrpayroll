from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_date

from core.birthday_notifications import process_daily_employee_birthdays


class Command(BaseCommand):
    help = 'Process employee birthday notifications.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show planned deliveries without writes.')
        parser.add_argument('--date', help='Testing date in YYYY-MM-DD format.')
        parser.add_argument('--employee-id', help='Limit processing to one employee_id.')

    def handle(self, *args, **options):
        for_date = None
        if options.get('date'):
            for_date = parse_date(options['date'])
            if not for_date:
                raise CommandError('--date must be in YYYY-MM-DD format.')

        summary = process_daily_employee_birthdays(
            for_date=for_date,
            dry_run=options['dry_run'],
            employee_id=options.get('employee_id'),
        )

        self.stdout.write(self.style.SUCCESS('Birthday processing completed.'))
        for key, value in summary.items():
            self.stdout.write(f'{key}: {value}')
