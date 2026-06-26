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

class DeviceUserSerializer(serializers.ModelSerializer):
    """Serializer for DeviceUser model"""
    device_name = serializers.CharField(source='device.name', read_only=True)
    device_type = serializers.CharField(source='device.device_type', read_only=True)
    system_user_name = serializers.SerializerMethodField()
    system_user_email = serializers.CharField(source='system_user.email', read_only=True)
    system_user_employee_id = serializers.CharField(source='system_user.employee_id', read_only=True)
    
    class Meta:
        model = DeviceUser
        fields = [
            'id', 'device', 'device_name', 'device_type', 'device_user_id', 'device_user_name',
            'device_user_privilege', 'device_user_password', 'device_user_group', 'device_user_card',
            'system_user', 'system_user_name', 'system_user_email', 'system_user_employee_id',
            'is_mapped', 'mapping_notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def get_system_user_name(self, obj):
        """Get system user full name"""
        if obj.system_user:
            return obj.system_user.get_full_name()
        return None
    
    def validate(self, attrs):
        """Validate device user data"""
        device = attrs.get('device')
        device_user_id = attrs.get('device_user_id')
        
        # Check for duplicate device_user_id within the same device
        if device and device_user_id:
            queryset = DeviceUser.objects.filter(device=device, device_user_id=device_user_id)
            if self.instance:
                queryset = queryset.exclude(id=self.instance.id)
            
            if queryset.exists():
                raise serializers.ValidationError({
                    'device_user_id': 'A user with this ID already exists on this device.'
                })
        
        return attrs

class DeviceUserCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating DeviceUser records"""
    class Meta:
        model = DeviceUser
        fields = [
            'device', 'device_user_id', 'device_user_name', 'device_user_privilege',
            'device_user_password', 'device_user_group', 'device_user_card',
            'system_user', 'is_mapped', 'mapping_notes'
        ]
    
    def validate(self, attrs):
        """Validate device user creation data"""
        device = attrs.get('device')
        device_user_id = attrs.get('device_user_id')
        
        # Check for duplicate device_user_id within the same device
        if device and device_user_id:
            queryset = DeviceUser.objects.filter(device=device, device_user_id=device_user_id)
            
            # Exclude current instance if updating
            if self.instance:
                queryset = queryset.exclude(id=self.instance.id)
            
            if queryset.exists():
                raise serializers.ValidationError({
                    'device_user_id': 'A user with this ID already exists on this device.'
                })
        
        return attrs

class DeviceUserMappingSerializer(serializers.ModelSerializer):
    """Serializer for mapping device users to system users"""
    class Meta:
        model = DeviceUser
        fields = ['system_user', 'is_mapped', 'mapping_notes']
    
    def validate(self, attrs):
        """Validate mapping data"""
        system_user = attrs.get('system_user')
        is_mapped = attrs.get('is_mapped', False)
        
        if is_mapped and not system_user:
            raise serializers.ValidationError({
                'system_user': 'System user is required when mapping is enabled.'
            })
        
        return attrs

class DeviceUserBulkCreateSerializer(serializers.Serializer):
    """Serializer for bulk creating device users"""
    device = serializers.UUIDField()
    device_users = serializers.ListField(
        child=serializers.DictField(),
        min_length=1
    )
    
    def validate_device_users(self, value):
        """Validate device users list"""
        if not value:
            raise serializers.ValidationError("Device users list cannot be empty.")
        
        # Check for duplicate device_user_ids in the list
        device_user_ids = [user.get('device_user_id') for user in value if user.get('device_user_id')]
        if len(device_user_ids) != len(set(device_user_ids)):
            raise serializers.ValidationError("Duplicate device_user_id found in the list.")
        
        return value
    
    def validate(self, attrs):
        """Validate bulk creation data"""
        device_id = attrs.get('device')
        device_users = attrs.get('device_users', [])
        
        if device_id:
            # Check for existing device_user_ids on the device
            existing_ids = set(
                DeviceUser.objects.filter(device_id=device_id)
                .values_list('device_user_id', flat=True)
            )
            
            new_ids = set(user.get('device_user_id') for user in device_users if user.get('device_user_id'))
            conflicts = existing_ids.intersection(new_ids)
            
            if conflicts:
                raise serializers.ValidationError({
                    'device_users': f'Device user IDs already exist on this device: {", ".join(conflicts)}'
                })
        
        return attrs


# Salary Management Serializers
