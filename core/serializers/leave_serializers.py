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

class LeaveSerializer(serializers.ModelSerializer):
    """Serializer for Leave model"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
    user = CustomUserSerializer(read_only=True)
    
    def __init__(self, *args, **kwargs):
        """Ensure nested user serializer receives the same context (for absolute media URLs)."""
        super().__init__(*args, **kwargs)
        # Re-bind user field with context so profile_picture_url is built with request
        self.fields['user'] = CustomUserSerializer(read_only=True, context=self.context)
    
    class Meta:
        model = Leave
        fields = '__all__'
        read_only_fields = ('id', 'approved_at', 'created_at', 'updated_at')

class LeaveListSerializer(serializers.ModelSerializer):
    """Lightweight leave serializer for paginated list responses."""
    user = LightweightUserSummarySerializer(read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)

    class Meta:
        model = Leave
        fields = [
            'id', 'user', 'user_name', 'leave_type', 'start_date', 'end_date',
            'total_days', 'reason', 'status', 'approved_by', 'approved_by_name',
            'approved_at', 'rejection_reason', 'created_at', 'updated_at'
        ]
        read_only_fields = fields

class LeaveCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating leave requests"""
    user = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), required=False)

    class Meta:
        model = Leave
        fields = ['user', 'leave_type', 'start_date', 'end_date', 'reason']
    
    def validate(self, attrs):
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')
        
        if start_date and end_date:
            if start_date > end_date:
                raise serializers.ValidationError("End date must be after start date")
            
            # Calculate total days (inclusive of both start and end dates)
            delta = end_date - start_date
            attrs['total_days'] = delta.days + 1
        
        request = self.context.get('request')
        if attrs.get('user') and request and request.user.role not in ['admin', 'manager', 'hr']:
            raise serializers.ValidationError({'user': 'You cannot create leave for another user.'})

        return attrs
    
    def create(self, validated_data):
        validated_data['user'] = validated_data.get('user') or self.context['request'].user
        return super().create(validated_data)

class LeaveApprovalSerializer(serializers.ModelSerializer):
    """Serializer for leave approval/rejection"""
    class Meta:
        model = Leave
        fields = ['status', 'rejection_reason']
