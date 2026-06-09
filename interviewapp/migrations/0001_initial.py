# Generated manually because the local Python launchers are unavailable in this workspace.

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.utils import timezone

import interviewapp.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="InterviewCandidate",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("full_name", models.CharField(blank=True, max_length=200)),
                ("phone", models.CharField(db_index=True, max_length=20)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("position_applied", models.CharField(blank=True, db_index=True, max_length=150)),
                ("experience_years", models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ("current_city", models.CharField(blank=True, max_length=100)),
                ("source", models.CharField(blank=True, db_index=True, max_length=100)),
                ("reference_name", models.CharField(blank=True, max_length=150)),
                ("expected_salary", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("current_salary", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("notice_period", models.CharField(blank=True, max_length=100)),
                ("remarks", models.TextField(blank=True)),
                ("aadhaar_number", models.CharField(blank=True, db_index=True, max_length=12)),
                ("pan_number", models.CharField(blank=True, db_index=True, max_length=10)),
                (
                    "resume",
                    models.FileField(
                        blank=True,
                        null=True,
                        upload_to=interviewapp.models.candidate_resume_upload_path,
                    ),
                ),
                (
                    "photo",
                    models.ImageField(
                        blank=True,
                        null=True,
                        upload_to=interviewapp.models.candidate_photo_upload_path,
                    ),
                ),
                ("token_number", models.CharField(blank=True, db_index=True, max_length=20, unique=True)),
                ("checkin_time", models.DateTimeField(blank=True, null=True)),
                ("interview_date", models.DateField(db_index=True, default=timezone.localdate)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("waiting", "Waiting"),
                            ("hr_round_done", "HR Round Done"),
                            ("manager_round_done", "Manager Round Done"),
                            ("selected", "Selected"),
                            ("rejected", "Rejected"),
                            ("on_hold", "On Hold"),
                            ("no_show", "No Show"),
                            ("converted", "Converted"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=25,
                    ),
                ),
                (
                    "hr_round_status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("passed", "Passed"),
                            ("failed", "Failed"),
                            ("on_hold", "On Hold"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("hr_round_at", models.DateTimeField(blank=True, null=True)),
                ("hr_round_remarks", models.TextField(blank=True)),
                (
                    "manager_round_status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("passed", "Passed"),
                            ("failed", "Failed"),
                            ("on_hold", "On Hold"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("manager_round_at", models.DateTimeField(blank=True, null=True)),
                ("manager_round_remarks", models.TextField(blank=True)),
                ("converted_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "converted_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="converted_interview_candidates",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "converted_employee",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="source_interview_candidate",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_interview_candidates",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "hr_round_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="interview_hr_rounds",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "manager_round_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="interview_manager_rounds",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="updated_interview_candidates",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-checkin_time", "-created_at"],
            },
        ),
        migrations.CreateModel(
            name="CandidateStatusLog",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "action_type",
                    models.CharField(
                        choices=[
                            ("checkin", "Check-in"),
                            ("update", "Update"),
                            ("hr_round", "HR Round"),
                            ("manager_round", "Manager Round"),
                            ("final_status", "Final Status"),
                            ("remarks", "Remarks"),
                            ("converted", "Converted"),
                        ],
                        max_length=30,
                    ),
                ),
                ("old_status", models.CharField(blank=True, max_length=25)),
                ("new_status", models.CharField(blank=True, max_length=25)),
                ("changed_at", models.DateTimeField(auto_now_add=True)),
                ("remarks", models.TextField(blank=True)),
                (
                    "candidate",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="status_logs",
                        to="interviewapp.interviewcandidate",
                    ),
                ),
                (
                    "changed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="interview_status_changes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-changed_at"],
            },
        ),
        migrations.AddIndex(
            model_name="interviewcandidate",
            index=models.Index(fields=["interview_date", "phone"], name="interviewap_intervi_580da1_idx"),
        ),
        migrations.AddIndex(
            model_name="interviewcandidate",
            index=models.Index(fields=["status", "interview_date"], name="interviewap_status_098b38_idx"),
        ),
        migrations.AddConstraint(
            model_name="interviewcandidate",
            constraint=models.UniqueConstraint(
                fields=("phone", "interview_date"),
                name="unique_interview_checkin_phone_date",
            ),
        ),
    ]
