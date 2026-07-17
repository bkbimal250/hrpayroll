from datetime import timedelta
from io import StringIO

from django.core import mail
from django.core.management import call_command
from django.test import override_settings
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from .birthday_notifications import birthday_observed_date, process_daily_employee_birthdays
from .models import BirthdayNotificationLog, CustomUser, Notification, Resignation


class ResignationSubmissionTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_accountant_can_submit_resignation(self):
        accountant = CustomUser.objects.create_user(
            username='accountant@example.com',
            email='accountant@example.com',
            password='test-pass-123',
            role='accountant',
            employee_id='ACC001',
        )
        self.client.force_authenticate(user=accountant)

        resignation_date = timezone.now().date()
        response = self.client.post(
            reverse('core:resignation-list'),
            {
                'resignation_date': resignation_date.isoformat(),
                'notice_period_days': 30,
                'reason': 'Personal reasons',
                'handover_notes': 'Pending work documented',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        resignation = Resignation.objects.get(user=accountant)
        self.assertEqual(resignation.status, 'pending')
        self.assertEqual(resignation.last_working_date, resignation_date + timedelta(days=30))
        accountant.refresh_from_db()
        self.assertEqual(accountant.employment_status, 'notice_period')

    def test_admin_can_update_resignation_to_past_date(self):
        employee = CustomUser.objects.create_user(
            username='employee@example.com',
            email='employee@example.com',
            password='test-pass-123',
            role='employee',
            employee_id='EMP001',
        )
        admin = CustomUser.objects.create_user(
            username='admin@example.com',
            email='admin@example.com',
            password='test-pass-123',
            role='admin',
            employee_id='ADM001',
            is_staff=True,
            is_superuser=True,
        )
        resignation = Resignation.objects.create(
            user=employee,
            resignation_date=timezone.now().date(),
            notice_period_days=30,
            reason='Personal reasons',
        )
        self.client.force_authenticate(user=admin)

        past_date = timezone.now().date() - timedelta(days=10)
        response = self.client.patch(
            reverse('core:resignation-detail', args=[resignation.id]),
            {'resignation_date': past_date.isoformat()},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        resignation.refresh_from_db()
        self.assertEqual(resignation.resignation_date, past_date)
        self.assertEqual(resignation.last_working_date, past_date + timedelta(days=30))
        employee.refresh_from_db()
        self.assertEqual(employee.resignation_date, past_date)
        self.assertEqual(employee.last_working_date, past_date + timedelta(days=30))


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    DEFAULT_FROM_EMAIL='noreply@example.com',
    COMPANY_NAME='Test Company',
)
class BirthdayNotificationTests(TestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_user(
            username='admin@example.com',
            email='admin@example.com',
            password='test-pass-123',
            role='admin',
            employee_id='ADM001',
            is_staff=True,
        )
        self.hr = CustomUser.objects.create_user(
            username='hr@example.com',
            email='hr@example.com',
            password='test-pass-123',
            role='hr',
            employee_id='HR001',
        )
        self.accountant = CustomUser.objects.create_user(
            username='accountant-bday@example.com',
            email='accountant-bday@example.com',
            password='test-pass-123',
            role='accountant',
            employee_id='ACC999',
        )
        self.other_employee = CustomUser.objects.create_user(
            username='other@example.com',
            email='other@example.com',
            password='test-pass-123',
            role='employee',
            employee_id='EMP999',
        )

    def create_employee(self, employee_id, dob, email='employee-bday@example.com', **kwargs):
        return CustomUser.objects.create_user(
            username=f'{employee_id.lower()}@example.com',
            email=email,
            password='test-pass-123',
            role='employee',
            employee_id=employee_id,
            first_name='Birthday',
            last_name='Person',
            date_of_birth=dob,
            **kwargs,
        )

    def test_employee_birthday_tomorrow_sends_management_reminders(self):
        employee = self.create_employee('EMP001', timezone.datetime(1990, 7, 18).date())

        summary = process_daily_employee_birthdays(for_date=timezone.datetime(2026, 7, 17).date())

        self.assertEqual(summary['tomorrow_birthdays_found'], 1)
        self.assertEqual(Notification.objects.filter(user=self.admin, title__icontains='Upcoming').count(), 1)
        self.assertEqual(Notification.objects.filter(user=employee).count(), 0)
        self.assertGreaterEqual(len(mail.outbox), 3)

    def test_employee_birthday_today_sends_wish_and_management_reminders(self):
        employee = self.create_employee('EMP002', timezone.datetime(1990, 7, 17).date())

        summary = process_daily_employee_birthdays(for_date=timezone.datetime(2026, 7, 17).date())

        self.assertEqual(summary['today_birthdays_found'], 1)
        self.assertEqual(Notification.objects.filter(user=employee, title__icontains='Happy Birthday').count(), 1)
        self.assertEqual(Notification.objects.filter(user=self.hr, title__icontains='Employee Birthday Today').count(), 1)
        self.assertGreaterEqual(len(mail.outbox), 4)

    def test_employee_birthday_on_another_date_is_ignored(self):
        self.create_employee('EMP003', timezone.datetime(1990, 7, 19).date())

        summary = process_daily_employee_birthdays(for_date=timezone.datetime(2026, 7, 17).date())

        self.assertEqual(summary['today_birthdays_found'], 0)
        self.assertEqual(summary['tomorrow_birthdays_found'], 0)
        self.assertEqual(Notification.objects.filter(notification_type='reminder').count(), 0)

    def test_december_31_to_january_1_advance_reminder(self):
        self.create_employee('EMP004', timezone.datetime(1990, 1, 1).date())

        summary = process_daily_employee_birthdays(for_date=timezone.datetime(2026, 12, 31).date())

        self.assertEqual(summary['tomorrow_birthdays_found'], 1)

    def test_february_29_observed_date(self):
        dob = timezone.datetime(1992, 2, 29).date()

        self.assertEqual(birthday_observed_date(dob, 2028), timezone.datetime(2028, 2, 29).date())
        self.assertEqual(birthday_observed_date(dob, 2027), timezone.datetime(2027, 2, 28).date())

    def test_inactive_and_missing_dob_employees_are_ignored(self):
        self.create_employee('EMP005', timezone.datetime(1990, 7, 17).date(), is_active=False)
        self.create_employee('EMP006', None)

        summary = process_daily_employee_birthdays(for_date=timezone.datetime(2026, 7, 17).date())

        self.assertEqual(summary['today_birthdays_found'], 0)
        self.assertEqual(Notification.objects.filter(notification_type='reminder').count(), 0)

    def test_employee_without_email_still_receives_portal_notification(self):
        employee = self.create_employee('EMP007', timezone.datetime(1990, 7, 17).date(), email='')

        summary = process_daily_employee_birthdays(for_date=timezone.datetime(2026, 7, 17).date())

        self.assertEqual(Notification.objects.filter(user=employee).count(), 1)
        self.assertGreaterEqual(summary['emails_skipped'], 1)

    def test_multiple_runs_do_not_duplicate_deliveries(self):
        self.create_employee('EMP008', timezone.datetime(1990, 7, 17).date())

        process_daily_employee_birthdays(for_date=timezone.datetime(2026, 7, 17).date())
        first_notification_count = Notification.objects.count()
        first_log_count = BirthdayNotificationLog.objects.count()
        process_daily_employee_birthdays(for_date=timezone.datetime(2026, 7, 17).date())

        self.assertEqual(Notification.objects.count(), first_notification_count)
        self.assertEqual(BirthdayNotificationLog.objects.count(), first_log_count)

    def test_unauthorized_employee_role_does_not_receive_management_reminder(self):
        self.create_employee('EMP009', timezone.datetime(1990, 7, 18).date())

        process_daily_employee_birthdays(for_date=timezone.datetime(2026, 7, 17).date())

        self.assertEqual(Notification.objects.filter(user=self.other_employee).count(), 0)

    def test_dry_run_command_performs_no_writes(self):
        self.create_employee('EMP010', timezone.datetime(1990, 7, 17).date())
        output = StringIO()

        call_command('process_employee_birthdays', '--dry-run', '--date', '2026-07-17', stdout=output)

        self.assertIn('today_birthdays_found: 1', output.getvalue())
        self.assertEqual(Notification.objects.filter(notification_type='reminder').count(), 0)
        self.assertEqual(BirthdayNotificationLog.objects.count(), 0)
