import os
import re

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from .models import CandidateStatusLog, InterviewCandidate


PHONE_RE = re.compile(r"^\+?[0-9]{10,15}$")
AADHAAR_RE = re.compile(r"^[0-9]{12}$")
PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")

RESUME_EXTENSIONS = {".pdf", ".doc", ".docx"}
PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
RESUME_CONTENT_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
PHOTO_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_RESUME_SIZE = 5 * 1024 * 1024
MAX_PHOTO_SIZE = 3 * 1024 * 1024


def normalize_phone(value):
    if not value:
        return value
    return re.sub(r"[\s\-()]", "", value.strip())


def validate_phone(value):
    value = normalize_phone(value)
    if not value or not PHONE_RE.match(value):
        raise serializers.ValidationError("Enter a valid phone number with 10 to 15 digits.")
    return value


def validate_aadhaar(value):
    if not value:
        return ""
    value = value.replace(" ", "").replace("-", "")
    if not AADHAAR_RE.match(value):
        raise serializers.ValidationError("Aadhaar number must be exactly 12 digits.")
    return value


def validate_pan(value):
    if not value:
        return ""
    value = value.replace(" ", "").upper()
    if not PAN_RE.match(value):
        raise serializers.ValidationError("PAN number must match the AAAAA9999A format.")
    return value


def validate_upload(file_obj, allowed_extensions, allowed_content_types, max_size, label):
    if not file_obj:
        return file_obj
    ext = os.path.splitext(file_obj.name)[1].lower()
    if ext not in allowed_extensions:
        allowed = ", ".join(sorted(allowed_extensions))
        raise serializers.ValidationError(f"{label} must be one of: {allowed}.")
    content_type = getattr(file_obj, "content_type", "")
    if content_type and content_type not in allowed_content_types:
        raise serializers.ValidationError(f"{label} file type is not allowed.")
    if file_obj.size > max_size:
        size_mb = max_size // (1024 * 1024)
        raise serializers.ValidationError(f"{label} must be {size_mb}MB or smaller.")
    return file_obj


class CandidateStatusLogSerializer(serializers.ModelSerializer):
    changed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = CandidateStatusLog
        fields = [
            "id",
            "candidate",
            "action_type",
            "old_status",
            "new_status",
            "changed_by",
            "changed_by_name",
            "changed_at",
            "remarks",
        ]
        read_only_fields = fields

    def get_changed_by_name(self, obj):
        if not obj.changed_by:
            return None
        return obj.changed_by.get_full_name() or obj.changed_by.username


class InterviewCandidateSerializer(serializers.ModelSerializer):
    hr_round_by_name = serializers.SerializerMethodField()
    manager_round_by_name = serializers.SerializerMethodField()
    converted_employee_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()

    class Meta:
        model = InterviewCandidate
        fields = [
            "id",
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
            "aadhaar_number",
            "pan_number",
            "resume",
            "photo",
            "token_number",
            "checkin_time",
            "interview_date",
            "status",
            "hr_round_status",
            "hr_round_by",
            "hr_round_by_name",
            "hr_round_at",
            "hr_round_remarks",
            "manager_round_status",
            "manager_round_by",
            "manager_round_by_name",
            "manager_round_at",
            "manager_round_remarks",
            "converted_employee",
            "converted_employee_name",
            "converted_at",
            "converted_by",
            "created_by",
            "created_by_name",
            "updated_by",
            "updated_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "token_number",
            "checkin_time",
            "status",
            "hr_round_by",
            "hr_round_by_name",
            "hr_round_at",
            "manager_round_by",
            "manager_round_by_name",
            "manager_round_at",
            "converted_employee",
            "converted_employee_name",
            "converted_at",
            "converted_by",
            "created_by",
            "created_by_name",
            "updated_by",
            "updated_by_name",
            "created_at",
            "updated_at",
        ]

    def validate_phone(self, value):
        return validate_phone(value)

    def validate_aadhaar_number(self, value):
        return validate_aadhaar(value)

    def validate_pan_number(self, value):
        return validate_pan(value)

    def validate_resume(self, value):
        return validate_upload(value, RESUME_EXTENSIONS, RESUME_CONTENT_TYPES, MAX_RESUME_SIZE, "Resume")

    def validate_photo(self, value):
        return validate_upload(value, PHOTO_EXTENSIONS, PHOTO_CONTENT_TYPES, MAX_PHOTO_SIZE, "Photo")

    def get_hr_round_by_name(self, obj):
        return self._user_name(obj.hr_round_by)

    def get_manager_round_by_name(self, obj):
        return self._user_name(obj.manager_round_by)

    def get_converted_employee_name(self, obj):
        return self._user_name(obj.converted_employee)

    def get_created_by_name(self, obj):
        return self._user_name(obj.created_by)

    def get_updated_by_name(self, obj):
        return self._user_name(obj.updated_by)

    def _user_name(self, user):
        if not user:
            return None
        return user.get_full_name() or user.username


class CandidateCheckInSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewCandidate
        fields = [
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
            "aadhaar_number",
            "pan_number",
            "resume",
            "photo",
            "interview_date",
        ]
        extra_kwargs = {
            "full_name": {"required": False, "allow_blank": True},
            "phone": {"required": True},
            "interview_date": {"required": False},
        }

    def validate_phone(self, value):
        return validate_phone(value)

    def validate_aadhaar_number(self, value):
        return validate_aadhaar(value)

    def validate_pan_number(self, value):
        return validate_pan(value)

    def validate_resume(self, value):
        return validate_upload(value, RESUME_EXTENSIONS, RESUME_CONTENT_TYPES, MAX_RESUME_SIZE, "Resume")

    def validate_photo(self, value):
        return validate_upload(value, PHOTO_EXTENSIONS, PHOTO_CONTENT_TYPES, MAX_PHOTO_SIZE, "Photo")

    def validate(self, attrs):
        attrs["interview_date"] = attrs.get("interview_date") or timezone.localdate()
        return attrs

    def create(self, validated_data):
        interview_date = validated_data["interview_date"]
        with transaction.atomic():
            candidate = InterviewCandidate.objects.create(
                **validated_data,
                token_number=InterviewCandidate.generate_token_number(interview_date),
                checkin_time=timezone.now(),
                status=InterviewCandidate.STATUS_WAITING,
            )
            CandidateStatusLog.objects.create(
                candidate=candidate,
                action_type=CandidateStatusLog.ACTION_CHECKIN,
                old_status="",
                new_status=InterviewCandidate.STATUS_WAITING,
                remarks="Candidate checked in through public QR API.",
            )
            return candidate


class RoundStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=InterviewCandidate.ROUND_STATUS_CHOICES)
    remarks = serializers.CharField(required=False, allow_blank=True)


class FinalStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[
            (InterviewCandidate.STATUS_SELECTED, "Selected"),
            (InterviewCandidate.STATUS_REJECTED, "Rejected"),
            (InterviewCandidate.STATUS_ON_HOLD, "On Hold"),
            (InterviewCandidate.STATUS_NO_SHOW, "No Show"),
        ]
    )
    remarks = serializers.CharField(required=False, allow_blank=True)


class RemarksUpdateSerializer(serializers.Serializer):
    remarks = serializers.CharField(allow_blank=True)


class ConvertCandidateSerializer(serializers.Serializer):
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    username = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(required=False, allow_blank=True, write_only=True)
    confirm_password = serializers.CharField(required=False, allow_blank=True, write_only=True)
    employee_id = serializers.CharField(required=False, allow_blank=True)
    biometric_id = serializers.CharField(required=False, allow_blank=True)
    aadhaar_card = serializers.CharField(required=False, allow_blank=True)
    pan_card = serializers.CharField(required=False, allow_blank=True)
    joining_date = serializers.DateField(required=False)
    salary = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    address = serializers.CharField(required=False, allow_blank=True)
    pay_bank_name = serializers.CharField(required=False, allow_blank=True)
    bank_name = serializers.CharField(required=False, allow_blank=True)
    account_holder_name = serializers.CharField(required=False, allow_blank=True)
    account_number = serializers.CharField(required=False, allow_blank=True)
    ifsc_code = serializers.CharField(required=False, allow_blank=True)
    bank_branch_name = serializers.CharField(required=False, allow_blank=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from core.models import Department, Designation, Office

        self.fields["office"] = serializers.PrimaryKeyRelatedField(
            queryset=Office.objects.filter(is_active=True),
            required=False,
            allow_null=True,
        )
        self.fields["department"] = serializers.PrimaryKeyRelatedField(
            queryset=Department.objects.filter(is_active=True),
            required=False,
            allow_null=True,
        )
        self.fields["designation"] = serializers.PrimaryKeyRelatedField(
            queryset=Designation.objects.filter(is_active=True),
            required=False,
            allow_null=True,
        )

    def validate(self, attrs):
        candidate = self.context["candidate"]
        if candidate.converted_employee_id:
            raise serializers.ValidationError("Candidate is already converted to an employee.")
        if candidate.status != InterviewCandidate.STATUS_SELECTED:
            raise serializers.ValidationError("Only selected candidates can be converted to employees.")

        missing_fields = []
        if not candidate.phone:
            missing_fields.append("phone")
        full_name = candidate.full_name.strip() if candidate.full_name else ""
        first_name = attrs.get("first_name") or full_name.partition(" ")[0]
        if not first_name:
            missing_fields.append("first_name")
        if missing_fields:
            raise serializers.ValidationError({"missing_fields": missing_fields})

        User = get_user_model()
        if User.objects.filter(phone=candidate.phone).exists():
            raise serializers.ValidationError({"phone": "An employee with this candidate phone number already exists."})

        username = attrs.get("username")
        if username and User.objects.filter(username__iexact=username).exists():
            raise serializers.ValidationError({"username": "This username is already used by another employee."})

        employee_id = attrs.get("employee_id")
        if employee_id and User.objects.filter(employee_id__iexact=employee_id).exists():
            raise serializers.ValidationError({"employee_id": "This employee ID is already used."})

        biometric_id = attrs.get("biometric_id")
        if biometric_id and User.objects.filter(biometric_id__iexact=biometric_id).exists():
            raise serializers.ValidationError({"biometric_id": "This biometric ID is already used."})

        department = attrs.get("department")
        designation = attrs.get("designation")
        if department and designation and designation.department_id != department.id:
            raise serializers.ValidationError({"designation": "Designation must belong to the selected department."})

        password = attrs.get("password") or ""
        confirm_password = attrs.get("confirm_password") or ""
        if password or confirm_password:
            if password != confirm_password:
                raise serializers.ValidationError({"confirm_password": "Password and confirm password do not match."})
            validate_password(password)
        return attrs

    def save(self, **kwargs):
        candidate = self.context["candidate"]
        converted_by = self.context["request"].user
        User = get_user_model()

        full_name = candidate.full_name.strip() if candidate.full_name else ""
        candidate_first_name, _, candidate_last_name = full_name.partition(" ")
        first_name = self.validated_data.get("first_name") or candidate_first_name
        last_name = self.validated_data.get("last_name") or candidate_last_name
        base_username = self.validated_data.get("username") or candidate.phone or candidate.token_number
        username = base_username
        if User.objects.filter(username=username).exists():
            username = f"{base_username}-{candidate.token_number}".replace(" ", "-")

        with transaction.atomic():
            employee = User.objects.create_user(
                username=username,
                email=self.validated_data.get("email", candidate.email or ""),
                first_name=first_name,
                last_name=last_name,
                role="employee",
                phone=candidate.phone,
                address=self.validated_data.get("address") or candidate.current_city,
                aadhaar_card=self.validated_data.get("aadhaar_card", candidate.aadhaar_number),
                pan_card=self.validated_data.get("pan_card", candidate.pan_number),
                employee_id=self.validated_data.get("employee_id") or None,
                biometric_id=self.validated_data.get("biometric_id") or None,
                joining_date=self.validated_data.get("joining_date"),
                office=self.validated_data.get("office"),
                department=self.validated_data.get("department"),
                designation=self.validated_data.get("designation"),
                salary=self.validated_data.get("salary"),
                pay_bank_name=self.validated_data.get("pay_bank_name", ""),
                bank_name=self.validated_data.get("bank_name", ""),
                account_holder_name=self.validated_data.get("account_holder_name", ""),
                account_number=self.validated_data.get("account_number", ""),
                ifsc_code=self.validated_data.get("ifsc_code", ""),
                bank_branch_name=self.validated_data.get("bank_branch_name", ""),
            )
            if candidate.photo:
                employee.profile_picture = candidate.photo
            password = self.validated_data.get("password")
            if password:
                employee.set_password(password)
            else:
                employee.set_unusable_password()
            employee.save(update_fields=["password", "profile_picture"] if candidate.photo else ["password"])

            old_status = candidate.status
            candidate.converted_employee = employee
            candidate.converted_at = timezone.now()
            candidate.converted_by = converted_by
            candidate.status = InterviewCandidate.STATUS_CONVERTED
            candidate.updated_by = converted_by
            candidate.save(
                update_fields=[
                    "converted_employee",
                    "converted_at",
                    "converted_by",
                    "status",
                    "updated_by",
                    "updated_at",
                ]
            )
            CandidateStatusLog.objects.create(
                candidate=candidate,
                action_type=CandidateStatusLog.ACTION_CONVERTED,
                old_status=old_status,
                new_status=candidate.status,
                changed_by=converted_by,
                remarks="Selected candidate converted to employee.",
            )
            return employee
