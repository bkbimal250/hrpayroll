from django.contrib import admin

from .models import CandidateStatusLog, InterviewCandidate


@admin.register(InterviewCandidate)
class InterviewCandidateAdmin(admin.ModelAdmin):
    list_display = (
        "token_number",
        "full_name",
        "phone",
        "position_applied",
        "status",
        "hr_round_status",
        "manager_round_status",
        "source",
        "interview_date",
        "checkin_time",
    )
    search_fields = (
        "token_number",
        "phone",
        "full_name",
        "email",
        "aadhaar_number",
        "pan_number",
    )
    list_filter = (
        "status",
        "hr_round_status",
        "manager_round_status",
        "source",
        "position_applied",
        "interview_date",
    )
    readonly_fields = (
        "token_number",
        "checkin_time",
        "created_at",
        "updated_at",
        "converted_at",
    )
    fieldsets = (
        ("Basic Details", {
            "fields": (
                "full_name",
                "phone",
                "email",
                "position_applied",
                "experience_years",
                "current_city",
                "source",
                "reference_name",
                "expected_salary",
                "current_salary",
                "notice_period",
                "remarks",
            )
        }),
        ("KYC Details", {"fields": ("aadhaar_number", "pan_number")}),
        ("Uploads", {"fields": ("resume", "photo")}),
        ("Check-in Details", {"fields": ("token_number", "checkin_time", "interview_date", "status")}),
        ("HR Round", {"fields": ("hr_round_status", "hr_round_by", "hr_round_at", "hr_round_remarks")}),
        (
            "Manager Round",
            {
                "fields": (
                    "manager_round_status",
                    "manager_round_by",
                    "manager_round_at",
                    "manager_round_remarks",
                )
            },
        ),
        ("Conversion", {"fields": ("converted_employee", "converted_at", "converted_by")}),
        ("Tracking", {"fields": ("created_by", "updated_by", "created_at", "updated_at")}),
    )


@admin.register(CandidateStatusLog)
class CandidateStatusLogAdmin(admin.ModelAdmin):
    list_display = (
        "candidate",
        "action_type",
        "old_status",
        "new_status",
        "changed_by",
        "changed_at",
    )
    search_fields = (
        "candidate__token_number",
        "candidate__full_name",
        "candidate__phone",
        "remarks",
    )
    list_filter = ("action_type", "old_status", "new_status", "changed_at")
    readonly_fields = ("candidate", "action_type", "old_status", "new_status", "changed_by", "changed_at")
