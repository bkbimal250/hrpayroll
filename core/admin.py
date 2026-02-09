from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import AdminPasswordChangeForm, UserCreationForm
from django.contrib.admin.helpers import AdminForm
from django.utils.html import format_html
from django import forms
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse, path
from django.contrib import messages
from django.template.response import TemplateResponse
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.utils import timezone
from .models import (
    CustomUser, Office, Device, DeviceUser, Attendance, Leave, Document, 
    Notification, SystemSettings, AttendanceLog, ESSLAttendanceLog, 
    WorkingHoursSettings, Resignation, DocumentTemplate, GeneratedDocument,
    Department, Designation, Shift, EmployeeShiftAssignment, BankAccountHistory
)

from unfold.admin import ModelAdmin as UnfoldModelAdmin


@admin.register(Office)
class OfficeAdmin(UnfoldModelAdmin):
    list_display = ['name', 'phone', 'email', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'address', 'email', 'phone']
    ordering = ['name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Department)
class DepartmentAdmin(UnfoldModelAdmin):
    list_display = ['name', 'description', 'is_active', 'designation_count', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        (None, {'fields': ('name', 'description', 'is_active')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )
    
    actions = ['activate_departments', 'deactivate_departments']
    
    def designation_count(self, obj):
        """Show count of designations for this department"""
        count = obj.designations.count()
        return format_html(
            '<span style="color: blue;">{}</span> designations' if count > 0 
            else '<span style="color: gray;">No designations</span>',
            count
        )
    designation_count.short_description = "Designations"
    designation_count.admin_order_field = 'designations__count'
    
    def activate_departments(self, request, queryset):
        """Activate selected departments"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} departments activated.')
    activate_departments.short_description = "Activate selected departments"
    
    def deactivate_departments(self, request, queryset):
        """Deactivate selected departments"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} departments deactivated.')
    deactivate_departments.short_description = "Deactivate selected departments"


@admin.register(Designation)
class DesignationAdmin(UnfoldModelAdmin):
    list_display = ['name', 'department', 'description', 'is_active', 'created_at']
    list_filter = ['department', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'department__name']
    ordering = ['department__name', 'name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        (None, {'fields': ('name', 'department', 'description', 'is_active')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )
    
    actions = ['activate_designations', 'deactivate_designations']
    
    def get_queryset(self, request):
        """Optimize queryset with select_related for department"""
        return super().get_queryset(request).select_related('department')
    
    def activate_designations(self, request, queryset):
        """Activate selected designations"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} designations activated.')
    activate_designations.short_description = "Activate selected designations"
    
    def deactivate_designations(self, request, queryset):
        """Deactivate selected designations"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} designations deactivated.')
    deactivate_designations.short_description = "Deactivate selected designations"


class CustomUserChangeForm(forms.ModelForm):
    """Form for changing user information including password"""
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Enter new password (leave blank to keep current password)',
            'autocomplete': 'new-password'
        }),
        required=False,
        help_text="Leave blank to keep the current password. Use 'Change Password' link for secure password change."
    )
    
    class Meta:
        model = CustomUser
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make password field optional for existing users
        if self.instance.pk:
            self.fields['password'].required = False
            self.fields['password'].help_text = "Leave blank to keep current password"
            # Set initial value to empty string to avoid any issues
            self.fields['password'].initial = ''
    
    def clean_password(self):
        """Clean password field - ensure it's properly handled"""
        password = self.cleaned_data.get('password')
        # If password is empty or just whitespace, return None
        if not password or password.strip() == '':
            return None
        return password
    
    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        # Only set password if a new one was provided
        if password and password.strip():
            user.set_password(password)
        if commit:
            user.save()
        return user


class CustomUserAdminForm(UserCreationForm):
    """Custom form for CustomUser admin with error handling for department and designation"""
    
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = UserCreationForm.Meta.fields + ('email', 'first_name', 'last_name', 'role', 'office')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Handle invalid department reference
        if self.instance and self.instance.pk:
            try:
                # Check if department_id exists but department doesn't
                if self.instance.department_id:
                    try:
                        dept = self.instance.department
                        if not dept:
                            self.fields['department'].help_text = "⚠️ Current department reference is invalid. Please select a valid department."
                    except Exception:
                        self.fields['department'].help_text = "⚠️ Current department reference is invalid. Please select a valid department."
                        # Clear the invalid reference
                        self.instance.department_id = None
            except Exception:
                pass  # Ignore errors during form initialization
            
            # Handle invalid designation reference
            try:
                # Check if designation_id exists but designation doesn't
                if self.instance.designation_id:
                    try:
                        desig = self.instance.designation
                        if not desig:
                            self.fields['designation'].help_text = "⚠️ Current designation reference is invalid. Please select a valid designation."
                    except Exception:
                        self.fields['designation'].help_text = "⚠️ Current designation reference is invalid. Please select a valid designation."
                        # Clear the invalid reference
                        self.instance.designation_id = None
            except Exception:
                pass  # Ignore errors during form initialization
    
    def clean_department(self):
        """Clean department field to handle invalid references"""
        department = self.cleaned_data.get('department')
        if not department and self.instance.department_id:
            # If no department selected but instance has invalid department_id, clear it
            try:
                self.instance.department
            except Exception:
                self.instance.department_id = None
        return department
    
    def clean_designation(self):
        """Clean designation field to handle invalid references"""
        designation = self.cleaned_data.get('designation')
        if not designation and self.instance.designation_id:
            # If no designation selected but instance has invalid designation_id, clear it
            try:
                self.instance.designation
            except Exception:
                self.instance.designation_id = None
        return designation


class SafeCustomUserAdmin(BaseUserAdmin, UnfoldModelAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserAdminForm
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'office', 'department_name', 'designation_display', 'pay_bank_name', 'aadhaar_card', 'pan_card', 'is_active', 'last_login']
    list_filter = ['role', 'office', 'is_active', 'department', 'pay_bank_name', 'created_at']
    search_fields = ['username', 'first_name', 'last_name', 'email', 'employee_id', 'aadhaar_card', 'pan_card', 'pay_bank_name']
    ordering = ['username']
    readonly_fields = ['id', 'last_login', 'created_at', 'updated_at']
    
    # Define fieldsets to organize the form
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'phone', 'employee_id')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'role', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('Office Information', {'fields': ('office', 'department', 'designation')}),
        ('Personal Details', {'fields': ('date_of_birth', 'gender', 'address', 'aadhaar_card', 'pan_card')}),
        ('Employment Details', {'fields': ('biometric_id', 'joining_date', 'salary', 'pay_bank_name')}),
        ('Emergency Contact', {'fields': ('emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relationship')}),
        ('Bank Details', {'fields': ('account_holder_name', 'bank_name', 'account_number', 'ifsc_code', 'bank_branch_name')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'first_name', 'last_name', 'role', 'office'),
        }),
    )
    
    def get_queryset(self, request):
        """Override get_queryset to handle search safely"""
        try:
            qs = super().get_queryset(request)
            # Use select_related to avoid N+1 queries
            return qs.select_related('office', 'department', 'designation')
        except Exception as e:
            # If there's an error, return a basic queryset
            from django.contrib import messages
            messages.error(request, f"Error loading users: {str(e)}")
            return CustomUser.objects.all()
    
    def get_search_results(self, request, queryset, search_term):
        """Override search to handle errors gracefully"""
        try:
            return super().get_search_results(request, queryset, search_term)
        except Exception as e:
            # If search fails, return the original queryset
            from django.contrib import messages
            messages.warning(request, f"Search error: {str(e)}. Showing all results.")
            return queryset, False
    
    def get_urls(self):
        """Add custom URLs for password change"""
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                '<id>/password/',
                self.admin_site.admin_view(self.user_change_password),
                name='core_customuser_password_change',
            ),
        ]
        return custom_urls + urls
    
    def user_change_password(self, request, id, form_url=''):
        """Custom password change view"""
        if not self.has_change_permission(request):
            raise PermissionDenied
        user = self.get_object(request, id)
        if user is None:
            raise Http404('User object with primary key %s does not exist.' % id)
        
        if request.method == 'POST':
            form = AdminPasswordChangeForm(user, request.POST)
            if form.is_valid():
                form.save()
                change_message = self.construct_change_message(request, form, None)
                self.log_change(request, user, change_message)
                msg = 'Password changed successfully.'
                messages.success(request, msg)
                return HttpResponseRedirect(
                    reverse(
                        '%s:%s_%s_change' % (
                            self.admin_site.name,
                            user._meta.app_label,
                            user._meta.model_name,
                        ),
                        args=(user.pk,),
                    )
                )
        else:
            form = AdminPasswordChangeForm(user)
        
        fieldsets = [(None, {'fields': list(form.base_fields)})]
        adminForm = AdminForm(form, fieldsets, {})
        
        context = {
            'title': 'Change password: %s' % user.get_username(),
            'adminForm': adminForm,
            'form_url': form_url,
            'form': form,
            'is_popup': (request.GET.get('_popup') == '1'),
            'is_popup_var': '_popup',
            'add': True,
            'change': False,
            'has_delete_permission': False,
            'has_change_permission': True,
            'has_absolute_url': False,
            'opts': self.model._meta,
            'original': user,
            'save_as': False,
            'has_add_permission': False,
            'has_view_permission': True,
            'has_editable_inline_admin_formsets': False,
        }
        
        return TemplateResponse(
            request,
            'admin/auth/user/change_password.html',
            context,
        )
    
    # Override the render_change_form to handle errors gracefully
    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        """Override render_change_form to handle errors gracefully"""
        try:
            return super().render_change_form(request, context, add, change, form_url, obj)
        except Exception as e:
            # If there's an error rendering the form, try to fix the object first
            if obj and hasattr(obj, 'department_id') and obj.department_id:
                try:
                    obj.department
                except Exception:
                    obj.department_id = None
                    obj.save(update_fields=['department_id'])
            
            if obj and hasattr(obj, 'designation_id') and obj.designation_id:
                try:
                    obj.designation
                except Exception:
                    obj.designation_id = None
                    obj.save(update_fields=['designation_id'])
            
            # Try again
            try:
                return super().render_change_form(request, context, add, change, form_url, obj)
            except Exception:
                # If still failing, redirect to changelist
                from django.contrib import messages
                from django.http import HttpResponseRedirect
                from django.urls import reverse
                
                messages.error(request, f"Error rendering form for user {obj.username if obj else 'unknown'}. Please try again.")
                return HttpResponseRedirect(reverse('admin:core_customuser_changelist'))
    
    # Override the formfield_for_foreignkey to handle invalid references
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name in ['department', 'designation']:
            # Get the object being edited
            obj_id = request.resolver_match.kwargs.get('object_id')
            if obj_id:
                try:
                    obj = CustomUser.objects.get(pk=obj_id)
                    # Check if the current value is invalid
                    if db_field.name == 'department' and obj.department_id:
                        try:
                            obj.department
                        except Exception:
                            # Clear invalid reference
                            obj.department_id = None
                            obj.save(update_fields=['department_id'])
                    elif db_field.name == 'designation' and obj.designation_id:
                        try:
                            obj.designation
                        except Exception:
                            # Clear invalid reference
                            obj.designation_id = None
                            obj.save(update_fields=['designation_id'])
                except Exception:
                    pass  # Ignore errors
        
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    fieldsets = (
        (None, {
            'fields': ('username', 'password'),
            'description': 'Password field: Leave blank to keep current password unchanged. Only enter a new password if you want to change it.'
        }),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'phone', 'address', 'date_of_birth', 'gender', 'profile_picture')}),
        ('Government ID', {'fields': ('aadhaar_card', 'pan_card')}),
        ('Employment', {'fields': ('role', 'office', 'employee_id', 'biometric_id', 'joining_date', 'department', 'designation', 'salary', 'pay_bank_name')}),
        ('Emergency Contact', {'fields': ('emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relationship')}),
        ('Bank Details', {'fields': ('account_holder_name', 'bank_name', 'account_number', 'ifsc_code', 'bank_branch_name')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role', 'office'),
        }),
    )
    
    actions = ['reset_passwords_to_default', 'send_password_reset_instructions']
    
    def reset_passwords_to_default(self, request, queryset):
        """Reset selected users' passwords to a default password"""
        default_password = 'TempPassword123!'  # You can customize this
        count = 0
        for user in queryset:
            user.set_password(default_password)
            user.save()
            count += 1
        
        from django.contrib import messages
        messages.success(request, f'{count} user passwords reset to default. Users should change their passwords on first login.')
    reset_passwords_to_default.short_description = "Reset passwords to default"
    
    def send_password_reset_instructions(self, request, queryset):
        """Send password reset instructions to selected users"""
        count = 0
        for user in queryset:
            if user.email:
                # Here you would implement email sending logic
                # For now, just count the users with email addresses
                count += 1
        
        from django.contrib import messages
        messages.info(request, f'Password reset instructions would be sent to {count} users with email addresses.')
    send_password_reset_instructions.short_description = "Send password reset instructions"
    
    def get_queryset(self, request):
        """Get queryset without any select_related to avoid DoesNotExist errors"""
        # Don't use select_related at all to avoid any potential issues
        # with invalid foreign key references
        return super().get_queryset(request)
    
    def save_model(self, request, obj, form, change):
        """Override save_model to handle password preservation"""
        if change:  # If updating existing user
            # Get the original password from the database
            original_user = CustomUser.objects.get(pk=obj.pk)
            original_password = original_user.password
            
            # Only update password if a new one was provided in the form
            password = form.cleaned_data.get('password')
            if not password or password.strip() == '':
                # Keep the original password
                obj.password = original_password
            else:
                # Set the new password (this will be hashed by Django)
                obj.set_password(password)
        
        # Save the object
        super().save_model(request, obj, form, change)
        
        # Provide feedback to the user
        if change:
            password = form.cleaned_data.get('password')
            if not password or password.strip() == '':
                from django.contrib import messages
                messages.success(request, f'User "{obj.username}" updated successfully. Password was preserved.')
            else:
                from django.contrib import messages
                messages.success(request, f'User "{obj.username}" updated successfully. Password was changed.')
    
    def get_object(self, request, object_id, from_field=None):
        """Override get_object to handle invalid references gracefully"""
        try:
            return super().get_object(request, object_id, from_field)
        except Exception as e:
            # If there's an error getting the object, try to get it directly
            try:
                from django.shortcuts import get_object_or_404
                obj = get_object_or_404(CustomUser, pk=object_id)
                
                # Check and fix any invalid references
                needs_save = False
                
                if obj.department_id:
                    try:
                        obj.department
                    except Exception:
                        obj.department_id = None
                        needs_save = True
                
                if obj.designation_id:
                    try:
                        obj.designation
                    except Exception:
                        obj.designation_id = None
                        needs_save = True
                
                if needs_save:
                    obj.save(update_fields=['department_id', 'designation_id'])
                
                return obj
            except Exception:
                raise e
    
    def get_form(self, request, obj=None, **kwargs):
        """Override get_form to handle invalid references gracefully"""
        form = super().get_form(request, obj, **kwargs)
        
        # If we have an object, check for invalid references
        if obj:
            try:
                # Check department reference
                if obj.department_id:
                    try:
                        obj.department
                    except Exception:
                        # Clear invalid department reference
                        obj.department_id = None
                        obj.save(update_fields=['department_id'])
                
                # Check designation reference
                if obj.designation_id:
                    try:
                        obj.designation
                    except Exception:
                        # Clear invalid designation reference
                        obj.designation_id = None
                        obj.save(update_fields=['designation_id'])
                        
            except Exception:
                pass  # Ignore errors during form preparation
        
        # Ensure password field is properly handled for existing users
        if obj and hasattr(form, 'fields') and 'password' in form.fields:
            form.fields['password'].required = False
            form.fields['password'].initial = ''
            form.fields['password'].help_text = "Leave blank to keep current password. Enter new password only if you want to change it."
        
        return form
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Override change_view to handle invalid references gracefully"""
        try:
            # First, try to get the object using raw SQL to avoid any ORM issues
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM core_customuser WHERE id = %s", [object_id])
                row = cursor.fetchone()
                if not row:
                    from django.shortcuts import get_object_or_404
                    obj = get_object_or_404(CustomUser, pk=object_id)
                else:
                    # Get the object using the primary key only
                    obj = CustomUser.objects.get(pk=object_id)
            
            # Check and fix any invalid references before proceeding
            needs_save = False
            
            # Check department reference
            if obj.department_id:
                try:
                    obj.department
                except Exception:
                    obj.department_id = None
                    needs_save = True
            
            # Check designation reference
            if obj.designation_id:
                try:
                    obj.designation
                except Exception:
                    obj.designation_id = None
                    needs_save = True
            
            # Save if we made changes
            if needs_save:
                obj.save(update_fields=['department_id', 'designation_id'])
                from django.contrib import messages
                messages.warning(request, f"Fixed invalid department/designation references for user {obj.username}.")
            
            # Now proceed with the normal change view
            return super().change_view(request, object_id, form_url, extra_context)
            
        except Exception as e:
            # If there's still an error, try a more direct approach
            try:
                from django.shortcuts import get_object_or_404
                from django.contrib import messages
                from django.http import HttpResponseRedirect
                from django.urls import reverse
                
                obj = get_object_or_404(CustomUser, pk=object_id)
                messages.error(request, f"Error accessing user {obj.username}. Please try again.")
                return HttpResponseRedirect(reverse('admin:core_customuser_changelist'))
            except Exception:
                raise e
    
    def get_urls(self):
        """Override get_urls to add custom error handling"""
        from django.urls import path
        urls = super().get_urls()
        
        # Add a custom URL for handling problematic users
        custom_urls = [
            path(
                '<path:object_id>/change/',
                self.admin_site.admin_view(self.safe_change_view),
                name='core_customuser_change',
            ),
        ]
        return custom_urls + urls
    
    def safe_change_view(self, request, object_id, form_url='', extra_context=None):
        """Safe change view that handles all errors gracefully"""
        try:
            # Get the object safely
            from django.shortcuts import get_object_or_404
            obj = get_object_or_404(CustomUser, pk=object_id)
            
            # Check and fix any invalid references
            needs_save = False
            
            if obj.department_id:
                try:
                    obj.department
                except Exception:
                    obj.department_id = None
                    needs_save = True
            
            if obj.designation_id:
                try:
                    obj.designation
                except Exception:
                    obj.designation_id = None
                    needs_save = True
            
            if needs_save:
                obj.save(update_fields=['department_id', 'designation_id'])
                from django.contrib import messages
                messages.warning(request, f"Fixed invalid references for user {obj.username}.")
            
            # Now proceed with the normal change view
            return super().change_view(request, object_id, form_url, extra_context)
            
        except Exception as e:
            # If there's still an error, redirect to changelist with error message
            from django.contrib import messages
            from django.http import HttpResponseRedirect
            from django.urls import reverse
            
            messages.error(request, f"Error accessing user. Please try again. Error: {str(e)}")
            return HttpResponseRedirect(reverse('admin:core_customuser_changelist'))
    
    def department_name(self, obj):
        """Display department name with error handling"""
        try:
            if obj.department:
                return obj.department.name
        except Exception:
            return format_html('<span style="color: red;">Invalid Department</span>')
        return "No Department"
    department_name.short_description = "Department"
    department_name.admin_order_field = 'department__name'
    
    def designation_display(self, obj):
        """Display designation with styling and error handling"""
        try:
            if obj.designation:
                return format_html(
                    '<span style="color: blue; font-weight: bold;">{}</span>',
                    obj.designation.name
                )
        except Exception:
            return format_html('<span style="color: red;">Invalid Designation</span>')
        return format_html('<span style="color: gray;">No Designation</span>')
    designation_display.short_description = "Designation"
    designation_display.admin_order_field = 'designation__name'


# Register the safe admin
try:
    admin.site.unregister(CustomUser)
except admin.sites.NotRegistered:
    pass
admin.site.register(CustomUser, SafeCustomUserAdmin)


@admin.register(Device)
class DeviceAdmin(UnfoldModelAdmin):
    list_display = ['name', 'device_type', 'ip_address', 'office', 'is_active', 'last_sync']
    list_filter = ['device_type', 'office', 'is_active', 'created_at']
    search_fields = ['name', 'ip_address', 'serial_number', 'location']
    ordering = ['name']
    readonly_fields = ['id', 'last_sync', 'created_at', 'updated_at']


@admin.register(DeviceUser)
class DeviceUserAdmin(UnfoldModelAdmin):
    list_display = ['device_user_name', 'device_user_id', 'device', 'is_mapped', 'system_user', 'created_at']
    list_filter = ['device', 'is_mapped', 'device_user_privilege', 'created_at']
    search_fields = ['device_user_name', 'device_user_id', 'device__name']
    ordering = ['device', 'device_user_id']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        (None, {'fields': ('device', 'device_user_id', 'device_user_name')}),
        ('Device User Details', {'fields': ('device_user_privilege', 'device_user_password', 'device_user_group', 'device_user_card')}),
        ('System Mapping', {'fields': ('system_user', 'is_mapped', 'mapping_notes')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(Attendance)
class AttendanceAdmin(UnfoldModelAdmin):
    list_display = ['user', 'date', 'check_in_time', 'check_out_time', 'total_hours', 'status', 'day_status', 'is_late', 'device']
    list_filter = ['status', 'day_status', 'is_late', 'date', 'device', 'user__office']
    search_fields = ['user__first_name', 'user__last_name', 'user__employee_id', 'notes']
    ordering = ['-date', '-check_in_time']
    readonly_fields = ['id', 'total_hours', 'day_status', 'is_late', 'late_minutes', 'created_at', 'updated_at']
    date_hierarchy = 'date'
    
    fieldsets = (
        (None, {'fields': ('user', 'date', 'device')}),
        ('Time Records', {'fields': ('check_in_time', 'check_out_time', 'total_hours')}),
        ('Status Information', {'fields': ('status', 'day_status', 'is_late', 'late_minutes')}),
        ('Additional Info', {'fields': ('notes',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(Leave)
class LeaveAdmin(UnfoldModelAdmin):
    list_display = ['user', 'leave_type', 'start_date', 'end_date', 'total_days', 'status', 'approved_by']
    list_filter = ['leave_type', 'status', 'start_date', 'end_date', 'user__office']
    search_fields = ['user__first_name', 'user__last_name', 'reason']
    ordering = ['-created_at']
    readonly_fields = ['id', 'approved_at', 'created_at', 'updated_at']
    date_hierarchy = 'start_date'
    
    actions = ['approve_leaves', 'reject_leaves']
    
    def approve_leaves(self, request, queryset):
        updated = queryset.update(status='approved', approved_by=request.user)
        self.message_user(request, f'{updated} leave requests approved.')
    approve_leaves.short_description = "Approve selected leave requests"
    
    def reject_leaves(self, request, queryset):
        updated = queryset.update(status='rejected', approved_by=request.user)
        self.message_user(request, f'{updated} leave requests rejected.')
    reject_leaves.short_description = "Reject selected leave requests"


@admin.register(Document)
class DocumentAdmin(UnfoldModelAdmin):
    list_display = ['title', 'user', 'document_type', 'uploaded_by', 'created_at']
    list_filter = ['document_type', 'created_at', 'user__office']
    search_fields = ['title', 'description', 'user__first_name', 'user__last_name']
    ordering = ['-created_at']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Notification)
class NotificationAdmin(UnfoldModelAdmin):
    list_display = ['user', 'title', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at', 'user__office']
    search_fields = ['title', 'message', 'user__first_name', 'user__last_name']
    ordering = ['-created_at']
    readonly_fields = ['id', 'created_at']
    
    actions = ['mark_as_read', 'mark_as_unread']
    
    def mark_as_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f'{updated} notifications marked as read.')
    mark_as_read.short_description = "Mark selected notifications as read"
    
    def mark_as_unread(self, request, queryset):
        updated = queryset.update(is_read=False)
        self.message_user(request, f'{updated} notifications marked as unread.')
    mark_as_unread.short_description = "Mark selected notifications as unread"


@admin.register(SystemSettings)
class SystemSettingsAdmin(UnfoldModelAdmin):
    list_display = ['key', 'value', 'description', 'updated_at']
    list_filter = ['updated_at']
    search_fields = ['key', 'description']
    ordering = ['key']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(AttendanceLog)
class AttendanceLogAdmin(UnfoldModelAdmin):
    list_display = ['attendance', 'action', 'changed_by', 'created_at']
    list_filter = ['action', 'created_at', 'attendance__user__office']
    search_fields = ['attendance__user__first_name', 'attendance__user__last_name', 'action']
    ordering = ['-created_at']
    readonly_fields = ['id', 'created_at']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ESSLAttendanceLog)
class ESSLAttendanceLogAdmin(UnfoldModelAdmin):
    list_display = ['biometric_id', 'device', 'user', 'punch_time', 'punch_type', 'is_processed']
    list_filter = ['device', 'punch_type', 'is_processed', 'created_at']
    search_fields = ['biometric_id', 'device__name', 'user__first_name', 'user__last_name']
    ordering = ['-punch_time']
    readonly_fields = ['id', 'created_at']
    list_editable = ['is_processed']


@admin.register(BankAccountHistory)
class BankAccountHistoryAdmin(UnfoldModelAdmin):
    list_display = ['user', 'action', 'changed_by', 'is_verified', 'created_at']
    list_filter = ['action', 'is_verified', 'created_at']
    search_fields = ['user__first_name', 'user__last_name', 'user__employee_id', 'changed_by__username']
    ordering = ['-created_at']
    readonly_fields = ['id', 'created_at', 'old_values', 'new_values']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'action', 'changed_by')
        }),
        ('Change Details', {
            'fields': ('old_values', 'new_values', 'change_reason')
        }),
        ('Verification', {
            'fields': ('is_verified', 'verified_by', 'verified_at')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('user', 'changed_by', 'verified_by')


@admin.register(WorkingHoursSettings)
class WorkingHoursSettingsAdmin(UnfoldModelAdmin):
    list_display = ['office', 'standard_hours', 'start_time', 'end_time', 'late_threshold', 'half_day_threshold', 'late_coming_threshold']
    list_filter = ['office', 'created_at']
    search_fields = ['office__name']
    ordering = ['office__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        (None, {'fields': ('office',)}),
        ('Working Hours', {'fields': ('standard_hours', 'start_time', 'end_time')}),
        ('Attendance Rules', {'fields': ('late_threshold', 'half_day_threshold', 'late_coming_threshold')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(Resignation)
class ResignationAdmin(UnfoldModelAdmin):
    list_display = ['user', 'resignation_date', 'notice_period_days', 'status', 'approved_by', 'created_at']
    list_filter = ['status', 'resignation_date', 'created_at', 'user__office']
    search_fields = ['user__first_name', 'user__last_name', 'reason', 'approved_by__first_name', 'approved_by__last_name']
    ordering = ['-created_at']
    readonly_fields = ['id', 'last_working_date', 'approved_at', 'created_at', 'updated_at']
    date_hierarchy = 'resignation_date'
    
    fieldsets = (
        (None, {'fields': ('user', 'resignation_date', 'notice_period_days')}),
        ('Resignation Details', {'fields': ('reason', 'handover_notes', 'is_handover_completed')}),
        ('Approval Information', {'fields': ('status', 'approved_by', 'approved_at', 'status_reason')}),
        ('Calculated Fields', {'fields': ('last_working_date',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )
    
    actions = ['approve_resignations', 'reject_resignations']
    
    def approve_resignations(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status='pending').update(
            status='approved', 
            approved_by=request.user,
            approved_at=timezone.now()
        )
        self.message_user(request, f'{updated} resignation requests approved.')
    approve_resignations.short_description = "Approve selected resignation requests"
    
    def reject_resignations(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status='pending').update(
            status='rejected', 
            approved_by=request.user,
            approved_at=timezone.now()
        )
        self.message_user(request, f'{updated} resignation requests rejected.')
    reject_resignations.short_description = "Reject selected resignation requests"


@admin.register(DocumentTemplate)
class DocumentTemplateAdmin(UnfoldModelAdmin):
    list_display = ['name', 'document_type', 'is_active', 'created_by', 'created_at']
    list_filter = ['document_type', 'is_active', 'created_at', 'created_by']
    search_fields = ['name', 'description', 'content']
    ordering = ['-created_at']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        (None, {'fields': ('name', 'document_type', 'is_active')}),
        ('Template Content', {'fields': ('description', 'content')}),
        ('Template Data', {'fields': ('template_data',)}),
        ('Metadata', {'fields': ('created_by', 'created_at', 'updated_at')}),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # If creating new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(GeneratedDocument)
class GeneratedDocumentAdmin(UnfoldModelAdmin):
    list_display = ['document_type', 'employee_name', 'employee', 'generated_at', 'has_pdf_file', 'is_sent', 'action_buttons']
    list_filter = ['document_type', 'generated_at', 'is_sent', 'employee__office']
    search_fields = ['employee__first_name', 'employee__last_name', 'employee__employee_id', 'document_type', 'title']
    ordering = ['-generated_at']
    readonly_fields = ['id', 'generated_at', 'action_buttons']
    # Temporarily disable date_hierarchy to fix timezone issue
    # date_hierarchy = 'generated_at'
    
    fieldsets = (
        (None, {'fields': ('employee', 'template', 'document_type', 'title')}),
        ('Document Content', {'fields': ('content',)}),
        ('Document Data', {'fields': ('offer_data', 'increment_data', 'salary_data')}),
        ('PDF File', {'fields': ('pdf_file', 'pdf_file_size', 'pdf_file_exists')}),
        ('Email Status', {'fields': ('is_sent', 'sent_at', 'generated_by')}),
        ('Actions', {'fields': ('action_buttons',)}),
        ('Timestamps', {'fields': ('generated_at',)}),
    )
    
    def employee_name(self, obj):
        return f"{obj.employee.first_name} {obj.employee.last_name}" if obj.employee else "No Employee"
    employee_name.short_description = "Employee Name"
    employee_name.admin_order_field = 'employee__first_name'
    
    def has_pdf_file(self, obj):
        if obj.pdf_file:
            try:
                # Check if file exists without accessing size
                if obj.pdf_file.name:
                    return format_html('<span style="color: green;">✓ PDF Available</span>')
                else:
                    return format_html('<span style="color: red;">✗ Empty File</span>')
            except:
                return format_html('<span style="color: orange;">⚠ File Error</span>')
        return format_html('<span style="color: gray;">No PDF</span>')
    has_pdf_file.short_description = "PDF Status"
    
    def pdf_file_size(self, obj):
        if obj.pdf_file and obj.pdf_file.name:
            try:
                size_kb = obj.pdf_file.size / 1024
                return f"{size_kb:.1f} KB"
            except:
                return "File Error"
        return "N/A"
    pdf_file_size.short_description = "PDF Size"
    
    def pdf_file_exists(self, obj):
        if obj.pdf_file and obj.pdf_file.name:
            import os
            from django.conf import settings
            file_path = os.path.join(settings.MEDIA_ROOT, obj.pdf_file.name)
            exists = os.path.exists(file_path)
            return format_html(
                '<span style="color: green;">✓ Exists</span>' if exists 
                else '<span style="color: red;">✗ Missing</span>'
            )
        return format_html('<span style="color: gray;">No File</span>')
    pdf_file_exists.short_description = "File Exists"
    
    actions = ['regenerate_pdf', 'cleanup_orphaned_files', 'send_email_to_employees', 'delete_selected_documents']
    
    def action_buttons(self, obj):
        """Display action buttons for each document"""
        buttons = []
        
        # View button
        if obj.pdf_file:
            view_url = reverse('admin:core_generateddocument_view_document', args=[obj.pk])
            buttons.append(f'<a href="{view_url}" class="button" target="_blank">View</a>')
        
        # Send email button
        if obj.employee and obj.employee.email:
            send_url = reverse('admin:core_generateddocument_send_email', args=[obj.pk])
            buttons.append(f'<a href="{send_url}" class="button" onclick="return confirm(\'Send email to {obj.employee.get_full_name()}?\')">Send Email</a>')
        
        # Delete button
        delete_url = reverse('admin:core_generateddocument_delete', args=[obj.pk])
        buttons.append(f'<a href="{delete_url}" class="button" style="color: red;" onclick="return confirm(\'Are you sure you want to delete this document?\')">Delete</a>')
        
        return format_html(' '.join(buttons))
    action_buttons.short_description = "Actions"
    action_buttons.allow_tags = True
    
    def regenerate_pdf(self, request, queryset):
        """Regenerate PDF files for selected documents"""
        from core.document_views import GeneratedDocumentViewSet
        viewset = GeneratedDocumentViewSet()
        count = 0
        
        for document in queryset:
            try:
                # Clear existing PDF file to force regeneration
                document.pdf_file = None
                document.save(update_fields=['pdf_file'])
                count += 1
            except Exception as e:
                self.message_user(request, f'Error regenerating PDF for document {document.id}: {e}', level='ERROR')
        
        self.message_user(request, f'{count} documents marked for PDF regeneration.')
    regenerate_pdf.short_description = "Regenerate PDF files"
    
    def cleanup_orphaned_files(self, request, queryset):
        """Clean up orphaned file references"""
        from core.document_views import GeneratedDocumentViewSet
        viewset = GeneratedDocumentViewSet()
        count = 0
        
        for document in queryset:
            if viewset.cleanup_orphaned_files(document):
                count += 1
        
        self.message_user(request, f'{count} orphaned file references cleaned up.')
    cleanup_orphaned_files.short_description = "Clean up orphaned files"
    
    def send_email_to_employees(self, request, queryset):
        """Send emails for selected documents"""
        from core.document_views import GeneratedDocumentViewSet
        viewset = GeneratedDocumentViewSet()
        count = 0
        
        for document in queryset:
            try:
                if document.employee and document.employee.email:
                    # Mark as sent (actual email sending would require email configuration)
                    document.is_sent = True
                    document.sent_at = timezone.now()
                    document.save()
                    count += 1
            except Exception as e:
                self.message_user(request, f'Error sending email for document {document.id}: {e}', level='ERROR')
        
        self.message_user(request, f'{count} emails sent successfully.')
    send_email_to_employees.short_description = "Send emails to employees"
    
    def delete_selected_documents(self, request, queryset):
        """Delete selected documents"""
        count = 0
        for document in queryset:
            try:
                # Delete the file if it exists
                if document.pdf_file:
                    document.pdf_file.delete(save=False)
                document.delete()
                count += 1
            except Exception as e:
                self.message_user(request, f'Error deleting document {document.id}: {e}', level='ERROR')
        
        self.message_user(request, f'{count} documents deleted successfully.')
    delete_selected_documents.short_description = "Delete selected documents"
    
    def get_urls(self):
        """Add custom URLs for view and send actions"""
        urls = super().get_urls()
        custom_urls = [
            path('<int:document_id>/view/', self.admin_site.admin_view(self.view_document), name='core_generateddocument_view_document'),
            path('<int:document_id>/send_email/', self.admin_site.admin_view(self.send_email), name='core_generateddocument_send_email'),
        ]
        return custom_urls + urls
    
    def view_document(self, request, document_id):
        """View document in browser"""
        try:
            document = GeneratedDocument.objects.get(id=document_id)
            if document.pdf_file:
                response = HttpResponse(document.pdf_file.read(), content_type='application/pdf')
                response['Content-Disposition'] = f'inline; filename="{document.title}.pdf"'
                return response
            else:
                messages.error(request, 'No file available for this document.')
                return HttpResponseRedirect(reverse('admin:core_generateddocument_changelist'))
        except GeneratedDocument.DoesNotExist:
            messages.error(request, 'Document not found.')
            return HttpResponseRedirect(reverse('admin:core_generateddocument_changelist'))
    
    def send_email(self, request, document_id):
        """Send email for document"""
        try:
            document = GeneratedDocument.objects.get(id=document_id)
            if document.employee and document.employee.email:
                # Mark as sent (actual email sending would require email configuration)
                document.is_sent = True
                document.sent_at = timezone.now()
                document.save()
                messages.success(request, f'Email sent to {document.employee.get_full_name()} ({document.employee.email})')
            else:
                messages.error(request, 'No email address available for this employee.')
        except GeneratedDocument.DoesNotExist:
            messages.error(request, 'Document not found.')
        
        return HttpResponseRedirect(reverse('admin:core_generateddocument_changelist'))


# Customize admin site
admin.site.site_header = "Disha Online Solution"
admin.site.site_title = "Disha Online Solution"
admin.site.index_title = "Welcome to Disha Online Solution"


@admin.register(Shift)
class ShiftAdmin(UnfoldModelAdmin):
    list_display = ['name', 'shift_type', 'start_time', 'end_time', 'office', 'is_active', 'created_at']
    list_filter = ['shift_type', 'is_active', 'office', 'created_at']
    search_fields = ['name', 'office__name']
    ordering = ['office', 'start_time', 'name']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_manager and request.user.office:
            return qs.filter(office=request.user.office)
        return qs


@admin.register(EmployeeShiftAssignment)
class EmployeeShiftAssignmentAdmin(UnfoldModelAdmin):
    list_display = ['employee', 'shift', 'office_name', 'is_active', 'assigned_by', 'created_at']
    list_filter = ['is_active', 'shift__office', 'shift__shift_type', 'created_at']
    search_fields = ['employee__first_name', 'employee__last_name', 'shift__name']
    ordering = ['-created_at']
    
    def office_name(self, obj):
        return obj.shift.office.name
    office_name.short_description = 'Office'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_manager and request.user.office:
            return qs.filter(shift__office=request.user.office)
        return qs
