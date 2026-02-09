from django.db import models
from django.conf import settings
import uuid
from decimal import Decimal


class SalaryIncrement(models.Model):
    INCREMENT_TYPE_CHOICES = [
        ('annual', 'Annual Increment'),
        ('promotion', 'Promotion'),
        ('performance', 'Performance Based'),
        ('adjustment', 'Adjustment'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Make sure the FK matches UUIDField type
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='increments',
        db_column='employee_id'
    )

    increment_type = models.CharField(max_length=20, choices=INCREMENT_TYPE_CHOICES)
    old_salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    increment_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    increment_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    new_salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    effective_from = models.DateField()
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='approved_salary_increments',
        db_column='approved_by_id'
    )

    applied_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-effective_from']
        verbose_name = "Salary Increment"
        verbose_name_plural = "Salary Increments"

    def __str__(self):
        return f"{self.employee.get_full_name()} | +{self.increment_amount or 0}"

    def clean(self):
        if not self.old_salary:
            self.old_salary = getattr(self.employee, 'salary', Decimal('0.00'))

        if self.increment_percentage and not self.increment_amount:
            self.increment_amount = (self.old_salary * self.increment_percentage / Decimal('100')).quantize(Decimal('0.01'))

        if self.increment_amount and not self.increment_percentage and self.old_salary:
            self.increment_percentage = (self.increment_amount * Decimal('100') / self.old_salary).quantize(Decimal('0.01'))

        if self.old_salary is not None and self.increment_amount is not None:
            self.new_salary = self.old_salary + self.increment_amount

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class SalaryIncrementHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='increment_history',
        db_column='employee_id'
    )

    increment = models.ForeignKey(
        SalaryIncrement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='history_records',
        db_column='increment_id'
    )

    old_salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    new_salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='salary_changes_made',
        db_column='changed_by_id'
    )

    changed_at = models.DateTimeField(auto_now_add=True)
    remarks = models.TextField(blank=True)

    class Meta:
        verbose_name = "Salary Increment History"
        verbose_name_plural = "Salary Increment Histories"
        ordering = ['-changed_at']

    def __str__(self):
        return f"{self.employee.get_full_name()} | {self.old_salary} → {self.new_salary}"


class Holiday(models.Model):
    HOLIDAY_TYPE = (
        ('NATIONAL', 'National'),
        ('STATE', 'State'),
        ('COMPANY', 'Company'),
    )

    name = models.CharField(max_length=100)
    date = models.DateField(unique=True)
    type = models.CharField(max_length=20, choices=HOLIDAY_TYPE)

    is_paid = models.BooleanField(default=True)
    double_pay_if_worked = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.date}"


