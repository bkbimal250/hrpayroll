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

class SalarySerializer(serializers.ModelSerializer):
    """Comprehensive serializer for Salary model"""
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    employee_email = serializers.CharField(source='employee.email', read_only=True)
    employee_employee_id = serializers.CharField(source='employee.employee_id', read_only=True)
    employee_office_name = serializers.CharField(source='employee.office.name', read_only=True)
    employee_department_name = serializers.CharField(source='employee.department.name', read_only=True)
    employee_designation_name = serializers.CharField(source='employee.designation.name', read_only=True)
    employee_pay_bank_name = serializers.CharField(source='employee.pay_bank_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    # Auto-calculated fields
    final_salary = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    per_day_salary = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    gross_salary = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    total_allowances = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    total_deductions = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    net_salary = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    final_payable_amount = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    
    # Salary breakdown
    salary_breakdown = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Salary
        fields = [
            'id', 'employee', 'employee_name', 'employee_email', 'employee_employee_id',
            'employee_office_name', 'employee_department_name', 'employee_designation_name',
            'employee_pay_bank_name', 'basic_pay', 'per_day_pay', 'increment', 'total_days', 'worked_days', 'previous_month_salary', 'deduction', 'balance_loan',
            'remaining_pay', 'salary_month', 'pay_date', 'paid_date', 'payment_method', 'Bank_name', 'status', 
            'approved_by', 'approved_by_name', 'approved_at', 'notes', 'status_reason', 
            'is_auto_calculated', 'attendance_based', 'created_by', 'created_by_name', 
            'created_at', 'updated_at', 'final_salary', 'per_day_salary', 'gross_salary', 
            'total_allowances', 'total_deductions', 'net_salary', 'final_payable_amount', 
            'salary_breakdown'
        ]
        read_only_fields = [
            'id', 'approved_at', 'created_at', 'updated_at', 'final_salary', 'per_day_salary',
            'gross_salary', 'total_allowances', 'total_deductions', 'net_salary', 'final_payable_amount'
        ]
    
    def get_salary_breakdown(self, obj):
        """Get detailed salary breakdown"""
        return obj.get_salary_breakdown()
    
    def validate(self, attrs):
        """Validate salary data"""
        # Note: worked_days can exceed total_days when including Sundays as working days
        # This is intentional for salary calculation purposes
        
        # Ensure basic_pay is positive
        basic_pay = attrs.get('basic_pay')
        if basic_pay is not None and basic_pay <= 0:
            raise serializers.ValidationError('Basic pay must be greater than zero.')
        
        return attrs

class SalaryListSerializer(serializers.ModelSerializer):
    """Lightweight salary serializer for list/table responses."""
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    employee_employee_id = serializers.CharField(source='employee.employee_id', read_only=True)
    employee_office_name = serializers.CharField(source='employee.office.name', read_only=True)
    employee_department_name = serializers.CharField(source='employee.department.name', read_only=True)
    employee_designation_name = serializers.CharField(source='employee.designation.name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)

    class Meta:
        model = Salary
        fields = [
            'id', 'employee', 'employee_name', 'employee_employee_id',
            'employee_office_name', 'employee_department_name',
            'employee_designation_name', 'basic_pay', 'per_day_pay',
            'increment', 'total_days', 'worked_days', 'deduction',
            'balance_loan', 'previous_month_salary', 'remaining_pay',
            'salary_month', 'pay_date', 'paid_date', 'payment_method',
            'Bank_name', 'status', 'approved_by', 'approved_by_name',
            'approved_at', 'created_by', 'created_by_name', 'created_at',
            'updated_at', 'final_salary', 'gross_salary', 'net_salary',
            'final_payable_amount'
        ]
        read_only_fields = fields


class PayrollAdminSerializer(SalarySerializer):
    """Privileged payroll serializer for admin/accountant payroll operations."""
    class Meta(SalarySerializer.Meta):
        fields = SalarySerializer.Meta.fields
        read_only_fields = SalarySerializer.Meta.read_only_fields

class SalaryCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating salary records"""
    class Meta:
        model = Salary
        fields = [
            'employee', 'basic_pay', 'per_day_pay', 'increment', 'total_days', 'worked_days',
            'deduction', 'balance_loan', 'previous_month_salary', 'salary_month', 'pay_date', 'payment_method', 'Bank_name',
            'notes', 'attendance_based', 'status'
        ]
    
    def validate_employee(self, value):
        """Validate that the user exists and is active"""
        if not value.is_active:
            raise serializers.ValidationError('Cannot create salary for inactive users.')
        return value
    
    def validate_salary_month(self, value):
        """Validate salary month format"""
        # Ensure it's the first day of the month
        if value.day != 1:
            raise serializers.ValidationError('Salary month must be the first day of the month.')
        return value
    
    def create(self, validated_data):
        """Create salary record with current user as creator"""
        validated_data['created_by'] = self.context['request'].user
        
        # If Bank_name is not provided, use employee's pay_bank_name
        if not validated_data.get('Bank_name') and validated_data.get('employee'):
            employee = validated_data['employee']
            if employee.pay_bank_name:
                validated_data['Bank_name'] = employee.pay_bank_name
        
        return super().create(validated_data)

class SalaryUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating salary records"""
    class Meta:
        model = Salary
        fields = [
            'basic_pay', 'per_day_pay', 'increment', 'total_days', 'worked_days', 'previous_month_salary', 'deduction', 'balance_loan',
            'pay_date', 'payment_method', 'Bank_name', 'notes', 'attendance_based'
        ]
    
    def validate(self, attrs):
        """Validate salary update data"""
        # Note: worked_days can exceed total_days when including Sundays as working days
        # This is intentional for salary calculation purposes
        
        return attrs

class SalaryApprovalSerializer(serializers.ModelSerializer):
    """Serializer for salary status changes (pending, paid, hold)"""
    class Meta:
        model = Salary
        fields = ['status', 'notes', 'status_reason']
    
    def validate_status(self, value):
        """Validate status change"""
        if value not in ['pending', 'paid', 'hold']:
            raise serializers.ValidationError("Status must be either 'pending', 'paid', or 'hold'.")
        return value

class SalaryPaymentSerializer(serializers.ModelSerializer):
    """Serializer for marking salary as paid"""
    class Meta:
        model = Salary
        fields = ['paid_date', 'payment_method', 'Bank_name']
    
    def validate_paid_date(self, value):
        """Validate payment date"""
        from django.utils import timezone
        if value and value > timezone.now().date():
            raise serializers.ValidationError("Payment date cannot be in the future.")
        return value

class SalaryTemplateSerializer(serializers.ModelSerializer):
    """Serializer for SalaryTemplate model"""
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = SalaryTemplate
        fields = [
            'id', 'name', 'designation_name', 'office_name', 'basic_pay', 'per_day_pay',
            'is_active', 'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, attrs):
        """Validate template data"""
        designation_name = attrs.get('designation_name')
        office_name = attrs.get('office_name')
        
        # Check for duplicate template for same designation and office
        if designation_name and office_name:
            queryset = SalaryTemplate.objects.filter(designation_name=designation_name, office_name=office_name)
            if self.instance:
                queryset = queryset.exclude(id=self.instance.id)
            
            if queryset.exists():
                raise serializers.ValidationError(
                    'A salary template already exists for this designation and office combination.'
                )
        
        return attrs

class SalaryTemplateCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating salary templates"""
    class Meta:
        model = SalaryTemplate
        fields = [
            'name', 'designation_name', 'office_name', 'basic_pay', 'per_day_pay', 'is_active'
        ]
    
    def create(self, validated_data):
        """Create template with current user as creator"""
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)

class SalaryBulkCreateSerializer(serializers.Serializer):
    """Serializer for bulk salary creation"""
    employee_ids = serializers.ListField(child=serializers.UUIDField())
    salary_month = serializers.DateField()
    template_id = serializers.UUIDField(required=False)
    basic_pay = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    increment = serializers.DecimalField(max_digits=15, decimal_places=2, default=0)
    attendance_based = serializers.BooleanField(default=True)
    
    def validate_employee_ids(self, value):
        """Validate employee IDs"""
        if not value:
            raise serializers.ValidationError("Employee IDs list cannot be empty.")
        
        # Check for duplicate IDs
        if len(value) != len(set(value)):
            raise serializers.ValidationError("Duplicate employee IDs found.")
        
        return value
    
    def validate_salary_month(self, value):
        """Validate salary month"""
        if value.day != 1:
            raise serializers.ValidationError("Salary month must be the first day of the month.")
        return value
    
    def validate(self, attrs):
        """Validate bulk creation data"""
        template_id = attrs.get('template_id')
        basic_pay = attrs.get('basic_pay')
        
        if not template_id and not basic_pay:
            raise serializers.ValidationError(
                "Either template_id or basic_pay must be provided."
            )
        
        return attrs

class SalaryReportSerializer(serializers.Serializer):
    """Serializer for salary reports"""
    office_id = serializers.UUIDField(required=False)
    department_id = serializers.UUIDField(required=False)
    year = serializers.IntegerField()
    month = serializers.IntegerField(min_value=1, max_value=12)
    include_inactive = serializers.BooleanField(required=False, default=False)
    employment_status = serializers.ChoiceField(
        choices=CustomUser.EMPLOYMENT_STATUS_CHOICES,
        required=False
    )
    # Allow filtering by standard salary statuses plus a special 'no_salary' bucket
    status = serializers.ChoiceField(
        choices=list(Salary.SALARY_STATUS_CHOICES) + [('no_salary', 'No Salary')],
        required=False
    )
    
    def validate(self, attrs):
        """Validate report parameters"""
        year = attrs.get('year')
        month = attrs.get('month')
        
        if year < 2020 or year > 2030:
            raise serializers.ValidationError("Invalid year.")
        
        return attrs

class SalarySummarySerializer(serializers.Serializer):
    """Serializer for salary summary statistics"""
    # Totals
    total_users = serializers.IntegerField()
    total_salaries = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)

    # By status
    paid_salaries = serializers.IntegerField()
    paid_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    pending_salaries = serializers.IntegerField()
    pending_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    hold_salaries = serializers.IntegerField()
    hold_amount = serializers.DecimalField(max_digits=12, decimal_places=2)

    # Stats
    average_salary = serializers.DecimalField(max_digits=15, decimal_places=2)
    highest_salary = serializers.DecimalField(max_digits=15, decimal_places=2)
    lowest_salary = serializers.DecimalField(max_digits=15, decimal_places=2)

    # Month labels
    month = serializers.CharField()
    month_ym = serializers.CharField()

class SalaryAutoCalculateSerializer(serializers.Serializer):
    """Serializer for auto-calculating salaries from attendance"""
    employee_ids = serializers.ListField(child=serializers.UUIDField(), required=False)
    salary_month = serializers.DateField()
    office_id = serializers.UUIDField(required=False)
    department_id = serializers.UUIDField(required=False)
    template_id = serializers.UUIDField(required=False)
    basic_pay = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    
    def validate_salary_month(self, value):
        """Validate salary month"""
        if value.day != 1:
            raise serializers.ValidationError("Salary month must be the first day of the month.")
        return value
    
    def validate(self, attrs):
        """Validate auto-calculation data"""
        template_id = attrs.get('template_id')
        basic_pay = attrs.get('basic_pay')
        employee_ids = attrs.get('employee_ids')
        
        if not template_id and not basic_pay:
            raise serializers.ValidationError(
                "Either template_id or basic_pay must be provided."
            )
        
        if not employee_ids and not attrs.get('office_id') and not attrs.get('department_id'):
            raise serializers.ValidationError(
                "Either employee_ids, office_id, or department_id must be provided."
            )
        
        return attrs
