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

class ResignationSerializer(serializers.ModelSerializer):
    """Serializer for Resignation model"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_employee_id = serializers.CharField(source='user.employee_id', read_only=True)
    user_office_name = serializers.CharField(source='user.office.name', read_only=True)
    user_department = serializers.SerializerMethodField()
    user_designation = serializers.SerializerMethodField()
    user_profile_picture = serializers.SerializerMethodField()
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
    
    class Meta:
        model = Resignation
        fields = [
            'id', 'user', 'user_name', 'user_email', 'user_employee_id', 
            'user_office_name', 'user_department', 'user_designation', 'user_profile_picture',
            'resignation_date', 'notice_period_days', 'reason', 'status', 'approved_by', 
            'approved_by_name', 'approved_at', 'rejection_reason', 
            'handover_notes', 'last_working_date', 'is_handover_completed',
            'created_at', 'updated_at'
        ]
        read_only_fields = ('id', 'approved_at', 'created_at', 'updated_at', 'last_working_date')
    
    def get_user_department(self, obj):
        """Get user department name - handle both CharField and ForeignKey"""
        try:
            if hasattr(obj.user, 'department') and obj.user.department:
                if hasattr(obj.user.department, 'name'):
                    return obj.user.department.name  # ForeignKey
                else:
                    return obj.user.department  # CharField
        except Exception:
            # Handle case where department was deleted but user still references it
            pass
        return None
    
    def get_user_designation(self, obj):
        """Get user designation name - handle both CharField and ForeignKey"""
        try:
            if hasattr(obj.user, 'designation') and obj.user.designation:
                if hasattr(obj.user.designation, 'name'):
                    return obj.user.designation.name  # ForeignKey
                else:
                    return obj.user.designation  # CharField
        except Exception:
            # Handle case where designation was deleted but user still references it
            pass
        return None
    
    def get_user_profile_picture(self, obj):
        """Get user profile picture URL"""
        if hasattr(obj.user, 'profile_picture') and obj.user.profile_picture:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.user.profile_picture.url)
            return obj.user.profile_picture.url
        return None

class ResignationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating resignation requests"""
    class Meta:
        model = Resignation
        fields = ['resignation_date', 'notice_period_days', 'reason', 'handover_notes']
    
    def validate_resignation_date(self, value):
        """Validate resignation date"""
        from django.utils import timezone
        if value < timezone.now().date():
            raise serializers.ValidationError("Resignation date cannot be in the past.")
        return value
    
    def validate_notice_period_days(self, value):
        """Validate notice period"""
        if value not in [15, 30]:
            raise serializers.ValidationError("Notice period must be either 15 or 30 days.")
        return value
    
    def create(self, validated_data):
        """Create resignation request"""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class ResignationAdminUpdateSerializer(serializers.ModelSerializer):
    """Serializer for privileged resignation date corrections."""
    class Meta:
        model = Resignation
        fields = ['resignation_date']

class ResignationApprovalSerializer(serializers.ModelSerializer):
    """Serializer for resignation approval/rejection"""
    class Meta:
        model = Resignation
        fields = ['status', 'rejection_reason', 'handover_notes', 'is_handover_completed']
    
    def validate_status(self, value):
        """Validate status change"""
        if value not in ['approved', 'rejected']:
            raise serializers.ValidationError("Status must be either 'approved' or 'rejected'.")
        return value
    
    def validate(self, attrs):
        """Validate approval data"""
        status = attrs.get('status')
        rejection_reason = attrs.get('rejection_reason', '')
        
        if status == 'rejected' and not rejection_reason:
            raise serializers.ValidationError("Rejection reason is required when rejecting a resignation.")
        
        return attrs
