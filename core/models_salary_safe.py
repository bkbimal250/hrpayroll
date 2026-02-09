"""
Safe version of Salary models to avoid foreign key constraint issues
Use this if the main models.py causes problems
"""

from django.db import models
from django.conf import settings
from decimal import Decimal
import uuid
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta


class Salary(models.Model):
    """Salary model for employee salary management with auto-calculation"""
    SALARY_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('bank_transfer', 'Bank Transfer'),
        ('cash', 'Cash'),
        ('cheque', 'Cheque'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="salaries"
    )
    
    # Basic Salary Information
    basic_pay = models.DecimalField(max_digits=10, decimal_places=2, help_text="Basic salary amount")
    increment = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Increment amount")
    total_days = models.PositiveIntegerField(default=30, help_text="Total working days in the month")
    worked_days = models.PositiveIntegerField(default=30, help_text="Days actually worked")
    
    # Deductions and Adjustments
    deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Total deductions")
    balance_loan = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Outstanding loan balance")
    remaining_pay = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Remaining pay after deductions")
    
    # Additional Allowances
    house_rent_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="House Rent Allowance")
    transport_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Transport Allowance")
    medical_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Medical Allowance")
    other_allowances = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Other Allowances")
    
    # Deductions Breakdown
    provident_fund = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Provident Fund deduction")
    professional_tax = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Professional Tax")
    income_tax = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Income Tax (TDS)")
    other_deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Other Deductions")
    
    # Salary Period and Payment
    salary_month = models.DateField(help_text="Salary month (first day of the month)")
    pay_date = models.DateField(null=True, blank=True, help_text="Scheduled pay date")
    paid_date = models.DateField(null=True, blank=True, help_text="Actual payment date")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='bank_transfer')
    
    # Status and Approval
    status = models.CharField(max_length=20, choices=SALARY_STATUS_CHOICES, default='draft')
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_salaries'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Notes and Comments
    notes = models.TextField(blank=True, help_text="Additional notes or comments")
    status_reason = models.TextField(blank=True, help_text="Reason for current status if applicable")
    
    # Auto-calculation flags
    is_auto_calculated = models.BooleanField(default=False, help_text="Whether salary was auto-calculated from attendance")
    attendance_based = models.BooleanField(default=True, help_text="Whether salary is based on attendance")
    
    # System fields
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_salaries'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Salary"
        verbose_name_plural = "Salaries"
        ordering = ['-salary_month', '-created_at']
        unique_together = ['employee', 'salary_month']

    def __str__(self):
        try:
            return f"Salary for {self.employee.get_full_name()} - {self.salary_month.strftime('%B %Y')}"
        except Exception:
            return f"Salary - {self.salary_month.strftime('%B %Y')}"

    def clean(self):
        """Validate salary data"""
        super().clean()
        
        # Ensure employee is actually an employee
        if self.employee.role != 'employee':
            raise ValidationError('Salary can only be assigned to employees.')
        
        # Ensure worked_days doesn't exceed total_days
        if self.worked_days > self.total_days:
            raise ValidationError('Worked days cannot exceed total days.')
        
        # Ensure basic_pay is positive
        if self.basic_pay <= 0:
            raise ValidationError('Basic pay must be greater than zero.')

    def save(self, *args, **kwargs):
        self.clean()
        
        # Auto-calculate worked_days from attendance if not manually set
        if self.attendance_based and not self._state.adding:
            self.calculate_worked_days_from_attendance()
        
        # Auto-calculate remaining_pay
        self.calculate_remaining_pay()
        
        super().save(*args, **kwargs)

    # Auto-calculated fields (properties)
    @property
    def final_salary(self):
        """Final salary before deductions (basic + increment)"""
        return self.basic_pay + self.increment

    @property
    def per_day_salary(self):
        """Salary per day"""
        return self.final_salary / Decimal(self.total_days) if self.total_days > 0 else 0

    @property
    def gross_salary(self):
        """Gross salary based on worked days"""
        return self.per_day_salary * Decimal(self.worked_days)

    @property
    def total_allowances(self):
        """Total of all allowances"""
        return (self.house_rent_allowance + self.transport_allowance + 
                self.medical_allowance + self.other_allowances)

    @property
    def total_deductions(self):
        """Total of all deductions"""
        return (self.deduction + self.provident_fund + self.professional_tax + 
                self.income_tax + self.other_deductions)

    @property
    def net_salary(self):
        """Net salary after all deductions"""
        return self.gross_salary + self.total_allowances - self.total_deductions

    @property
    def final_payable_amount(self):
        """Final amount to be paid (net salary - loan balance)"""
        return max(0, self.net_salary - self.balance_loan)

    def calculate_worked_days_from_attendance(self):
        """Calculate worked days from attendance records"""
        try:
            from django.utils import timezone
            from datetime import datetime
            
            # Get the month and year from salary_month
            year = self.salary_month.year
            month = self.salary_month.month
            
            # Calculate start and end dates for the month
            start_date = datetime(year, month, 1).date()
            if month == 12:
                end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
            else:
                end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)
            
            # Get attendance records for the month
            from .models import Attendance
            attendance_records = Attendance.objects.filter(
                user=self.employee,
                date__range=[start_date, end_date]
            )
            
            # Count worked days based on attendance status
            worked_days = 0
            for record in attendance_records:
                if record.status == 'present':
                    if record.day_status == 'complete_day':
                        worked_days += 1
                    elif record.day_status == 'half_day':
                        worked_days += 0.5
            
            # Update worked_days
            self.worked_days = int(worked_days)
            self.is_auto_calculated = True
            
        except Exception as e:
            # If calculation fails, keep the current worked_days
            pass

    def calculate_remaining_pay(self):
        """Calculate remaining pay after deductions and loan balance"""
        self.remaining_pay = self.final_payable_amount

    def approve_salary(self, approved_by):
        """Approve salary"""
        if approved_by.role not in ['admin', 'manager']:
            raise ValidationError('Only admin or manager can approve salaries.')
        
        self.status = 'approved'
        self.approved_by = approved_by
        self.approved_at = timezone.now()
        self.save()

    def mark_as_paid(self, paid_date=None):
        """Mark salary as paid"""
        self.status = 'paid'
        self.paid_date = paid_date or timezone.now().date()
        self.save()

    def reject_salary(self, rejected_by, reason):
        """Reject salary"""
        if rejected_by.role not in ['admin', 'manager']:
            raise ValidationError('Only admin or manager can reject salaries.')
        
        self.status = 'cancelled'
        self.rejection_reason = reason
        self.save()

    def get_salary_breakdown(self):
        """Get detailed salary breakdown for display"""
        return {
            'basic_pay': float(self.basic_pay),
            'increment': float(self.increment),
            'final_salary': float(self.final_salary),
            'per_day_salary': float(self.per_day_salary),
            'worked_days': self.worked_days,
            'total_days': self.total_days,
            'gross_salary': float(self.gross_salary),
            'allowances': {
                'house_rent': float(self.house_rent_allowance),
                'transport': float(self.transport_allowance),
                'medical': float(self.medical_allowance),
                'other': float(self.other_allowances),
                'total': float(self.total_allowances)
            },
            'deductions': {
                'general': float(self.deduction),
                'provident_fund': float(self.provident_fund),
                'professional_tax': float(self.professional_tax),
                'income_tax': float(self.income_tax),
                'other': float(self.other_deductions),
                'total': float(self.total_deductions)
            },
            'loan_balance': float(self.balance_loan),
            'net_salary': float(self.net_salary),
            'final_payable': float(self.final_payable_amount)
        }


class SalaryTemplate(models.Model):
    """Template for salary structure by designation"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, help_text="Template name")
    designation = models.ForeignKey('Designation', on_delete=models.CASCADE, related_name='salary_templates')
    office = models.ForeignKey('Office', on_delete=models.CASCADE, related_name='salary_templates')
    
    # Salary structure
    basic_pay = models.DecimalField(max_digits=10, decimal_places=2)
    house_rent_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    transport_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    medical_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_allowances = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Default deductions (as percentage)
    provident_fund_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=12.0)
    professional_tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Salary Template"
        verbose_name_plural = "Salary Templates"
        unique_together = ['designation', 'office']
        ordering = ['designation__name', 'office__name']

    def __str__(self):
        return f"{self.name} - {self.designation.name} ({self.office.name})"

    def apply_to_employee(self, employee, salary_month):
        """Apply this template to create a salary for an employee"""
        if employee.designation != self.designation or employee.office != self.office:
            raise ValidationError('Employee designation or office does not match template.')
        
        # Create salary record
        salary = Salary.objects.create(
            employee=employee,
            basic_pay=self.basic_pay,
            house_rent_allowance=self.house_rent_allowance,
            transport_allowance=self.transport_allowance,
            medical_allowance=self.medical_allowance,
            other_allowances=self.other_allowances,
            provident_fund=self.basic_pay * (self.provident_fund_percentage / 100),
            professional_tax=self.professional_tax,
            salary_month=salary_month,
            attendance_based=True,
            is_auto_calculated=True
        )
        
        return salary
