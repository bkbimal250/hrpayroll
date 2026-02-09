from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from decimal import Decimal

from .models import SalaryIncrement, SalaryIncrementHistory, Holiday


@receiver(post_save, sender=SalaryIncrement)
def apply_salary_increment(sender, instance, created, **kwargs):
    """
    Apply salary increment automatically when approved.
    Runs only once.
    """

    # Only when approved
    if instance.status != 'approved':
        return

    # Prevent double-apply
    if instance.applied_at:
        return

    employee = instance.employee

    old_salary = employee.salary or Decimal('0.00')
    new_salary = instance.new_salary

    # Update base salary
    employee.salary = new_salary
    employee.save(update_fields=['salary'])

    # Create history
    SalaryIncrementHistory.objects.create(
        employee=employee,
        increment=instance,
        old_salary=old_salary,
        new_salary=new_salary,
        changed_by=instance.approved_by,
        remarks=f"{instance.increment_type} increment approved"
    )

    # Mark as applied
    instance.applied_at = timezone.now()
    instance.save(update_fields=['applied_at'])

@receiver(pre_save, sender=Holiday)
def update_holiday(sender, instance, **kwargs):
    """
    Placeholder for holiday-related pre-save logic.
    """
    if instance.is_paid and instance.double_pay_if_worked:
        # Potential future logic
        pass