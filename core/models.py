from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from datetime import timedelta
import uuid
from django.core.exceptions import ValidationError
from django.template import Template, Context
from django.conf import settings
from decimal import Decimal


class Office(models.Model):
    """Office model for multi-office support"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    address = models.TextField()
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    description = models.TextField(blank=True)
    managers = models.ManyToManyField('CustomUser', blank=True, 
                                     related_name='managed_offices', limit_choices_to={'role': 'manager'},
                                     help_text="Up to 5 managers can be assigned to an office")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Offices"
        ordering = ['name']

    def __str__(self):
        return self.name

    def clean(self):
        """Validate that managers are actually manager role and limit to 5"""
        # This validation will be handled in the serializer since ManyToMany fields
        # are not available during model.clean() for new instances
        pass

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class Department(models.Model):
    """Department model for organizing employees"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Departments"
        ordering = ['name']

    def __str__(self):
        return self.name


class Designation(models.Model):
    """Designation model for employee job titles"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='designations')
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Designations"
        ordering = ['department__name', 'name']
        unique_together = ['name', 'department']

    def __str__(self):
        try:
            return f"{self.name} ({self.department.name})"
        except Exception:
            return f"{self.name} (No Department)"


class CustomUser(AbstractUser):
    """Custom User model with role-based access"""
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('employee', 'Employee'),
        ('accountant', 'Accountant'),
    ]
    
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='employee')
    office = models.ForeignKey(Office, on_delete=models.CASCADE, null=True, blank=True)
    
    # Personal Information
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True)
    
    # Government ID Information
    aadhaar_card = models.CharField(max_length=12, blank=True, help_text="12-digit Aadhaar card number")
    pan_card = models.CharField(max_length=10, blank=True, help_text="10-character PAN card number")
    
    # Employment Information
    employee_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
    biometric_id = models.CharField(max_length=50, unique=True, null=True, blank=True, help_text="Biometric ID from ESSL device")
    joining_date = models.DateField(null=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='employees', db_column='department_id')
    designation = models.ForeignKey(Designation, on_delete=models.SET_NULL, null=True, blank=True, related_name='employees', db_column='designation_id')
    salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    pay_bank_name=models.CharField(max_length=200, blank=True, help_text="Bank name for salary payment")
    
    # Emergency Contact
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(max_length=15, blank=True)
    emergency_contact_relationship = models.CharField(max_length=50, blank=True)
    
    # Bank Details
    account_holder_name = models.CharField(max_length=200, blank=True, help_text="Name as it appears on bank account")
    bank_name = models.CharField(max_length=200, blank=True)
    account_number = models.CharField(max_length=50, blank=True)
    ifsc_code = models.CharField(max_length=20, blank=True, help_text="IFSC Code of the bank branch")
    bank_branch_name = models.CharField(max_length=200, blank=True)
    
    # Payments - UPI QR (image only)
    upi_qr = models.ImageField(upload_to='user_qr_codes/', null=True, blank=True, help_text="User uploaded UPI QR image (PNG/JPG/WebP)")
    
    # Bank Account Tracking
    bank_account_updated_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp when bank account was last updated")
    
    # System Fields
    is_active = models.BooleanField(default=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ['username']

    def __str__(self):
        return f"{self.get_full_name()} ({self.role})"

    def clean(self):
        """Validate user data"""
        super().clean()
        # Ensure managers have an office assigned
        if self.role == 'manager' and not self.office:
            raise ValidationError('Managers must be assigned to an office.')
        
        # Ensure admins don't have office restrictions
        if self.role == 'admin' and self.office:
            # Admin can have office but it's not required
            pass
        
        # Validate Aadhaar card number
        if self.aadhaar_card:
            aadhaar = self.aadhaar_card.replace(' ', '').replace('-', '')
            if not aadhaar.isdigit() or len(aadhaar) != 12:
                raise ValidationError({'aadhaar_card': 'Aadhaar card number must be exactly 12 digits.'})
        
        # Validate PAN card number
        if self.pan_card:
            pan = self.pan_card.upper().replace(' ', '')
            if len(pan) != 10:
                raise ValidationError({'pan_card': 'PAN card number must be exactly 10 characters.'})
            if not (pan[:5].isalpha() and pan[5:9].isdigit() and pan[9].isalpha()):
                raise ValidationError({'pan_card': 'PAN card number format should be: AAAAA9999A (5 letters, 4 digits, 1 letter).'})

        # Validate Designation belongs to Department
        if self.designation and self.department:
            if self.designation.department != self.department:
                raise ValidationError({
                    'designation': f"The designation '{self.designation.name}' belongs to '{self.designation.department.name}', but you selected '{self.department.name}'."
                })

    def save(self, *args, **kwargs):
        # Auto-null biometric_id if user is inactive
        if self.is_active is False and self.biometric_id is not None:
            self.biometric_id = None
            if kwargs.get('update_fields') is not None:
                update_fields = set(kwargs['update_fields'])
                update_fields.add('biometric_id')
                kwargs['update_fields'] = list(update_fields)

        # Validation is handled by serializers for API requests. 
        # Forcing clean() here can trigger unhandled ValidationErrors for existing 
        # "dirty" data during unrelated updates (like is_active toggle).
        
        # Handle UUID field compatibility issues
        try:
            super().save(*args, **kwargs)
        except Exception as e:
            if "Save with update_fields did not affect any rows" in str(e):
                # If it's a partial update that failed, try a full save
                if kwargs.get('update_fields'):
                    # Remove update_fields and try again
                    kwargs.pop('update_fields', None)
                    super().save(*args, **kwargs)
                else:
                    raise
            elif "Duplicate entry" in str(e) and "username" in str(e):
                # Handle duplicate username error - this shouldn't happen for updates
                # If we're trying to update an existing user, ignore this error
                if self.pk:
                    # This is an update, so the duplicate error is unexpected
                    # This is likely a last_login update issue, so we'll ignore it
                    pass
                else:
                    raise
            else:
                raise

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_manager(self):
        return self.role == 'manager'

    @property
    def is_employee(self):
        return self.role == 'employee'
    
    @property
    def is_accountant(self):
        return self.role == 'accountant'
    
    def get_full_name(self):
        """Return the user's full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        else:
            return self.email or "Unknown User"



class BankAccountHistory(models.Model):
    """Track all bank account changes for audit purposes"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='bank_account_history')
    action = models.CharField(max_length=50)  # 'created', 'updated', 'verified'
    
    # Store old and new values as JSON
    old_values = models.JSONField(null=True, blank=True, help_text="Previous bank account values")
    new_values = models.JSONField(null=True, blank=True, help_text="New bank account values")
    
    # Track who made the change
    changed_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='bank_account_changes_made',
        help_text="User who made this change"
    )
    
    # Additional metadata
    change_reason = models.TextField(blank=True, help_text="Optional reason for the change")
    is_verified = models.BooleanField(default=False, help_text="Whether accountant has verified this change")
    verified_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bank_account_verifications',
        limit_choices_to={'role': 'accountant'},
        help_text="Accountant who verified this change"
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Bank Account History"
        verbose_name_plural = "Bank Account Histories"
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['is_verified', '-created_at']),
        ]

    def __str__(self):
        try:
            return "Bank Account {} - {} ({})".format(
                self.action, 
                self.user.get_full_name(), 
                self.created_at.date()
            )
        except Exception:
            return "Bank Account {} - Unknown User".format(self.action)

    def get_changed_fields(self):
        """Return list of field names that changed"""
        if not self.old_values or not self.new_values:
            return []
        
        changed = []
        for field in ['account_holder_name', 'bank_name', 'account_number', 'ifsc_code', 'bank_branch_name']:
            old_val = self.old_values.get(field)
            new_val = self.new_values.get(field)
            if old_val != new_val:
                changed.append(field)
        
        # Check UPI QR separately (it's a file path)
        if self.old_values.get('upi_qr') != self.new_values.get('upi_qr'):
            changed.append('upi_qr')
        
        return changed

class Device(models.Model):
    """Biometric device model for attendance tracking"""
    DEVICE_TYPE_CHOICES = [
        ('essl', 'ESSL'),
        ('zkteco', 'ZKTeco'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    device_type = models.CharField(max_length=10, choices=DEVICE_TYPE_CHOICES)
    ip_address = models.GenericIPAddressField()
    port = models.IntegerField(default=4370)
    serial_number = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=200, blank=True)
    office = models.ForeignKey(Office, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    last_sync = models.DateTimeField(null=True, blank=True)
    
    # ESSL Device Specific Fields
    device_id = models.CharField(max_length=50, blank=True, help_text="Device ID from ESSL device")
    firmware_version = models.CharField(max_length=50, blank=True)
    device_status = models.CharField(max_length=20, default='online', choices=[
        ('online', 'Online'),
        ('offline', 'Offline'),
        ('error', 'Error'),
    ])
    sync_interval = models.IntegerField(default=5, help_text="Sync interval in minutes")
    last_attendance_sync = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.device_type})"


class DeviceUser(models.Model):
    """Model to map users from ZKTeco devices to system users"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='device_users')
    device_user_id = models.CharField(max_length=50, help_text="User ID from the device")
    device_user_name = models.CharField(max_length=100, help_text="Name from the device")
    device_user_privilege = models.CharField(max_length=20, default='user', choices=[
        ('user', 'User'),
        ('admin', 'Admin'),
        ('super_admin', 'Super Admin'),
    ])
    device_user_password = models.CharField(max_length=50, blank=True, help_text="Password from device (if available)")
    device_user_group = models.CharField(max_length=50, blank=True, help_text="Group from device")
    device_user_card = models.CharField(max_length=50, blank=True, help_text="Card number from device")
    
    # Mapping to system user
    system_user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='device_mappings')
    is_mapped = models.BooleanField(default=False, help_text="Whether this device user is mapped to a system user")
    mapping_notes = models.TextField(blank=True, help_text="Notes about the mapping")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['device', 'device_user_id']
        ordering = ['device', 'device_user_id']

    def __str__(self):
        try:
            return f"{self.device.name} - {self.device_user_name} ({self.device_user_id})"
        except Exception:
            return f"Device User - {self.device_user_name} ({self.device_user_id})"

    def map_to_system_user(self, system_user):
        """Map this device user to a system user"""
        self.system_user = system_user
        self.is_mapped = True
        self.save()


class Attendance(models.Model):
    """Attendance model for tracking employee attendance"""
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('upcoming', 'Upcoming'),
        ('weekend', 'Weekend'),
        ('holiday', 'Holiday'),
    ]
    
    DAY_STATUS_CHOICES = [
        ('complete_day', 'Complete Day'),
        ('half_day', 'Half Day'),
        ('absent', 'Absent'),
        ('upcoming', 'Upcoming'),
        ('weekend', 'Weekend'),
        ('holiday', 'Holiday'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    date = models.DateField()
    check_in_time = models.DateTimeField(null=True, blank=True)
    check_out_time = models.DateTimeField(null=True, blank=True)
    total_hours = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='present')
    day_status = models.CharField(max_length=15, choices=DAY_STATUS_CHOICES, default='complete_day')
    is_late = models.BooleanField(default=False, help_text="Whether employee came late")
    late_minutes = models.IntegerField(default=0, help_text="Minutes late from start time")
    device = models.ForeignKey(Device, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Custom manager to ensure save method is called
    class AttendanceManager(models.Manager):
        def create(self, **kwargs):
            # Create the instance
            instance = self.model(**kwargs)
            # Calculate attendance status
            instance.calculate_attendance_status()
            # Save to database
            instance.save()
            return instance
    
    objects = AttendanceManager()

    class Meta:
        unique_together = ['user', 'date']
        ordering = ['-date', '-check_in_time']

    def __str__(self):
        try:
            return f"{self.user.get_full_name()} - {self.date} ({self.status})"
        except Exception:
            return f"Attendance - {self.date} ({self.status})"

    def calculate_total_hours(self):
        """Calculate total working hours"""
        if self.check_in_time and self.check_out_time:
            # Make both times timezone-aware for comparison
            from django.utils import timezone
            
            check_in = self.check_in_time
            check_out = self.check_out_time
            
            # If check_in is naive, make it timezone-aware
            if timezone.is_naive(check_in):
                check_in = timezone.make_aware(check_in, timezone.get_current_timezone())
            
            # If check_out is naive, make it timezone-aware
            if timezone.is_naive(check_out):
                check_out = timezone.make_aware(check_out, timezone.get_current_timezone())
            
            duration = check_out - check_in
            return round(duration.total_seconds() / 3600, 2)
        return None

    def calculate_attendance_status(self):
        """Calculate attendance status based on working hours and late coming"""
        try:
            from django.utils import timezone
            from datetime import time, datetime, date
            
            # Check if this is a future date
            today = date.today()
            if self.date > today:
                # Future date - set as upcoming
                self.status = 'upcoming'
                self.day_status = 'upcoming'
                self.is_late = False
                self.late_minutes = 0
                return
            
            # Get working hours settings for the user's office
            office = self.user.office
            if not office:
                # Default settings if no office assigned
                start_time = time(10, 0)  # 10:00 AM
                late_threshold_minutes = 15
                half_day_hours = 5.0
                late_coming_threshold = time(11, 30)  # 11:30 AM
            else:
                # Get office-specific settings
                settings = WorkingHoursSettings.objects.filter(office=office).first()
                if settings:
                    start_time = settings.start_time
                    late_threshold_minutes = settings.late_threshold
                    half_day_hours = float(settings.half_day_threshold) / 60  # Convert minutes to hours
                    late_coming_threshold = settings.late_coming_threshold
                else:
                    # Default settings
                    start_time = time(10, 0)
                    late_threshold_minutes = 15
                    half_day_hours = 5.0
                    late_coming_threshold = time(11, 30)  # 11:30 AM
            
            # Check if present (has check-in time)
            if not self.check_in_time:
                self.status = 'absent'
                self.day_status = 'absent'
                self.is_late = False
                self.late_minutes = 0
                return
            
            # Check if late coming (after late_coming_threshold)
            check_in_time_only = self.check_in_time.time()
            
            if check_in_time_only > late_coming_threshold:
                self.is_late = True
                # Calculate minutes late from late_coming_threshold (11:30 AM), not start_time
                late_threshold_datetime = datetime.combine(self.date, late_coming_threshold)
                
                # Make both times timezone-aware for comparison
                if timezone.is_naive(late_threshold_datetime):
                    late_threshold_datetime = timezone.make_aware(late_threshold_datetime, timezone.get_current_timezone())
                
                check_in_time = self.check_in_time
                if timezone.is_naive(check_in_time):
                    check_in_time = timezone.make_aware(check_in_time, timezone.get_current_timezone())
                
                late_delta = check_in_time - late_threshold_datetime
                self.late_minutes = max(0, int(late_delta.total_seconds() / 60))
            else:
                self.is_late = False
                self.late_minutes = 0
            
            # Calculate day status based on working hours
            if self.total_hours:
                if self.total_hours < half_day_hours:
                    self.day_status = 'half_day'
                    self.status = 'present'  # Status is always present if checked in
                else:
                    self.day_status = 'complete_day'
                    self.status = 'present'
            else:
                # If no check-out time, assume present for the day
                self.day_status = 'complete_day'
                self.status = 'present'
                
        except Exception as e:
            # Fallback to default values if calculation fails
            self.status = 'present'
            self.day_status = 'complete_day'
            self.is_late = False
            self.late_minutes = 0

    def save(self, *args, **kwargs):
        # Check for existing attendance record for the same user on the same date
        if self.pk is None:  # Only check on creation
            existing = Attendance.objects.filter(user=self.user, date=self.date).first()
            if existing:
                # Update existing record instead of creating duplicate
                existing.check_in_time = self.check_in_time or existing.check_in_time
                existing.check_out_time = self.check_out_time or existing.check_out_time
                existing.status = self.status or existing.status
                existing.device = self.device or existing.device
                existing.notes = self.notes or existing.notes
                existing.save()
                # Return the existing record's ID to prevent creation
                self.pk = existing.pk
                return
        
        # Calculate total hours if both check-in and check-out times are available
        if self.check_in_time and self.check_out_time:
            self.total_hours = self.calculate_total_hours()
        
        # Automatically calculate attendance status
        self.calculate_attendance_status()
        
        super().save(*args, **kwargs)

    def manual_update_status(self, new_status, new_day_status=None, notes=None):
        """Manually update attendance status without triggering automatic calculations"""
        # Use Django's update() method to bypass the model's save method
        update_data = {
            'status': new_status,
            'notes': notes if notes is not None else self.notes,
            'updated_at': timezone.now()
        }
        
        if new_day_status:
            update_data['day_status'] = new_day_status
        else:
            # Auto-set day_status based on status
            if new_status == 'absent':
                update_data['day_status'] = 'absent'
            else:
                update_data['day_status'] = 'complete_day'
        
        # Update the instance attributes
        self.status = update_data['status']
        self.day_status = update_data['day_status']
        self.notes = update_data['notes']
        self.updated_at = update_data['updated_at']
        
        # Use update() to bypass the model's save method
        Attendance.objects.filter(id=self.id).update(**update_data)
        
        return self


class Leave(models.Model):
    """Leave model for employee leave management"""
    LEAVE_TYPE_CHOICES = [
        ('casual', 'Personal Leave'),
        ('sick', 'Sick Leave'),
        ('annual', 'Annual Leave'),
        ('maternity', 'Maternity Leave'),
        ('paternity', 'Paternity Leave'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPE_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    total_days = models.IntegerField()
    reason = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    approved_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='approved_leaves'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        try:
            return f"{self.user.get_full_name()} - {self.leave_type} ({self.status})"
        except Exception:
            return f"Leave - {self.leave_type} ({self.status})"


class Document(models.Model):
    """Document model for file management"""
    DOCUMENT_TYPE_CHOICES = [
        ('salary_slip', 'Salary Slip'),
        ('offer_letter', 'Offer Letter'),
        ('id_proof', 'ID Proof'),
        ('address_proof', 'Address Proof'),
        ('aadhar_card', 'Aadhar Card'),
        ('pan_card', 'PAN Card'),
        ('voter_id', 'Voter ID'),
        ('id_card', 'ID Card'),
        ('driving_license', 'Driving License'),
        ('passport', 'Passport'),
        ('birth_certificate', 'Birth Certificate'),
        ('educational_certificate', 'Educational Certificate'),
        ('experience_certificate', 'Experience Certificate'),
        ('medical_certificate', 'Medical Certificate'),
        ('bank_statement', 'Bank Statement'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    document_type = models.CharField(max_length=30, choices=DOCUMENT_TYPE_CHOICES)
    file = models.FileField(upload_to='documents/')
    description = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='uploaded_documents'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        try:
            return f"{self.title} - {self.user.get_full_name()}"
        except Exception:
            return f"{self.title} - Unknown User"


class Notification(models.Model):
    """Enhanced notification model for system notifications"""
    NOTIFICATION_TYPE_CHOICES = [
        ('attendance', 'Attendance'),
        ('leave', 'Leave'),
        ('system', 'System'),
        ('document', 'Document'),
        ('resignation', 'Resignation'),
        ('device', 'Device'),
        ('announcement', 'Announcement'),
        ('reminder', 'Reminder'),
        ('approval', 'Approval'),
        ('rejection', 'Rejection'),
        ('bank_update', 'Bank Account Update'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    CATEGORY_CHOICES = [
        ('info', 'Information'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPE_CHOICES)
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES, default='info')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    is_read = models.BooleanField(default=False)
    is_email_sent = models.BooleanField(default=False)
    action_url = models.URLField(blank=True, null=True, help_text="URL to navigate when notification is clicked")
    action_text = models.CharField(max_length=100, blank=True, help_text="Text for action button")
    expires_at = models.DateTimeField(blank=True, null=True, help_text="When notification expires")
    related_object_id = models.UUIDField(blank=True, null=True, help_text="ID of related object (attendance, leave, etc.)")
    related_object_type = models.CharField(max_length=50, blank=True, help_text="Type of related object")
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_notifications')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['notification_type', 'created_at']),
            models.Index(fields=['priority', 'created_at']),
        ]

    def __str__(self):
        try:
            return f"{self.title} - {self.user.get_full_name()}"
        except Exception:
            return f"{self.title} - Unknown User"
    
    def is_expired(self):
        """Check if notification has expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    def mark_as_read(self):
        """Mark notification as read"""
        self.is_read = True
        self.save(update_fields=['is_read', 'updated_at'])
    
    def mark_email_sent(self):
        """Mark email as sent"""
        self.is_email_sent = True
        self.save(update_fields=['is_email_sent', 'updated_at'])




class SystemSettings(models.Model):
    """System settings model for configuration"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "System Settings"
        ordering = ['key']

    def __str__(self):
        return f"{self.key}: {self.value}"


class AttendanceLog(models.Model):
    """Log model for tracking attendance changes"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attendance = models.ForeignKey(Attendance, on_delete=models.CASCADE)
    action = models.CharField(max_length=50)  # 'created', 'updated', 'deleted'
    old_values = models.JSONField(null=True, blank=True)
    new_values = models.JSONField(null=True, blank=True)
    changed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        try:
            return f"{self.action} - {self.attendance}"
        except Exception:
            return f"{self.action} - Unknown Attendance"


class ESSLAttendanceLog(models.Model):
    """Raw attendance log from ESSL devices"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    biometric_id = models.CharField(max_length=50)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    punch_time = models.DateTimeField()
    punch_type = models.CharField(max_length=10, choices=[
        ('in', 'Check In'),
        ('out', 'Check Out'),
    ])
    is_processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-punch_time']
        indexes = [
            models.Index(fields=['biometric_id', 'punch_time']),
            models.Index(fields=['device', 'punch_time']),
        ]

    def __str__(self):
        return f"{self.biometric_id} - {self.punch_time} ({self.punch_type})"


class WorkingHoursSettings(models.Model):
    """Settings for working hours and attendance rules"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    office = models.ForeignKey(Office, on_delete=models.CASCADE)
    standard_hours = models.DecimalField(max_digits=4, decimal_places=2, default=9.0, help_text="Standard working hours per day")
    start_time = models.TimeField(default='10:00:00', help_text="Standard start time")
    end_time = models.TimeField(default='19:00:00', help_text="Standard end time")
    late_threshold = models.IntegerField(default=15, help_text="Minutes after start time to consider late")
    half_day_threshold = models.IntegerField(default=300, help_text="Minutes to consider half day (5 hours)")
    late_coming_threshold = models.TimeField(default='11:30:00', help_text="Time after which check-in is considered late coming")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Working Hours Settings"
        unique_together = ['office']

    def __str__(self):
        try:
            return f"{self.office.name} - {self.standard_hours} hours"
        except Exception:
            return f"Working Hours - {self.standard_hours} hours"


class DocumentTemplate(models.Model):
    """Template for generating documents like offer letters, salary increment letters"""
    DOCUMENT_TYPE_CHOICES = [
        ('offer_letter', 'Offer Letter'),
        ('salary_increment', 'Salary Increment Letter'),
        ('salary_slip', 'Salary Slip'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPE_CHOICES)
    template_content = models.TextField(help_text="HTML template with Django template variables")
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Document Templates"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_document_type_display()})"


class GeneratedDocument(models.Model):
    """Generated documents for employees"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='generated_documents')
    template = models.ForeignKey(DocumentTemplate, on_delete=models.CASCADE)
    document_type = models.CharField(max_length=50, choices=DocumentTemplate.DOCUMENT_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    content = models.TextField(help_text="Generated HTML content")
    pdf_file = models.FileField(upload_to='generated_documents/', null=True, blank=True)
    generated_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='generated_documents_by')
    generated_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    is_sent = models.BooleanField(default=False)
    
    # Additional data for specific document types
    offer_data = models.JSONField(null=True, blank=True, help_text="Data specific to offer letters")
    increment_data = models.JSONField(null=True, blank=True, help_text="Data specific to salary increment letters")
    salary_data = models.JSONField(null=True, blank=True, help_text="Data specific to salary slips")

    class Meta:
        verbose_name_plural = "Generated Documents"
        ordering = ['-generated_at']

    def __str__(self):
        try:
            return f"{self.title} - {self.employee.get_full_name()} ({self.generated_at.date()})"
        except Exception:
            return f"{self.title} - Unknown Employee ({self.generated_at.date()})"


class Resignation(models.Model):
    """Resignation model for employee resignation"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='resignations')
    resignation_date = models.DateField(help_text="Resignation submission date")
    notice_period_days = models.IntegerField(default=30, help_text="Notice period in days (15 or 30)")
    reason = models.TextField(help_text="Reason for resignation")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    approved_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='approved_resignations',
        limit_choices_to={'role__in': ['admin', 'manager']}
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, help_text="Reason for rejection if applicable")
    handover_notes = models.TextField(blank=True, help_text="Handover notes and pending work")
    last_working_date = models.DateField(null=True, blank=True, help_text="Automatically calculated last working date (resignation_date + notice_period)")
    is_handover_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Resignation"
        verbose_name_plural = "Resignations"

    def __str__(self):
        try:
            return f"{self.user.get_full_name()} - {self.resignation_date} ({self.status})"
        except Exception:
            return f"Resignation - {self.resignation_date} ({self.status})"

    def clean(self):
        """Validate resignation data"""
        # Ensure resignation date is today or in the future (submission date)
        # Only validate on creation, not on updates (approvals)
        if not self.pk and self.resignation_date and self.resignation_date < timezone.now().date():
            raise ValidationError('Resignation date cannot be in the past.')
        
        # Ensure notice period is reasonable (15 or 30 days)
        if self.notice_period_days and self.notice_period_days not in [15, 30]:
            raise ValidationError('Notice period must be either 15 or 30 days.')
        
        # Ensure approved_by is admin or manager
        if self.approved_by and self.approved_by.role not in ['admin', 'manager']:
            raise ValidationError('Only admin or manager can approve resignations.')
        
        # Ensure user is an employee
        if self.user.role != 'employee':
            raise ValidationError('Only employees can submit resignation requests.')

    def save(self, *args, **kwargs):
        self.clean()
        
        # Calculate last working date based on notice period
        # Last working day = resignation_date + notice_period_days
        if self.resignation_date and self.notice_period_days:
            self.last_working_date = self.resignation_date + timedelta(days=self.notice_period_days)
        
        super().save(*args, **kwargs)


class Salary(models.Model):
    """Salary model for employee salary management with auto-calculation"""
    SALARY_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('hold', 'Hold'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('bank_transfer', 'Bank Transfer'),
        ('cash', 'Cash'),
        ('cheque', 'Cheque'),
        ('upi', 'Upi'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="salaries"
    )
    
    # Basic Salary Information
    basic_pay = models.DecimalField(max_digits=10, decimal_places=2, help_text="Basic salary amount (for reference only)")
    per_day_pay = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Per day pay amount (used for calculation)")
    increment = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Increment amount")
    total_days = models.PositiveIntegerField(default=30, help_text="Total working days in the month")
    worked_days = models.DecimalField(max_digits=5, decimal_places=2, default=30, help_text="Days actually worked (including holiday pay)")
    previous_month_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Previous month balance")
    
    # Deductions and Adjustments
    deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Total deductions")
    balance_loan = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Outstanding loan balance")
    remaining_pay = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Remaining pay after deductions")
    
    # Calculated Salary Fields (stored in database)
    gross_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Gross salary (per_day_pay * worked_days)")
    net_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Net salary after deductions")
    
    
    # Salary Period and Payment
    salary_month = models.DateField(help_text="Salary month (first day of the month)")
    pay_date = models.DateField(null=True, blank=True, help_text="Scheduled pay date")
    paid_date = models.DateField(null=True, blank=True, help_text="Actual payment date")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='bank_transfer')
    Bank_name = models.CharField(max_length=100, null=True, blank=True, help_text="Bank name for salary payment")
    
    # Status and Approval
    status = models.CharField(max_length=20, choices=SALARY_STATUS_CHOICES, default='pending')
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_salaries',
        limit_choices_to={'role__in': ['admin', 'manager','accountant']}
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Notes and Comments
    notes = models.TextField(blank=True, help_text="Additional notes or comments")
    status_reason = models.TextField(blank=True, help_text="Reason for current status if applicable")
    
    # Auto-calculation flags
    is_auto_calculated = models.BooleanField(default=False, help_text="Whether salary was auto-calculated from attendance")
    attendance_based = models.BooleanField(default=True, help_text="Whether salary is based on attendance")
    
    # System fields
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_salaries',
        limit_choices_to={'role__in': ['admin', 'manager', 'accountant']}
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Salary"
        verbose_name_plural = "Salaries"
        ordering = ['-salary_month', '-created_at']
        unique_together = ['employee', 'salary_month']
        indexes = [
            models.Index(fields=['employee', 'salary_month']),
            models.Index(fields=['status', 'salary_month']),
            models.Index(fields=['approved_by', 'approved_at']),
        ]

    def __str__(self):
        try:
            return f"Salary for {self.employee.get_full_name()} - {self.salary_month.strftime('%B %Y')}"
        except Exception:
            return f"Salary - {self.salary_month.strftime('%B %Y')}"

    def clean(self):
        """Validate salary data"""
        super().clean()
        
        # Ensure basic_pay is positive
        if self.basic_pay <= 0:
            raise ValidationError('Basic pay must be greater than zero.')
        
        # Ensure approved_by is admin or manager
        if self.approved_by and self.approved_by.role not in ['admin', 'manager', 'accountant']:
            raise ValidationError('Only admin, manager or accountant can approve salaries.')

    def save(self, *args, **kwargs):
        self.clean()
        
        # Auto-calculate worked_days from attendance if not manually set
        if self.attendance_based and (self._state.adding or hasattr(self, '_recalculate_from_attendance')):
            self.calculate_worked_days_from_attendance()
        
        # Ensure worked_days has a reasonable default if it's 0
        if self.worked_days == 0:
            if not self.attendance_based:
                self.worked_days = self.total_days
        
        # Calculate and store gross_salary and net_salary in database fields
        self.gross_salary = Decimal(str(self.per_day_pay)) * Decimal(str(self.worked_days))
        self.net_salary=self.previous_month_salary+ self.gross_salary - self.deduction
        
        # Auto-calculate remaining_pay
        self.calculate_remaining_pay()
        
        super().save(*args, **kwargs)

    # Auto-calculated fields (properties)
    @property
    def final_salary(self):
        """Final salary before deductions (basic + increment)"""
        return self.basic_pay + self.increment

    @property
    def per_day_salary(self):
        """Salary per day (returns the per_day_pay field)"""
        return Decimal(str(self.per_day_pay))

    @property
    def gross_salary_property(self):
        """Gross salary based on worked days (property for backward compatibility)"""
        return self.per_day_salary * Decimal(self.worked_days)

    @property
    def total_allowances(self):
        """Total of all allowances"""
        return 0  # No additional allowances

    @property
    def total_deductions(self):
        """Total of all deductions"""
        return Decimal(str(self.deduction))  # Only basic deduction

    @property
    def net_salary_property(self):
        """Net salary after all deductions (property for backward compatibility)"""
        return self.gross_salary - self.total_deductions

    @property
    def final_payable_amount(self):
        """Final amount to be paid (net salary - loan balance)"""
        return max(0, self.net_salary - self.balance_loan)

    def calculate_worked_days_from_attendance(self):
        """Calculate worked days from attendance records matching frontend logic"""
        try:
            from django.utils import timezone
            from datetime import datetime, timedelta
            from coreapp.models import Holiday  # Local import to avoid circular dependencies
            
            # Get the month and year from salary_month
            year = self.salary_month.year
            month = self.salary_month.month
            
            # Calculate start and end dates for the month
            start_date = datetime(year, month, 1).date()
            if month == 12:
                # For December, next month is Jan of next year
                end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
            else:
                end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)
            
            # 1. Calculate Present Days
            # Count distinct dates where status is 'present'
            present_days_count = Attendance.objects.filter(
                user=self.employee,
                date__range=[start_date, end_date],
                status='present'
            ).count()
            
            # 2. Calculate Sundays
            total_sundays = 0
            current = start_date
            while current <= end_date:
                if current.weekday() == 6:  # 6 is Sunday
                    total_sundays += 1
                current += timedelta(days=1)
                
            # 3. Calculate Effective Holidays (excluding Sundays)
            # Fetch holidays in the range
            holidays_qs = Holiday.objects.filter(
                date__range=[start_date, end_date]
            )
            
            effective_holidays = 0
            for holiday in holidays_qs:
                # Check if holiday is NOT on a Sunday
                if holiday.date.weekday() != 6:
                    effective_holidays += 1
                    
            # 4. Calculate Extra Days (to reach 30 standard days logic if applicable)
            # Matches frontend "Extra Days" logic: 30 - actual_days if actual < 30
            actual_days_in_month = (end_date - start_date).days + 1
            extra_days = 0
            if actual_days_in_month < 30:
                extra_days = 30 - actual_days_in_month
            
            # Total Formula: Present + Sundays + Holidays(non-Sunday) + Extra
            total_worked_days = present_days_count + total_sundays + effective_holidays + extra_days
            
            # Update worked_days
            self.worked_days = Decimal(str(total_worked_days))
            self.is_auto_calculated = True
            
        except Exception as e:
            # If calculation fails, keep the current worked_days or log error
            print(f"Error calculating worked days for {self.employee}: {e}")
            pass

    def calculate_remaining_pay(self):
        """Calculate remaining pay after deductions and loan balance"""
        self.remaining_pay = self.final_payable_amount

    def mark_as_paid(self, paid_date=None):
        """Mark salary as paid"""
        self.status = 'paid'
        self.paid_date = paid_date or timezone.now().date()
        self.save()
    
    def mark_as_hold(self):
        """Mark salary as hold"""
        self.status = 'hold'
        self.save()
    
    def mark_as_pending(self):
        """Mark salary as pending"""
        self.status = 'pending'
        self.save()

    def get_salary_breakdown(self):
        """Get detailed salary breakdown for display"""
        return {
            'basic_pay': float(self.basic_pay),
            'per_day_pay': float(self.per_day_pay),
            'increment': float(self.increment),
            'final_salary': float(self.final_salary),
            'per_day_salary': float(self.per_day_salary),
            'worked_days': float(self.worked_days),
            'total_days': self.total_days,
            'gross_salary': float(self.gross_salary),
            'allowances': {
                'total': float(self.total_allowances)
            },
            'deductions': {
                'general': float(self.deduction),
                'total': float(self.total_deductions)
            },
            'loan_balance': float(self.balance_loan),
            'net_salary': float(self.net_salary),
            'final_payable': float(self.final_payable_amount)
        }


class SalaryTemplate(models.Model):
    """Template for salary structure by designation"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, help_text="Template name")
    designation = models.ForeignKey(Designation, on_delete=models.CASCADE, related_name='salary_templates')
    office = models.ForeignKey(Office, on_delete=models.CASCADE, related_name='salary_templates')
    
    # Salary structure
    basic_pay = models.DecimalField(max_digits=10, decimal_places=2, help_text="Basic salary amount (for reference only)")
    per_day_pay = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Per day pay amount (used for calculation)")
    
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Salary Template"
        verbose_name_plural = "Salary Templates"
        unique_together = ['designation', 'office']
        ordering = ['designation__name', 'office__name']

    def __str__(self):
        return f"{self.name} - {self.designation.name} ({self.office.name})"

    def apply_to_employee(self, employee, salary_month):
        """Apply this template to create a salary for an employee"""
        if employee.designation != self.designation or employee.office != self.office:
            raise ValidationError('Employee designation or office does not match template.')
        
        # Create salary record
        salary = Salary.objects.create(
            employee=employee,
            basic_pay=self.basic_pay,
            per_day_pay=self.per_day_pay,
            salary_month=salary_month,
            attendance_based=True,
            is_auto_calculated=True
        )
        
        return salary


class Shift(models.Model):
    """Simple Shift model for managing work shifts"""
    SHIFT_CHOICES = [
        ('morning', 'Morning'),
        ('afternoon', 'Afternoon'),
        ('evening', 'Evening'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, help_text="Shift name")
    shift_type = models.CharField(max_length=20, choices=SHIFT_CHOICES)
    start_time = models.TimeField(help_text="Shift start time")
    end_time = models.TimeField(help_text="Shift end time")
    office = models.ForeignKey(Office, on_delete=models.CASCADE, related_name='shifts')
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='created_shifts',
        limit_choices_to={'role__in': ['admin', 'manager']}
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Shift"
        verbose_name_plural = "Shifts"
        ordering = ['office', 'start_time', 'name']
        unique_together = ['name', 'office']

    def __str__(self):
        try:
            return f"{self.name} ({self.office.name}) - {self.start_time} to {self.end_time}"
        except Exception:
            return f"{self.name} - {self.start_time} to {self.end_time}"

    def clean(self):
        """Validate shift data"""
        super().clean()
        
        # Ensure start time is before end time
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError('Start time must be before end time.')
        
        # Ensure created_by is admin or manager
        if self.created_by and self.created_by.role not in ['admin', 'manager']:
            raise ValidationError('Only admin or manager can create shifts.')

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class EmployeeShiftAssignment(models.Model):
    """Simple model for assigning employees to shifts permanently"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='shift_assignments',
        limit_choices_to={'role': 'employee'}
    )
    shift = models.ForeignKey(Shift, on_delete=models.CASCADE, related_name='employee_assignments')
    assigned_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='assigned_shifts',
        limit_choices_to={'role__in': ['admin', 'manager']}
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Employee Shift Assignment"
        verbose_name_plural = "Employee Shift Assignments"
        ordering = ['-created_at']
        unique_together = ['employee', 'shift']  # One assignment per employee per shift

    def __str__(self):
        try:
            return f"{self.employee.get_full_name()} - {self.shift.name}"
        except Exception:
            return f"Shift Assignment - {self.shift.name}"

    def clean(self):
        """Validate assignment data"""
        super().clean()
        
        # Ensure employee is actually an employee
        if self.employee.role != 'employee':
            raise ValidationError('Only employees can be assigned to shifts.')
        
        # Ensure assigned_by is admin or manager
        if self.assigned_by and self.assigned_by.role not in ['admin', 'manager']:
            raise ValidationError('Only admin or manager can assign shifts.')

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)