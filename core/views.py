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
from django.db.models import Sum, Count, Q
from django.db import models, transaction, IntegrityError
from datetime import datetime, timedelta, date
import calendar
import logging
import traceback
import sys
from django.core.exceptions import ValidationError
from rest_framework.exceptions import APIException, ValidationError as DRFValidationError

from .models import (
    CustomUser, Office, Device, DeviceUser, Attendance, WorkingHoursSettings, 
    ESSLAttendanceLog, Leave, Document, Notification, SystemSettings,
    DocumentTemplate, GeneratedDocument, Resignation, Department, Designation,
    Shift, EmployeeShiftAssignment
)
from .serializers import (
    CustomUserSerializer, OfficeSerializer, DeviceSerializer, DeviceUserSerializer,
    DeviceUserCreateSerializer, DeviceUserMappingSerializer, DeviceUserBulkCreateSerializer,
    AttendanceSerializer, AttendanceCreateSerializer, BulkAttendanceSerializer, WorkingHoursSettingsSerializer,
    ESSLAttendanceLogSerializer, LeaveSerializer, LeaveCreateSerializer, LeaveApprovalSerializer,
    DocumentSerializer, DocumentCreateSerializer, NotificationSerializer, SystemSettingsSerializer,
    UserRegistrationSerializer, UserProfileSerializer, PasswordChangeSerializer,
    DashboardStatsSerializer, AttendanceLogSerializer, OfficeStatsSerializer,
    UserLoginSerializer, DeviceSyncSerializer, DocumentTemplateSerializer, 
    GeneratedDocumentSerializer, DocumentGenerationSerializer, ResignationSerializer,
    ResignationCreateSerializer, ResignationApprovalSerializer, DepartmentSerializer, DesignationSerializer,
    ShiftSerializer, EmployeeShiftAssignmentSerializer
)
# Permissions are defined inline in this file
from .zkteco_service import zkteco_service
from .db_manager import DatabaseConnectionManager

logger = logging.getLogger(__name__)


from .filters import (
    CustomUserFilter, DeviceUserFilter, AttendanceFilter, LeaveFilter, 
    DocumentFilter, NotificationFilter, ShiftFilter, EmployeeShiftAssignmentFilter
)


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


class IsSuperuserOrAdminOrManager(IsAuthenticated):
    """Permission to allow superuser, admin, or manager users"""
    def has_permission(self, request, view):
        return super().has_permission(request, view) and (
            request.user.is_superuser or request.user.is_admin or request.user.is_manager
        )


class ReportsViewSet(viewsets.ViewSet):
    """ViewSet for generating reports - Admin, Manager, and Accountant access"""
    permission_classes = [IsAdminOrManagerOrAccountant]

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

            # Build query - only show attendance for active users
            queryset = Attendance.objects.select_related('user', 'user__office', 'user__department').filter(user__is_active=True)

            # For managers, restrict to their assigned office
            if request.user.is_manager and not request.user.is_admin:
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
            elif request.user.is_admin:
                # Admins can see all data, apply office filter if specified
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
            
            logger.info(f" Monthly summary request - Year: {year}, Month: {month}, Office: {office_id}, User: {user_id}")
            logger.info(f" All query params: {dict(request.query_params)}")

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
            
            # Get users
            users_query = CustomUser.objects.filter(role='employee', is_active=True)
            total_users_before_filter = users_query.count()
            
            if office_id:
                users_query = users_query.filter(office_id=office_id)
                logger.info(f" Filtering by office_id: {office_id}")
            
            users = users_query.select_related('office')
            total_users_after_filter = users.count()
            
            logger.info(f" Users count - Before filter: {total_users_before_filter}, After filter: {total_users_after_filter}")
            
            report_data = []
            for user in users:
                # Get attendance records for the month
                attendance_records = Attendance.objects.filter(
                    user=user,
                    date__range=[start_date, end_date]
                )
                
                # Calculate statistics
                total_days = (end_date - start_date).days + 1
                present_days = attendance_records.filter(status='present').count()
                late_days = attendance_records.filter(status='late').count()
                half_days = attendance_records.filter(status='half_day').count()
                
                # Calculate absent days - days without attendance records or with absent status
                # Absent = Total working days - Days with any attendance record
                attended_days = attendance_records.count()
                absent_days = total_days - attended_days
                
                # If there are records with 'absent' status, add them to absent_days
                explicit_absent_days = attendance_records.filter(status='absent').count()
                absent_days += explicit_absent_days
                
                # Ensure absent_days is not negative
                absent_days = max(0, absent_days)
                
                # Log the calculation for debugging
                logger.info(f"User {user.get_full_name()}: total_days={total_days}, attended_days={attended_days}, explicit_absent={explicit_absent_days}, calculated_absent={absent_days}")
                
                # Calculate total hours - convert to float to avoid decimal type issues
                try:
                    total_hours = sum([
                        float(record.total_hours or 0) 
                        for record in attendance_records 
                        if record.total_hours is not None
                    ])
                except (TypeError, ValueError):
                    # Fallback if there are any type conversion issues
                    total_hours = 0.0
                
                # Calculate attendance percentage
                attendance_percentage = (present_days / total_days * 100) if total_days > 0 else 0
                
                report_data.append({
                    'user_id': user.id,
                    'user_name': user.get_full_name(),
                    'employee_id': user.employee_id,
                    'office': user.office.name if user.office else '',
                    'total_days': total_days,
                    'present_days': present_days,
                    'absent_days': absent_days,
                    'late_days': late_days,
                    'half_days': half_days,
                    'total_hours': round(total_hours, 2),
                    'attendance_percentage': round(attendance_percentage, 2),
                    'standard_hours': 9.0 * total_days,  # 9 hours per day
                    'hours_deficit': max(0, (9.0 * total_days) - total_hours)
                })

            # Filter by specific user if requested
            if user_id:
                report_data = [
                    record for record in report_data 
                    if str(record['user_id']) == str(user_id)
                ]

            # Calculate overall statistics
            if report_data:
                total_present = sum(record['present_days'] for record in report_data)
                total_absent = sum(record['absent_days'] for record in report_data)
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
                total_present = total_absent = total_late = total_hours = avg_attendance = 0

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
                    'totalLateDays': total_late,
                    'totalHours': round(total_hours, 2),
                    'averageAttendanceRate': round(avg_attendance, 2)
                },
                'employeeData': report_data
            })

        except Exception as e:
            logger.error(f"Error generating monthly summary: {str(e)}")
            return Response(
                {'error': f'Failed to generate monthly summary: {str(e)}'}, 
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
            
            # Build query - only show attendance for active users
            queryset = Attendance.objects.select_related('user', 'user__office', 'device').filter(user__is_active=True)
            
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


class OfficeViewSet(viewsets.ModelViewSet):
    """ViewSet for Office model"""
    queryset = Office.objects.all()
    serializer_class = OfficeSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'address', 'email']
    ordering_fields = ['name', 'created_at']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]  # Only admin can modify offices
        elif self.action in ['list', 'retrieve']:
            return [IsAdminOrManagerOrAccountant()]  # Admin, manager, and accountant can view
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        """Get queryset based on user role"""
        user = self.request.user
        
        if user.is_admin:
            # Admin can see all offices
            return Office.objects.all()
        elif user.is_manager:
            # Manager can only see their assigned office
            if user.office:
                return Office.objects.filter(id=user.office.id)
            else:
                # If manager has no office assigned, return empty queryset
                return Office.objects.none()
        elif user.is_accountant:
            # Accountant can see all offices (read-only)
            return Office.objects.all()
        else:
            # Regular employees can see their assigned office
            if user.office:
                return Office.objects.filter(id=user.office.id)
            else:
                # If employee has no office assigned, return empty queryset
                return Office.objects.none()

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Get office-specific statistics"""
        office = self.get_object()
        
        stats = {
            'office_id': office.id,
            'office_name': office.name,
            'total_employees': CustomUser.objects.filter(office=office, role='employee', is_active=True).count(),
            'present_today': Attendance.objects.filter(
                user__office=office, 
                user__is_active=True,
                date=timezone.now().date(), 
                status='present'
            ).count(),
            'absent_today': Attendance.objects.filter(
                user__office=office, 
                user__is_active=True,
                date=timezone.now().date(), 
                status='absent'
            ).count(),
            'pending_leaves': Leave.objects.filter(
                user__office=office, 
                user__is_active=True,
                status='pending'
            ).count(),
        }
        
        serializer = OfficeStatsSerializer(stats)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def debug_users(self, request, pk=None):
        """Debug endpoint to see users assigned to this office"""
        office = self.get_object()
        
        all_users = CustomUser.objects.filter(office=office)
        managers = CustomUser.objects.filter(office=office, role='manager')
        employees = CustomUser.objects.filter(office=office, role='employee')
        
        debug_data = {
            'office_id': str(office.id),
            'office_name': office.name,
            'total_users': all_users.count(),
            'managers_count': managers.count(),
            'employees_count': employees.count(),
            'managers': [
                {
                    'id': str(user.id),
                    'name': user.get_full_name(),
                    'email': user.email,
                    'role': user.role
                } for user in managers
            ],
            'employees': [
                {
                    'id': str(user.id),
                    'name': user.get_full_name(),
                    'email': user.email,
                    'role': user.role
                } for user in employees
            ]
        }
        
        return Response(debug_data)


class CustomUserViewSet(viewsets.ModelViewSet):
    """ViewSet for CustomUser model"""
    serializer_class = CustomUserSerializer
    filter_backends = [filters.OrderingFilter, DjangoFilterBackend]
    ordering_fields = ['username', 'first_name', 'last_name', 'created_at']
    filterset_class = CustomUserFilter
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get_queryset(self):
        user = self.request.user
        queryset = CustomUser.objects.select_related('office', 'department', 'designation')
        
        logger.info(f"CustomUserViewSet.get_queryset - User: {user.username}, Role: {user.role}, Is Manager: {user.is_manager}")
        logger.info(f"CustomUserViewSet.get_queryset - User office: {user.office}")
        
        if user.is_admin:
            queryset = queryset.all()
            logger.info("CustomUserViewSet.get_queryset - Admin: returning all users")
        elif user.is_manager:
            # Managers can see users from their assigned office + themselves
            if user.office:
                queryset = queryset.filter(
                    Q(office=user.office) | Q(id=user.id)
                )
                logger.info(f"CustomUserViewSet.get_queryset - Manager: filtering by office {user.office.id}")
            else:
                # If manager has no office, they can only see themselves
                queryset = queryset.filter(id=user.id)
                logger.info("CustomUserViewSet.get_queryset - Manager: no office, returning only self")
        elif user.is_accountant:
            # Accountant can see all users from all offices (read-only)
            queryset = queryset.all()
            logger.info("CustomUserViewSet.get_queryset - Accountant: returning all users")
        else:
            queryset = queryset.filter(id=user.id)
            logger.info("CustomUserViewSet.get_queryset - Employee: returning only self")
        
        logger.info(f"CustomUserViewSet.get_queryset - Final queryset count: {queryset.count()}")
        return queryset

    def get_permissions(self):
        if self.action in ['login', 'register']:
            return [permissions.AllowAny()]
        elif self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminOrManager()]  # Only admin/manager can modify users
        elif self.action in ['list', 'retrieve']:
            return [IsAdminOrManagerOrAccountant()]  # Admin, manager, and accountant can view
        return [permissions.IsAuthenticated()]

    @action(detail=False, methods=['post'])
    def register(self, request):
        """User registration endpoint"""
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': CustomUserSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def login(self, request):
        """User login endpoint with role-based dashboard access"""
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            dashboard_type = request.data.get('dashboard_type', '').lower()
            
            # Validate dashboard access based on user role
            if dashboard_type == 'admin' and user.role != 'admin':
                return Response({
                    'error': 'Access denied. Admin dashboard is only for admin users.'
                }, status=status.HTTP_403_FORBIDDEN)
            elif dashboard_type == 'manager' and user.role != 'manager':
                return Response({
                    'error': 'Access denied. Manager dashboard is only for manager users.'
                }, status=status.HTTP_403_FORBIDDEN)
            elif dashboard_type == 'employee' and user.role != 'employee':
                return Response({
                    'error': 'Access denied. Employee dashboard is only for employee users.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': CustomUserSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def profile(self, request):
        """Get current user profile"""
        serializer = CustomUserSerializer(request.user, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user profile (alias for profile)"""
        serializer = CustomUserSerializer(request.user, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['put', 'patch'], parser_classes=[MultiPartParser, FormParser, JSONParser])
    def update_profile(self, request):
        """Update current user profile"""
        # Debug logging
        logger.info(f"Profile update called by user: {request.user}")
        logger.info(f"Authentication: {request.user.is_authenticated}")
        logger.info(f"User ID: {request.user.id if request.user.is_authenticated else 'None'}")
        logger.info(f"Headers: {dict(request.headers)}")
        logger.info(f"Request data: {request.data}")
        logger.info(f"META HTTP_AUTHORIZATION: {request.META.get('HTTP_AUTHORIZATION', 'Not present')}")
        logger.info(f"Request path: {request.path}")
        logger.info(f"Request method: {request.method}")
        
        if not request.user.is_authenticated:
            logger.error("User not authenticated in update_profile")
            logger.error(f"User object: {request.user}")
            logger.error(f"User class: {type(request.user)}")
            logger.error(f"Is anonymous: {request.user.is_anonymous}")
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Check if this is a password change request
        if 'current_password' in request.data and 'new_password' in request.data:
            logger.info("Password change request detected")
            return self._handle_password_change(request)
        
        # Regular profile update
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            # Log what fields are being updated
            logger.info(f"Valid fields to update: {serializer.validated_data.keys()}")
            logger.info(f"Original user data: {dict(request.user.__dict__)}")
            
            # Save the updated data
            updated_user = serializer.save()
            logger.info(f"Profile updated successfully for user {request.user.id}")
            logger.info(f"Updated fields: {serializer.validated_data}")
            
            # Return complete user data using CustomUserSerializer
            user_serializer = CustomUserSerializer(updated_user, context={'request': request})
            return Response(user_serializer.data)
        
        logger.error(f"Profile update validation failed: {serializer.errors}")
        logger.error(f"Received data: {request.data}")
        logger.error(f"Validation errors: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def _handle_password_change(self, request):
        """Handle password change within profile update"""
        try:
            current_password = request.data.get('current_password')
            new_password = request.data.get('new_password')
            
            if not current_password or not new_password:
                return Response(
                    {'error': 'Both current_password and new_password are required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate current password
            if not request.user.check_password(current_password):
                return Response(
                    {'error': 'Invalid current password'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate new password
            if len(new_password) < 8:
                return Response(
                    {'error': 'New password must be at least 8 characters long'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Set new password
            request.user.set_password(new_password)
            request.user.save()
            
            logger.info(f"Password changed successfully for user {request.user.id}")
            return Response({'message': 'Password changed successfully'})
            
        except Exception as e:
            logger.error(f"Error changing password: {str(e)}")
            return Response(
                {'error': 'Failed to change password'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


    @action(detail=False, methods=['post','patch'])
    def change_password(self, request):
        """Change user password"""
        serializer = PasswordChangeSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            if not user.check_password(serializer.validated_data['old_password']):
                return Response({'error': 'Invalid old password'}, status=status.HTTP_400_BAD_REQUEST)
            
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({'message': 'Password changed successfully'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='upload_upi_qr', parser_classes=[MultiPartParser, FormParser])
    def upload_upi_qr(self, request):
        """Dedicated endpoint to upload UPI QR with minimal validation."""
        try:
            if not request.user.is_authenticated:
                return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

            file_obj = request.FILES.get('upi_qr')
            if not file_obj:
                return Response({'upi_qr': ['File is required']}, status=status.HTTP_400_BAD_REQUEST)

            user = request.user
            user.upi_qr = file_obj
            # reason removed
            user.save()

            return Response(CustomUserSerializer(user, context={'request': request}).data)
        except Exception as e:
            logger.exception(f"upload_upi_qr failed: {e}")
            return Response({'error': 'Failed to upload UPI QR'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def count(self, request):
        """Get user count for debugging"""
        queryset = self.get_queryset()
        total_count = queryset.count()
        office_counts = {}
        
        for office in Office.objects.all():
            office_counts[office.name] = queryset.filter(office=office).count()
        
        no_office_count = queryset.filter(office__isnull=True).count()
        
        return Response({
            'total_users': total_count,
            'office_counts': office_counts,
            'no_office_count': no_office_count,
            'user_ids': list(queryset.values_list('id', flat=True))
        })

    @action(detail=False, methods=['get'])
    def debug_assignments(self, request):
        """Debug endpoint to see all users and their office assignments"""
        user = request.user
        if not user.is_admin:
            return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
        
        all_users = CustomUser.objects.all().select_related('office')
        debug_data = {
            'total_users': all_users.count(),
            'users_with_office': all_users.filter(office__isnull=False).count(),
            'users_without_office': all_users.filter(office__isnull=True).count(),
            'users_by_office': {}
        }
        
        for user_obj in all_users:
            office_name = user_obj.office.name if user_obj.office else 'No Office'
            if office_name not in debug_data['users_by_office']:
                debug_data['users_by_office'][office_name] = {
                    'managers': [],
                    'employees': [],
                    'admins': []
                }
            
            user_info = {
                'id': str(user_obj.id),
                'name': user_obj.get_full_name(),
                'email': user_obj.email,
                'role': user_obj.role
            }
            
            if user_obj.role == 'manager':
                debug_data['users_by_office'][office_name]['managers'].append(user_info)
            elif user_obj.role == 'employee':
                debug_data['users_by_office'][office_name]['employees'].append(user_info)
            elif user_obj.role == 'admin':
                debug_data['users_by_office'][office_name]['admins'].append(user_info)
        
        return Response(debug_data)

    def update(self, request, *args, **kwargs):
        """Override update to detect bank account changes"""
        instance = self.get_object()
        
        # Store old bank account values before update (as dictionary for JSON storage)
        bank_fields = ['account_holder_name', 'bank_name', 'account_number', 'ifsc_code', 'bank_branch_name']
        old_bank_values = {}
        for field in bank_fields:
            old_bank_values[field] = getattr(instance, field, None) or ''
        
        old_upi_qr = str(instance.upi_qr) if instance.upi_qr else None
        
        # Perform the update
        response = super().update(request, *args, **kwargs)
        
        # Check if bank account fields changed
        if response.status_code == status.HTTP_200_OK:
            instance.refresh_from_db()
            changed_fields = {}
            
            for field in bank_fields:
                new_value = getattr(instance, field, None) or ''
                old_value = old_bank_values.get(field, '')
                if old_value != new_value:
                    changed_fields[field] = (old_value, new_value)
            
            # Check UPI QR change
            new_upi_qr = str(instance.upi_qr) if instance.upi_qr else None
            if old_upi_qr != new_upi_qr:
                changed_fields['upi_qr'] = (old_upi_qr, new_upi_qr)
            
            # Send notifications if bank account fields changed
            if changed_fields:
                from .notification_service import notify_bank_account_updated
                notify_bank_account_updated(instance, request.user, changed_fields)
        
        return response
    
    def partial_update(self, request, *args, **kwargs):
        """Override partial_update to detect bank account changes"""
        instance = self.get_object()
        
        # Store old bank account values before update (as dictionary for JSON storage)
        bank_fields = ['account_holder_name', 'bank_name', 'account_number', 'ifsc_code', 'bank_branch_name']
        old_bank_values = {}
        for field in bank_fields:
            old_bank_values[field] = getattr(instance, field, None) or ''
        
        old_upi_qr = str(instance.upi_qr) if instance.upi_qr else None
        
        # Perform the partial update
        response = super().partial_update(request, *args, **kwargs)
        
        # Check if bank account fields changed
        if response.status_code == status.HTTP_200_OK:
            instance.refresh_from_db()
            changed_fields = {}
            
            # Only check fields that were actually updated
            updated_fields = request.data.keys()
            
            for field in bank_fields:
                if field in updated_fields:
                    new_value = getattr(instance, field, None) or ''
                    old_value = old_bank_values.get(field, '')
                    if old_value != new_value:
                        changed_fields[field] = (old_value, new_value)
            
            # Check UPI QR change
            if 'upi_qr' in updated_fields:
                new_upi_qr = str(instance.upi_qr) if instance.upi_qr else None
                if old_upi_qr != new_upi_qr:
                    changed_fields['upi_qr'] = (old_upi_qr, new_upi_qr)
            
            # Send notifications if bank account fields changed
            if changed_fields:
                from .notification_service import notify_bank_account_updated
                notify_bank_account_updated(instance, request.user, changed_fields)
        
        return response

    @action(detail=False, methods=['get'])
    def debug_auth(self, request):
        """Debug endpoint to test authentication"""
        return Response({
            'authenticated': request.user.is_authenticated,
            'user_id': str(request.user.id) if request.user.is_authenticated else None,
            'username': request.user.username if request.user.is_authenticated else None,
            'role': request.user.role if request.user.is_authenticated else None,
            'auth_header': request.headers.get('Authorization'),
            'http_auth_header': request.META.get('HTTP_AUTHORIZATION'),
            'all_headers': dict(request.headers),
            'all_meta': {k: v for k, v in request.META.items() if k.startswith('HTTP_')}
        })

    @action(detail=False, methods=['get'])
    def updated_bank_accounts(self, request):
        """Get users with recently updated bank accounts"""
        from datetime import timedelta
        
        # Get users updated in the last 30 days (configurable)
        days = int(request.query_params.get('days', 30))
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Filter by bank_account_updated_at field (more accurate)
        queryset = self.get_queryset().filter(
            bank_account_updated_at__gte=cutoff_date
        ).exclude(
            bank_account_updated_at__isnull=True
        ).order_by('-bank_account_updated_at')
        
        serializer = CustomUserSerializer(queryset, many=True, context={'request': request})
        return Response({
            'count': queryset.count(),
            'results': serializer.data
        })
    
    @action(detail=True, methods=['get'])
    def bank_account_history(self, request, pk=None):
        """Get bank account change history for a user"""
        from .models import BankAccountHistory
        
        user = self.get_object()
        history = BankAccountHistory.objects.filter(user=user).order_by('-created_at')
        
        history_data = []
        for record in history:
            history_data.append({
                'id': str(record.id),
                'action': record.action,
                'old_values': record.old_values,
                'new_values': record.new_values,
                'changed_by': record.changed_by.get_full_name() if record.changed_by else 'System',
                'changed_by_id': str(record.changed_by.id) if record.changed_by else None,
                'changed_by_role': record.changed_by.role if record.changed_by else None,
                'is_verified': record.is_verified,
                'verified_by': record.verified_by.get_full_name() if record.verified_by else None,
                'verified_at': record.verified_at.isoformat() if record.verified_at else None,
                'created_at': record.created_at.isoformat(),
                'changed_fields': record.get_changed_fields(),
                'change_reason': record.change_reason,
            })
        
        return Response({
            'user_id': str(user.id),
            'user_name': user.get_full_name(),
            'employee_id': user.employee_id,
            'history': history_data,
            'count': len(history_data)
        })


class DeviceViewSet(viewsets.ModelViewSet):
    """ViewSet for Device model"""
    serializer_class = DeviceSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'ip_address', 'serial_number']
    ordering_fields = ['name', 'created_at']

    def get_queryset(self):
        user = self.request.user
        print(f"DeviceViewSet.get_queryset() - User: {user.username}, Role: {getattr(user, 'role', 'No role')}, Is Admin: {getattr(user, 'is_admin', 'No is_admin property')}")
        
        if user.is_admin:
            print(f"User {user.username} is admin, returning all devices")
            return Device.objects.all()
        elif user.is_manager:
            print(f"User {user.username} is manager, returning office devices")
            return Device.objects.filter(office=user.office)
        else:
            print(f"User {user.username} has no access to devices")
            return Device.objects.none()

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]  # Only admin can modify devices
        return [permissions.IsAuthenticated()]

    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        """Sync device data"""
        device = self.get_object()
        
        # Add device_id to request data if not present
        data = request.data.copy()
        if 'device_id' not in data:
            data['device_id'] = str(device.id)
        
        serializer = DeviceSyncSerializer(data=data)
        if serializer.is_valid():
            # TODO: Implement device synchronization logic
            device.last_sync = timezone.now()
            device.save()
            return Response({'message': 'Device sync initiated successfully'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AttendanceViewSet(viewsets.ModelViewSet):
    """ViewSet for Attendance model"""
    serializer_class = AttendanceSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = AttendanceFilter
    search_fields = ['user__first_name', 'user__last_name', 'notes']
    ordering_fields = ['date', 'check_in_time', 'check_out_time']

    def get_queryset(self):
        user = self.request.user
        # Base queryset - only show attendance for active users
        base_queryset = Attendance.objects.select_related('user', 'user__office', 'device').filter(user__is_active=True)
        
        if user.is_admin:
            return base_queryset
        elif user.is_manager:
            return base_queryset.filter(user__office=user.office)
        elif user.is_accountant:
            # Accountant can only see their own attendance (like employee)
            return base_queryset.filter(user=user)
        else:
            return base_queryset.filter(user=user)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get attendance statistics based on applied filters"""
        queryset = self.filter_queryset(self.get_queryset())
        
        # Calculate totals from attendance records
        total_records = queryset.count()
        present_records = queryset.filter(status='present').count()
        absent_records = queryset.filter(status='absent').count()
        late_records = queryset.filter(status='late').count()
        half_day_records = queryset.filter(day_status='half_day').count()
        complete_day_records = queryset.filter(day_status='complete_day').count()
        late_coming_records = queryset.filter(is_late=True).count()
        
        # Calculate distinct employees present
        present_employees = queryset.filter(status='present').values('user').distinct().count()
        
        # Calculate total active users for absence calculation
        # This considers the current office filter if applied
        user_queryset = CustomUser.objects.filter(is_active=True)
        office_id = request.query_params.get('office') or request.query_params.get('office_id')
        if office_id:
             user_queryset = user_queryset.filter(office__id=office_id)
        
        # If user is manager, limit to their office
        if request.user.is_manager and request.user.office:
             user_queryset = user_queryset.filter(office=request.user.office)
             
        total_active_users = user_queryset.count()
        
        # Inferred absent (Active users - Distinct present users)
        # Note: This is an approximation mainly useful for 'today' view
        inferred_absent = max(0, total_active_users - present_employees)
        
        return Response({
            'total_records': total_records,
            'present_records': present_records,
            'absent_records': absent_records,
            'late_records': late_records,
            'half_day_records': half_day_records,
            'complete_day_records': complete_day_records,
            'late_coming_records': late_coming_records,
            'present_employees': present_employees,
            'total_active_users': total_active_users,
            'inferred_absent': inferred_absent,
            'attendance_percentage': (present_employees / total_active_users * 100) if total_active_users > 0 else 0
        })

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminOrManager()]  # Only admin/manager can modify attendance
        elif self.action in ['list', 'retrieve']:
            return [IsAdminOrManagerOrAccountant()]  # Admin, manager, and accountant can view
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'create':
            return AttendanceCreateSerializer
        return AttendanceSerializer

    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """Bulk create attendance records"""
        serializer = BulkAttendanceSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            attendances = []
            for user_id in data['user_ids']:
                user = get_object_or_404(CustomUser, id=user_id)
                attendance = Attendance(
                    user=user,
                    date=data['date'],
                    status=data['status'],
                    notes=data.get('notes', '')
                )
                attendances.append(attendance)
            
            Attendance.objects.bulk_create(attendances)
            return Response({'message': f'{len(attendances)} attendance records created'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def today(self, request):
        """Get today's attendance with statistics"""
        today = timezone.now().date()
        queryset = self.get_queryset().filter(date=today)
        
        # Calculate statistics
        total_records = queryset.count()
        present_records = queryset.filter(status='present').count()
        absent_records = queryset.filter(status='absent').count()
        late_records = queryset.filter(status='late').count()
        half_day_records = queryset.filter(day_status='half_day').count()
        complete_day_records = queryset.filter(day_status='complete_day').count()
        late_coming_records = queryset.filter(is_late=True).count()
        
        # Serialize attendance records
        serializer = self.get_serializer(queryset, many=True)
        
        # Prepare response with statistics
        response_data = {
            'date': today,
            'statistics': {
                'total_records': total_records,
                'present_records': present_records,
                'absent_records': absent_records,
                'late_records': late_records,
                'half_day_records': half_day_records,
                'complete_day_records': complete_day_records,
                'late_coming_records': late_coming_records,
                'attendance_percentage': (present_records / total_records * 100) if total_records > 0 else 0
            },
            'attendance_records': serializer.data
        }
        
        return Response(response_data)

    @action(detail=False, methods=['get'])
    def report(self, request):
        """Get attendance report"""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        user_id = request.query_params.get('user_id')
        
        queryset = self.get_queryset()
        
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # Calculate statistics
        total_days = queryset.count()
        present_days = queryset.filter(status='present').count()
        absent_days = queryset.filter(status='absent').count()
        late_days = queryset.filter(status='late').count()
        total_hours = queryset.aggregate(total=Sum('total_hours'))['total'] or 0
        
        report = {
            'total_days': total_days,
            'present_days': present_days,
            'absent_days': absent_days,
            'late_days': late_days,
            'total_hours': total_hours,
            'attendance_percentage': (present_days / total_days * 100) if total_days > 0 else 0
        }
        
        return Response(report)

    @action(detail=False, methods=['get'])
    def my(self, request):
        """Get current user's attendance records"""
        queryset = self.get_queryset().filter(user=request.user)
        
        # Apply pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def monthly_attendance(self, request):
        """Get monthly attendance data for a specific user"""
        try:
            user_id = request.query_params.get('user')
            year = int(request.query_params.get('year'))
            month = int(request.query_params.get('month'))
            
            if not user_id:
                return Response(
                    {'error': 'user parameter is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                # FIXED: Added designation__department to select_related to fix the __str__ method issue
                user = CustomUser.objects.select_related('department', 'designation', 'designation__department', 'office').get(id=user_id, is_active=True)
            except CustomUser.DoesNotExist:
                return Response(
                    {'error': 'User not found or inactive'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Create target date for the month and capture today's date once
            target_date = date(year, month, 1)
            today = date.today()
            
            # Get ALL days in the month (including weekends)
            all_days = []
            first_day = date(year, month, 1)
            last_day = date(year, month, calendar.monthrange(year, month)[1])
            current_date = first_day
            
            while current_date <= last_day:
                all_days.append(current_date)
                current_date += timedelta(days=1)
            
            # Get existing attendance records for the month
            existing_attendance = Attendance.objects.filter(
                user=user,
                date__gte=first_day,
                date__lte=last_day
            ).select_related('device')
            
            # Create a dictionary for quick lookup
            attendance_dict = {att.date: att for att in existing_attendance}
            
            # Prepare monthly data with all days
            monthly_data = []
            
            for day in all_days:
                if day in attendance_dict:
                    # Existing attendance record
                    attendance = attendance_dict[day]
                    is_sunday = day.weekday() == 6

                    # Rule: If the day is Sunday and the user is not present, treat as weekend
                    if is_sunday and attendance.status not in ['present', 'half_day']:
                        monthly_data.append({
                            'id': str(attendance.id),
                            'date': day.isoformat(),
                            'check_in_time': None,
                            'check_out_time': None,
                            'total_hours': None,
                            'status': 'weekend',
                            'day_status': 'weekend',
                            'is_late': False,
                            'late_minutes': 0,
                            'device_name': None,
                            'notes': 'Sunday - Weekend',
                            'created_at': attendance.created_at.isoformat() if attendance.created_at else None,
                            'updated_at': attendance.updated_at.isoformat() if attendance.updated_at else None,
                        })
                    else:
                        monthly_data.append({
                            'id': str(attendance.id),
                            'date': day.isoformat(),
                            'check_in_time': attendance.check_in_time.isoformat() if attendance.check_in_time else None,
                            'check_out_time': attendance.check_out_time.isoformat() if attendance.check_out_time else None,
                            'total_hours': float(attendance.total_hours) if attendance.total_hours else None,
                            'status': attendance.status,
                            'day_status': attendance.day_status,
                            'is_late': attendance.is_late,
                            'late_minutes': attendance.late_minutes,
                            'device_name': attendance.device.name if attendance.device else None,
                            'notes': attendance.notes,
                            'created_at': attendance.created_at.isoformat() if attendance.created_at else None,
                            'updated_at': attendance.updated_at.isoformat() if attendance.updated_at else None,
                        })
                else:
                    # Determine status based on date
                    today = date.today()
                    is_sunday = day.weekday() == 6  # Sunday = 6, Saturday = 5
                    
                    if day > today:
                        # Future date - mark as upcoming
                        status = 'upcoming'
                        day_status = 'upcoming'
                        notes = 'Upcoming day'
                    elif is_sunday:
                        # Only Sunday - mark as weekend
                        status = 'weekend'
                        day_status = 'weekend'
                        notes = 'Sunday - Weekend'
                    else:
                        # Past working day without attendance - mark as absent (including Saturday)
                        status = 'absent'
                        day_status = 'absent'
                        notes = 'No attendance recorded'
                    
                    monthly_data.append({
                        'id': None,
                        'date': day.isoformat(),
                        'check_in_time': None,
                        'check_out_time': None,
                        'total_hours': None,
                        'status': status,
                        'day_status': day_status,
                        'is_late': False,
                        'late_minutes': 0,
                        'device_name': None,
                        'notes': notes,
                        'created_at': None,
                        'updated_at': None,
                    })
            
            # Calculate monthly statistics
            total_days_in_month = len(all_days)
            present_days = sum(1 for day in monthly_data if day['status'] in ['present', 'half_day'])
            absent_days = sum(1 for day in monthly_data if day['status'] == 'absent')
            upcoming_days = sum(1 for day in monthly_data if day['status'] == 'upcoming')
            weekend_days = sum(1 for day in monthly_data if day['status'] == 'weekend')
            complete_days = sum(1 for day in monthly_data if day['day_status'] == 'complete_day')
            half_days = sum(1 for day in monthly_data if day['day_status'] == 'half_day')
            late_coming_days = sum(1 for day in monthly_data if day['is_late'] is True)
            
            # Calculate attendance rate based on past working days only (excluding upcoming days)
            try:
                past_working_days = sum(
                    1
                    for day in monthly_data
                    if day['date'] <= today.isoformat()
                    and day['status'] != 'upcoming'
                    and not (datetime.strptime(day['date'], '%Y-%m-%d').weekday() >= 5)
                )
                if past_working_days > 0:
                    attendance_rate = (present_days / past_working_days) * 100
                else:
                    attendance_rate = 0
            except Exception:
                # Be resilient to any unexpected parsing issues so endpoint never 500s for edge cases
                attendance_rate = 0
            
            # Prepare response
            response_data = {
                'user': {
                    'id': str(user.id),
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'employee_id': user.employee_id,
                    'department': user.department.name if user.department else None,
                    'office_name': user.office.name if user.office else None,
                },
                'month': {
                    'year': year,
                    'month': month,
                    'month_name': target_date.strftime('%B'),
                    'total_days_in_month': total_days_in_month,
                },
                'statistics': {
                    'total_days_in_month': total_days_in_month,
                    'present_days': present_days,
                    'absent_days': absent_days,
                    'upcoming_days': upcoming_days,
                    'weekend_days': weekend_days,
                    'complete_days': complete_days,
                    'half_days': half_days,
                    'late_coming_days': late_coming_days,
                    'attendance_rate': round(attendance_rate, 1),
                },
                'monthly_data': monthly_data
            }
            
            return Response(response_data)
            
        except (ValueError, TypeError) as e:
            return Response(
                {'error': f'Invalid parameters: {str(e)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error in monthly_attendance: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return Response(
                {'error': f'An error occurred: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def update_status(self, request):
        """Update attendance status for a specific date - Only for managers and admins"""
        print(f"update_status called with data: {request.data}")
        print(f"User: {request.user.username}, Role: {request.user.role}")
        
        try:
            # Check if user has permission (manager or admin)
            if request.user.role not in ['manager', 'admin']:
                return Response(
                    {'error': 'Only managers and admins can update attendance status'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            user_id = request.data.get('user_id')
            date_str = request.data.get('date')
            new_status = request.data.get('status')
            new_day_status = request.data.get('day_status')
            notes = request.data.get('notes', '')
            
            if not all([user_id, date_str, new_status]):
                return Response(
                    {'error': 'user_id, date, and status are required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if new_status not in ['present', 'absent', 'upcoming', 'weekend']:
                return Response(
                    {'error': 'Status must be either "present", "absent", "upcoming", or "weekend"'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if new_day_status and new_day_status not in ['complete_day', 'half_day', 'absent', 'upcoming', 'weekend']:
                return Response(
                    {'error': 'Day status must be either "complete_day", "half_day", "absent", "upcoming", or "weekend"'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                user = CustomUser.objects.get(id=user_id, is_active=True)
            except CustomUser.DoesNotExist:
                return Response(
                    {'error': 'User not found or inactive'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Parse the date
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Invalid date format. Use YYYY-MM-DD'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get or create attendance record
            attendance, created = Attendance.objects.get_or_create(
                user=user,
                date=target_date,
                defaults={
                    'status': new_status,
                    'day_status': new_day_status or ('absent' if new_status == 'absent' else 'complete_day'),
                    'notes': notes,
                    'is_late': False,
                    'late_minutes': 0,
                }
            )
            
            if not created:
                # Update existing record using manual method to bypass automatic calculations
                attendance.manual_update_status(
                    new_status=new_status,
                    new_day_status=new_day_status,
                    notes=notes
                )
            else:
                # For newly created records, also update using manual method to ensure consistency
                attendance.manual_update_status(
                    new_status=new_status,
                    new_day_status=new_day_status,
                    notes=notes
                )
            
            # Return updated attendance data
            response_data = {
                'id': str(attendance.id),
                'date': attendance.date.isoformat(),
                'status': attendance.status,
                'day_status': attendance.day_status,
                'notes': attendance.notes,
                'updated_at': attendance.updated_at.isoformat(),
                'message': 'Attendance status updated successfully'
            }
            
            print(f"Returning response: {response_data}")
            return Response(response_data, status=status.HTTP_200_OK)
        
        except Exception as e:
            print(f"Error in update_status: {str(e)}")
            traceback.print_exc()
            return Response(
                {'error': f'An error occurred: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def fingerprint_changes(self, request):
        """Get recent fingerprint changes for real-time detection"""
        try:
            # Get today's attendance with recent updates
            today = timezone.now().date()
            queryset = self.get_queryset().filter(
                date=today,
                updated_at__gte=timezone.now() - timezone.timedelta(minutes=5)  # Last 5 minutes
            ).order_by('-updated_at')
            
            # Group by user and get latest changes
            changes = []
            user_changes = {}
            
            for attendance in queryset:
                user_id = attendance.user.id
                if user_id not in user_changes:
                    user_changes[user_id] = {
                        'user': attendance.user,
                        'check_in_time': attendance.check_in_time,
                        'check_out_time': attendance.check_out_time,
                        'last_update': attendance.updated_at,
                        'device': attendance.device
                    }
                else:
                    # Update with latest data
                    if attendance.updated_at > user_changes[user_id]['last_update']:
                        user_changes[user_id] = {
                            'user': attendance.user,
                            'check_in_time': attendance.check_in_time,
                            'check_out_time': attendance.check_out_time,
                            'last_update': attendance.updated_at,
                            'device': attendance.device
                        }
            
            # Convert to list format
            for user_id, data in user_changes.items():
                changes.append({
                    'user_id': user_id,
                    'user_name': f"{data['user'].first_name} {data['user'].last_name}",
                    'check_in_time': data['check_in_time'],
                    'check_out_time': data['check_out_time'],
                    'last_update': data['last_update'],
                    'device_name': data['device'].name if data['device'] else 'Unknown Device'
                })
            
            return Response({
                'changes': changes,
                'timestamp': timezone.now(),
                'total_changes': len(changes)
            })
            
        except Exception as e:
            logger.error(f"Error getting fingerprint changes: {str(e)}")
            return Response(
                {'error': 'Failed to get fingerprint changes'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def debug(self, request):
        """Debug endpoint to check attendance data"""
        user = request.user
        if not user.is_admin:
            return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
        
        # Get all attendance records with user data
        all_attendance = Attendance.objects.select_related('user', 'user__office').all()
        
        debug_data = {
            'total_attendance_records': all_attendance.count(),
            'attendance_with_user_data': [],
            'users_without_attendance': []
        }
        
        # Check attendance records
        for attendance in all_attendance[:10]:  # Limit to first 10 for debugging
            debug_data['attendance_with_user_data'].append({
                'attendance_id': str(attendance.id),
                'date': attendance.date.isoformat(),
                'status': attendance.status,
                'user_id': str(attendance.user.id) if attendance.user else None,
                'user_name': attendance.user.get_full_name() if attendance.user else None,
                'user_office': attendance.user.office.name if attendance.user and attendance.user.office else None,
                'check_in': attendance.check_in_time.isoformat() if attendance.check_in_time else None,
                'check_out': attendance.check_out_time.isoformat() if attendance.check_out_time else None
            })
        
        # Check users without attendance
        users_with_attendance = set(all_attendance.values_list('user_id', flat=True))
        all_users = CustomUser.objects.all()
        
        for user_obj in all_users[:10]:  # Limit to first 10 for debugging
            if user_obj.id not in users_with_attendance:
                debug_data['users_without_attendance'].append({
                    'user_id': str(user_obj.id),
                    'user_name': user_obj.get_full_name(),
                    'user_office': user_obj.office.name if user_obj.office else None,
                    'user_role': user_obj.role
                })
        
        return Response(debug_data)

    @action(detail=False, methods=['post'])
    def check_in(self, request):
        """Manual check-in for current user"""
        today = timezone.now().date()
        current_time = timezone.now()
        
        # Check if already checked in today
        existing_attendance = Attendance.objects.filter(
            user=request.user,
            date=today
        ).first()
        
        if existing_attendance and existing_attendance.check_in_time:
            return Response(
                {'error': 'Already checked in today'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get or create attendance record
        attendance, created = Attendance.objects.get_or_create(
            user=request.user,
            date=today,
            defaults={
                'status': 'present',
                'check_in_time': current_time,
                'device': request.user.office.devices.first() if request.user.office else None
            }
        )
        
        if not created:
            attendance.check_in_time = current_time
            attendance.status = 'present'
            attendance.save()
        
        serializer = self.get_serializer(attendance)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def checkin_checkout(self, request):
        """Get check-in/check-out data for a specific date with proper absent day calculation"""
        try:
            # Get query parameters
            date_str = request.query_params.get('date')
            office_id = request.query_params.get('office')
            user_id = request.query_params.get('user')
            
            # Parse date
            if date_str:
                try:
                    target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    return Response(
                        {'error': 'Invalid date format. Use YYYY-MM-DD'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                target_date = timezone.now().date()
            
            # Get base queryset
            queryset = self.get_queryset()
            
            # Apply filters
            if office_id:
                queryset = queryset.filter(user__office_id=office_id)
            if user_id:
                queryset = queryset.filter(user_id=user_id)
            
            # Get all employees for the office/date
            if office_id:
                office_users = CustomUser.objects.filter(
                    office_id=office_id, 
                    role='employee', 
                    is_active=True
                )
            else:
                # If no office specified, get users from manager's office
                if request.user.is_manager and request.user.office:
                    office_users = CustomUser.objects.filter(
                        office=request.user.office, 
                        role='employee', 
                        is_active=True
                    )
                else:
                    office_users = CustomUser.objects.filter(role='employee', is_active=True)
            
            # Get attendance records for the date - IMPORTANT: Use distinct to avoid duplicates
            # Note: distinct('user_id') only works with PostgreSQL, use Python-level deduplication for MySQL
            attendance_records = queryset.filter(date=target_date)
            
            # Create a map of user_id to attendance record - ensure one record per user
            attendance_map = {}
            for record in attendance_records:
                user_id = record.user_id
                
                # If this is the first record for this user, add it
                if user_id not in attendance_map:
                    attendance_map[user_id] = record
                else:
                    # If multiple records exist for same user, take the one with most complete data
                    existing = attendance_map[user_id]
                    
                    # Priority: Complete record > Check-in only > Incomplete
                    existing_score = self._get_attendance_completeness_score(existing)
                    new_score = self._get_attendance_completeness_score(record)
                    
                    if new_score > existing_score:
                        attendance_map[user_id] = record
            
            # Prepare response data
            attendance_details = []
            present_count = 0
            absent_count = 0
            checked_in_only = 0
            checked_out_count = 0
            
            for user in office_users:
                attendance = attendance_map.get(user.id)
                
                if attendance:
                    # User has attendance record - determine status based on check-in/check-out
                    has_checkin = bool(attendance.check_in_time)
                    has_checkout = bool(attendance.check_out_time)
                    
                    # Determine status - only one status per user per day
                    if has_checkin and has_checkout:
                        present_count += 1
                        status = 'present'
                        status_text = 'Present'
                    elif has_checkin and not has_checkout:
                        checked_in_only += 1
                        status = 'checked_in_only'
                        status_text = 'Checked In Only'
                    else:
                        # This case shouldn't happen with proper data, but handle it
                        status = 'incomplete'
                        status_text = 'Incomplete'
                    
                    attendance_details.append({
                        'employee_id': user.employee_id,
                        'employee_name': user.get_full_name(),
                        'check_in_time': attendance.check_in_time.isoformat() if attendance.check_in_time else None,
                        'check_out_time': attendance.check_out_time.isoformat() if attendance.check_out_time else None,
                        'working_hours': attendance.total_hours or 0,
                        'status': status,
                        'status_text': status_text,
                        'day_status': attendance.day_status,
                        'is_late': attendance.is_late,
                        'late_minutes': attendance.late_minutes,
                        'device_name': attendance.device.name if attendance.device else None,
                        'has_checkin': has_checkin,
                        'has_checkout': has_checkout
                    })
                else:
                    # User has NO attendance record - mark as absent
                    absent_count += 1
                    attendance_details.append({
                        'employee_id': user.employee_id,
                        'employee_name': user.get_full_name(),
                        'check_in_time': None,
                        'check_out_time': None,
                        'working_hours': 0,
                        'status': 'absent',
                        'status_text': 'Absent',
                        'day_status': 'absent',
                        'is_late': False,
                        'late_minutes': 0,
                        'device_name': None,
                        'has_checkin': False,
                        'has_checkout': False
                    })
            
            # Calculate attendance rate
            total_employees = len(office_users)
            attendance_rate = (present_count / total_employees * 100) if total_employees > 0 else 0
            
            response_data = {
                'date': target_date.isoformat(),
                'summary': {
                    'total_employees': total_employees,
                    'present_employees': present_count,
                    'absent_employees': absent_count,
                    'checked_in_only': checked_in_only,
                    'checked_out': checked_out_count,
                    'attendance_rate': round(attendance_rate, 2)
                },
                'attendance_details': attendance_details
            }
            
            return Response(response_data)
            
        except Exception as e:
            logger.error(f"Error in checkin_checkout endpoint: {str(e)}")
            return Response(
                {'error': 'Internal server error'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _get_attendance_completeness_score(self, attendance):
        """Calculate a score for how complete an attendance record is"""
        score = 0
        if attendance.check_in_time:
            score += 1
        if attendance.check_out_time:
            score += 2  # Check-out is more important
        if attendance.total_hours and attendance.total_hours > 0:
            score += 1
        return score

    @action(detail=False, methods=['post'])
    def cleanup_duplicates(self, request):
        """Clean up duplicate attendance records for the same user on the same date"""
        try:
            user = request.user
            if not user.is_admin:
                return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
            
            # Find duplicate records
            duplicates = []
            from django.db.models import Count
            from django.db import connection
            
            # Get all attendance records grouped by user and date
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT user_id, date, COUNT(*) as count
                    FROM core_attendance 
                    GROUP BY user_id, date 
                    HAVING COUNT(*) > 1
                    ORDER BY user_id, date
                """)
                duplicate_groups = cursor.fetchall()
            
            cleaned_count = 0
            for user_id, date, count in duplicate_groups:
                # Get all records for this user on this date
                records = Attendance.objects.filter(user_id=user_id, date=date).order_by('-created_at')
                
                # Keep the most recent/complete record, delete others
                if records.count() > 1:
                    keep_record = records.first()  # Most recent
                    delete_records = records.exclude(id=keep_record.id)
                    delete_count = delete_records.count()
                    delete_records.delete()
                    cleaned_count += delete_count
                    
                    duplicates.append({
                        'user_id': user_id,
                        'date': date.isoformat(),
                        'duplicates_found': count,
                        'duplicates_removed': delete_count,
                        'kept_record_id': str(keep_record.id)
                    })
            
            return Response({
                'message': f'Cleaned up {cleaned_count} duplicate attendance records',
                'duplicates_cleaned': duplicates,
                'total_cleaned': cleaned_count
            })
            
        except Exception as e:
            logger.error(f"Error cleaning up duplicates: {str(e)}")
            return Response(
                {'error': 'Failed to clean up duplicates'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def check_out(self, request):
        """Manual check-out for current user"""
        today = timezone.now().date()
        current_time = timezone.now()
        
        # Get today's attendance record
        attendance = Attendance.objects.filter(
            user=request.user,
            date=today
        ).first()
        
        if not attendance:
            return Response(
                {'error': 'No check-in record found for today'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if attendance.check_out_time:
            return Response(
                {'error': 'Already checked out today'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update check-out time
        attendance.check_out_time = current_time
        
        # Calculate total hours
        if attendance.check_in_time:
            duration = attendance.check_out_time - attendance.check_in_time
            attendance.total_hours = round(duration.total_seconds() / 3600, 2)
        
        attendance.save()
        
        serializer = self.get_serializer(attendance)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get attendance summary for current user"""
        user = request.user
        today = timezone.now().date()
        
        # Get today's attendance
        today_attendance = Attendance.objects.filter(
            user=user,
            date=today
        ).first()
        
        # Get monthly statistics
        current_month = timezone.now().replace(day=1)
        monthly_attendance = Attendance.objects.filter(
            user=user,
            date__gte=current_month
        )
        
        # Calculate statistics
        total_days = monthly_attendance.count()
        present_days = monthly_attendance.filter(status='present').count()
        absent_days = monthly_attendance.filter(status='absent').count()
        late_days = monthly_attendance.filter(status='late').count()
        total_hours = monthly_attendance.aggregate(total=Sum('total_hours'))['total'] or 0
        
        summary = {
            'today': {
                'checked_in': bool(today_attendance and today_attendance.check_in_time),
                'checked_out': bool(today_attendance and today_attendance.check_out_time),
                'check_in_time': today_attendance.check_in_time if today_attendance else None,
                'check_out_time': today_attendance.check_out_time if today_attendance else None,
                'total_hours': today_attendance.total_hours if today_attendance else 0,
                'status': today_attendance.status if today_attendance else 'absent'
            },
            'monthly': {
                'total_days': total_days,
                'present_days': present_days,
                'absent_days': absent_days,
                'late_days': late_days,
                'total_hours': total_hours,
                'attendance_percentage': (present_days / total_days * 100) if total_days > 0 else 0
            }
        }
        
        return Response(summary)


class ZKTecoAttendanceViewSet(viewsets.ViewSet):
    """ViewSet for ZKTeco attendance synchronization"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def sync_device(self, request):
        """Sync attendance from a specific ZKTeco device"""
        try:
            device_ip = request.data.get('device_ip')
            device_port = request.data.get('device_port', 4370)
            start_date = request.data.get('start_date')
            end_date = request.data.get('end_date')
            
            if not device_ip:
                return Response(
                    {'error': 'device_ip is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Parse dates if provided
            if start_date:
                start_date = datetime.strptime(start_date, '%Y-%m-%d')
            if end_date:
                end_date = datetime.strptime(end_date, '%Y-%m-%d')
            
            # Fetch attendance from device
            attendance_logs = zkteco_service.fetch_attendance_from_device(
                device_ip, device_port, start_date, end_date
            )
            
            if not attendance_logs:
                return Response(
                    {'error': 'No attendance data found or device connection failed'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Sync to database
            device_info = {
                'ip_address': device_ip,
                'port': device_port,
                'name': f"ZKTeco_{device_ip}"
            }
            
            synced_count, error_count = zkteco_service.sync_attendance_to_database(
                attendance_logs, device_info
            )
            
            return Response({
                'message': f'Successfully synced {synced_count} attendance records',
                'synced_count': synced_count,
                'error_count': error_count,
                'total_logs': len(attendance_logs)
            })
            
        except Exception as e:
            logger.error(f"Error syncing ZKTeco device: {str(e)}")
            return Response(
                {'error': f'Sync failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def sync_all_devices(self, request):
        """Sync attendance from all ZKTeco devices"""
        try:
            # Get all active ZKTeco devices
            devices = Device.objects.filter(
                device_type='zkteco',
                is_active=True
            ).values('ip_address', 'port', 'name', 'office')
            
            if not devices:
                return Response(
                    {'error': 'No active ZKTeco devices found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            start_date = request.data.get('start_date')
            end_date = request.data.get('end_date')
            
            # Parse dates if provided
            if start_date:
                start_date = datetime.strptime(start_date, '%Y-%m-%d')
            if end_date:
                end_date = datetime.strptime(end_date, '%Y-%m-%d')
            
            total_synced = 0
            total_errors = 0
            device_results = {}
            
            # Try to fetch attendance from all devices with individual error handling
            try:
                all_attendance = zkteco_service.fetch_all_devices_attendance(
                    list(devices), start_date, end_date
                )
                
                # Sync each device's attendance
                for device_name, device_data in all_attendance.items():
                    device_info = device_data['device_info']
                    attendance_logs = device_data['attendance_logs']
                    
                    synced_count, error_count = zkteco_service.sync_attendance_to_database(
                        attendance_logs, device_info
                    )
                    
                    total_synced += synced_count
                    total_errors += error_count
                    
                    device_results[device_name] = {
                        'synced_count': synced_count,
                        'error_count': error_count,
                        'total_logs': len(attendance_logs)
                    }
                    
            except Exception as sync_error:
                logger.warning(f"Failed to sync devices: {str(sync_error)}")
                # Mark all devices as failed
                for device in devices:
                    device_results[device['name']] = {
                        'synced_count': 0,
                        'error_count': 1,
                        'total_logs': 0,
                        'error': 'Device timeout or network unreachable'
                    }
                    total_errors += 1
            
            return Response({
                'message': f'Sync completed: {total_synced} records synced, {total_errors} errors',
                'total_synced': total_synced,
                'total_errors': total_errors,
                'device_results': device_results
            })
            
        except Exception as e:
            logger.error(f"Error in sync_all_devices: {str(e)}")
            # Return error status for all devices instead of failing completely
            devices = Device.objects.filter(device_type='zkteco', is_active=True)
            device_results = {}
            for device in devices:
                device_results[device.name] = {
                    'synced_count': 0,
                    'error_count': 1,
                    'total_logs': 0,
                    'error': 'Service unavailable'
                }
            
            return Response({
                'message': 'Sync failed - devices may be offline',
                'total_synced': 0,
                'total_errors': len(devices),
                'device_results': device_results,
                'error': 'Service temporarily unavailable'
            })
    
    @action(detail=False, methods=['get'])
    def device_status(self, request):
        """Get status of all ZKTeco devices"""
        try:
            devices = Device.objects.filter(
                device_type='zkteco',
                is_active=True
            )
            
            device_status = []
            for device in devices:
                # Try to connect to device with timeout handling
                try:
                    device_connection = zkteco_service.get_device(device.ip_address, device.port)
                    is_online = device_connection is not None
                except Exception as e:
                    logger.warning(f"Failed to connect to device {device.name} ({device.ip_address}): {str(e)}")
                    is_online = False
                
                status_info = {
                    'id': device.id,
                    'name': device.name,
                    'ip_address': device.ip_address,
                    'port': device.port,
                    'office': device.office.name if device.office else None,
                    'is_online': is_online,
                    'last_sync': device.last_sync.isoformat() if device.last_sync else None,
                    'connection_error': None if is_online else 'Device timeout or network unreachable'
                }
                
                device_status.append(status_info)
            
            return Response({
                'devices': device_status,
                'total_devices': len(device_status),
                'online_devices': len([d for d in device_status if d['is_online']]),
                'offline_devices': len([d for d in device_status if not d['is_online']])
            })
            
        except Exception as e:
            logger.error(f"Error getting device status: {str(e)}")
            # Return offline status for all devices instead of error
            devices = Device.objects.filter(device_type='zkteco', is_active=True)
            device_status = []
            for device in devices:
                device_status.append({
                    'id': device.id,
                    'name': device.name,
                    'ip_address': device.ip_address,
                    'port': device.port,
                    'office': device.office.name if device.office else None,
                    'is_online': False,
                    'last_sync': device.last_sync.isoformat() if device.last_sync else None,
                    'connection_error': 'Service unavailable'
                })
            
            return Response({
                'devices': device_status,
                'total_devices': len(device_status),
                'online_devices': 0,
                'offline_devices': len(device_status),
                'error': 'Service temporarily unavailable'
            })
    
    @action(detail=False, methods=['get'])
    def get_user_attendance(self, request):
        """Get attendance data for current user from ZKTeco devices"""
        try:
            user = request.user
            if not user.biometric_id:
                return Response(
                    {'error': 'User does not have a biometric ID assigned'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get user's office devices
            user_devices = []
            if user.office:
                user_devices = Device.objects.filter(
                    office=user.office,
                    device_type='zkteco',
                    is_active=True
                ).values('ip_address', 'port', 'name')
            
            if not user_devices:
                return Response(
                    {'error': 'No ZKTeco devices found for user\'s office'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get date range
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            
            if start_date:
                start_date = datetime.strptime(start_date, '%Y-%m-%d')
            else:
                start_date = timezone.now() - timedelta(days=30)  # Last 30 days
            
            if end_date:
                end_date = datetime.strptime(end_date, '%Y-%m-%d')
            else:
                end_date = timezone.now()
            
            # Fetch attendance from all user's devices
            all_attendance = zkteco_service.fetch_all_devices_attendance(
                list(user_devices), start_date, end_date
            )
            
            # Process attendance for current user
            user_attendance = []
            for device_name, device_data in all_attendance.items():
                device_logs = device_data['attendance_logs']
                user_logs = zkteco_service.process_attendance_for_user(
                    user.biometric_id, device_logs
                )
                
                for log in user_logs:
                    user_attendance.append({
                        'device_name': device_name,
                        'device_ip': log['device_ip'],
                        'punch_time': log['punch_time'].isoformat(),
                        'punch_type': log['punch_type'],
                        'timestamp': log['timestamp']
                    })
            
            # Sort by timestamp
            user_attendance.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return Response({
                'user_id': user.id,
                'biometric_id': user.biometric_id,
                'attendance_logs': user_attendance,
                'total_logs': len(user_attendance),
                'date_range': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                }
            })
            
        except Exception as e:
            logger.error(f"Error getting user attendance: {str(e)}")
            return Response(
                {'error': f'Failed to get user attendance: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LeaveViewSet(viewsets.ModelViewSet):
    """ViewSet for Leave model"""
    serializer_class = LeaveSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = LeaveFilter
    search_fields = [
        'user__first_name', 
        'user__last_name', 
        'user__employee_id',
        'user__department__name',
        'user__designation__name',
        'reason',
        'leave_type'
    ]
    ordering_fields = ['start_date', 'end_date', 'created_at']

    def get_queryset(self):
        user = self.request.user
        base_queryset = Leave.objects.select_related(
            'user', 
            'user__department', 
            'user__designation', 
            'user__office',
            'approved_by'
        ).prefetch_related('user__department', 'user__designation')
        
        if user.is_admin:
            return base_queryset
        elif user.is_manager:
            return base_queryset.filter(user__office=user.office)
        else:
            return base_queryset.filter(user=user)

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            if self.action == 'create':
                return [permissions.IsAuthenticated()]
            return [IsAdminOrManager()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'create':
            return LeaveCreateSerializer
        elif self.action in ['approve', 'reject']:
            return LeaveApprovalSerializer
        return LeaveSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def my(self, request):
        """Get current user's leaves"""
        queryset = Leave.objects.filter(user=request.user)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrManager])
    def approve(self, request, pk=None):
        """Approve leave request"""
        leave = self.get_object()
        serializer = LeaveApprovalSerializer(leave, data=request.data, partial=True)
        if serializer.is_valid():
            # Set approved status and clear any previous rejection reason
            leave.status = 'approved'
            leave.rejection_reason = ''
            leave.approved_by = request.user
            leave.approved_at = timezone.now()
            leave.save()
            # Return full leave payload
            return Response(LeaveSerializer(leave, context={'request': request}).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrManager])
    def reject(self, request, pk=None):
        """Reject leave request"""
        leave = self.get_object()
        serializer = LeaveApprovalSerializer(leave, data=request.data, partial=True)
        if serializer.is_valid():
            # Set rejected status and persist rejection reason if provided
            leave.status = 'rejected'
            leave.rejection_reason = request.data.get('rejection_reason', serializer.validated_data.get('rejection_reason', ''))
            leave.approved_by = request.user
            leave.approved_at = timezone.now()
            leave.save()
            # Return full leave payload
            return Response(LeaveSerializer(leave, context={'request': request}).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get pending leave requests"""
        queryset = self.get_queryset().filter(status='pending')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class DocumentViewSet(viewsets.ModelViewSet):
    """ViewSet for Document model"""
    serializer_class = DocumentSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = DocumentFilter
    search_fields = ['title', 'description', 'user__first_name', 'user__last_name']
    ordering_fields = ['title', 'created_at']

    def get_queryset(self):
        user = self.request.user
        base_queryset = Document.objects.select_related('user', 'user__office', 'uploaded_by')
        
        if user.is_admin:
            return base_queryset.all()
        elif user.is_manager:
            # Managers can see documents uploaded by them or documents of their office employees
            return base_queryset.filter(
                Q(uploaded_by=user) | Q(user__office=user.office)
            )
        else:
            return base_queryset.filter(user=user)

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'create':
            return DocumentCreateSerializer
        return DocumentSerializer
    
    def get_serializer_context(self):
        """Add request to serializer context for file URL generation"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def perform_create(self, serializer):
        user = self.request.user
        # If manager is uploading for another user, validate the user belongs to their office
        if user.is_manager and 'user' in serializer.validated_data:
            target_user = serializer.validated_data['user']
            if target_user.office != user.office:
                raise serializers.ValidationError("You can only upload documents for employees in your office")
        
        serializer.save(uploaded_by=user)

    @action(detail=False, methods=['get'])
    def my(self, request):
        """Get documents for the current user"""
        user = request.user
        queryset = self.get_queryset()
        
        # Apply standard filtering
        queryset = self.filter_queryset(queryset)
        
        # Apply additional custom logic if needed (e.g. category)
        category = request.query_params.get('category', '')
        assigned_only = request.query_params.get('assigned_only', 'false').lower() == 'true'

        # Filter by category
        if category:
            if category == 'personal':
                queryset = queryset.filter(document_type__in=['aadhar_card', 'pan_card', 'voter_id', 'driving_license', 'passport', 'birth_certificate'])
            elif category == 'salary':
                queryset = queryset.filter(document_type__in=['salary_slip', 'offer_letter'])
            elif category == 'uploaded':
                queryset = queryset.filter(uploaded_by=user)
        
        # Filter by assigned only (for managers)
        if assigned_only and user.is_manager:
            queryset = queryset.filter(uploaded_by=user)
        
        # Apply pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def manager_employees(self, request):
        """Get employees that manager can upload documents for"""
        user = request.user
        if not user.is_manager:
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
        
        employees = CustomUser.objects.filter(
            office=user.office,
            role='employee',
            is_active=True
        ).values('id', 'first_name', 'last_name', 'employee_id', 'email')
        
        return Response({
            'employees': list(employees)
        })

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download a document file"""
        document = self.get_object()
        
        # Check if user has permission to download this document
        user = request.user
        if not (user.is_admin or user.is_manager or document.user == user or document.uploaded_by == user):
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            from django.http import FileResponse
            import os
            import mimetypes
            from urllib.parse import quote
            
            file_path = document.file.path
            if os.path.exists(file_path):
                filename = os.path.basename(document.file.name) or os.path.basename(file_path)
                content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
                fh = open(file_path, 'rb')
                response = FileResponse(fh, content_type=content_type)
                # RFC 5987 encoding for UTF-8 filenames
                response['Content-Disposition'] = f"attachment; filename*=UTF-8''{quote(filename)}"
                try:
                    response['Content-Length'] = os.path.getsize(file_path)
                except Exception:
                    pass
                return response
            else:
                return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': f'Error downloading file: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class NotificationViewSet(viewsets.ModelViewSet):
    """Enhanced ViewSet for Notification model"""
    serializer_class = NotificationSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_class = NotificationFilter
    ordering_fields = ['created_at', 'priority', 'notification_type']
    ordering = ['-created_at']
    search_fields = ['title', 'message']

    def get_queryset(self):
        """Get notifications for current user, filtering out expired ones"""
        from django.utils import timezone
        from django.db.models import Q
        
        queryset = Notification.objects.filter(user=self.request.user)
        
        # Filter out expired notifications
        queryset = queryset.filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
        )
        
        return queryset

    def get_permissions(self):
        """Set permissions based on action"""
        if self.action in ['list', 'retrieve', 'mark_read', 'mark_all_read', 'unread_count', 'destroy']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAdminOrManagerOrAccountant]
        return [permission() for permission in permission_classes]

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark notification as read"""
        from .notification_service import NotificationService
        
        success = NotificationService.mark_as_read(pk, request.user)
        if success:
            return Response({'message': 'Notification marked as read'})
        return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read"""
        from .notification_service import NotificationService
        
        updated_count = NotificationService.mark_all_as_read(request.user)
        return Response({
            'message': f'{updated_count} notifications marked as read'
        })

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get unread notification count"""
        from .notification_service import NotificationService
        
        count = NotificationService.get_unread_count(request.user)
        return Response({'unread_count': count})

    def destroy(self, request, pk=None):
        """Delete a notification"""
        from .notification_service import NotificationService
        
        success = NotificationService.delete_notification(pk, request.user)
        if success:
            return Response({'message': 'Notification deleted'})
        return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'])
    def delete_expired(self, request):
        """Delete expired notifications"""
        from .notification_service import NotificationService
        
        deleted_count = NotificationService.delete_expired_notifications()
        return Response({
            'message': f'{deleted_count} expired notifications deleted'
        })

    @action(detail=False, methods=['post'])
    def cleanup_old(self, request):
        """Clean up old notifications (admin only)"""
        from .notification_service import NotificationService
        
        days = request.data.get('days', 30)
        deleted_count = NotificationService.cleanup_old_notifications(days)
        return Response({
            'message': f'{deleted_count} old notifications deleted'
        })

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get notification statistics"""
        from django.db.models import Count, Q
        
        user = request.user
        qs = self.get_queryset()
        
        total_count = qs.count()
        unread_count = qs.filter(is_read=False).count()
        system_count = qs.filter(notification_type='system').count()
        email_sent_count = qs.filter(is_email_sent=True).count()
        
        return Response({
            'total_count': total_count,
            'unread_count': unread_count,
            'system_count': system_count,
            'email_sent_count': email_sent_count
        })

    @action(detail=False, methods=['post'])
    def create_bulk(self, request):
        """Create notifications for multiple users (admin/manager only)"""
        import logging
        from .notification_service import NotificationService
        
        logger = logging.getLogger(__name__)
        
        # Get target type and parameters
        target_type = request.data.get('target_type', 'users')  # 'users', 'office', 'role', 'all'
        users = request.data.get('users', [])
        office_ids = request.data.get('office_ids', [])
        roles = request.data.get('roles', [])
        
        title = request.data.get('title')
        message = request.data.get('message')
        notification_type = request.data.get('notification_type', 'system')
        category = request.data.get('category', 'info')
        priority = request.data.get('priority', 'medium')
        action_url = request.data.get('action_url', '')
        action_text = request.data.get('action_text', '')
        expires_at = request.data.get('expires_at')
        send_email = request.data.get('send_email', False)
        
        if not title or not message:
            return Response({
                'error': 'title and message are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get user objects based on target type
        user_objects = []
        
        if target_type == 'users' and users:
            user_objects = CustomUser.objects.filter(id__in=users, is_active=True)
        elif target_type == 'office' and office_ids:
            user_objects = CustomUser.objects.filter(office__in=office_ids, is_active=True)
        elif target_type == 'role' and roles:
            user_objects = CustomUser.objects.filter(role__in=roles, is_active=True)
        elif target_type == 'all':
            user_objects = CustomUser.objects.filter(is_active=True)
        else:
            return Response({
                'error': 'Invalid target type or missing target parameters'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not user_objects.exists():
            return Response({
                'error': 'No users found for the specified criteria'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Parse expires_at if provided
        expires_at_parsed = None
        if expires_at:
            try:
                from django.utils.dateparse import parse_datetime
                from django.utils import timezone
                expires_at_parsed = parse_datetime(expires_at)
                # Make timezone-aware if it's naive
                if expires_at_parsed and expires_at_parsed.tzinfo is None:
                    expires_at_parsed = timezone.make_aware(expires_at_parsed)
            except:
                return Response({
                    'error': 'Invalid expires_at format. Use ISO format: YYYY-MM-DDTHH:MM:SS'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            notifications = NotificationService.create_bulk_notifications(
                user_objects, title, message,
                notification_type=notification_type,
                category=category,
                priority=priority,
                action_url=action_url,
                action_text=action_text,
                expires_at=expires_at_parsed,
                created_by=request.user,
                send_email=send_email
            )
            
            return Response({
                'message': f'{len(notifications)} notifications created successfully',
                'notifications': NotificationSerializer(notifications, many=True).data,
                'target_info': {
                    'target_type': target_type,
                    'user_count': len(user_objects),
                    'email_sent': send_email,
                    'email_queued': send_email  # Emails are queued for background processing
                }
            })
            
        except Exception as e:
            logger.error(f"Error creating bulk notifications: {str(e)}")
            return Response({
                'error': 'Failed to create notifications',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def get_target_options(self, request):
        """Get available target options for notifications (offices, roles, etc.)"""
        from .models import Office
        
        offices = Office.objects.all().values('id', 'name')
        roles = CustomUser.objects.values_list('role', flat=True).distinct()
        
        return Response({
            'offices': list(offices),
            'roles': list(roles),
            'role_choices': [
                {'value': 'admin', 'label': 'Admin'},
                {'value': 'manager', 'label': 'Manager'},
                {'value': 'employee', 'label': 'Employee'},
                {'value': 'accountant', 'label': 'Accountant'},
            ]
        })


class SystemSettingsViewSet(viewsets.ModelViewSet):
    """ViewSet for SystemSettings model - Admin only"""
    queryset = SystemSettings.objects.all()
    serializer_class = SystemSettingsSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['key', 'description']
    ordering_fields = ['key', 'created_at']


class AttendanceLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for AttendanceLog model - Read only"""
    serializer_class = AttendanceLogSerializer
    permission_classes = [IsAdminOrManager]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at']

    def get_queryset(self):
        user = self.request.user
        if user.is_admin:
            return AttendanceLog.objects.all()
        elif user.is_manager:
            return AttendanceLog.objects.filter(attendance__user__office=user.office)
        else:
            return AttendanceLog.objects.none()


# Dashboard Views
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def debug_user_permissions(request):
    """
    Debug endpoint to check user permissions and role
    """
    user = request.user
    return Response({
        'user_id': user.id,
        'username': user.username,
        'email': user.email,
        'role': user.role,
        'is_admin': user.is_admin,
        'is_manager': user.is_manager,
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
            
            if user.is_admin:
                # Calculate comprehensive statistics for admin - only active users
                total_employees = CustomUser.objects.filter(role='employee', is_active=True).count()
                total_managers = CustomUser.objects.filter(role='manager', is_active=True).count()
                total_accountants = CustomUser.objects.filter(role='accountant', is_active=True).count()
                total_offices = Office.objects.count()
                total_devices = Device.objects.count()
                active_devices = Device.objects.filter(is_active=True).count()
                
                # Attendance statistics - only active users
                today_attendance = Attendance.objects.filter(
                    date=today, 
                    status='present',
                    user__is_active=True
                ).count()
                total_today_records = Attendance.objects.filter(
                    date=today,
                    user__is_active=True
                ).count()
                attendance_rate = (today_attendance / total_today_records * 100) if total_today_records > 0 else 0
                
                # Leave statistics
                pending_leaves = Leave.objects.filter(status='pending').count()
                approved_leaves = Leave.objects.filter(status='approved').count()
                total_leaves = Leave.objects.count()
                leave_approval_rate = (approved_leaves / total_leaves * 100) if total_leaves > 0 else 0
                
                # User statistics
                active_users = CustomUser.objects.filter(is_active=True).count()
                total_users = CustomUser.objects.count()
                inactive_users = total_users - active_users
                
                # Growth statistics (comparing with last month)
                last_month_employees = CustomUser.objects.filter(
                    role='employee',
                    date_joined__lt=last_month
                ).count()
                employee_growth = ((total_employees - last_month_employees) / last_month_employees * 100) if last_month_employees > 0 else 0
                
                stats = {
                    'total_employees': total_employees,
                    'total_managers': total_managers,
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
                    'employee_growth': round(employee_growth, 2),
                    'user_activation_rate': round((active_users / total_users * 100), 2) if total_users > 0 else 0,
                }
            elif user.is_manager:
                # Calculate office-specific statistics for manager
                office = user.office
                total_employees = CustomUser.objects.filter(
                    office=office, 
                    role='employee',
                    is_active=True
                ).count()
                total_devices = Device.objects.filter(office=office).count()
                active_devices = Device.objects.filter(office=office, is_active=True).count()
                
                # Office attendance statistics - only active users
                today_attendance = Attendance.objects.filter(
                    user__office=office,
                    user__is_active=True,
                    date=today, 
                    status='present'
                ).count()
                total_today_records = Attendance.objects.filter(
                    user__office=office,
                    user__is_active=True,
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
                    is_active=True
                ).count()
                total_users = CustomUser.objects.filter(office=office).count()
                
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
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))
        
        # Build queryset for office employees
        queryset = CustomUser.objects.filter(
            office=office,
            role='employee'
        ).select_related('office', 'department', 'designation')
        
        # Apply filters
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(employee_id__icontains=search) |
                Q(email__icontains=search)
            )
        
        if department:
            queryset = queryset.filter(department__name__icontains=department)
        
        if status:
            if status == 'active':
                queryset = queryset.filter(is_active=True)
            elif status == 'inactive':
                queryset = queryset.filter(is_active=False)
        
        # Pagination
        total_count = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        employees = queryset[start:end]
        
        # Serialize data
        serializer = CustomUserSerializer(employees, many=True, context={'request': request})
        
        return Response({
            'results': serializer.data,
            'count': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': (total_count + page_size - 1) // page_size,
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


class ResignationViewSet(viewsets.ModelViewSet):
    """ViewSet for Resignation model"""
    serializer_class = ResignationSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'user__office', 'resignation_date']
    search_fields = ['user__first_name', 'user__last_name', 'user__employee_id', 'user__office__name', 'reason', 'status']
    ordering_fields = ['resignation_date', 'created_at', 'status']
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get queryset based on user role"""
        user = self.request.user
        
        if user.is_admin:
            # Admin can see all resignations
            return Resignation.objects.select_related('user', 'approved_by').all()
        elif user.is_manager:
            # Manager can see resignations from their office
            if user.office:
                return Resignation.objects.select_related('user', 'approved_by').filter(
                    user__office=user.office
                )
            else:
                return Resignation.objects.none()
        else:
            # Employee can only see their own resignations
            return Resignation.objects.select_related('user', 'approved_by').filter(
                user=user
            )

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return ResignationCreateSerializer
        elif self.action in ['approve', 'reject']:
            return ResignationApprovalSerializer
        return ResignationSerializer

    def get_permissions(self):
        """Set permissions based on action"""
        if self.action in ['create']:
            # Only employees can create resignation requests
            permission_classes = [IsAuthenticated]
        elif self.action in ['approve', 'reject']:
            # Only admin and manager can approve/reject
            permission_classes = [IsAdminOrManager]
        else:
            # Default permissions
            permission_classes = [IsAuthenticated]
        
        return [permission() for permission in permission_classes]

    def create(self, request, *args, **kwargs):
        """Create a new resignation request"""
        # Ensure only employees and accountants can create resignation requests
        if request.user.role not in ['employee', 'accountant']:
            return Response({
                'error': 'Only employees and accountants can submit resignation requests'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Check if user already has a pending resignation
        existing_resignation = Resignation.objects.filter(
            user=request.user,
            status='pending'
        ).first()
        
        if existing_resignation:
            return Response({
                'error': 'You already have a pending resignation request'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        resignation = serializer.save()
        
        # Create notification for managers/admins
        self._create_resignation_notification(resignation)
        
        return Response(
            ResignationSerializer(resignation).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a resignation request"""
        resignation = self.get_object()
        
        if resignation.status != 'pending':
            return Response({
                'error': 'Only pending resignations can be approved'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = ResignationApprovalSerializer(
            resignation, 
            data={'status': 'approved'}, 
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        
        # Save the status using the serializer
        resignation = serializer.save()
        
        # Update approval details
        resignation.approved_by = request.user
        resignation.approved_at = timezone.now()
        resignation.save()
        
        # Create notification for the employee
        self._create_approval_notification(resignation, 'approved')
        
        # Broadcast resignation update via WebSocket
        try:
            from .consumers import broadcast_resignation_update_sync
            resignation_data = ResignationSerializer(resignation).data
            broadcast_resignation_update_sync(resignation_data)
        except Exception as e:
            print(f"Error broadcasting resignation update: {e}")
        
        return Response(ResignationSerializer(resignation).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a resignation request"""
        resignation = self.get_object()
        
        if resignation.status != 'pending':
            return Response({
                'error': 'Only pending resignations can be rejected'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = ResignationApprovalSerializer(
            resignation, 
            data=request.data, 
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        
        # Update rejection details
        resignation.approved_by = request.user
        resignation.approved_at = timezone.now()
        resignation.status = 'rejected'
        resignation.rejection_reason = serializer.validated_data.get('rejection_reason', '')
        resignation.save()
        
        # Create notification for the employee
        self._create_approval_notification(resignation, 'rejected')
        
        # Broadcast resignation update via WebSocket
        try:
            from .consumers import broadcast_resignation_update_sync
            resignation_data = ResignationSerializer(resignation).data
            broadcast_resignation_update_sync(resignation_data)
        except Exception as e:
            print(f"Error broadcasting resignation update: {e}")
        
        return Response(ResignationSerializer(resignation).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a resignation request (only by the employee who created it)"""
        resignation = self.get_object()
        
        if resignation.user != request.user:
            return Response({
                'error': 'You can only cancel your own resignation requests'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if resignation.status != 'pending':
            return Response({
                'error': 'Only pending resignations can be cancelled'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        resignation.status = 'cancelled'
        resignation.save()
        
        return Response(ResignationSerializer(resignation).data)

    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get pending resignation requests"""
        queryset = self.get_queryset().filter(status='pending')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def my_resignations(self, request):
        """Get current user's resignation requests"""
        if request.user.role not in ['employee', 'accountant']:
            return Response({
                'error': 'Only employees and accountants can access their resignation requests'
            }, status=status.HTTP_403_FORBIDDEN)
        
        queryset = Resignation.objects.filter(user=request.user)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get resignation statistics"""
        user = request.user
        
        # Get base queryset based on user role
        if user.is_admin:
            # Admin can see all resignations
            queryset = Resignation.objects.all()
        elif user.is_manager:
            # Manager can see resignations from their office
            if user.office:
                queryset = Resignation.objects.filter(user__office=user.office)
            else:
                queryset = Resignation.objects.none()
        else:
            # Employee can only see their own resignations
            queryset = Resignation.objects.filter(user=user)
        
        # Calculate statistics
        stats = {
            'total': queryset.count(),
            'pending': queryset.filter(status='pending').count(),
            'approved': queryset.filter(status='approved').count(),
            'rejected': queryset.filter(status='rejected').count(),
            'cancelled': queryset.filter(status='cancelled').count(),
        }
        
        # Add recent resignations (last 30 days)
        from datetime import timedelta
        thirty_days_ago = timezone.now().date() - timedelta(days=30)
        stats['recent'] = queryset.filter(created_at__date__gte=thirty_days_ago).count()
        
        return Response(stats)

    def _create_resignation_notification(self, resignation):
        """Create notification for managers/admins about new resignation"""
        # Get managers and admins who should be notified
        if resignation.user.office:
            # Notify office manager and admins
            managers = CustomUser.objects.filter(
                Q(role='manager', office=resignation.user.office) | 
                Q(role='admin')
            ).distinct()
        else:
            # Notify all admins if user has no office
            managers = CustomUser.objects.filter(role='admin')
        
        for manager in managers:
            Notification.objects.create(
                user=manager,
                title='New Resignation Request',
                message=f'{resignation.user.get_full_name()} has submitted a resignation request with last working date {resignation.resignation_date}.',
                notification_type='system'
            )

    def _create_approval_notification(self, resignation, action):
        """Create notification for employee about resignation approval/rejection"""
        action_text = 'approved' if action == 'approved' else 'rejected'
        message = f'Your resignation request has been {action_text} by {resignation.approved_by.get_full_name()}.'
        
        if action == 'rejected' and resignation.rejection_reason:
            message += f' Reason: {resignation.rejection_reason}'
        
        Notification.objects.create(
            user=resignation.user,
            title=f'Resignation Request {action_text.title()}',
            message=message,
            notification_type='system'
        )


class DepartmentViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Department model - Read only for dropdowns"""
    queryset = Department.objects.filter(is_active=True)
    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    @action(detail=True, methods=['get'])
    def designations(self, request, pk=None):
        """Get all designations for a specific department"""
        department = self.get_object()
        designations = department.designations.filter(is_active=True)
        serializer = DesignationSerializer(designations, many=True)
        return Response(serializer.data)


class DesignationViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Designation model - Read only for dropdowns"""
    queryset = Designation.objects.filter(is_active=True)
    serializer_class = DesignationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description', 'department__name']
    ordering_fields = ['name', 'department__name', 'created_at']
    ordering = ['department__name', 'name']
    
    def get_queryset(self):
        """Filter designations by department if specified"""
        queryset = super().get_queryset()
        
        # Check for department_id in URL kwargs (for /departments/{id}/designations/)
        department_id = self.kwargs.get('department_id')
        
        # If not in URL kwargs, check query params (for /designations/?department=)
        if not department_id:
            department_id = self.request.query_params.get('department')
        
        if department_id:
            try:
                # Try to parse as UUID first
                import uuid
                department_uuid = uuid.UUID(department_id)
                queryset = queryset.filter(department_id=department_uuid)
            except (ValueError, TypeError):
                # If not a valid UUID, try to filter by department name
                queryset = queryset.filter(department__name__icontains=department_id)
        return queryset
    
    @action(detail=False, methods=['get'], url_path='by-department/(?P<department_id>[^/.]+)')
    def by_department(self, request, department_id=None):
        """Get designations by department ID"""
        # Use the base queryset to avoid double filtering
        queryset = Designation.objects.filter(is_active=True)
        
        if department_id:
            try:
                import uuid
                department_uuid = uuid.UUID(department_id)
                queryset = queryset.filter(department_id=department_uuid)
            except (ValueError, TypeError):
                queryset = queryset.filter(department__name__icontains=department_id)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


# Custom error handlers for production
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


class DeviceUserViewSet(viewsets.ModelViewSet):
    """ViewSet for DeviceUser model"""
    serializer_class = DeviceUserSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = DeviceUserFilter
    search_fields = ['device_user_name', 'device_user_id', 'device__name', 'system_user__first_name', 'system_user__last_name']
    ordering_fields = ['device_user_name', 'device_user_id', 'created_at', 'updated_at']
    ordering = ['device', 'device_user_id']

    def get_queryset(self):
        user = self.request.user
        
        if user.is_superuser or user.is_admin:
            # Superuser and admin can see all device users
            return DeviceUser.objects.select_related('device', 'system_user', 'device__office').all()
        elif user.is_manager:
            # Manager can see device users from their office devices
            return DeviceUser.objects.select_related('device', 'system_user', 'device__office').filter(
                device__office=user.office
            )
        else:
            # Other users have no access
            return DeviceUser.objects.none()

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsSuperuserOrAdminOrManager()]  # Superuser, admin, and manager can modify device users
        elif self.action in ['list', 'retrieve']:
            return [IsSuperuserOrAdminOrManager()]  # Superuser, admin, and manager can view device users
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'create':
            return DeviceUserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return DeviceUserCreateSerializer
        return DeviceUserSerializer

    @action(detail=True, methods=['post'])
    def map_to_system_user(self, request, pk=None):
        """Map device user to a system user"""
        device_user = self.get_object()
        serializer = DeviceUserMappingSerializer(device_user, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Device user mapped successfully',
                'data': DeviceUserSerializer(device_user).data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def unmap_from_system_user(self, request, pk=None):
        """Unmap device user from system user"""
        device_user = self.get_object()
        
        device_user.system_user = None
        device_user.is_mapped = False
        device_user.mapping_notes = ''
        device_user.save()
        
        return Response({
            'message': 'Device user unmapped successfully',
            'data': DeviceUserSerializer(device_user).data
        })

    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """Bulk create device users"""
        serializer = DeviceUserBulkCreateSerializer(data=request.data)
        
        if serializer.is_valid():
            device_id = serializer.validated_data['device']
            device_users_data = serializer.validated_data['device_users']
            
            try:
                with transaction.atomic():
                    created_users = []
                    for user_data in device_users_data:
                        user_data['device_id'] = device_id
                        device_user = DeviceUser.objects.create(**user_data)
                        created_users.append(DeviceUserSerializer(device_user).data)
                    
                    return Response({
                        'message': f'Successfully created {len(created_users)} device users',
                        'data': created_users
                    }, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({
                    'error': 'Failed to create device users',
                    'details': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def unmapped_users(self, request):
        """Get unmapped device users"""
        queryset = self.get_queryset().filter(is_mapped=False)
        
        # Apply filters
        queryset = self.filter_queryset(queryset)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def mapped_users(self, request):
        """Get mapped device users"""
        queryset = self.get_queryset().filter(is_mapped=True)
        
        # Apply filters
        queryset = self.filter_queryset(queryset)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_device(self, request):
        """Get device users by device ID"""
        device_id = request.query_params.get('device_id')
        
        if not device_id:
            return Response({
                'error': 'device_id parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            import uuid
            device_uuid = uuid.UUID(device_id)
            queryset = self.get_queryset().filter(device_id=device_uuid)
            
            # Apply filters
            queryset = self.filter_queryset(queryset)
            
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        except ValueError:
            return Response({
                'error': 'Invalid device_id format'
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get device user statistics"""
        queryset = self.get_queryset()
        
        total_users = queryset.count()
        mapped_users = queryset.filter(is_mapped=True).count()
        unmapped_users = queryset.filter(is_mapped=False).count()
        
        # Group by device
        device_stats = queryset.values('device__name', 'device__id').annotate(
            total_users=Count('id'),
            mapped_users=Count('id', filter=Q(is_mapped=True)),
            unmapped_users=Count('id', filter=Q(is_mapped=False))
        )
        
        # Group by privilege
        privilege_stats = queryset.values('device_user_privilege').annotate(
            count=Count('id')
        )
        
        return Response({
            'total_users': total_users,
            'mapped_users': mapped_users,
            'unmapped_users': unmapped_users,
            'mapping_percentage': round((mapped_users / total_users * 100) if total_users > 0 else 0, 2),
            'device_stats': list(device_stats),
            'privilege_stats': list(privilege_stats)
        })


class ShiftViewSet(viewsets.ModelViewSet):
    """ViewSet for Shift model"""
    queryset = Shift.objects.all()
    serializer_class = ShiftSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ShiftFilter
    search_fields = ['name', 'shift_type']
    ordering_fields = ['name', 'start_time', 'created_at']
    ordering = ['office', 'start_time', 'name']
    
    def get_pagination_class(self):
        """Disable pagination for list action to show all shifts"""
        if self.action == 'list':
            return None
        return super().get_pagination_class()

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminOrManager()]  # Only admin or manager can modify shifts
        elif self.action in ['list', 'retrieve']:
            return [IsAdminOrManagerOrAccountant()]  # Admin, manager, and accountant can view
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        """Get queryset based on user role"""
        user = self.request.user
        
        if user.is_admin:
            # Admin can see all shifts
            return Shift.objects.all()
        elif user.is_manager:
            # Manager can only see shifts from their office
            if user.office:
                return Shift.objects.filter(office=user.office)
            else:
                return Shift.objects.none()
        elif user.is_accountant:
            # Accountant can see all shifts (read-only)
            return Shift.objects.all()
        else:
            return Shift.objects.none()

    def perform_create(self, serializer):
        """Automatically set office and created_by for managers"""
        user = self.request.user
        
        # Auto-set office for managers
        if user.is_manager:
            if user.office:
                serializer.save(office=user.office, created_by=user)
            else:
                # If manager has no office, try to get the first available office
                from core.models import Office
                first_office = Office.objects.first()
                if first_office:
                    serializer.save(office=first_office, created_by=user)
                else:
                    # Create default office if none exists
                    default_office = Office.objects.create(
                        name="Default Office",
                        address="Default Address"
                    )
                    serializer.save(office=default_office, created_by=user)
        else:
            serializer.save(created_by=user)


class EmployeeShiftAssignmentViewSet(viewsets.ModelViewSet):
    """ViewSet for EmployeeShiftAssignment model"""
    queryset = EmployeeShiftAssignment.objects.all()
    serializer_class = EmployeeShiftAssignmentSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = EmployeeShiftAssignmentFilter
    search_fields = ['employee__first_name', 'employee__last_name', 'shift__name']
    ordering_fields = ['created_at', 'employee__first_name']
    ordering = ['-created_at']
    
    def get_pagination_class(self):
        """Disable pagination for list action to show all assignments"""
        if self.action == 'list':
            logger.info("EmployeeShiftAssignmentViewSet - Pagination disabled for list action")
            return None
        return super().get_pagination_class()
    
    def list(self, request, *args, **kwargs):
        """Override list method to ensure all assignments are returned"""
        queryset = self.filter_queryset(self.get_queryset())
        logger.info(f"EmployeeShiftAssignmentViewSet.list - Final queryset count: {queryset.count()}")
        
        serializer = self.get_serializer(queryset, many=True)
        logger.info(f"EmployeeShiftAssignmentViewSet.list - Returning {len(serializer.data)} assignments")
        
        return Response(serializer.data)

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminOrManager()]  # Only admin or manager can modify assignments
        elif self.action in ['list', 'retrieve']:
            return [IsAdminOrManagerOrAccountant()]  # Admin, manager, and accountant can view
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        """Get queryset based on user role"""
        user = self.request.user
        
        if user.is_admin:
            # Admin can see all assignments
            queryset = EmployeeShiftAssignment.objects.all()
            logger.info(f"EmployeeShiftAssignmentViewSet - Admin: returning {queryset.count()} assignments")
            return queryset
        elif user.is_manager:
            # Manager can only see assignments from their office
            if user.office:
                queryset = EmployeeShiftAssignment.objects.filter(shift__office=user.office)
                logger.info(f"EmployeeShiftAssignmentViewSet - Manager: office={user.office}, returning {queryset.count()} assignments")
                # Log some details about the assignments
                for assignment in queryset[:5]:  # Log first 5 assignments
                    logger.info(f"Assignment: {assignment.employee.get_full_name()} -> {assignment.shift.name} (Office: {assignment.shift.office.name})")
                return queryset
            else:
                logger.info("EmployeeShiftAssignmentViewSet - Manager: no office assigned")
                return EmployeeShiftAssignment.objects.none()
        elif user.is_accountant:
            # Accountant can see all assignments (read-only)
            queryset = EmployeeShiftAssignment.objects.all()
            logger.info(f"EmployeeShiftAssignmentViewSet - Accountant: returning {queryset.count()} assignments")
            return queryset
        else:
            logger.info("EmployeeShiftAssignmentViewSet - No permission")
            return EmployeeShiftAssignment.objects.none()

    def perform_create(self, serializer):
        """Automatically set assigned_by for managers and validate for duplicates"""
        user = self.request.user
        
        # Get the data from serializer
        employee = serializer.validated_data.get('employee')
        shift = serializer.validated_data.get('shift')
        
        # Check if this employee is already assigned to this shift
        existing_assignment = EmployeeShiftAssignment.objects.filter(
            employee=employee,
            shift=shift,
            is_active=True
        ).first()
        
        if existing_assignment:
            raise DRFValidationError({
                'non_field_errors': [
                    f'Employee {employee.get_full_name()} is already assigned to shift {shift.name}. '
                    f'Please remove the existing assignment first or select a different shift.'
                ]
            })
        
        # Check if employee is already assigned to any other active shift
        other_assignments = EmployeeShiftAssignment.objects.filter(
            employee=employee,
            is_active=True
        ).exclude(shift=shift)
        
        if other_assignments.exists():
            other_shift = other_assignments.first().shift
            raise DRFValidationError({
                'non_field_errors': [
                    f'Employee {employee.get_full_name()} is already assigned to shift {other_shift.name}. '
                    f'An employee can only be assigned to one shift at a time.'
                ]
            })
        
        serializer.save(assigned_by=user)
    
    @action(detail=False, methods=['post'], url_path='bulk-assign')
    def bulk_assign(self, request):
        """Bulk assign multiple employees to a shift"""
        try:
            data = request.data
            employee_ids = data.get('employees', [])
            shift_id = data.get('shift')
            
            if not employee_ids or not shift_id:
                return Response({
                    'error': True,
                    'message': 'Employees and shift are required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get the shift
            try:
                shift = Shift.objects.get(id=shift_id)
            except Shift.DoesNotExist:
                return Response({
                    'error': True,
                    'message': 'Shift not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get employees
            employees = CustomUser.objects.filter(id__in=employee_ids, role='employee')
            
            if not employees.exists():
                return Response({
                    'error': True,
                    'message': 'No valid employees found'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check for existing assignments
            existing_assignments = EmployeeShiftAssignment.objects.filter(
                employee__in=employees,
                is_active=True
            )
            
            if existing_assignments.exists():
                conflicting_employees = []
                for assignment in existing_assignments:
                    if assignment.shift == shift:
                        conflicting_employees.append(f"{assignment.employee.get_full_name()} (already assigned to this shift)")
                    else:
                        conflicting_employees.append(f"{assignment.employee.get_full_name()} (assigned to {assignment.shift.name})")
                
                return Response({
                    'error': True,
                    'message': 'Some employees are already assigned to shifts',
                    'conflicts': conflicting_employees
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Create assignments
            created_assignments = []
            for employee in employees:
                assignment = EmployeeShiftAssignment.objects.create(
                    employee=employee,
                    shift=shift,
                    assigned_by=request.user,
                    is_active=True
                )
                created_assignments.append(assignment)
            
            return Response({
                'success': True,
                'message': f'Successfully assigned {len(created_assignments)} employees to shift {shift.name}',
                'assignments': EmployeeShiftAssignmentSerializer(created_assignments, many=True).data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error in bulk assignment: {str(e)}")
            return Response({
                'error': True,
                'message': f'An error occurred: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
