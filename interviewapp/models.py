import os
import uuid

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone


def candidate_resume_upload_path(instance, filename):
    return os.path.join("interview", "resumes", str(instance.id), filename)


def candidate_photo_upload_path(instance, filename):
    return os.path.join("interview", "photos", str(instance.id), filename)


class InterviewCandidate(models.Model):
    STATUS_PENDING = "pending"
    STATUS_WAITING = "waiting"
    STATUS_HR_ROUND_DONE = "hr_round_done"
    STATUS_MANAGER_ROUND_DONE = "manager_round_done"
    STATUS_SELECTED = "selected"
    STATUS_REJECTED = "rejected"
    STATUS_ON_HOLD = "on_hold"
    STATUS_NO_SHOW = "no_show"
    STATUS_CONVERTED = "converted"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_WAITING, "Waiting"),
        (STATUS_HR_ROUND_DONE, "HR Round Done"),
        (STATUS_MANAGER_ROUND_DONE, "Manager Round Done"),
        (STATUS_SELECTED, "Selected"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_ON_HOLD, "On Hold"),
        (STATUS_NO_SHOW, "No Show"),
        (STATUS_CONVERTED, "Converted"),
    ]

    ROUND_PENDING = "pending"
    ROUND_PASSED = "passed"
    ROUND_FAILED = "failed"
    ROUND_ON_HOLD = "on_hold"

    ROUND_STATUS_CHOICES = [
        (ROUND_PENDING, "Pending"),
        (ROUND_PASSED, "Passed"),
        (ROUND_FAILED, "Failed"),
        (ROUND_ON_HOLD, "On Hold"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    full_name = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=20, db_index=True)
    email = models.EmailField(blank=True)
    position_applied = models.CharField(max_length=150, blank=True, db_index=True)
    experience_years = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    current_city = models.CharField(max_length=100, blank=True)
    source = models.CharField(max_length=100, blank=True, db_index=True)
    reference_name = models.CharField(max_length=150, blank=True)
    expected_salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    current_salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    notice_period = models.CharField(max_length=100, blank=True)
    remarks = models.TextField(blank=True)

    aadhaar_number = models.CharField(max_length=12, blank=True, db_index=True)
    pan_number = models.CharField(max_length=10, blank=True, db_index=True)

    resume = models.FileField(upload_to=candidate_resume_upload_path, null=True, blank=True)
    photo = models.ImageField(upload_to=candidate_photo_upload_path, null=True, blank=True)

    token_number = models.CharField(max_length=20, unique=True, db_index=True, blank=True)
    checkin_time = models.DateTimeField(null=True, blank=True)
    interview_date = models.DateField(default=timezone.localdate, db_index=True)

    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)

    hr_round_status = models.CharField(
        max_length=20,
        choices=ROUND_STATUS_CHOICES,
        default=ROUND_PENDING,
        db_index=True,
    )
    hr_round_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="interview_hr_rounds",
    )
    hr_round_at = models.DateTimeField(null=True, blank=True)
    hr_round_remarks = models.TextField(blank=True)

    manager_round_status = models.CharField(
        max_length=20,
        choices=ROUND_STATUS_CHOICES,
        default=ROUND_PENDING,
        db_index=True,
    )
    manager_round_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="interview_manager_rounds",
    )
    manager_round_at = models.DateTimeField(null=True, blank=True)
    manager_round_remarks = models.TextField(blank=True)

    converted_employee = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="source_interview_candidate",
    )
    converted_at = models.DateTimeField(null=True, blank=True)
    converted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="converted_interview_candidates",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_interview_candidates",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="updated_interview_candidates",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-checkin_time", "-created_at"]
        indexes = [
            models.Index(fields=["interview_date", "phone"]),
            models.Index(fields=["status", "interview_date"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["phone", "interview_date"],
                name="unique_interview_checkin_phone_date",
            ),
        ]

    def __str__(self):
        name = self.full_name or "Walk-in Candidate"
        return f"{self.token_number} - {name}"

    def save(self, *args, **kwargs):
        if not self.token_number:
            self.token_number = self.generate_token_number(self.interview_date)
        super().save(*args, **kwargs)

    @classmethod
    def generate_token_number(cls, interview_date=None):
        interview_date = interview_date or timezone.localdate()
        year = interview_date.year
        prefix = f"INT-{year}-"

        with transaction.atomic():
            latest_token = (
                cls.objects.select_for_update()
                .filter(token_number__startswith=prefix)
                .order_by("-token_number")
                .values_list("token_number", flat=True)
                .first()
            )
            next_number = 1
            if latest_token:
                try:
                    next_number = int(latest_token.rsplit("-", 1)[-1]) + 1
                except (TypeError, ValueError):
                    next_number = cls.objects.filter(token_number__startswith=prefix).count() + 1

            while True:
                token = f"{prefix}{next_number:04d}"
                if not cls.objects.filter(token_number=token).exists():
                    return token
                next_number += 1


class CandidateStatusLog(models.Model):
    ACTION_CHECKIN = "checkin"
    ACTION_UPDATE = "update"
    ACTION_HR_ROUND = "hr_round"
    ACTION_MANAGER_ROUND = "manager_round"
    ACTION_FINAL_STATUS = "final_status"
    ACTION_REMARKS = "remarks"
    ACTION_CONVERTED = "converted"

    ACTION_TYPE_CHOICES = [
        (ACTION_CHECKIN, "Check-in"),
        (ACTION_UPDATE, "Update"),
        (ACTION_HR_ROUND, "HR Round"),
        (ACTION_MANAGER_ROUND, "Manager Round"),
        (ACTION_FINAL_STATUS, "Final Status"),
        (ACTION_REMARKS, "Remarks"),
        (ACTION_CONVERTED, "Converted"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    candidate = models.ForeignKey(
        InterviewCandidate,
        on_delete=models.CASCADE,
        related_name="status_logs",
    )
    action_type = models.CharField(max_length=30, choices=ACTION_TYPE_CHOICES)
    old_status = models.CharField(max_length=25, blank=True)
    new_status = models.CharField(max_length=25, blank=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="interview_status_changes",
    )
    changed_at = models.DateTimeField(auto_now_add=True)
    remarks = models.TextField(blank=True)

    class Meta:
        ordering = ["-changed_at"]

    def __str__(self):
        return f"{self.candidate.token_number}: {self.old_status} -> {self.new_status}"
