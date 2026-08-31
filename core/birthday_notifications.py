import calendar
import logging
from dataclasses import dataclass
from datetime import date, timedelta

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.template.loader import render_to_string
from django.utils import timezone

from .models import BirthdayNotificationLog, CustomUser
from .notification_service import NotificationService

logger = logging.getLogger(__name__)


BIRTHDAY_REMINDER_ROLES = ('admin', 'hr', 'employee')
ACTIVE_EMPLOYMENT_STATUSES = ('active',)


@dataclass
class BirthdayProcessingSummary:
    employees_checked: int = 0
    today_birthdays_found: int = 0
    tomorrow_birthdays_found: int = 0
    in_app_notifications_created: int = 0
    emails_sent: int = 0
    emails_skipped: int = 0
    duplicates_skipped: int = 0
    failures: int = 0

    def as_dict(self):
        return self.__dict__.copy()


def birthday_observed_date(date_of_birth, year):
    if not date_of_birth:
        return None

    if date_of_birth.month == 2 and date_of_birth.day == 29 and not calendar.isleap(year):
        return date(year, 2, 28)

    try:
        return date(year, date_of_birth.month, date_of_birth.day)
    except ValueError:
        return None


def is_birthday_on(date_of_birth, target_date):
    return birthday_observed_date(date_of_birth, target_date.year) == target_date


def get_active_birthday_employees():
    return CustomUser.objects.select_related('department', 'designation').filter(
        role='employee',
        is_active=True,
        employment_status__in=ACTIVE_EMPLOYMENT_STATUSES,
        date_of_birth__isnull=False,
        archived_at__isnull=True,
        exit_date__isnull=True,
    )


def get_birthday_reminder_recipients(employee=None):
    recipients = CustomUser.objects.filter(is_active=True).filter(
        role__in=BIRTHDAY_REMINDER_ROLES,
    )

    employee_recipients = recipients.filter(role='employee').filter(
        employment_status__in=ACTIVE_EMPLOYMENT_STATUSES,
        archived_at__isnull=True,
        exit_date__isnull=True,
    )
    admin_hr_recipients = recipients.filter(role__in=('admin', 'hr'))
    recipients = admin_hr_recipients | employee_recipients | CustomUser.objects.filter(
        is_active=True,
        is_superuser=True,
    )

    if employee:
        recipients = recipients.exclude(id=employee.id)

    return recipients.distinct()


def employee_context(employee, target_date):
    return {
        'employee_full_name': employee.get_full_name() or employee.username,
        'employee_first_name': employee.first_name or employee.get_full_name() or employee.username,
        'employee_id': employee.employee_id or 'N/A',
        'department': employee.department.name if employee.department else 'N/A',
        'designation': employee.designation.name if employee.designation else 'N/A',
        'birthday_date': target_date.strftime('%d-%m-%Y'),
        'company_name': getattr(settings, 'COMPANY_NAME', 'Company'),
    }


def has_valid_email(user):
    if not user.email:
        return False
    try:
        validate_email(user.email)
        return True
    except Exception:
        return False


def render_birthday_email(template_name, context):
    html = render_to_string(f'emails/{template_name}.html', context)
    text = render_to_string(f'emails/{template_name}.txt', context)
    return text, html


def send_birthday_email(recipient, subject, template_name, context):
    if not has_valid_email(recipient):
        logger.info('birthday_email_skipped recipient=%s reason=missing_or_invalid_email', recipient.id)
        return False, 'missing_or_invalid_email'

    text, html = render_birthday_email(template_name, context)
    message = EmailMultiAlternatives(
        subject=subject,
        body=text,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient.email],
    )
    message.attach_alternative(html, 'text/html')
    message.send()
    logger.info('birthday_email_sent recipient=%s subject=%s', recipient.id, subject)
    return True, ''


def get_or_create_delivery_log(employee, recipient, birthday_year, notification_type, channel):
    try:
        with transaction.atomic():
            log, created = BirthdayNotificationLog.objects.get_or_create(
                employee=employee,
                recipient=recipient,
                birthday_year=birthday_year,
                notification_type=notification_type,
                channel=channel,
                defaults={'status': 'skipped'},
            )
        return log, created
    except IntegrityError:
        return BirthdayNotificationLog.objects.get(
            employee=employee,
            recipient=recipient,
            birthday_year=birthday_year,
            notification_type=notification_type,
            channel=channel,
        ), False


def create_in_app_once(employee, recipient, birthday_year, notification_type, title, message, created_by=None):
    log, created = get_or_create_delivery_log(
        employee, recipient, birthday_year, notification_type, 'in_app'
    )
    if not created and log.status == 'sent':
        logger.info('birthday_delivery_duplicate_skipped log=%s', log.id)
        return False, True

    notification = NotificationService.create_notification(
        user=recipient,
        title=title,
        message=message,
        notification_type='reminder',
        category='info',
        priority='low',
        related_object=employee,
        created_by=created_by,
        send_email=False,
    )

    if notification:
        log.notification = notification
        log.status = 'sent'
        log.sent_at = timezone.now()
        log.error_message = ''
        log.save(update_fields=['notification', 'status', 'sent_at', 'error_message', 'updated_at'])
        return True, False

    log.status = 'failed'
    log.error_message = 'Notification creation failed'
    log.save(update_fields=['status', 'error_message', 'updated_at'])
    logger.info('birthday_delivery_failed log=%s channel=in_app', log.id)
    return False, False


def send_email_once(employee, recipient, birthday_year, notification_type, subject, template_name, context):
    log, created = get_or_create_delivery_log(
        employee, recipient, birthday_year, notification_type, 'email'
    )
    if not created and log.status == 'sent':
        logger.info('birthday_delivery_duplicate_skipped log=%s', log.id)
        return 'duplicate'

    try:
        sent, error = send_birthday_email(recipient, subject, template_name, context)
        log.status = 'sent' if sent else 'skipped'
        log.sent_at = timezone.now() if sent else None
        log.error_message = error
        log.save(update_fields=['status', 'sent_at', 'error_message', 'updated_at'])
        return 'sent' if sent else 'skipped'
    except Exception as exc:
        log.status = 'failed'
        log.error_message = str(exc)[:1000]
        log.save(update_fields=['status', 'error_message', 'updated_at'])
        logger.exception('birthday_delivery_failed log=%s channel=email', log.id)
        return 'failed'


def process_daily_employee_birthdays(for_date=None, dry_run=False, employee_id=None):
    today = for_date or timezone.localdate()
    tomorrow = today + timedelta(days=1)
    summary = BirthdayProcessingSummary()

    logger.info('birthday_processing_started date=%s dry_run=%s', today, dry_run)

    employees_qs = get_active_birthday_employees()
    if employee_id:
        employees_qs = employees_qs.filter(employee_id=employee_id)

    employees = list(employees_qs)
    summary.employees_checked = len(employees)

    today_employees = [employee for employee in employees if is_birthday_on(employee.date_of_birth, today)]
    tomorrow_employees = [employee for employee in employees if is_birthday_on(employee.date_of_birth, tomorrow)]
    summary.today_birthdays_found = len(today_employees)
    summary.tomorrow_birthdays_found = len(tomorrow_employees)

    if dry_run:
        dry_run_employees = today_employees + tomorrow_employees
        recipients = list(
            CustomUser.objects.filter(
                id__in=[
                    recipient.id
                    for employee in dry_run_employees
                    for recipient in get_birthday_reminder_recipients(employee)
                ]
            ).distinct()
        )
        return {
            **summary.as_dict(),
            'today': today.isoformat(),
            'tomorrow': tomorrow.isoformat(),
            'today_birthdays': [employee.employee_id or str(employee.id) for employee in today_employees],
            'tomorrow_birthdays': [employee.employee_id or str(employee.id) for employee in tomorrow_employees],
            'authorized_recipients': [recipient.email or recipient.username for recipient in recipients],
            'notification_types': ['advance_reminder', 'today_reminder', 'employee_wish'],
        }

    for employee in tomorrow_employees:
        recipients = list(get_birthday_reminder_recipients(employee))
        logger.info('birthday_employee_matched employee=%s timing=tomorrow', employee.id)
        ctx = employee_context(employee, tomorrow)
        title = 'Upcoming Employee Birthday 🎉'
        message = (
            f"Tomorrow is {ctx['employee_full_name']}'s birthday.\n\n"
            "Please remember to send your wishes and help make their day special.\n\n"
            f"Employee ID: {ctx['employee_id']}\n"
            f"Department: {ctx['department']}\n"
            f"Designation: {ctx['designation']}\n"
            f"Birthday: {ctx['birthday_date']}"
        )
        for recipient in recipients:
            created, duplicate = create_in_app_once(
                employee, recipient, tomorrow.year, 'advance_reminder', title, message
            )
            summary.in_app_notifications_created += int(created)
            summary.duplicates_skipped += int(duplicate)
            if created:
                logger.info('birthday_advance_notification_created employee=%s recipient=%s', employee.id, recipient.id)

            email_context = {**ctx, 'recipient_name': recipient.get_full_name() or recipient.username}
            status = send_email_once(
                employee,
                recipient,
                tomorrow.year,
                'advance_reminder',
                f"Birthday Reminder: {ctx['employee_full_name']}",
                'birthday_advance_reminder',
                email_context,
            )
            summary.emails_sent += int(status == 'sent')
            summary.emails_skipped += int(status == 'skipped')
            summary.duplicates_skipped += int(status == 'duplicate')
            summary.failures += int(status == 'failed')

    for employee in today_employees:
        recipients = list(get_birthday_reminder_recipients(employee))
        logger.info('birthday_employee_matched employee=%s timing=today', employee.id)
        ctx = employee_context(employee, today)

        wish_title = f"Happy Birthday, {ctx['employee_first_name']}! 🎂🎉"
        wish_message = (
            f"Happy Birthday, {ctx['employee_first_name']}!\n\n"
            "Wishing you a wonderful day filled with happiness, success and memorable moments.\n\n"
            "Thank you for being a valued member of our team.\n\n"
            f"Best wishes from everyone at {ctx['company_name']}!"
        )
        created, duplicate = create_in_app_once(
            employee, employee, today.year, 'employee_wish', wish_title, wish_message
        )
        summary.in_app_notifications_created += int(created)
        summary.duplicates_skipped += int(duplicate)
        if created:
            logger.info('birthday_employee_wish_created employee=%s', employee.id)

        status = send_email_once(
            employee,
            employee,
            today.year,
            'employee_wish',
            f"Happy Birthday, {ctx['employee_first_name']}!",
            'employee_birthday_wish',
            {**ctx, 'recipient_name': employee.get_full_name() or employee.username},
        )
        summary.emails_sent += int(status == 'sent')
        summary.emails_skipped += int(status == 'skipped')
        summary.duplicates_skipped += int(status == 'duplicate')
        summary.failures += int(status == 'failed')

        today_title = 'Employee Birthday Today 🎂'
        today_message = (
            f"Today is {ctx['employee_full_name']}'s birthday.\n\n"
            "Please take a moment to send your birthday wishes.\n\n"
            f"Employee ID: {ctx['employee_id']}\n"
            f"Department: {ctx['department']}\n"
            f"Designation: {ctx['designation']}\n"
            f"Birthday: {ctx['birthday_date']}"
        )
        for recipient in recipients:
            created, duplicate = create_in_app_once(
                employee, recipient, today.year, 'today_reminder', today_title, today_message
            )
            summary.in_app_notifications_created += int(created)
            summary.duplicates_skipped += int(duplicate)
            if created:
                logger.info('birthday_today_notification_created employee=%s recipient=%s', employee.id, recipient.id)

            email_context = {**ctx, 'recipient_name': recipient.get_full_name() or recipient.username}
            status = send_email_once(
                employee,
                recipient,
                today.year,
                'today_reminder',
                f"Employee Birthday Today: {ctx['employee_full_name']}",
                'birthday_today_reminder',
                email_context,
            )
            summary.emails_sent += int(status == 'sent')
            summary.emails_skipped += int(status == 'skipped')
            summary.duplicates_skipped += int(status == 'duplicate')
            summary.failures += int(status == 'failed')

    logger.info('birthday_processing_completed summary=%s', summary.as_dict())
    return summary.as_dict()
