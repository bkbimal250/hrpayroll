"""
Management command to process pending email notifications
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.email_service import EmailNotificationManager, EmailNotificationService
from core.notification_service import NotificationService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process pending email notifications'

    def add_arguments(self, parser):
        parser.add_argument(
            '--urgent-only',
            action='store_true',
            help='Process only urgent notifications',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without actually sending emails',
        )
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Clean up expired notifications after processing',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting email notification processing...')
        )
        
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No emails will be sent')
            )
        
        # Process pending emails
        if options['urgent_only']:
            self.process_urgent_notifications(options['dry_run'])
        else:
            self.process_all_notifications(options['dry_run'])
        
        # Cleanup if requested
        if options['cleanup']:
            self.cleanup_notifications()
        
        self.stdout.write(
            self.style.SUCCESS('Email notification processing completed!')
        )

    def process_urgent_notifications(self, dry_run=False):
        """Process only urgent notifications"""
        from core.models import Notification
        
        urgent_notifications = Notification.objects.filter(
            is_email_sent=False,
            priority='urgent',
            user__email__isnull=False
        ).exclude(user__email='')
        
        self.stdout.write(f'Found {urgent_notifications.count()} urgent notifications to process')
        
        if dry_run:
            for notification in urgent_notifications:
                self.stdout.write(
                    f'Would send urgent email to {notification.user.email}: {notification.title}'
                )
        else:
            sent_count = 0
            for notification in urgent_notifications:
                if EmailNotificationService.send_urgent_notification_email(notification):
                    sent_count += 1
                    self.stdout.write(
                        f'Sent urgent email to {notification.user.email}: {notification.title}'
                    )
            
            self.stdout.write(
                self.style.SUCCESS(f'Sent {sent_count} urgent notification emails')
            )

    def process_all_notifications(self, dry_run=False):
        """Process all pending notifications"""
        sent_count = EmailNotificationManager.process_pending_emails()
        
        if dry_run:
            from core.models import Notification
            pending_count = Notification.objects.filter(
                is_email_sent=False,
                user__email__isnull=False
            ).exclude(user__email='').count()
            
            self.stdout.write(f'Would process {pending_count} pending notifications')
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Processed {sent_count} notification emails')
            )

    def cleanup_notifications(self):
        """Clean up expired notifications"""
        deleted_count = NotificationService.delete_expired_notifications()
        self.stdout.write(
            self.style.SUCCESS(f'Deleted {deleted_count} expired notifications')
        )
