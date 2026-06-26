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

class ShiftSerializer(serializers.ModelSerializer):
    """Serializer for Shift model"""
    office_name = serializers.CharField(source='office.name', read_only=True)
    employee_count = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Shift
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')
        extra_kwargs = {
            'office': {'required': False, 'allow_null': True}  # Make office optional and allow null
        }
    
    def validate(self, attrs):
        """Custom validation to handle office assignment"""
        # If office is not provided, it will be set in perform_create
        return attrs

    def get_employee_count(self, obj):
        """Get number of employees assigned to this shift"""
        return obj.employee_assignments.filter(is_active=True).count()

class EmployeeShiftAssignmentSerializer(serializers.ModelSerializer):
    """Serializer for EmployeeShiftAssignment model"""
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    shift_name = serializers.CharField(source='shift.name', read_only=True)
    office_name = serializers.CharField(source='shift.office.name', read_only=True)
    office_id = serializers.UUIDField(source='shift.office.id', read_only=True)
    shift_start_time = serializers.TimeField(source='shift.start_time', read_only=True)
    shift_end_time = serializers.TimeField(source='shift.end_time', read_only=True)
    
    class Meta:
        model = EmployeeShiftAssignment
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')
