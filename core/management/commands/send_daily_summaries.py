"""
Management command to send daily notification summaries
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import CustomUser
from core.email_service import EmailNotificationManager
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Send daily notification summaries to all users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--users',
            nargs='+',
            help='Send summaries to specific user IDs',
        )
        parser.add_argument(
            '--role',
            choices=['admin', 'manager', 'employee', 'accountant'],
            help='Send summaries to users with specific role',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be sent without actually sending emails',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting daily summary sending...')
        )
        
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No emails will be sent')
            )
        
        # Get users to send summaries to
        users = self.get_target_users(options)
        
        self.stdout.write(f'Found {users.count()} users to send summaries to')
        
        sent_count = 0
        failed_count = 0
        
        for user in users:
            if options['dry_run']:
                self.stdout.write(
                    f'Would send daily summary to {user.email} ({user.get_full_name()})'
                )
            else:
                try:
                    if EmailNotificationManager.send_daily_summary(user):
                        sent_count += 1
                        self.stdout.write(
                            f'Sent daily summary to {user.email} ({user.get_full_name()})'
                        )
                    else:
                        failed_count += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f'Failed to send daily summary to {user.email} ({user.get_full_name()})'
                            )
                        )
                except Exception as e:
                    failed_count += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f'Error sending daily summary to {user.email}: {str(e)}'
                        )
                    )
        
        if not options['dry_run']:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Daily summary sending completed! Sent: {sent_count}, Failed: {failed_count}'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('Dry run completed!')
            )

    def get_target_users(self, options):
        """Get users to send summaries to"""
        users = CustomUser.objects.filter(
            is_active=True,
            email__isnull=False
        ).exclude(email='')
        
        # Filter by specific users if provided
        if options['users']:
            users = users.filter(id__in=options['users'])
        
        # Filter by role if provided
        if options['role']:
            users = users.filter(role=options['role'])
        
        return users
