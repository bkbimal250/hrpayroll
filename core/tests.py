from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from .models import CustomUser, Resignation


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
