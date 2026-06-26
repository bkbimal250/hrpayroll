from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status, filters, viewsets, permissions, serializers
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as django_filters
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Sum, Count, Q, Exists, OuterRef, Subquery
from django.db import models, transaction, IntegrityError
from datetime import datetime, timedelta, date
import calendar
import logging
import traceback
import sys
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from rest_framework.exceptions import APIException, ValidationError as DRFValidationError

from ..models import (
    CustomUser, Office, Device, DeviceUser, Attendance, WorkingHoursSettings, 
    ESSLAttendanceLog, Leave, Document, Notification, SystemSettings,
    DocumentTemplate, GeneratedDocument, Resignation, Department, Designation,
    Shift, EmployeeShiftAssignment, EmployeeStatusAuditLog, BiometricAssignmentHistory, PasswordChangeHistory, Salary,
    AttendanceAuditLog, DuplicatePunchAttempt, UnmatchedBiometricPunch
)
from ..serializers import (
    CustomUserSerializer, CustomUserListSerializer, OfficeSerializer, DeviceSerializer, DeviceUserSerializer,
    DeviceUserCreateSerializer, DeviceUserMappingSerializer, DeviceUserBulkCreateSerializer,
    AttendanceSerializer, AttendanceCreateSerializer, BulkAttendanceSerializer, WorkingHoursSettingsSerializer,
    ESSLAttendanceLogSerializer, LeaveSerializer, LeaveListSerializer, LeaveCreateSerializer, LeaveApprovalSerializer,
    DocumentSerializer, DocumentListSerializer, DocumentCreateSerializer,
    NotificationSerializer, NotificationListSerializer, SystemSettingsSerializer,
    UserRegistrationSerializer, UserProfileSerializer, PasswordChangeSerializer,
    DashboardStatsSerializer, AttendanceLogSerializer, OfficeStatsSerializer,
    UserLoginSerializer, DeviceSyncSerializer, DocumentTemplateSerializer, 
    GeneratedDocumentSerializer, DocumentGenerationSerializer, ResignationSerializer,
    ResignationCreateSerializer, ResignationAdminUpdateSerializer, ResignationApprovalSerializer, DepartmentSerializer, DesignationSerializer,
    ShiftSerializer, EmployeeShiftAssignmentSerializer, EmployeeStatusAuditLogSerializer,
    BiometricAssignmentHistorySerializer, PasswordChangeHistorySerializer, AttendanceAuditLogSerializer,
    ManagerEmployeeListSerializer,
    DuplicatePunchAttemptSerializer, UnmatchedBiometricPunchSerializer
)
# Permissions are defined inline in this file
from ..zkteco_service import zkteco_service
from ..db_manager import DatabaseConnectionManager
from ..auth_logging import log_auth_event
from ..auth_views import set_refresh_cookie
from ..throttles import AuthLoginThrottle

logger = logging.getLogger(__name__)


from ..filters import (
    CustomUserFilter, DeviceUserFilter, AttendanceFilter, LeaveFilter, 
    DocumentFilter, NotificationFilter, ShiftFilter, EmployeeShiftAssignmentFilter
)
from ..pagination import StandardResultsSetPagination


# Removed CustomUserFilter class definition as it is now in filters.py

class IsAdminUser(IsAuthenticated):
    """Permission to only allow admin users"""
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.is_admin
class IsManagerUser(IsAuthenticated):
    """Permission to only allow manager users"""
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.is_manager
class IsAdminOrManager(IsAuthenticated):
    """Permission to allow admin or manager users"""
    def has_permission(self, request, view):
        return super().has_permission(request, view) and (
            request.user.is_admin or request.user.is_manager
        )
class IsAdminOrManagerOrHR(IsAuthenticated):
    """Permission to allow admin, manager, or HR users."""
    def has_permission(self, request, view):
        return super().has_permission(request, view) and (
            request.user.is_superuser or request.user.is_admin or request.user.is_manager or request.user.is_hr
        )
class IsAdminOrManagerOrHRNoDelete(IsAdminOrManagerOrHR):
    """HR can create, read, and update, but cannot delete."""
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if request.method == 'DELETE' and request.user.is_hr:
            return False
        return True
class IsAdminOrHRNoDelete(IsAuthenticated):
    """Admin has full access; HR can create/read/update but cannot delete."""
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if request.user.is_admin:
            return True
        if request.user.is_hr and request.method != 'DELETE':
            return True
        return False
class IsAccountantUser(IsAuthenticated):
    """Permission to only allow accountant users"""
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.is_accountant
class IsAdminOrManagerOrAccountant(IsAuthenticated):
    """Permission to allow admin, manager, or accountant users"""
    def has_permission(self, request, view):
        return super().has_permission(request, view) and (
            request.user.is_admin or request.user.is_manager or request.user.is_accountant
        )
class IsAdminOrManagerOrAccountantOrHR(IsAuthenticated):
    """Permission to allow admin, manager, accountant, or HR users."""
    def has_permission(self, request, view):
        return super().has_permission(request, view) and (
            request.user.is_admin or request.user.is_manager or request.user.is_accountant or request.user.is_hr
        )
class IsSuperuserOrAdminOrManager(IsAuthenticated):
    """Permission to allow superuser, admin, or manager users"""
    def has_permission(self, request, view):
        return super().has_permission(request, view) and (
            request.user.is_superuser or request.user.is_admin or request.user.is_manager
        )

class ReportsViewSet(viewsets.ViewSet):
    """ViewSet for generating reports - Admin, Manager, Accountant, and HR access"""
    permission_classes = [IsAdminOrManagerOrAccountantOrHR]

    @action(detail=False, methods=['get'])
    def attendance(self, request):
        """Generate attendance report with filters"""
        try:
            # Get query parameters
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            office_id = request.query_params.get('office')
            user_id = request.query_params.get('user')
            status_filter = request.query_params.get('status')

            # Default to active users for operational compatibility; allow historical reports to include inactive users.
            queryset = Attendance.objects.select_related('user', 'user__office', 'user__department')
            include_inactive = request.query_params.get('include_inactive') in ['true', '1', 'yes']
            employment_status = request.query_params.get('employment_status')
            if employment_status:
                queryset = queryset.filter(user__employment_status=employment_status)
            elif not include_inactive:
                queryset = queryset.filter(user__employment_status__in=['active', 'notice_period'])

            # For managers, restrict to their assigned office
            if request.user.is_manager and not (request.user.is_admin or request.user.is_hr):
                if request.user.office:
                    queryset = queryset.filter(user__office=request.user.office)
                else:
                    # If manager has no office assigned, return empty result
                    return Response({
                        'type': 'attendance',
                        'summary': {
                            'totalRecords': 0,
                            'presentCount': 0,
                            'absentCount': 0,
                            'lateCount': 0,
                            'attendanceRate': 0
                        },
                        'dailyStats': [],
                        'rawData': []
                    })
            elif request.user.is_admin or request.user.is_hr or request.user.is_accountant:
                # Admin, HR, and accountant users can see all data, apply office filter if specified.
                if office_id:
                    queryset = queryset.filter(user__office_id=office_id)

            # Apply filters with proper date handling
            if start_date:
                try:
                    queryset = queryset.filter(date__gte=start_date)
                except Exception as e:
                    logger.warning(f"Invalid start_date format: {start_date}, error: {e}")
            
            if end_date:
                try:
                    queryset = queryset.filter(date__lte=end_date)
                except Exception as e:
                    logger.warning(f"Invalid end_date format: {end_date}, error: {e}")
            
            if user_id:
                queryset = queryset.filter(user_id=user_id)
            if status_filter:
                queryset = queryset.filter(status=status_filter)

            # Get data with safe date handling
            attendance_data = []
            for attendance in queryset:
                try:
                    data = {
                        'id': str(attendance.id),
                        'date': attendance.date.isoformat() if attendance.date else None,
                        'check_in_time': attendance.check_in_time.isoformat() if attendance.check_in_time else None,
                        'check_out_time': attendance.check_out_time.isoformat() if attendance.check_out_time else None,
                        'status': attendance.status,
                        'user__id': str(attendance.user.id) if attendance.user else None,
                        'user__first_name': attendance.user.first_name if attendance.user else None,
                        'user__last_name': attendance.user.last_name if attendance.user else None,
                        'user__employee_id': attendance.user.employee_id if attendance.user else None,
                        'user__office__name': attendance.user.office.name if attendance.user and attendance.user.office else None,
                        'user__department__name': attendance.user.department.name if attendance.user and attendance.user.department else None,
                    }
                    attendance_data.append(data)
                except Exception as e:
                    logger.warning(f"Error processing attendance record {attendance.id}: {e}")
                    continue

            # Calculate statistics
            total_records = len(attendance_data)
            present_count = sum(1 for a in attendance_data if a['status'] == 'present')
            absent_count = sum(1 for a in attendance_data if a['status'] == 'absent')
            late_count = sum(1 for a in attendance_data if a['status'] == 'late')
            attendance_rate = (present_count / total_records * 100) if total_records > 0 else 0

            # Group by date with safe date handling
            daily_stats = {}
            for record in attendance_data:
                try:
                    date = record['date']
                    if date:
                        # Extract just the date part if it's a full datetime string
                        if 'T' in date:
                            date = date.split('T')[0]
                        
                        if date not in daily_stats:
                            daily_stats[date] = {'present': 0, 'absent': 0, 'late': 0, 'total': 0}
                        daily_stats[date][record['status']] += 1
                        daily_stats[date]['total'] += 1
                except Exception as e:
                    logger.warning(f"Error processing date for record: {e}")
                    continue

            # Convert to list format
            daily_stats_list = []
            for date, stats in daily_stats.items():
                try:
                    rate = (stats['present'] / stats['total'] * 100) if stats['total'] > 0 else 0
                    daily_stats_list.append({
                        'date': date,
                        'present': stats['present'],
                        'absent': stats['absent'],
                        'late': stats['late'],
                        'total': stats['total'],
                        'rate': round(rate, 2)
                    })
                except Exception as e:
                    logger.warning(f"Error calculating stats for date {date}: {e}")
                    continue

            # Sort by date
            daily_stats_list.sort(key=lambda x: x['date'])

            return Response({
                'type': 'attendance',
                'summary': {
                    'totalRecords': total_records,
                    'presentCount': present_count,
                    'absentCount': absent_count,
                    'lateCount': late_count,
                    'attendanceRate': round(attendance_rate, 2)
                },
                'dailyStats': daily_stats_list,
                'rawData': attendance_data
            })

        except Exception as e:
            logger.error(f"Error generating attendance report: {str(e)}")
            return Response(
                {'error': f'Failed to generate attendance report: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def leave(self, request):
        """Generate leave report with filters"""
        try:
            # Get query parameters
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            office_id = request.query_params.get('office')
            user_id = request.query_params.get('user')
            status_filter = request.query_params.get('status')

            # Build query
            queryset = Leave.objects.select_related('user', 'user__office')

            # For managers, restrict to their assigned office
            if request.user.is_manager and not request.user.is_admin:
                if request.user.office:
                    queryset = queryset.filter(user__office=request.user.office)
                else:
                    # If manager has no office assigned, return empty result
                    return Response({
                        'type': 'leave',
                        'summary': {
                            'totalLeaves': 0,
                            'approvedLeaves': 0,
                            'pendingLeaves': 0,
                            'rejectedLeaves': 0,
                            'approvalRate': 0
                        },
                        'leaveTypeStats': [],
                        'rawData': []
                    })
            elif request.user.is_admin:
                # Admins can see all data, apply office filter if specified
                if office_id:
                    queryset = queryset.filter(user__office_id=office_id)

            # Apply filters with proper date handling
            if start_date:
                try:
                    queryset = queryset.filter(start_date__gte=start_date)
                except Exception as e:
                    logger.warning(f"Invalid start_date format: {start_date}, error: {e}")
            
            if end_date:
                try:
                    queryset = queryset.filter(end_date__lte=end_date)
                except Exception as e:
                    logger.warning(f"Invalid end_date format: {end_date}, error: {e}")
            
            if user_id:
                queryset = queryset.filter(user_id=user_id)
            if status_filter:
                queryset = queryset.filter(status=status_filter)

            # Get data with safe date handling
            leave_data = []
            for leave in queryset:
                try:
                    data = {
                        'id': str(leave.id),
                        'leave_type': leave.leave_type,
                        'start_date': leave.start_date.isoformat() if leave.start_date else None,
                        'end_date': leave.end_date.isoformat() if leave.end_date else None,
                        'status': leave.status,
                        'reason': leave.reason,
                        'applied_at': leave.created_at.isoformat() if leave.created_at else None,
                        'approved_at': leave.approved_at.isoformat() if leave.approved_at else None,
                        'approved_by__first_name': leave.approved_by.first_name if leave.approved_by else None,
                        'approved_by__last_name': leave.approved_by.last_name if leave.approved_by else None,
                        'user__id': str(leave.user.id) if leave.user else None,
                        'user__first_name': leave.user.first_name if leave.user else None,
                        'user__last_name': leave.user.last_name if leave.user else None,
                        'user__employee_id': leave.user.employee_id if leave.user else None,
                        'user__office__name': leave.user.office.name if leave.user and leave.user.office else None,
                    }
                    leave_data.append(data)
                except Exception as e:
                    logger.warning(f"Error processing leave record {leave.id}: {e}")
                    continue

            # Calculate statistics
            total_leaves = len(leave_data)
            approved_leaves = sum(1 for l in leave_data if l['status'] == 'approved')
            pending_leaves = sum(1 for l in leave_data if l['status'] == 'pending')
            rejected_leaves = sum(1 for l in leave_data if l['status'] == 'rejected')
            approval_rate = (approved_leaves / total_leaves * 100) if total_leaves > 0 else 0

            # Group by leave type
            leave_type_stats = {}
            for record in leave_data:
                try:
                    leave_type = record['leave_type']
                    if leave_type not in leave_type_stats:
                        leave_type_stats[leave_type] = {'approved': 0, 'pending': 0, 'rejected': 0, 'total': 0}
                    leave_type_stats[leave_type][record['status']] += 1
                    leave_type_stats[leave_type]['total'] += 1
                except Exception as e:
                    logger.warning(f"Error processing leave type for record: {e}")
                    continue

            # Convert to list format
            leave_type_list = []
            for leave_type, stats in leave_type_stats.items():
                try:
                    leave_type_list.append({
                        'type': leave_type,
                        'approved': stats['approved'],
                        'pending': stats['pending'],
                        'rejected': stats['rejected'],
                        'total': stats['total']
                    })
                except Exception as e:
                    logger.warning(f"Error creating leave type stats for {leave_type}: {e}")
                    continue

            return Response({
                'type': 'leave',
                'summary': {
                    'totalLeaves': total_leaves,
                    'approvedLeaves': approved_leaves,
                    'pendingLeaves': pending_leaves,
                    'rejectedLeaves': rejected_leaves,
                    'approvalRate': round(approval_rate, 2)
                },
                'leaveTypeStats': leave_type_list,
                'rawData': leave_data
            })

        except Exception as e:
            logger.error(f"Error generating leave report: {str(e)}")
            return Response(
                {'error': f'Failed to generate leave report: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def office(self, request):
        """Generate office report"""
        try:
            # Get all offices with related data
            offices = Office.objects.prefetch_related('customuser_set').all()
            
            # Get all users for statistics
            all_users = CustomUser.objects.select_related('office').all()

            # Calculate office statistics
            office_stats = []
            for office in offices:
                try:
                    office_users = [u for u in all_users if u.office_id == office.id]
                    employees = sum(1 for u in office_users if u.role == 'employee')
                    managers = sum(1 for u in office_users if u.role == 'manager')
                    active_users = sum(1 for u in office_users if u.is_active)

                    office_stats.append({
                        'id': str(office.id),
                        'name': office.name,
                        'employees': employees,
                        'managers': managers,
                        'activeUsers': active_users,
                        'totalUsers': len(office_users),
                        'manager': f"{office.manager.first_name} {office.manager.last_name}" if office.manager else 'Not assigned'
                    })
                except Exception as e:
                    logger.warning(f"Error processing office {office.id}: {e}")
                    continue

            # Calculate summary statistics
            total_offices = len(offices)
            total_employees = sum(1 for u in all_users if u.role == 'employee')
            total_managers = sum(1 for u in all_users if u.role == 'manager')
            total_users = len(all_users)

            return Response({
                'type': 'office',
                'summary': {
                    'totalOffices': total_offices,
                    'totalEmployees': total_employees,
                    'totalManagers': total_managers,
                    'totalUsers': total_users
                },
                'officeStats': office_stats,
                'rawData': list(offices.values())
            })

        except Exception as e:
            logger.error(f"Error generating office report: {str(e)}")
            return Response(
                {'error': f'Failed to generate office report: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def user(self, request):
        """Generate user report"""
        try:
            # Get users based on user role
            if request.user.is_manager and not request.user.is_admin:
                # Managers can only see users from their assigned office
                if request.user.office:
                    users = CustomUser.objects.select_related('office').filter(office=request.user.office)
                else:
                    # If manager has no office assigned, return empty result
                    return Response({
                        'type': 'user',
                        'summary': {
                            'totalUsers': 0,
                            'activeUsers': 0,
                            'inactiveUsers': 0,
                            'activationRate': 0
                        },
                        'roleStats': [],
                        'officeStats': [],
                        'rawData': []
                    })
            else:
                # Admins can see all users
                users = CustomUser.objects.select_related('office').all()

            # Calculate user statistics
            role_stats = {}
            office_stats = {}
            active_users = sum(1 for u in users if u.is_active)
            inactive_users = sum(1 for u in users if not u.is_active)

            for user in users:
                try:
                    # Role statistics
                    if user.role not in role_stats:
                        role_stats[user.role] = {'active': 0, 'inactive': 0, 'total': 0}
                    role_stats[user.role]['total'] += 1
                    if user.is_active:
                        role_stats[user.role]['active'] += 1
                    else:
                        role_stats[user.role]['inactive'] += 1

                    # Office statistics
                    office_name = user.office.name if user.office else 'No Office'
                    if office_name not in office_stats:
                        office_stats[office_name] = {'active': 0, 'inactive': 0, 'total': 0}
                    office_stats[office_name]['total'] += 1
                    if user.is_active:
                        office_stats[office_name]['active'] += 1
                    else:
                        office_stats[office_name]['inactive'] += 1
                except Exception as e:
                    logger.warning(f"Error processing user {user.id}: {e}")
                    continue

            # Convert to list format
            role_stats_list = []
            for role, stats in role_stats.items():
                try:
                    role_stats_list.append({
                        'role': role,
                        'active': stats['active'],
                        'inactive': stats['inactive'],
                        'total': stats['total']
                    })
                except Exception as e:
                    logger.warning(f"Error creating role stats for {role}: {e}")
                    continue

            office_stats_list = []
            for office, stats in office_stats.items():
                try:
                    office_stats_list.append({
                        'office': office,
                        'active': stats['active'],
                        'inactive': stats['inactive'],
                        'total': stats['total']
                    })
                except Exception as e:
                    logger.warning(f"Error creating office stats for {office}: {e}")
                    continue

            activation_rate = (active_users / len(users) * 100) if users else 0

            return Response({
                'type': 'user',
                'summary': {
                    'totalUsers': len(users),
                    'activeUsers': active_users,
                    'inactiveUsers': inactive_users,
                    'activationRate': round(activation_rate, 2)
                },
                'roleStats': role_stats_list,
                'officeStats': office_stats_list,
                'rawData': list(users.values())
            })

        except Exception as e:
            logger.error(f"Error generating user report: {str(e)}")
            return Response(
                {'error': f'Failed to generate user report: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def export(self, request):
        """Export report data"""
        try:
            report_type = request.query_params.get('type', 'attendance')
            
            # Generate the appropriate report
            if report_type == 'attendance':
                response = self.attendance(request)
            elif report_type == 'leave':
                response = self.leave(request)
            elif report_type == 'office':
                response = self.office(request)
            elif report_type == 'user':
                response = self.user(request)
            else:
                return Response(
                    {'error': f'Invalid report type: {report_type}'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Return the report data for export
            return response

        except Exception as e:
            logger.error(f"Error exporting report: {str(e)}")
            return Response(
                {'error': f'Failed to export report: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def monthly_summary(self, request):
        """Generate monthly attendance summary for all employees"""
        try:
            # Get query parameters
            year = request.query_params.get('year')
            month = request.query_params.get('month')
            office_id = request.query_params.get('office')
            user_id = request.query_params.get('user')
            
            logger.debug(f"Monthly summary request - Year: {year}, Month: {month}, Office: {office_id}, User: {user_id}")
            logger.debug(f"Monthly summary query params: {dict(request.query_params)}")

            # Convert to integers
            if year:
                year = int(year)
            if month:
                month = int(month)

            # Calculate date range
            from datetime import datetime, timedelta
            start_date = datetime(year, month, 1).date()
            if month == 12:
                end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
            else:
                end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)
            
            # Fetch holidays for the month
            from coreapp.models import Holiday
            holidays_in_month = set(Holiday.objects.filter(date__range=[start_date, end_date]).values_list('date', flat=True))
            total_holidays = len(holidays_in_month)
            
            # Get users. Default is operational employees; historical reports can opt in.
            include_inactive = request.query_params.get('include_inactive') in ['true', '1', 'yes']
            employment_status = request.query_params.get('employment_status')
            users_query = CustomUser.objects.filter(role='employee')
            if employment_status:
                users_query = users_query.filter(employment_status=employment_status)
            elif not include_inactive:
                users_query = users_query.filter(employment_status__in=['active', 'notice_period'])
            
            if office_id:
                users_query = users_query.filter(office_id=office_id)
                logger.debug(f"Filtering monthly summary by office_id: {office_id}")
            if user_id:
                users_query = users_query.filter(id=user_id)

            total_days = (end_date - start_date).days + 1
            users = list(
                users_query
                .select_related('office')
                .values('id', 'first_name', 'last_name', 'employee_id', 'office__name')
            )
            user_ids = [user['id'] for user in users]

            attendance_stats = Attendance.objects.filter(
                user_id__in=user_ids,
                date__range=[start_date, end_date]
            ).values('user_id').annotate(
                attended_days=Count('id'),
                present_days=Count('id', filter=Q(status='present')),
                late_days=Count('id', filter=Q(status='late')),
                half_days=Count('id', filter=Q(status='half_day')),
                recorded_holiday_days=Count('id', filter=Q(status='holiday')),
                attended_holiday_dates=Count('date', filter=Q(date__in=holidays_in_month), distinct=True),
                total_hours_sum=Sum('total_hours'),
            )
            stats_by_user = {item['user_id']: item for item in attendance_stats}

            report_data = []
            for user in users:
                user_stats = stats_by_user.get(user['id'], {})
                attended_days = user_stats.get('attended_days') or 0
                present_days = user_stats.get('present_days') or 0
                late_days = user_stats.get('late_days') or 0
                half_days = user_stats.get('half_days') or 0
                recorded_holiday_days = user_stats.get('recorded_holiday_days') or 0
                attended_holiday_dates = user_stats.get('attended_holiday_dates') or 0
                missing_holiday_days = max(0, total_holidays - attended_holiday_dates)
                holiday_days = recorded_holiday_days + missing_holiday_days
                absent_days = max(0, total_days - attended_days - missing_holiday_days)
                total_hours_value = float(user_stats.get('total_hours_sum') or 0)
                attendance_percentage = (present_days / total_days * 100) if total_days > 0 else 0
                full_name = f"{user.get('first_name') or ''} {user.get('last_name') or ''}".strip()

                report_data.append({
                    'user_id': str(user['id']),
                    'user_name': full_name,
                    'employee_id': user.get('employee_id') or '',
                    'office': user.get('office__name') or '',
                    'total_days': total_days,
                    'present_days': present_days,
                    'absent_days': absent_days,
                    'holiday_days': holiday_days,
                    'late_days': late_days,
                    'half_days': half_days,
                    'total_hours': round(total_hours_value, 2),
                    'attendance_percentage': round(attendance_percentage, 2),
                    'standard_hours': 9.0 * total_days,
                    'hours_deficit': max(0, (9.0 * total_days) - total_hours_value)
                })

            # Calculate overall statistics
            if report_data:
                total_present = sum(record['present_days'] for record in report_data)
                total_absent = sum(record['absent_days'] for record in report_data)
                total_holiday = sum(record['holiday_days'] for record in report_data)
                total_late = sum(record['late_days'] for record in report_data)
                
                # Safe calculation of total hours and attendance percentage
                try:
                    total_hours = sum(float(record['total_hours'] or 0) for record in report_data)
                    avg_attendance = sum(float(record['attendance_percentage'] or 0) for record in report_data) / len(report_data)
                except (TypeError, ValueError) as e:
                    logger.warning(f"Type conversion issue in overall statistics: {e}, setting values to 0")
                    total_hours = 0.0
                    avg_attendance = 0.0
            else:
                total_present = total_absent = total_holiday = total_late = total_hours = avg_attendance = 0

            return Response({
                'type': 'monthly_summary',
                'period': {
                    'year': year,
                    'month': month,
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'total_days': report_data[0]['total_days'] if report_data else 0
                },
                'summary': {
                    'totalEmployees': len(report_data),
                    'totalPresentDays': total_present,
                    'totalAbsentDays': total_absent,
                    'totalHolidayDays': total_holiday,
                    'totalLateDays': total_late,
                    'totalHours': round(total_hours, 2),
                    'averageAttendanceRate': round(avg_attendance, 2)
                },
                'employeeData': report_data
            })

        except Exception as e:
            import traceback
            error_msg = f"Error generating monthly summary: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            return Response(
                {'error': error_msg}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def latest_attendance(self, request):
        """Get latest attendance records for real-time updates"""
        try:
            # Get query parameters
            limit = int(request.query_params.get('limit', 10))
            office_id = request.query_params.get('office')
            user_id = request.query_params.get('user')
            
            # Default to current employees; historical reports can opt in to inactive/status-specific records.
            queryset = Attendance.objects.select_related('user', 'user__office', 'device')
            include_inactive = request.query_params.get('include_inactive') in ['true', '1', 'yes']
            employment_status = request.query_params.get('employment_status')
            if employment_status:
                queryset = queryset.filter(user__employment_status=employment_status)
            elif not include_inactive:
                queryset = queryset.filter(user__employment_status__in=['active', 'notice_period'])
            
            # Apply filters
            if office_id:
                queryset = queryset.filter(user__office_id=office_id)
            if user_id:
                queryset = queryset.filter(user_id=user_id)
            
            # Get latest records
            latest_records = queryset.order_by('-created_at')[:limit]
            
            # Serialize data
            attendance_data = []
            for record in latest_records:
                try:
                    data = {
                        'id': str(record.id),
                        'user_name': record.user.get_full_name(),
                        'employee_id': record.user.employee_id,
                        'office': record.user.office.name if record.user.office else None,
                        'date': record.date.isoformat() if record.date else None,
                        'check_in_time': record.check_in_time.isoformat() if record.check_in_time else None,
                        'check_out_time': record.check_out_time.isoformat() if record.check_out_time else None,
                        'status': record.status,
                        'device': record.device.name if record.device else None,
                        'created_at': record.created_at.isoformat() if record.created_at else None,
                        'updated_at': record.updated_at.isoformat() if record.updated_at else None,
                    }
                    attendance_data.append(data)
                except Exception as e:
                    logger.warning(f"Error processing attendance record {record.id}: {e}")
                    continue
            
            return Response({
                'success': True,
                'data': attendance_data,
                'count': len(attendance_data),
                'timestamp': timezone.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error fetching latest attendance: {e}")
            return Response({
                'success': False,
                'error': 'Failed to fetch latest attendance data'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DashboardViewSet(viewsets.ViewSet):
    """ViewSet for dashboard statistics"""
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get dashboard statistics"""
        try:
            user = request.user
            today = timezone.now().date()
            last_month = today - timedelta(days=30)
            
            if user.is_admin or user.is_hr:
                operational_statuses = ['active', 'notice_period']
                # Calculate comprehensive statistics for admin - operational employees
                total_employees = CustomUser.objects.filter(role='employee', employment_status__in=operational_statuses).count()
                total_managers = CustomUser.objects.filter(role='manager', employment_status__in=operational_statuses).count()
                total_hr = CustomUser.objects.filter(role='hr', employment_status__in=operational_statuses).count()
                total_accountants = CustomUser.objects.filter(role='accountant', employment_status__in=operational_statuses).count()
                total_offices = Office.objects.count()
                total_devices = Device.objects.count()
                active_devices = Device.objects.filter(is_active=True).count()
                
                # Attendance statistics - operational employees only
                today_attendance = Attendance.objects.filter(
                    date=today, 
                    status='present',
                    user__employment_status__in=operational_statuses
                ).count()
                total_today_records = Attendance.objects.filter(
                    date=today,
                    user__employment_status__in=operational_statuses
                ).count()
                attendance_rate = (today_attendance / total_today_records * 100) if total_today_records > 0 else 0
                
                # Leave statistics
                pending_leaves = Leave.objects.filter(status='pending').count()
                approved_leaves = Leave.objects.filter(status='approved').count()
                total_leaves = Leave.objects.count()
                leave_approval_rate = (approved_leaves / total_leaves * 100) if total_leaves > 0 else 0
                
                # User statistics
                active_users = CustomUser.objects.filter(employment_status__in=operational_statuses).count()
                total_users = CustomUser.objects.count()
                inactive_users = total_users - active_users
                lifecycle_counts = {
                    item['employment_status']: item['total']
                    for item in CustomUser.objects.values('employment_status').annotate(total=Count('id'))
                }
                
                # Growth statistics (comparing with last month)
                last_month_employees = CustomUser.objects.filter(
                    role='employee',
                    date_joined__lt=last_month
                ).count()
                employee_growth = ((total_employees - last_month_employees) / last_month_employees * 100) if last_month_employees > 0 else 0
                
                stats = {
                    'total_employees': total_employees,
                    'total_managers': total_managers,
                    'total_hr': total_hr,
                    'total_accountants': total_accountants,
                    'total_offices': total_offices,
                    'total_devices': total_devices,
                    'active_devices': active_devices,
                    'today_attendance': today_attendance,
                    'total_today_records': total_today_records,
                    'attendance_rate': round(attendance_rate, 2),
                    'pending_leaves': pending_leaves,
                    'approved_leaves': approved_leaves,
                    'total_leaves': total_leaves,
                    'leave_approval_rate': round(leave_approval_rate, 2),
                    'active_users': active_users,
                    'inactive_users': inactive_users,
                    'total_users': total_users,
                    'lifecycle_counts': lifecycle_counts,
                    'employee_growth': round(employee_growth, 2),
                    'user_activation_rate': round((active_users / total_users * 100), 2) if total_users > 0 else 0,
                }
            elif user.is_manager:
                # Calculate office-specific statistics for manager
                office = user.office
                total_employees = CustomUser.objects.filter(
                    office=office, 
                    role='employee',
                    employment_status__in=['active', 'notice_period']
                ).count()
                total_devices = Device.objects.filter(office=office).count()
                active_devices = Device.objects.filter(office=office, is_active=True).count()
                
                # Office attendance statistics - operational employees only
                today_attendance = Attendance.objects.filter(
                    user__office=office,
                    user__employment_status__in=['active', 'notice_period'],
                    date=today, 
                    status='present'
                ).count()
                total_today_records = Attendance.objects.filter(
                    user__office=office,
                    user__employment_status__in=['active', 'notice_period'],
                    date=today
                ).count()
                attendance_rate = (today_attendance / total_today_records * 100) if total_today_records > 0 else 0
                
                # Office leave statistics
                pending_leaves = Leave.objects.filter(
                    user__office=office, 
                    status='pending'
                ).count()
                approved_leaves = Leave.objects.filter(
                    user__office=office,
                    status='approved'
                ).count()
                total_leaves = Leave.objects.filter(user__office=office).count()
                leave_approval_rate = (approved_leaves / total_leaves * 100) if total_leaves > 0 else 0
                
                # Office user statistics
                active_users = CustomUser.objects.filter(
                    office=office, 
                    employment_status__in=['active', 'notice_period']
                ).count()
                total_users = CustomUser.objects.filter(office=office).count()
                lifecycle_counts = {
                    item['employment_status']: item['total']
                    for item in CustomUser.objects.filter(office=office).values('employment_status').annotate(total=Count('id'))
                }
                
                stats = {
                    'total_employees': total_employees,
                    'total_managers': 1,  # Manager themselves
                    'total_offices': 1,
                    'total_devices': total_devices,
                    'active_devices': active_devices,
                    'today_attendance': today_attendance,
                    'total_today_records': total_today_records,
                    'attendance_rate': round(attendance_rate, 2),
                    'pending_leaves': pending_leaves,
                    'approved_leaves': approved_leaves,
                    'total_leaves': total_leaves,
                    'leave_approval_rate': round(leave_approval_rate, 2),
                    'active_users': active_users,
                    'total_users': total_users,
                    'lifecycle_counts': lifecycle_counts,
                    'user_activation_rate': round((active_users / total_users * 100), 2) if total_users > 0 else 0,
                    'employee_growth': 0,  # Not applicable for managers
                }
            elif user.is_accountant:
                # Accountant statistics - same as employee (only own data)
                today_attendance = Attendance.objects.filter(
                    user=user,
                    date=today
                ).count()
                pending_leaves = Leave.objects.filter(
                    user=user, 
                    status='pending'
                ).count()
                approved_leaves = Leave.objects.filter(
                    user=user,
                    status='approved'
                ).count()
                total_leaves = Leave.objects.filter(user=user).count()
                leave_approval_rate = (approved_leaves / total_leaves * 100) if total_leaves > 0 else 0
                
                stats = {
                    'total_employees': 1,
                    'total_managers': 0,
                    'total_offices': 1,
                    'total_devices': 0,
                    'active_devices': 0,
                    'today_attendance': today_attendance,
                    'total_today_records': today_attendance,
                    'attendance_rate': 100 if today_attendance > 0 else 0,
                    'pending_leaves': pending_leaves,
                    'approved_leaves': approved_leaves,
                    'total_leaves': total_leaves,
                    'leave_approval_rate': round(leave_approval_rate, 2),
                    'active_users': 1,
                    'total_users': 1,
                    'user_activation_rate': 100,
                }
            else:
                # Employee statistics
                today_attendance = Attendance.objects.filter(
                    user=user,
                    date=today
                ).count()
                pending_leaves = Leave.objects.filter(
                    user=user, 
                    status='pending'
                ).count()
                approved_leaves = Leave.objects.filter(
                    user=user,
                    status='approved'
                ).count()
                total_leaves = Leave.objects.filter(user=user).count()
                leave_approval_rate = (approved_leaves / total_leaves * 100) if total_leaves > 0 else 0
                
                stats = {
                    'total_employees': 1,
                    'total_managers': 0,
                    'total_offices': 1,
                    'total_devices': 0,
                    'active_devices': 0,
                    'today_attendance': today_attendance,
                    'total_today_records': today_attendance,
                    'attendance_rate': 100 if today_attendance > 0 else 0,
                    'pending_leaves': pending_leaves,
                    'approved_leaves': approved_leaves,
                    'total_leaves': total_leaves,
                    'leave_approval_rate': round(leave_approval_rate, 2),
                    'active_users': 1,
                    'total_users': 1,
                    'user_activation_rate': 100,
                }
            
            serializer = DashboardStatsSerializer(stats)
            return Response(serializer.data)
        
        except Exception as e:
            logger.error(f"Error fetching dashboard stats: {e}")
            return Response({
                'error': 'Failed to fetch dashboard statistics',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def manager_stats(self, request):
        """Get manager-specific dashboard statistics"""
        user = request.user
        
        if not user.is_manager:
            return Response({
                'error': 'Access denied. Only managers can access this endpoint.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        office = user.office
        if not office:
            return Response({
                'error': 'Manager not assigned to any office'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        today = timezone.now().date()
        
        # Office-specific statistics
        total_employees = CustomUser.objects.filter(
            office=office, 
            role='employee'
        ).count()
        
        # Today's attendance for the office
        today_attendance = Attendance.objects.filter(
            user__office=office,
            date=today,
            status='present'
        ).count()
        
        # Pending leave requests for the office
        pending_leaves = Leave.objects.filter(
            user__office=office, 
            status='pending'
        ).count()
        
        # Active employees in the office
        active_employees = CustomUser.objects.filter(
            office=office, 
            is_active=True,
            role='employee'
        ).count()
        
        # Office devices
        total_devices = Device.objects.filter(office=office).count()
        active_devices = Device.objects.filter(office=office, is_active=True).count()
        
        # Recent activity (last 7 days)
        week_ago = today - timedelta(days=7)
        recent_attendance = Attendance.objects.filter(
            user__office=office,
            date__gte=week_ago
        ).count()
        
        recent_leaves = Leave.objects.filter(
            user__office=office,
            created_at__gte=week_ago
        ).count()
        
        stats = {
            'office_name': office.name,
            'office_id': str(office.id),
            'total_employees': total_employees,
            'today_attendance': today_attendance,
            'pending_leaves': pending_leaves,
            'active_employees': active_employees,
            'total_devices': total_devices,
            'active_devices': active_devices,
            'recent_attendance': recent_attendance,
            'recent_leaves': recent_leaves,
            'attendance_rate': round((today_attendance / total_employees * 100), 2) if total_employees > 0 else 0,
        }
        
        return Response(stats)

    @action(detail=False, methods=['get'])
    def manager_employees(self, request):
        """Get employees from manager's office"""
        user = request.user
        
        if not user.is_manager:
            return Response({
                'error': 'Access denied. Only managers can access this endpoint.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        office = user.office
        if not office:
            return Response({
                'error': 'Manager not assigned to any office'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get query parameters
        search = request.query_params.get('search', '')
        department = request.query_params.get('department', '')
        status = request.query_params.get('status', '')
        is_active = request.query_params.get('is_active')
        page = int(request.query_params.get('page', 1))
        page_size = min(int(request.query_params.get('page_size', 10)), 100)
        
        # Build queryset for office employees
        queryset = CustomUser.objects.filter(
            office=office,
            role='employee'
        ).select_related('office', 'department', 'designation')
        
        # Apply filters used by the manager dashboard.
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(employee_id__icontains=search) |
                Q(email__icontains=search)
            )
        
        if department:
            queryset = queryset.filter(department__name__icontains=department)

        counts = queryset.aggregate(
            active_count=Count('id', filter=Q(is_active=True)),
            inactive_count=Count('id', filter=Q(is_active=False)),
        )
        
        if status:
            if status == 'active':
                queryset = queryset.filter(is_active=True)
            elif status == 'inactive':
                queryset = queryset.filter(is_active=False)
        elif is_active in ['true', '1', 'yes']:
            queryset = queryset.filter(is_active=True)
        elif is_active in ['false', '0', 'no']:
            queryset = queryset.filter(is_active=False)
        
        # Pagination
        total_count = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        employees = queryset[start:end]
        
        # Serialize data
        serializer = ManagerEmployeeListSerializer(employees, many=True, context={'request': request})
        
        return Response({
            'results': serializer.data,
            'count': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': (total_count + page_size - 1) // page_size,
            'active_count': counts['active_count'],
            'inactive_count': counts['inactive_count'],
            'office_name': office.name,
            'office_id': str(office.id)
        })

    @action(detail=True, methods=['put'])
    def manager_approve_leave(self, request, pk=None):
        """Approve or reject leave request (manager only)"""
        user = request.user
        
        if not user.is_manager:
            return Response({
                'error': 'Access denied. Only managers can approve leaves.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        office = user.office
        if not office:
            return Response({
                'error': 'Manager not assigned to any office'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            leave = Leave.objects.get(pk=pk)
        except Leave.DoesNotExist:
            return Response({
                'error': 'Leave request not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if leave belongs to manager's office
        if leave.user.office != office:
            return Response({
                'error': 'Access denied. Can only approve leaves from your office.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get action and reason
        action = request.data.get('action')  # 'approve' or 'reject'
        reason = request.data.get('reason', '')
        
        if action not in ['approve', 'reject']:
            return Response({
                'error': 'Invalid action. Must be "approve" or "reject".'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Update leave status
        if action == 'approve':
            leave.status = 'approved'
            leave.approved_by = user
            leave.approved_at = timezone.now()
        else:
            leave.status = 'rejected'
            leave.rejected_by = user
            leave.rejected_at = timezone.now()
            leave.rejection_reason = reason
        
        leave.save()
        
        # Serialize and return updated leave
        serializer = LeaveSerializer(leave, context={'request': request})
        return Response({
            'message': f'Leave request {action}d successfully',
            'leave': serializer.data
        })

    @action(detail=False, methods=['get'])
    def manager_attendance(self, request):
        """Get attendance data for manager's office"""
        user = request.user
        
        if not user.is_manager:
            return Response({
                'error': 'Access denied. Only managers can access this endpoint.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        office = user.office
        if not office:
            return Response({
                'error': 'Manager not assigned to any office'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get query parameters
        date = request.query_params.get('date', timezone.now().date().isoformat())
        user_id = request.query_params.get('user', '')
        status = request.query_params.get('status', '')
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))
        
        try:
            target_date = timezone.datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            target_date = timezone.now().date()
        
        # Build queryset for office attendance
        queryset = Attendance.objects.filter(
            user__office=office
        ).select_related('user', 'user__office', 'device')
        
        # Apply filters
        if target_date:
            queryset = queryset.filter(date=target_date)
        
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        if status:
            queryset = queryset.filter(status=status)
        
        # Order by most recent
        queryset = queryset.order_by('-created_at')
        
        # Pagination
        total_count = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        attendance_records = queryset[start:end]
        
        # Serialize data
        serializer = AttendanceSerializer(attendance_records, many=True)
        
        return Response({
            'results': serializer.data,
            'count': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': (total_count + page_size - 1) // page_size,
            'office_name': office.name,
            'office_id': str(office.id),
            'date': target_date.isoformat()
        })

    @action(detail=False, methods=['get'])
    def manager_leaves(self, request):
        """Get leave requests for manager's office"""
        user = request.user
        
        if not user.is_manager:
            return Response({
                'error': 'Access denied. Only managers can access this endpoint.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        office = user.office
        if not office:
            return Response({
                'error': 'Manager not assigned to any office'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get query parameters
        status = request.query_params.get('status', '')
        start_date = request.query_params.get('start_date', '')
        end_date = request.query_params.get('end_date', '')
        user_id = request.query_params.get('user', '')
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))
        
        # Build queryset for office leaves
        queryset = Leave.objects.filter(
            user__office=office
        ).select_related('user', 'user__office')
        
        # Apply filters
        if status:
            queryset = queryset.filter(status=status)
        
        if start_date:
            try:
                start = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
                queryset = queryset.filter(start_date__gte=start)
            except ValueError:
                pass
        
        if end_date:
            try:
                end = timezone.datetime.strptime(end_date, '%Y-%m-%d').date()
                queryset = queryset.filter(end_date__lte=end)
            except ValueError:
                pass
        
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # Order by most recent
        queryset = queryset.order_by('-created_at')
        
        # Pagination
        total_count = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        leave_requests = queryset[start:end]
        
        # Serialize data
        serializer = LeaveSerializer(leave_requests, many=True, context={'request': request})
        
        return Response({
            'results': serializer.data,
            'count': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': (total_count + page_size - 1) // page_size,
            'office_name': office.name,
            'office_id': str(office.id)
        })

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def debug_user_permissions(request):
    """
    Debug endpoint to check user permissions and role
    """
    from django.conf import settings

    user = request.user
    if not user.is_admin:
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    if getattr(settings, 'ENVIRONMENT', 'development') == 'production':
        return Response({'error': 'Debug endpoint is disabled in production'}, status=status.HTTP_404_NOT_FOUND)
    return Response({
        'user_id': user.id,
        'username': user.username,
        'email': user.email,
        'role': user.role,
        'is_admin': user.is_admin,
        'is_manager': user.is_manager,
        'is_hr': user.is_hr,
        'is_accountant': user.is_accountant,
        'is_employee': user.is_employee,
        'office_id': str(user.office.id) if user.office else None,
        'office_name': user.office.name if user.office else None,
        'is_authenticated': user.is_authenticated,
        'is_active': user.is_active,
        'has_office': bool(user.office),
        'permissions': {
            'can_create_salary': user.role in ['admin', 'manager', 'accountant'],
            'can_update_salary': user.role in ['admin', 'manager', 'accountant'],
            'can_delete_salary': user.role in ['admin', 'manager', 'accountant'],
            'can_view_salary': user.role in ['admin', 'manager', 'employee'],
        }
    })

def custom_404(request, exception=None):
    """Custom 404 error handler"""
    from django.http import JsonResponse
    return JsonResponse({
        'error': 'Not Found',
        'message': 'The requested resource was not found',
        'status_code': 404
    }, status=404)

def custom_500(request):
    """Custom 500 error handler"""
    from django.http import JsonResponse
    return JsonResponse({
        'error': 'Internal Server Error',
        'message': 'An internal server error occurred',
        'status_code': 500
    }, status=500)


# Removed DeviceUserFilter class definition as it is now in filters.py
