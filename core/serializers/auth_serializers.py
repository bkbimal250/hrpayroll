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
import re
from ..models import (
    CustomUser, Office, Device, DeviceUser, Attendance, Leave, Document, 
    Notification, SystemSettings, AttendanceLog, ESSLAttendanceLog, 
    WorkingHoursSettings, DocumentTemplate, GeneratedDocument, Resignation,
    Department, Designation, Salary, SalaryTemplate, Shift, EmployeeShiftAssignment,
    EmployeeStatusAuditLog, BiometricAssignmentHistory, PasswordChangeHistory, AttendanceAuditLog,
    DuplicatePunchAttempt, UnmatchedBiometricPunch
)

class OfficeSerializer(serializers.ModelSerializer):
    """Serializer for Office model"""
    managers_data = serializers.SerializerMethodField(read_only=True)
    total_staff = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Office
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_total_staff(self, obj):
        """Get total number of staff in this office"""
        return obj.customuser_set.count()

    def get_managers_data(self, obj):
        """Get detailed information about managers"""
        return [
            {
                'id': manager.id,
                'name': manager.get_full_name(),
                'email': manager.email,
                'username': manager.username
            }
            for manager in obj.managers.all()
        ]

    def validate_managers(self, value):
        """Validate that managers are actually manager role and limit to 5"""
        if len(value) > 5:
            raise serializers.ValidationError('An office can have at most 5 managers.')
        
        for manager in value:
            if manager.role != 'manager':
                raise serializers.ValidationError(f'User {manager.get_full_name()} is not a manager.')
        
        return value

    def validate(self, attrs):
        """Validate office data"""
        # Validate that managers don't already manage too many offices
        if 'managers' in attrs:
            for manager in attrs['managers']:
                # Count how many offices this manager already manages (excluding current office)
                existing_offices_count = Office.objects.filter(managers=manager).exclude(
                    id=self.instance.id if self.instance else None
                ).count()
                
                if existing_offices_count >= 3:  # Allow managers to manage up to 3 offices
                    raise serializers.ValidationError(
                        f'Manager {manager.get_full_name()} is already managing {existing_offices_count} offices. '
                        'A manager can manage at most 3 offices.'
                    )
        
        return attrs

class DepartmentSerializer(serializers.ModelSerializer):
    """Serializer for Department model"""
    designations_count = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Department
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def get_designations_count(self, obj):
        """Get the number of designations in this department"""
        return obj.designations.count()

class DesignationSerializer(serializers.ModelSerializer):
    """Serializer for Designation model"""
    department_name = serializers.CharField(source='department.name', read_only=True)
    
    class Meta:
        model = Designation
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')

class CustomUserSerializer(serializers.ModelSerializer):
    """Serializer for CustomUser model"""
    aadhaar_card = serializers.CharField(required=False, allow_blank=True, max_length=32, trim_whitespace=True)
    pan_card = serializers.CharField(required=False, allow_blank=True, max_length=20, trim_whitespace=True)
    office_name = serializers.CharField(source='office.name', read_only=True)
    department_name = serializers.SerializerMethodField()
    designation_name = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    profile_picture_url = serializers.SerializerMethodField()
    has_resignation = serializers.SerializerMethodField()
    resignation_status = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'office', 'office_name', 'phone', 'address', 'date_of_birth',
            'gender', 'profile_picture', 'profile_picture_url', 'aadhaar_card', 'pan_card', 'employee_id', 'biometric_id', 'joining_date',
            'department', 'department_name', 'designation', 'designation_name', 'salary', 'pay_bank_name',
            'employment_status', 'exit_type', 'resignation_date', 'last_working_date',
            'exit_date', 'exit_reason', 'final_settlement_status', 'rehire_eligible',
            'archived_at', 'archived_by', 'status_changed_at', 'status_changed_by',
            'status_change_remarks','marital_status',
            'emergency_contact_name',
            'emergency_contact_phone', 'emergency_contact_relationship',
            'account_holder_name', 'bank_name', 'account_number', 'ifsc_code', 'bank_branch_name',
            'upi_qr', 'bank_account_updated_at',
            'is_active', 'last_login', 'created_at', 'updated_at', 'password',
            'has_resignation', 'resignation_status'
        ]
        read_only_fields = (
            'id', 'last_login', 'created_at', 'updated_at', 'archived_at',
            'archived_by', 'status_changed_at', 'status_changed_by'
        )
        extra_kwargs = {
            'password': {'write_only': True, 'required': False}
        }

    def get_full_name(self, obj):
        return obj.get_full_name()
    
    def get_department_name(self, obj):
        """Get department name from ForeignKey relationship"""
        try:
            if obj.department:
                return obj.department.name
        except:
            # Handle case where department was deleted but reference still exists
            pass
        return None
    
    def get_designation_name(self, obj):
        """Get designation name from ForeignKey relationship"""
        try:
            if obj.designation:
                return obj.designation.name
        except:
            # Handle case where designation was deleted but reference still exists
            pass
        return None
    
    def get_profile_picture_url(self, obj):
        """Get profile picture absolute URL"""
        if obj.profile_picture:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_picture.url)
            return obj.profile_picture.url
        return None

    def get_has_resignation(self, obj):
        """Check if the user has a pending or approved resignation"""
        if hasattr(obj, 'has_active_resignation'):
            return obj.has_active_resignation
        from ..models import Resignation
        return Resignation.objects.filter(user=obj, status__in=['pending', 'approved']).exists()

    def get_resignation_status(self, obj):
        """Get the current resignation status of the user"""
        if hasattr(obj, 'latest_resignation_status'):
            return obj.latest_resignation_status
        from ..models import Resignation
        latest_resignation = Resignation.objects.filter(user=obj).order_by('-created_at').first()
        return latest_resignation.status if latest_resignation else None

    def validate(self, attrs):
        """Validate user data"""
        # Ensure managers have an office assigned
        if attrs.get('role') == 'manager' and not attrs.get('office'):
            raise serializers.ValidationError('Managers must be assigned to an office.')
        
        # Ensure admins can have offices but it's not required
        if attrs.get('role') == 'admin':
            # Admin can have office but it's not required
            pass
        
        # Validate password if provided
        password = attrs.get('password')
        if password:
            if len(password) < 6:
                raise serializers.ValidationError({'password': 'Password must be at least 6 characters long.'})
        
        # Validate Aadhaar card number
        aadhaar_card = attrs.get('aadhaar_card')
        if aadhaar_card:
            if '*' in str(aadhaar_card):
                attrs.pop('aadhaar_card', None)
            else:
                aadhaar = re.sub(r'\D', '', str(aadhaar_card))
                if len(aadhaar) != 12:
                    raise serializers.ValidationError({'aadhaar_card': 'Aadhaar card number must be exactly 12 digits.'})
                attrs['aadhaar_card'] = aadhaar
        elif aadhaar_card == '':
            attrs['aadhaar_card'] = ''

        # Validate PAN card number
        pan_card = attrs.get('pan_card')
        if pan_card:
            if '*' in str(pan_card):
                attrs.pop('pan_card', None)
            else:
                pan = re.sub(r'[^A-Za-z0-9]', '', str(pan_card)).upper()
                if len(pan) != 10:
                    raise serializers.ValidationError({'pan_card': 'PAN card number must be exactly 10 characters.'})
                if not (pan[:5].isalpha() and pan[5:9].isdigit() and pan[9].isalpha()):
                    raise serializers.ValidationError({'pan_card': 'PAN card number format should be: AAAAA9999A (5 letters, 4 digits, 1 letter).'})
                attrs['pan_card'] = pan
        elif pan_card == '':
            attrs['pan_card'] = ''
        
        return attrs

    def create(self, validated_data):
        """Create a new user with hashed password"""
        password = validated_data.pop('password', None)
        user = CustomUser.objects.create_user(**validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user

    def update(self, instance, validated_data):
        """Update user with hashed password if provided"""
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance

class CustomUserListSerializer(serializers.ModelSerializer):
    """Lean serializer for users table/list endpoints."""
    office_name = serializers.CharField(source='office.name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    designation_name = serializers.CharField(source='designation.name', read_only=True)
    full_name = serializers.SerializerMethodField()
    profile_picture_url = serializers.SerializerMethodField()
    has_resignation = serializers.SerializerMethodField()
    resignation_status = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'full_name',
            'role',
            'employee_id',
            'biometric_id',
            'phone',
            'profile_picture',
            'profile_picture_url',
            'office',
            'office_name',
            'department',
            'department_name',
            'designation',
            'designation_name',
            'joining_date',
            'salary',
            'pay_bank_name',
            'employment_status',
            'exit_type',
            'resignation_date',
            'last_working_date',
            'exit_date',
            'final_settlement_status',
            'rehire_eligible',
            'archived_at',
            'status_changed_at',
            'is_active',
            'has_resignation',
            'resignation_status',
            'marital_status',
        ]

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_profile_picture_url(self, obj):
        if obj.profile_picture:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_picture.url)
            return obj.profile_picture.url
        return None

    def get_has_resignation(self, obj):
        return bool(getattr(obj, 'has_active_resignation', False))

    def get_resignation_status(self, obj):
        return getattr(obj, 'latest_resignation_status', None)


def _mask_tail(value, visible=4):
    if not value:
        return ''
    text = str(value)
    if len(text) <= visible:
        return '*' * len(text)
    return f"{'*' * (len(text) - visible)}{text[-visible:]}"


class EmployeeSelfSerializer(serializers.ModelSerializer):
    """Safe profile serializer for an employee viewing their own account."""
    office_name = serializers.CharField(source='office.name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    designation_name = serializers.CharField(source='designation.name', read_only=True)
    full_name = serializers.SerializerMethodField()
    aadhaar_card = serializers.SerializerMethodField()
    pan_card = serializers.SerializerMethodField()
    account_number = serializers.SerializerMethodField()
    ifsc_code = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'employee_id', 'biometric_id', 'phone', 'address',
            'date_of_birth', 'gender', 'profile_picture', 'office',
            'office_name', 'department', 'department_name', 'designation',
            'designation_name', 'joining_date', 'employment_status',
            'marital_status', 'emergency_contact_name',
            'emergency_contact_phone', 'emergency_contact_relationship',
            'account_holder_name', 'bank_name', 'account_number', 'ifsc_code',
            'bank_branch_name', 'aadhaar_card', 'pan_card', 'bank_account_updated_at',
            'is_active', 'last_login', 'created_at', 'updated_at',
        ]
        read_only_fields = fields

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_aadhaar_card(self, obj):
        return _mask_tail(obj.aadhaar_card)

    def get_pan_card(self, obj):
        return _mask_tail(obj.pan_card)

    def get_account_number(self, obj):
        return _mask_tail(obj.account_number)

    def get_ifsc_code(self, obj):
        return _mask_tail(obj.ifsc_code)


class ManagerEmployeeListSerializer(serializers.ModelSerializer):
    """Manager-safe team list serializer without payroll or government IDs."""
    office_name = serializers.CharField(source='office.name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    designation_name = serializers.CharField(source='designation.name', read_only=True)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'employee_id', 'biometric_id', 'phone', 'profile_picture',
            'office', 'office_name', 'department', 'department_name',
            'designation', 'designation_name', 'joining_date',
            'employment_status', 'is_active',
        ]
        read_only_fields = fields

    def get_full_name(self, obj):
        return obj.get_full_name()


class HREmployeeDetailSerializer(CustomUserSerializer):
    """HR detail serializer. Salary and bank account are masked."""
    aadhaar_card = serializers.SerializerMethodField()
    pan_card = serializers.SerializerMethodField()
    account_number = serializers.SerializerMethodField()
    ifsc_code = serializers.SerializerMethodField()
    salary = serializers.SerializerMethodField()

    def get_aadhaar_card(self, obj):
        return _mask_tail(obj.aadhaar_card)

    def get_pan_card(self, obj):
        return _mask_tail(obj.pan_card)

    def get_account_number(self, obj):
        return _mask_tail(obj.account_number)

    def get_ifsc_code(self, obj):
        return _mask_tail(obj.ifsc_code)

    def get_salary(self, obj):
        return None


class AdminEmployeeDetailSerializer(CustomUserSerializer):
    """Admin detail serializer for privileged employee administration."""
    pass

class EmployeeStatusAuditLogSerializer(serializers.ModelSerializer):
    """Serializer for employee lifecycle status audit entries."""
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    changed_by_name = serializers.CharField(source='changed_by.get_full_name', read_only=True)

    class Meta:
        model = EmployeeStatusAuditLog
        fields = [
            'id', 'employee', 'employee_name', 'old_status', 'new_status',
            'changed_by', 'changed_by_name', 'reason', 'old_values',
            'new_values', 'created_at'
        ]
        read_only_fields = fields

class BiometricAssignmentHistorySerializer(serializers.ModelSerializer):
    """Serializer for biometric ID assignment history."""
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    changed_by_name = serializers.CharField(source='changed_by.get_full_name', read_only=True)

    class Meta:
        model = BiometricAssignmentHistory
        fields = [
            'id', 'employee', 'employee_name', 'old_biometric_id',
            'new_biometric_id', 'changed_by', 'changed_by_name',
            'reason', 'created_at'
        ]
        read_only_fields = fields

class PasswordChangeHistorySerializer(serializers.ModelSerializer):
    """Serializer for privileged password reset audit entries."""
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    changed_by_name = serializers.CharField(source='changed_by.get_full_name', read_only=True)

    class Meta:
        model = PasswordChangeHistory
        fields = [
            'id', 'employee', 'employee_name', 'changed_by',
            'changed_by_name', 'changed_by_role', 'reason', 'created_at'
        ]
        read_only_fields = fields

class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = CustomUser
        fields = [
            'username', 'email', 'password', 'password_confirm', 'first_name',
            'last_name', 'role', 'office', 'phone', 'employee_id', 'biometric_id'
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        
        # Ensure managers have an office assigned
        if attrs.get('role') == 'manager' and not attrs.get('office'):
            raise serializers.ValidationError('Managers must be assigned to an office.')
        
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = CustomUser.objects.create_user(**validated_data)
        return user

class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError('Invalid credentials')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled')
            attrs['user'] = user
        else:
            raise serializers.ValidationError('Must include username and password')

        return attrs

class LoginUserResponseSerializer(serializers.ModelSerializer):
    """Only safe fields for login response"""

    full_name = serializers.SerializerMethodField()
    profile_picture_url = serializers.SerializerMethodField()
    office_name = serializers.CharField(source="office.name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    designation_name = serializers.CharField(source="designation.name", read_only=True)

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "username",
            "employee_id",
            "full_name",
            "role",
            "office",
            "office_name",
            "department_name",
            "designation_name",
            "profile_picture_url",
            "employment_status",
            "is_active",
        ]

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_profile_picture_url(self, obj):
        request = self.context.get("request")
        if obj.profile_picture:
            if request:
                return request.build_absolute_uri(obj.profile_picture.url)
            return obj.profile_picture.url
        return None

class LightweightUserSummarySerializer(serializers.ModelSerializer):
    """Small user payload for list/table rows."""
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    office_name = serializers.CharField(source='office.name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    designation_name = serializers.CharField(source='designation.name', read_only=True)

    class Meta:
        model = CustomUser
        fields = [
            'id', 'full_name', 'first_name', 'last_name', 'employee_id',
            'email', 'office_name', 'department_name', 'designation_name'
        ]

class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile updates"""
    department_name = serializers.SerializerMethodField()
    designation_name = serializers.SerializerMethodField()
    profile_picture_url = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = [
            # Basic Information
            'first_name', 'last_name', 'email', 'phone', 'address', 
            'date_of_birth', 'gender', 'marital_status', 'profile_picture', 'profile_picture_url',
            
            # Government ID Information
            'aadhaar_card', 'pan_card',
            
            # Employment Information (non-sensitive)
            'employee_id', 'biometric_id', 'joining_date', 
            'department', 'department_name', 'designation', 'designation_name', 'salary',
            
            # Emergency Contact
            'emergency_contact_name', 'emergency_contact_phone', 
            'emergency_contact_relationship',
            
            # Bank Details
            'account_holder_name', 'bank_name', 'account_number', 
            'ifsc_code', 'bank_branch_name',
            'upi_qr'
        ]
        extra_kwargs = {
            'upi_qr': {'required': False, 'allow_null': True}
        }
        read_only_fields = [
            'id', 'username', 'role', 'office', 'is_active', 
            'last_login', 'created_at', 'updated_at'
        ]
    
    def validate_salary(self, value):
        """Validate and convert salary field"""
        if value is None or value == '':
            return None
        try:
            # Convert to decimal if it's a string or float
            if isinstance(value, str):
                value = value.strip()
                if value == '':
                    return None
                value = float(value)
            if isinstance(value, (int, float)):
                if value < 0:
                    raise serializers.ValidationError("Salary cannot be negative")
                return value
        except (ValueError, TypeError):
            raise serializers.ValidationError("Invalid salary format")
        return value
    
    def validate_joining_date(self, value):
        """Validate joining date field"""
        if value is None or value == '':
            return None
        # Django will handle date parsing automatically
        return value
    
    def validate_date_of_birth(self, value):
        """Validate date of birth field"""
        if value is None or value == '':
            return None
        # Django will handle date parsing automatically
        return value
    
    def get_department_name(self, obj):
        """Get department name from ForeignKey relationship"""
        try:
            if obj.department:
                return obj.department.name
        except:
            # Handle case where department was deleted but reference still exists
            pass
        return None
    
    def get_designation_name(self, obj):
        """Get designation name from ForeignKey relationship"""
        try:
            if obj.designation:
                return obj.designation.name
        except:
            # Handle case where designation was deleted but reference still exists
            pass
        return None
    
    def get_profile_picture_url(self, obj):
        """Get profile picture absolute URL"""
        if obj.profile_picture:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_picture.url)
            return obj.profile_picture.url
        return None

class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for password change"""
    old_password = serializers.CharField()
    new_password = serializers.CharField(validators=[validate_password])
    confirm_password = serializers.CharField()

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError("New passwords don't match")
        return attrs
