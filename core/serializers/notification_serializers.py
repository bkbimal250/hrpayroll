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

class NotificationSerializer(serializers.ModelSerializer):
    """Enhanced serializer for Notification model"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'user_name', 'title', 'message', 'notification_type',
            'category', 'priority', 'is_read', 'is_email_sent', 'action_url',
            'action_text', 'expires_at', 'related_object_id', 'related_object_type',
            'created_by', 'created_by_name', 'created_at', 'updated_at', 'is_expired'
        ]
        read_only_fields = ('id', 'created_at', 'updated_at', 'is_expired')

class NotificationListSerializer(serializers.ModelSerializer):
    """Lightweight notification serializer for list responses."""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'user_name', 'title', 'message', 'notification_type',
            'category', 'priority', 'is_read', 'action_url', 'action_text',
            'created_by', 'created_by_name', 'created_at', 'is_expired'
        ]
        read_only_fields = fields

class SystemSettingsSerializer(serializers.ModelSerializer):
    """Serializer for SystemSettings model"""
    class Meta:
        model = SystemSettings
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')
