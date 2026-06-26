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

class DeviceSerializer(serializers.ModelSerializer):
    """Serializer for Device model"""
    office_name = serializers.CharField(source='office.name', read_only=True)
    total_users = serializers.SerializerMethodField()
    mapped_users = serializers.SerializerMethodField()
    
    class Meta:
        model = Device
        fields = '__all__'
        read_only_fields = ('id', 'last_sync', 'created_at', 'updated_at')
    
    def get_total_users(self, obj):
        """Get total number of users on this device"""
        return obj.device_users.count()
    
    def get_mapped_users(self, obj):
        """Get number of mapped users on this device"""
        return obj.device_users.filter(is_mapped=True).count()

class AttendanceSerializer(serializers.ModelSerializer):
    """Serializer for Attendance model"""
    user = CustomUserSerializer(read_only=True)  # Include complete user object
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_employee_id = serializers.CharField(source='user.employee_id', read_only=True)
    user_office_name = serializers.CharField(source='user.office.name', read_only=True)
    device_name = serializers.CharField(source='device.name', read_only=True)
    
    class Meta:
        model = Attendance
        fields = '__all__'
        read_only_fields = ('id', 'total_hours', 'day_status', 'is_late', 'late_minutes', 'created_at', 'updated_at')

class AttendanceCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating attendance records"""
    class Meta:
        model = Attendance
        fields = ['user', 'date', 'check_in_time', 'check_out_time', 'status', 'day_status', 'device', 'notes']

class AttendanceLogSerializer(serializers.ModelSerializer):
    """Serializer for AttendanceLog model"""
    changed_by_name = serializers.CharField(source='changed_by.get_full_name', read_only=True)
    
    class Meta:
        model = AttendanceLog
        fields = '__all__'
        read_only_fields = ('id', 'created_at')

class ESSLAttendanceLogSerializer(serializers.ModelSerializer):
    """Serializer for ESSL attendance logs"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    device_name = serializers.CharField(source='device.name', read_only=True)
    
    class Meta:
        model = ESSLAttendanceLog
        fields = '__all__'
        read_only_fields = ('id', 'created_at')

class DuplicatePunchAttemptSerializer(serializers.ModelSerializer):
    """Serializer for duplicate biometric punch review records"""
    device_name = serializers.CharField(source='device.name', read_only=True)

    class Meta:
        model = DuplicatePunchAttempt
        fields = '__all__'
        read_only_fields = ('id', 'created_at')

class UnmatchedBiometricPunchSerializer(serializers.ModelSerializer):
    """Serializer for unmatched biometric punch review records"""
    device_name = serializers.CharField(source='device.name', read_only=True)
    resolved_user_name = serializers.CharField(source='resolved_user.get_full_name', read_only=True)
    resolved_by_name = serializers.CharField(source='resolved_by.get_full_name', read_only=True)

    class Meta:
        model = UnmatchedBiometricPunch
        fields = '__all__'
        read_only_fields = ('id', 'created_at')

class AttendanceAuditLogSerializer(serializers.ModelSerializer):
    """Serializer for detailed attendance audit history"""
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    changed_by_name = serializers.CharField(source='changed_by.get_full_name', read_only=True)

    class Meta:
        model = AttendanceAuditLog
        fields = '__all__'
        read_only_fields = ('id', 'created_at')

class WorkingHoursSettingsSerializer(serializers.ModelSerializer):
    """Serializer for working hours settings"""
    office_name = serializers.CharField(source='office.name', read_only=True)
    
    class Meta:
        model = WorkingHoursSettings
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')

class ESSLDeviceSyncSerializer(serializers.Serializer):
    """Serializer for ESSL device synchronization"""
    device_id = serializers.UUIDField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    
    def validate(self, attrs):
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError("Start date cannot be after end date")
        
        return attrs

class MonthlyAttendanceReportSerializer(serializers.Serializer):
    """Serializer for monthly attendance reports"""
    office_id = serializers.UUIDField(required=False)
    year = serializers.IntegerField()
    month = serializers.IntegerField(min_value=1, max_value=12)
    
    def validate(self, attrs):
        year = attrs.get('year')
        month = attrs.get('month')
        
        if year < 2020 or year > 2030:
            raise serializers.ValidationError("Invalid year")
        
        return attrs


# Dashboard Statistics Serializers

class DashboardStatsSerializer(serializers.Serializer):
    """Serializer for dashboard statistics"""
    total_employees = serializers.IntegerField()
    total_managers = serializers.IntegerField()
    total_offices = serializers.IntegerField()
    total_devices = serializers.IntegerField()
    active_devices = serializers.IntegerField()
    today_attendance = serializers.IntegerField()
    total_today_records = serializers.IntegerField()
    attendance_rate = serializers.FloatField()
    pending_leaves = serializers.IntegerField()
    approved_leaves = serializers.IntegerField()
    total_leaves = serializers.IntegerField()
    leave_approval_rate = serializers.FloatField()
    active_users = serializers.IntegerField()
    inactive_users = serializers.IntegerField(required=False)
    total_users = serializers.IntegerField()
    employee_growth = serializers.FloatField(required=False)
    user_activation_rate = serializers.FloatField()

class OfficeStatsSerializer(serializers.Serializer):
    """Serializer for office-specific statistics"""
    office_id = serializers.UUIDField()
    office_name = serializers.CharField()
    total_employees = serializers.IntegerField()
    present_today = serializers.IntegerField()
    absent_today = serializers.IntegerField()
    pending_leaves = serializers.IntegerField()

class AttendanceReportSerializer(serializers.Serializer):
    """Serializer for attendance reports"""
    user_id = serializers.UUIDField()
    user_name = serializers.CharField()
    total_days = serializers.IntegerField()
    present_days = serializers.IntegerField()
    absent_days = serializers.IntegerField()
    late_days = serializers.IntegerField()
    total_hours = serializers.DecimalField(max_digits=6, decimal_places=2)
    attendance_percentage = serializers.DecimalField(max_digits=5, decimal_places=2)

class BulkAttendanceSerializer(serializers.Serializer):
    """Serializer for bulk attendance operations"""
    user_ids = serializers.ListField(child=serializers.UUIDField())
    date = serializers.DateField()
    status = serializers.ChoiceField(choices=Attendance.STATUS_CHOICES)
    notes = serializers.CharField(required=False, allow_blank=True)

class DeviceSyncSerializer(serializers.Serializer):
    """Serializer for device synchronization"""
    device_id = serializers.UUIDField(required=False)  # Optional since it's in URL
    sync_type = serializers.ChoiceField(choices=[
        ('attendance', 'Attendance Data'),
        ('users', 'User Data'),
        ('both', 'Both')
    ])
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    
    def validate(self, attrs):
        """Validate sync data"""
        # If device_id is provided, ensure it's a valid UUID
        if 'device_id' in attrs:
            try:
                uuid.UUID(str(attrs['device_id']))
            except ValueError:
                raise serializers.ValidationError("Invalid device_id format")
        
        # Validate date range if both dates are provided
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError("Start date cannot be after end date")
        
        return attrs
