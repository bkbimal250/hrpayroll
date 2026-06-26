"""Grouped API views for the core app."""

from .auth_views import OfficeViewSet, CustomUserViewSet, DepartmentViewSet, DesignationViewSet
from .attendance_views import AttendanceViewSet, ZKTecoAttendanceViewSet, AttendanceLogViewSet
from .device_views import DeviceViewSet, DeviceUserViewSet
from .leave_views import LeaveViewSet
from .document_views import DocumentViewSet
from .notification_views import NotificationViewSet, SystemSettingsViewSet
from .report_views import ReportsViewSet, DashboardViewSet, debug_user_permissions, custom_404, custom_500
from .employee_views import ResignationViewSet, ShiftViewSet, EmployeeShiftAssignmentViewSet

__all__ = [
    'OfficeViewSet',
    'CustomUserViewSet',
    'DepartmentViewSet',
    'DesignationViewSet',
    'AttendanceViewSet',
    'ZKTecoAttendanceViewSet',
    'AttendanceLogViewSet',
    'DeviceViewSet',
    'DeviceUserViewSet',
    'LeaveViewSet',
    'DocumentViewSet',
    'NotificationViewSet',
    'SystemSettingsViewSet',
    'ReportsViewSet',
    'DashboardViewSet',
    'debug_user_permissions',
    'custom_404',
    'custom_500',
    'ResignationViewSet',
    'ShiftViewSet',
    'EmployeeShiftAssignmentViewSet',
]
