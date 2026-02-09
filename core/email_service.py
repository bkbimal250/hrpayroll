"""
Email Service for sending notification emails
"""
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from .models import Notification, CustomUser
import logging

logger = logging.getLogger(__name__)


class EmailNotificationService:
    """Service for sending email notifications"""
    
    @staticmethod
    def send_notification_email(notification):
        """Send email for a notification"""
        try:
            if not notification.user.email:
                logger.warning(f"No email address for user {notification.user.get_full_name()}")
                return False
            
            # Skip if email already sent
            if notification.is_email_sent:
                return True
            
            # Prepare email content
            subject = f"[{notification.priority.upper()}] {notification.title}"
            
            # Create HTML email content
            html_content = EmailNotificationService._create_html_email(notification)
            text_content = EmailNotificationService._create_text_email(notification)
            
            # Create email message
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[notification.user.email]
            )
            msg.attach_alternative(html_content, "text/html")
            
            # Send email
            msg.send()
            
            # Mark email as sent
            notification.mark_email_sent()
            
            logger.info(f"Email sent successfully to {notification.user.email} for notification {notification.id}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email for notification {notification.id}: {str(e)}")
            return False
    
    @staticmethod
    def _create_html_email(notification):
        """Create HTML email content"""
        # Get role-based dashboard URL
        dashboard_url = EmailNotificationService._get_dashboard_url(notification.user.role)
        
        # Get approver information if available
        approver_name = None
        if notification.created_by:
            approver_name = notification.created_by.get_full_name()
        
        context = {
            'notification': notification,
            'user': notification.user,
            'site_url': getattr(settings, 'SITE_URL', 'https://company.d0s369.co.in'),
            'dashboard_url': dashboard_url,
            'company_name': getattr(settings, 'COMPANY_NAME', 'Company'),
            'approver_name': approver_name,
        }
        
        return render_to_string('emails/notification.html', context)
    
    @staticmethod
    def _get_dashboard_url(user_role):
        """Get dashboard URL based on user role"""
        dashboard_urls = {
            'admin': 'https://admindos.dishaonlinesolution.in',
            'manager': 'https://dosmanagers.dishaonlinesolution.in',
            'employee': 'https://dosemployees.dishaonlinesolution.in',
            'accountant': 'https://dosaccounts.dishaonlinesolution.in/dashboard',
        }
        return dashboard_urls.get(user_role, 'https://company.d0s369.co.in')
    
    @staticmethod
    def _create_text_email(notification):
        """Create plain text email content"""
        dashboard_url = EmailNotificationService._get_dashboard_url(notification.user.role)
        
        # Get approver information if available
        approver_info = ""
        if notification.created_by:
            approver_name = notification.created_by.get_full_name()
            approver_info = f"\nApproved by: {approver_name}"
        
        return f"""
{notification.title}

{notification.message}{approver_info}

Priority: {notification.priority.title()}
Type: {notification.notification_type.title()}
Created: {notification.created_at.strftime('%Y-%m-%d %H:%M:%S')}

---
This notification was sent from {getattr(settings, 'COMPANY_NAME', 'Company')} Attendance System.
Please take immediate action if required.
Visit {dashboard_url} for more details.

Please do not reply to this email.
        """.strip()
    
    @staticmethod
    def send_bulk_notification_emails(notifications):
        """Send emails for multiple notifications"""
        sent_count = 0
        for notification in notifications:
            if EmailNotificationService.send_notification_email(notification):
                sent_count += 1
        return sent_count
    
    @staticmethod
    def send_urgent_notification_email(notification):
        """Send urgent notification with immediate delivery"""
        try:
            if not notification.user.email:
                return False
            
            subject = f"🚨 URGENT: {notification.title}"
            
            # Create urgent email content
            html_content = EmailNotificationService._create_urgent_html_email(notification)
            text_content = EmailNotificationService._create_urgent_text_email(notification)
            
            # Create email message with high priority
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[notification.user.email]
            )
            msg.attach_alternative(html_content, "text/html")
            
            # Add urgent headers
            msg.extra_headers['X-Priority'] = '1'
            msg.extra_headers['X-MSMail-Priority'] = 'High'
            msg.extra_headers['Importance'] = 'high'
            
            # Send email
            msg.send()
            
            # Mark email as sent
            notification.mark_email_sent()
            
            logger.info(f"Urgent email sent to {notification.user.email} for notification {notification.id}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending urgent email for notification {notification.id}: {str(e)}")
            return False
    
    @staticmethod
    def _create_urgent_html_email(notification):
        """Create urgent HTML email content"""
        dashboard_url = EmailNotificationService._get_dashboard_url(notification.user.role)
        
        # Get approver information if available
        approver_name = None
        if notification.created_by:
            approver_name = notification.created_by.get_full_name()
        
        context = {
            'notification': notification,
            'user': notification.user,
            'site_url': getattr(settings, 'SITE_URL', 'https://company.d0s369.co.in'),
            'dashboard_url': dashboard_url,
            'company_name': getattr(settings, 'COMPANY_NAME', 'Company'),
            'approver_name': approver_name,
            'is_urgent': True,
        }
        
        return render_to_string('emails/urgent_notification.html', context)
    
    @staticmethod
    def _create_urgent_text_email(notification):
        """Create urgent plain text email content"""
        dashboard_url = EmailNotificationService._get_dashboard_url(notification.user.role)
        
        # Get approver information if available
        approver_info = ""
        if notification.created_by:
            approver_name = notification.created_by.get_full_name()
            approver_info = f"\nApproved by: {approver_name}"
        
        return f"""
🚨 URGENT NOTIFICATION 🚨

{notification.title}

{notification.message}{approver_info}

Priority: {notification.priority.title()}
Type: {notification.notification_type.title()}
Created: {notification.created_at.strftime('%Y-%m-%d %H:%M:%S')}

This is an urgent notification that requires immediate attention.

---
This urgent notification was sent from {getattr(settings, 'COMPANY_NAME', 'Company')} Attendance System.
Please take immediate action if required.
Visit {dashboard_url} for more details.

Please do not reply to this email.
        """.strip()


class EmailNotificationManager:
    """Manager for handling email notification workflows"""
    
    @staticmethod
    def process_pending_emails():
        """Process pending email notifications"""
        # Get notifications that need email sending
        pending_notifications = Notification.objects.filter(
            is_email_sent=False,
            user__email__isnull=False
        ).exclude(user__email='')
        
        sent_count = 0
        for notification in pending_notifications:
            # Check if notification is expired
            if notification.is_expired():
                continue
            
            # Send email based on priority
            if notification.priority == 'urgent':
                if EmailNotificationService.send_urgent_notification_email(notification):
                    sent_count += 1
            else:
                if EmailNotificationService.send_notification_email(notification):
                    sent_count += 1
        
        logger.info(f"Processed {sent_count} pending email notifications")
        return sent_count
    
    @staticmethod
    def send_daily_summary(user):
        """Send daily notification summary to user"""
        try:
            if not user.email:
                return False
            
            # Get today's notifications
            today = timezone.now().date()
            today_notifications = Notification.objects.filter(
                user=user,
                created_at__date=today
            ).order_by('-created_at')
            
            if not today_notifications.exists():
                return True  # No notifications to send
            
            # Create summary email
            subject = f"Daily Notification Summary - {today.strftime('%Y-%m-%d')}"
            
            context = {
                'user': user,
                'notifications': today_notifications,
                'date': today,
                'site_url': getattr(settings, 'SITE_URL', 'https://company.d0s369.co.in'),
                'company_name': getattr(settings, 'COMPANY_NAME', 'Company'),
            }
            
            html_content = render_to_string('emails/daily_summary.html', context)
            text_content = render_to_string('emails/daily_summary.txt', context)
            
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email]
            )
            msg.attach_alternative(html_content, "text/html")
            
            msg.send()
            
            logger.info(f"Daily summary sent to {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending daily summary to {user.email}: {str(e)}")
            return False
    
    @staticmethod
    def send_weekly_summary(user):
        """Send weekly notification summary to user"""
        try:
            if not user.email:
                return False
            
            # Get this week's notifications
            from datetime import timedelta
            week_start = timezone.now().date() - timedelta(days=7)
            week_notifications = Notification.objects.filter(
                user=user,
                created_at__date__gte=week_start
            ).order_by('-created_at')
            
            if not week_notifications.exists():
                return True  # No notifications to send
            
            # Create summary email
            subject = f"Weekly Notification Summary - Week of {week_start.strftime('%Y-%m-%d')}"
            
            context = {
                'user': user,
                'notifications': week_notifications,
                'week_start': week_start,
                'site_url': getattr(settings, 'SITE_URL', 'https://company.d0s369.co.in'),
                'company_name': getattr(settings, 'COMPANY_NAME', 'Company'),
            }
            
            html_content = render_to_string('emails/weekly_summary.html', context)
            text_content = render_to_string('emails/weekly_summary.txt', context)
            
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email]
            )
            msg.attach_alternative(html_content, "text/html")
            
            msg.send()
            
            logger.info(f"Weekly summary sent to {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending weekly summary to {user.email}: {str(e)}")
            return False


# Convenience functions
def send_notification_email(notification):
    """Send email for a notification"""
    return EmailNotificationService.send_notification_email(notification)

def send_urgent_notification_email(notification):
    """Send urgent email for a notification"""
    return EmailNotificationService.send_urgent_notification_email(notification)

def process_pending_emails():
    """Process all pending email notifications"""
    return EmailNotificationManager.process_pending_emails()
