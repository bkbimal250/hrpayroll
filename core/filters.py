import django_filters
from django.db.models import Q
from .models import (
    CustomUser, Attendance, Leave, Document, Notification, 
    Shift, EmployeeShiftAssignment, DeviceUser, Office, GeneratedDocument
)

class CustomUserFilter(django_filters.FilterSet):
    """FilterSet for CustomUser with proper filtering capabilities"""
    office = django_filters.CharFilter(method='filter_office')
    department = django_filters.CharFilter(method='filter_department')
    role = django_filters.CharFilter(field_name='role')
    is_active = django_filters.BooleanFilter(field_name='is_active')
    search = django_filters.CharFilter(method='filter_search')
    aadhaar_card = django_filters.CharFilter(field_name='aadhaar_card', lookup_expr='icontains')
    pan_card = django_filters.CharFilter(field_name='pan_card', lookup_expr='icontains')
    
    class Meta:
        model = CustomUser
        fields = ['office', 'department', 'role', 'is_active', 'search', 'aadhaar_card', 'pan_card']
    
    def filter_office(self, queryset, name, value):
        """Custom office filter to handle null values"""
        if not value:
            return queryset
        if value == 'null':
            return queryset.filter(office__isnull=True)
        try:
            # Try to parse as UUID
            import uuid
            office_uuid = uuid.UUID(value)
            return queryset.filter(office__id=office_uuid)
        except (ValueError, TypeError):
            # If not a valid UUID, try to filter by office name
            return queryset.filter(office__name__icontains=value)
    
    def filter_department(self, queryset, name, value):
        """Custom department filter to handle both department IDs and names"""
        if not value:
            return queryset
        
        # First try to filter by department ID (UUID)
        try:
            import uuid
            department_uuid = uuid.UUID(value)
            # Filter users where department field contains the UUID
            return queryset.filter(department=department_uuid)
        except (ValueError, TypeError):
            # If not a valid UUID, try to filter by department name
            # Since department is now a ForeignKey, we can filter by name directly
            return queryset.filter(department__name__icontains=value)
    
    def filter_search(self, queryset, name, value):
        """Custom search filter across multiple fields"""
        if not value:
            return queryset
        return queryset.filter(
            Q(username__icontains=value) |
            Q(first_name__icontains=value) |
            Q(last_name__icontains=value) |
            Q(email__icontains=value) |
            Q(employee_id__icontains=value) |
            Q(phone_number__icontains=value)
        )

class DeviceUserFilter(django_filters.FilterSet):
    """FilterSet for DeviceUser with proper filtering capabilities"""
    device = django_filters.CharFilter(method='filter_device')
    is_mapped = django_filters.BooleanFilter(field_name='is_mapped')
    device_user_privilege = django_filters.CharFilter(field_name='device_user_privilege')
    search = django_filters.CharFilter(method='filter_search')
    
    class Meta:
        model = DeviceUser
        fields = ['device', 'is_mapped', 'device_user_privilege', 'search']
    
    def filter_device(self, queryset, name, value):
        """Custom device filter to handle UUID values"""
        if not value:
            return queryset
        try:
            # Try to parse as UUID
            import uuid
            device_uuid = uuid.UUID(value)
            return queryset.filter(device__id=device_uuid)
        except (ValueError, TypeError):
            # If not a valid UUID, try to filter by device name
            return queryset.filter(device__name__icontains=value)
    
    def filter_search(self, queryset, name, value):
        """Custom search filter across multiple fields"""
        if not value:
            return queryset
        return queryset.filter(
            Q(device_user_name__icontains=value) |
            Q(device_user_id__icontains=value) |
            Q(device__name__icontains=value) |
            Q(system_user__first_name__icontains=value) |
            Q(system_user__last_name__icontains=value) |
            Q(system_user__email__icontains=value)
        )

class AttendanceFilter(django_filters.FilterSet):
    """FilterSet for Attendance"""
    date = django_filters.DateFilter(field_name='date')
    start_date = django_filters.DateFilter(field_name='date', lookup_expr='gte')
    end_date = django_filters.DateFilter(field_name='date', lookup_expr='lte')
    user = django_filters.CharFilter(field_name='user__id')
    office = django_filters.CharFilter(field_name='user__office__id')
    status = django_filters.CharFilter(field_name='status')
    day_status = django_filters.CharFilter(field_name='day_status')
    is_late = django_filters.BooleanFilter(field_name='is_late')
    device = django_filters.CharFilter(field_name='device__id')

    class Meta:
        model = Attendance
        fields = ['date', 'status', 'day_status', 'is_late', 'user', 'office']

class LeaveFilter(django_filters.FilterSet):
    """FilterSet for Leave"""
    status = django_filters.CharFilter(field_name='status')
    leave_type = django_filters.CharFilter(field_name='leave_type')
    user = django_filters.CharFilter(field_name='user__id')
    office = django_filters.CharFilter(field_name='user__office__id')
    
    # Overlap logic:
    # Works when (LeaveStart <= FilterEnd) AND (LeaveEnd >= FilterStart)
    # Filter 'start_date' param maps to FilterStart -> Check if leave ends on/after it (end_date__gte)
    # Filter 'end_date' param maps to FilterEnd -> Check if leave starts on/before it (start_date__lte)
    start_date = django_filters.DateFilter(field_name='end_date', lookup_expr='gte')
    end_date = django_filters.DateFilter(field_name='start_date', lookup_expr='lte')

    class Meta:
        model = Leave
        fields = ['status', 'leave_type', 'user']

class DocumentFilter(django_filters.FilterSet):
    """FilterSet for Document"""
    title = django_filters.CharFilter(lookup_expr='icontains')
    description = django_filters.CharFilter(lookup_expr='icontains')
    document_type = django_filters.CharFilter(field_name='document_type')
    date = django_filters.DateFilter(field_name='created_at', lookup_expr='date')
    user = django_filters.CharFilter(field_name='user__id')
    uploaded_by = django_filters.CharFilter(field_name='uploaded_by__id')
    search = django_filters.CharFilter(method='filter_search')

    class Meta:
        model = Document
        fields = ['document_type', 'user', 'uploaded_by', 'search']

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(title__icontains=value) |
            Q(description__icontains=value) |
            Q(user__first_name__icontains=value) |
            Q(user__last_name__icontains=value)
        )

class NotificationFilter(django_filters.FilterSet):
    """FilterSet for Notification"""
    notification_type = django_filters.CharFilter(field_name='notification_type')
    is_read = django_filters.BooleanFilter(field_name='is_read')
    priority = django_filters.CharFilter(field_name='priority')
    created_at_gte = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')

    class Meta:
        model = Notification
        fields = ['notification_type', 'is_read', 'priority']

class ShiftFilter(django_filters.FilterSet):
    """FilterSet for Shift"""
    office = django_filters.CharFilter(field_name='office__id')
    shift_type = django_filters.CharFilter(field_name='shift_type')

    class Meta:
        model = Shift
        fields = ['office', 'shift_type']

class EmployeeShiftAssignmentFilter(django_filters.FilterSet):
    """FilterSet for EmployeeShiftAssignment"""
    employee = django_filters.CharFilter(field_name='employee__id')
    shift = django_filters.CharFilter(field_name='shift__id')
    is_active = django_filters.BooleanFilter(field_name='is_active')
    office = django_filters.CharFilter(field_name='shift__office__id')

    class Meta:
        model = EmployeeShiftAssignment
        fields = ['employee', 'shift', 'is_active', 'office']

class GeneratedDocumentFilter(django_filters.FilterSet):
    """FilterSet for GeneratedDocument"""
    document_type = django_filters.CharFilter(field_name='document_type')
    date = django_filters.DateFilter(field_name='generated_at', lookup_expr='date')
    employee = django_filters.CharFilter(field_name='employee__id')
    generated_by = django_filters.CharFilter(field_name='generated_by__id')
    office = django_filters.CharFilter(field_name='employee__office__id')
    is_sent = django_filters.BooleanFilter(field_name='is_sent')
    search = django_filters.CharFilter(method='filter_search')

    class Meta:
        model = GeneratedDocument
        fields = ['document_type', 'employee', 'generated_by', 'is_sent', 'search']

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(title__icontains=value) |
            Q(employee__first_name__icontains=value) |
            Q(employee__last_name__icontains=value) |
            Q(employee__employee_id__icontains=value)
        )