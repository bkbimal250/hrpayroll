from rest_framework import serializers
from django.core.exceptions import ValidationError
from rest_framework.fields import DateField, DateTimeField

class NullableDateField(DateField):
    """Custom DateField that converts empty strings to None"""
    def to_internal_value(self, data):
        if data == "" or data is None:
            return None
        return super().to_internal_value(data)
    
    def validate_empty_values(self, data):
        """Override to handle empty strings"""
        if data == "":
            return (True, None)
        return super().validate_empty_values(data)
class NullableDateTimeField(DateTimeField):
    """Custom DateTimeField that converts empty strings to None"""
    def to_internal_value(self, data):
        if data == "" or data is None:
            return None
        return super().to_internal_value(data)
    
    def validate_empty_values(self, data):
        """Override to handle empty strings"""
        if data == "":
            return (True, None)
        return super().validate_empty_values(data)
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
import uuid
from ..models import (
    CustomUser, Office, Device, DeviceUser, Attendance, Leave, Document, 
    Notification, SystemSettings, AttendanceLog, ESSLAttendanceLog, 
    WorkingHoursSettings, DocumentTemplate, GeneratedDocument, Resignation,
    Department, Designation, Salary, SalaryTemplate, Shift, EmployeeShiftAssignment,
    EmployeeStatusAuditLog, BiometricAssignmentHistory, PasswordChangeHistory, AttendanceAuditLog,
    DuplicatePunchAttempt, UnmatchedBiometricPunch
)

from .auth_serializers import CustomUserSerializer, LightweightUserSummarySerializer

class DocumentSerializer(serializers.ModelSerializer):
    """Serializer for Document model"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    uploaded_by_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)
    file_url = serializers.SerializerMethodField()
    file_type = serializers.SerializerMethodField()
    file_size = serializers.SerializerMethodField()
    salary_month = serializers.SerializerMethodField()
    
    # Include full user objects
    user = CustomUserSerializer(read_only=True)
    uploaded_by = CustomUserSerializer(read_only=True)
    
    class Meta:
        model = Document
        fields = [
            'id', 'title', 'document_type', 'file', 'description', 
            'user', 'user_name', 'uploaded_by', 'uploaded_by_name',
            'created_at', 'updated_at', 'file_url', 'file_type', 'file_size', 'salary_month'
        ]
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def get_file_url(self, obj):
        """Get the full URL for the file"""
        try:
            if obj.file:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(obj.file.url)
                return obj.file.url
        except (FileNotFoundError, OSError, ValueError):
            # File doesn't exist or can't be accessed
            return None
        return None
    
    def get_file_type(self, obj):
        """Get the file type from the filename"""
        try:
            if obj.file:
                return obj.file.name.split('.')[-1].lower() if '.' in obj.file.name else 'unknown'
        except (FileNotFoundError, OSError, ValueError, AttributeError):
            # File doesn't exist or can't be accessed
            return 'unknown'
        return None
    
    def get_file_size(self, obj):
        """Get the file size in bytes"""
        try:
            if obj.file and hasattr(obj.file, 'size'):
                return obj.file.size
        except (FileNotFoundError, OSError, ValueError):
            # File doesn't exist or can't be accessed
            return 0
        return 0

    def get_salary_month(self, obj):
        """Extract or calculate the salary month for a document"""
        if obj.document_type == 'salary_slip':
            import re
            title = obj.title
            
            # Pattern for standard month names
            months_pattern = r'\b(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b'
            year_pattern = r'\b(20\d{2})\b'
            
            month_match = re.search(months_pattern, title, re.IGNORECASE)
            year_match = re.search(year_pattern, title)
            
            month = month_match.group(0).title() if month_match else None
            year = year_match.group(0) if year_match else None
            
            if month and year:
                return f"{month} {year}"
            elif month:
                return month
            elif year:
                return year
            
            if obj.created_at:
                return obj.created_at.strftime("%B %Y")
        return "N/A"

class DocumentListSerializer(serializers.ModelSerializer):
    """Lightweight document serializer for table/list responses."""
    user = LightweightUserSummarySerializer(read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    uploaded_by_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)
    file_url = serializers.SerializerMethodField()
    file_type = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            'id', 'title', 'document_type', 'description', 'user', 'user_name',
            'uploaded_by', 'uploaded_by_name', 'created_at', 'updated_at',
            'file_url', 'file_type'
        ]
        read_only_fields = fields

    def get_file_url(self, obj):
        return DocumentSerializer.get_file_url(self, obj)

    def get_file_type(self, obj):
        return DocumentSerializer.get_file_type(self, obj)

class DocumentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating documents"""
    class Meta:
        model = Document
        fields = ['title', 'document_type', 'file', 'description', 'user']
    
    def validate_user(self, value):
        """Validate that the user exists and is active"""
        if not value.is_active:
            raise serializers.ValidationError("Cannot upload documents for inactive users")
        return value
    
    def to_representation(self, instance):
        """Return full document data after creation"""
        return DocumentSerializer(instance, context=self.context).data

class DocumentTemplateSerializer(serializers.ModelSerializer):
    """Serializer for DocumentTemplate model"""
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = DocumentTemplate
        fields = [
            'id', 'name', 'document_type', 'template_content', 'is_active',
            'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class GeneratedDocumentSerializer(serializers.ModelSerializer):
    """Serializer for GeneratedDocument model"""
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    employee_email = serializers.CharField(source='employee.email', read_only=True)
    employee_employee_id = serializers.CharField(source='employee.employee_id', read_only=True)
    employee_biometric_id = serializers.CharField(source='employee.biometric_id', read_only=True)
    employee_office = serializers.CharField(source='employee.office.name', read_only=True)
    generated_by_name = serializers.CharField(source='generated_by.get_full_name', read_only=True)
    template_name = serializers.CharField(source='template.name', read_only=True)
    salary_month = serializers.SerializerMethodField()
    
    class Meta:
        model = GeneratedDocument
        fields = [
            'id', 'employee', 'employee_name', 'employee_email', 'template', 'template_name',
            'employee_employee_id', 'employee_biometric_id', 'employee_office', 'document_type',
            'title', 'content', 'pdf_file', 'generated_by', 'generated_by_name', 'generated_at',
            'sent_at', 'is_sent', 'offer_data', 'increment_data', 'salary_data', 'salary_month'
        ]
        read_only_fields = ['id', 'generated_at']

    def get_salary_month(self, obj):
        """Extract or calculate the salary month for a generated document"""
        if obj.document_type == 'salary_slip':
            month = None
            year = None
            if obj.salary_data:
                try:
                    data = obj.salary_data
                    if isinstance(data, str):
                        import json
                        data = json.loads(data)
                    month = data.get('salary_month', '')
                    year = data.get('salary_year', '')
                except Exception:
                    pass
            
            if month and year:
                return f"{str(month).strip().title()} {str(year).strip()}"
            elif month:
                return str(month).strip().title()
            elif year:
                return str(year).strip()
            
            # Fallback to title regex search
            import re
            title = obj.title
            months_pattern = r'\b(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b'
            year_pattern = r'\b(20\d{2})\b'
            
            month_match = re.search(months_pattern, title, re.IGNORECASE)
            year_match = re.search(year_pattern, title)
            
            month = month_match.group(0).title() if month_match else None
            year = year_match.group(0) if year_match else None
            
            if month and year:
                return f"{month} {year}"
            elif month:
                return month
            elif year:
                return year
            
            if obj.generated_at:
                return obj.generated_at.strftime("%B %Y")
        return "N/A"

class GeneratedDocumentListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for GeneratedDocument list view (excludes content)"""
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    employee_employee_id = serializers.CharField(source='employee.employee_id', read_only=True)
    employee_office = serializers.CharField(source='employee.office.name', read_only=True)
    generated_by_name = serializers.CharField(source='generated_by.get_full_name', read_only=True)
    template_name = serializers.CharField(source='template.name', read_only=True)
    
    class Meta:
        model = GeneratedDocument
        fields = [
            'id', 'employee', 'employee_name', 'employee_employee_id',
            'employee_office', 'template', 'template_name', 'document_type',
            'title', 'generated_by', 'generated_by_name', 'generated_at',
            'sent_at', 'is_sent'
        ]
        read_only_fields = ['id', 'generated_at']

class DocumentGenerationSerializer(serializers.Serializer):
    """Serializer for document generation requests"""
    employee_id = serializers.UUIDField()
    document_type = serializers.ChoiceField(choices=DocumentTemplate.DOCUMENT_TYPE_CHOICES)
    template_id = serializers.UUIDField(required=False)
    
    # Salary ID for auto-fetching salary data from DB (no need to send all fields)
    salary_id = serializers.UUIDField(required=False, allow_null=True)
    
    # Salary increment ID for auto-fetching data
    increment_id = serializers.UUIDField(required=False, allow_null=True)
    
    # Offer letter specific fields
    position = serializers.CharField(required=False, allow_blank=True)
    start_date = serializers.DateField(required=False, allow_null=True)
    starting_salary = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    
    # Salary increment specific fields
    previous_salary = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    increment_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    new_salary = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    effective_date = serializers.DateField(required=False, allow_null=True)
    
    # Salary slip specific fields - increased max_digits to handle larger values
    salary_month = serializers.CharField(required=False, allow_blank=True)
    salary_year = serializers.CharField(required=False, allow_blank=True)
    basic_salary = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    extra_days_pay = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    
    # Additional salary slip fields from frontend - increased max_digits
    total_days = serializers.IntegerField(required=False)
    worked_days = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    per_day_pay = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    gross_salary = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    net_salary = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    total_gross_salary = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    absent_days = serializers.IntegerField(required=False)
    total_deductions = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    final_salary = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    basic_pay = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    status = serializers.CharField(required=False, allow_blank=True)
    office_name = serializers.CharField(required=False, allow_blank=True)
    department = serializers.CharField(required=False, allow_blank=True)
    designation = serializers.CharField(required=False, allow_blank=True)
    employee_id = serializers.CharField(required=False, allow_blank=True)
    full_name = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    date_of_joining = serializers.DateField(required=False, allow_null=True)
    bank_name = serializers.CharField(required=False, allow_blank=True)
    account_number = serializers.CharField(required=False, allow_blank=True)
    ifsc_code = serializers.CharField(required=False, allow_blank=True)
    pan_number = serializers.CharField(required=False, allow_blank=True)
    aadhar_number = serializers.CharField(required=False, allow_blank=True)
    uan_number = serializers.CharField(required=False, allow_blank=True)
    esi_number = serializers.CharField(required=False, allow_blank=True)
    pf_number = serializers.CharField(required=False, allow_blank=True)
    created_at = NullableDateTimeField(required=False, allow_null=True)
    updated_at = NullableDateTimeField(required=False, allow_null=True)
    
    # Handle field variations from different frontends
    employee_name = serializers.CharField(required=False, allow_blank=True)
    employee_id_number = serializers.CharField(required=False, allow_blank=True)
    employee_employee_id = serializers.CharField(required=False, allow_blank=True)
    employee_designation = serializers.CharField(required=False, allow_blank=True)
    employee_department = serializers.CharField(required=False, allow_blank=True)
    employee_office = serializers.CharField(required=False, allow_blank=True)
    employee_email = serializers.EmailField(required=False, allow_blank=True)
    employee_phone = serializers.CharField(required=False, allow_blank=True)
    
    # Additional fields from payload - increased max_digits for consistency
    increment = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    deduction = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    loan_deduction = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    remaining_pay = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    payment_method = serializers.CharField(required=False, allow_blank=True)
    pay_date = serializers.DateField(required=False, allow_null=True)
    paid_date = serializers.DateField(required=False, allow_null=True)
    status_reason = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    approved_by = serializers.CharField(required=False, allow_blank=True)
    approved_at = serializers.DateTimeField(required=False, allow_null=True)
    total_salary = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    
    # Common fields
    custom_message = serializers.CharField(required=False, allow_blank=True)
    send_email = serializers.BooleanField(default=True)
    

    def validate(self, attrs):
        document_type = attrs.get('document_type')
        
        if document_type == 'offer_letter':
            if not attrs.get('position'):
                raise serializers.ValidationError("Position is required for offer letters")
            if not attrs.get('start_date'):
                raise serializers.ValidationError("Start date is required for offer letters")
            if not attrs.get('starting_salary'):
                raise serializers.ValidationError("Starting salary is required for offer letters")
                
        elif document_type == 'salary_increment':
            if not attrs.get('previous_salary'):
                raise serializers.ValidationError("Previous salary is required for salary increment letters")
            if not attrs.get('new_salary'):
                raise serializers.ValidationError("New salary is required for salary increment letters")
            if not attrs.get('effective_date'):
                raise serializers.ValidationError("Effective date is required for salary increment letters")
        
        return attrs
