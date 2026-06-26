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
    AttendanceAuditLog, DuplicatePunchAttempt, UnmatchedBiometricPunch, AsyncJob
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
from ..tasks import sync_zkteco_device_task, sync_all_zkteco_devices_task


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

class AttendanceViewSet(viewsets.ModelViewSet):
    """ViewSet for Attendance model"""
    serializer_class = AttendanceSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = AttendanceFilter
    search_fields = ['user__first_name', 'user__last_name', 'notes']
    ordering_fields = ['date', 'check_in_time', 'check_out_time']

    def get_queryset(self):
        user = self.request.user
        # Base queryset defaults to active/notice-period users, with opt-in historical inclusion.
        base_queryset = Attendance.objects.select_related('user', 'user__office', 'device')
        include_inactive = self.request.query_params.get('include_inactive') in ['true', '1', 'yes']
        employment_status = self.request.query_params.get('employment_status')
        if employment_status:
            base_queryset = base_queryset.filter(user__employment_status=employment_status)
        elif not include_inactive:
            base_queryset = base_queryset.filter(user__employment_status__in=['active', 'notice_period'])
        
        if user.is_admin or user.is_hr:
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
        holiday_records = queryset.filter(status='holiday').count()
        half_day_records = queryset.filter(day_status='half_day').count()
        complete_day_records = queryset.filter(day_status='complete_day').count()
        late_coming_records = queryset.filter(is_late=True).count()
        
        # Calculate distinct employees present
        present_employees = queryset.filter(status='present').values('user').distinct().count()
        
        # Calculate total active users for absence calculation
        # This considers the current office filter if applied
        user_queryset = CustomUser.objects.filter(employment_status__in=['active', 'notice_period'])
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
            'holiday_records': holiday_records,
            'half_day_records': half_day_records,
            'complete_day_records': complete_day_records,
            'late_coming_records': late_coming_records,
            'present_employees': present_employees,
            'total_active_users': total_active_users,
            'inferred_absent': inferred_absent,
            'attendance_percentage': (present_employees / total_active_users * 100) if total_active_users > 0 else 0
        })

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'bulk_create']:
            return [IsAdminOrManagerOrHRNoDelete()]
        elif self.action in ['list', 'retrieve']:
            return [IsAdminOrManagerOrAccountantOrHR()]
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
                user = CustomUser.objects.select_related(
                    'department', 'designation', 'designation__department', 'office'
                ).get(id=user_id, employment_status__in=['active', 'notice_period'])
            except CustomUser.DoesNotExist:
                return Response(
                    {'error': 'User not found or not eligible for operational attendance'},
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
            
            # Get holidays for the month
            from coreapp.models import Holiday
            holidays_in_month = Holiday.objects.filter(
                date__gte=first_day,
                date__lte=last_day
            )
            holiday_dict = {h.date: h.name for h in holidays_in_month}
            
            # Prepare monthly data with all days
            monthly_data = []
            
            for day in all_days:
                if day in attendance_dict:
                    # Existing attendance record
                    attendance = attendance_dict[day]
                    is_sunday = day.weekday() == 6

                    # Rule: Holiday date logic:
                    #   - Employee checked in on holiday → Present (use real attendance data)
                    #   - Employee did NOT check in on holiday → Holiday
                    if day in holiday_dict and not attendance.check_in_time:
                        monthly_data.append({
                            'id': str(attendance.id),
                            'date': day.isoformat(),
                            'check_in_time': None,
                            'check_out_time': None,
                            'total_hours': None,
                            'status': 'holiday',
                            'day_status': 'holiday',
                            'is_late': False,
                            'late_minutes': 0,
                            'device_name': None,
                            'notes': f"Holiday: {holiday_dict[day]}",
                            'created_at': attendance.created_at.isoformat() if attendance.created_at else None,
                            'updated_at': attendance.updated_at.isoformat() if attendance.updated_at else None,
                        })
                    # Rule: If the day is Sunday and the user is not present, treat as weekend
                    elif is_sunday and attendance.status not in ['present', 'half_day']:
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
                    elif day in holiday_dict:
                        # Holiday check
                        status = 'holiday'
                        day_status = 'holiday'
                        notes = f"Holiday: {holiday_dict[day]}"
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
            holiday_days = sum(1 for day in monthly_data if day['status'] == 'holiday')
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
                    'holiday_days': holiday_days,
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
            reason = request.data.get('reason') or request.data.get('remarks') or notes
            has_check_in_time = 'check_in_time' in request.data
            has_check_out_time = 'check_out_time' in request.data
            check_in_value = request.data.get('check_in_time')
            check_out_value = request.data.get('check_out_time')
            
            if not all([user_id, date_str, new_status]):
                return Response(
                    {'error': 'user_id, date, and status are required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if new_status not in ['present', 'absent', 'holiday', 'upcoming', 'weekend']:
                return Response(
                    {'error': 'Status must be either "present", "absent", "holiday", "upcoming", or "weekend"'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if new_day_status and new_day_status not in ['complete_day', 'half_day', 'absent', 'holiday', 'upcoming', 'weekend']:
                return Response(
                    {'error': 'Day status must be either "complete_day", "half_day", "absent", "holiday", "upcoming", or "weekend"'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                user = CustomUser.objects.get(id=user_id, employment_status__in=['active', 'notice_period'])
            except CustomUser.DoesNotExist:
                return Response(
                    {'error': 'User not found or not eligible for operational attendance'},
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

            def parse_attendance_time(value, field_name):
                if value in [None, '']:
                    return None

                value = str(value).strip()
                parsed_datetime = None

                try:
                    parsed_time = datetime.strptime(value, '%H:%M').time()
                    parsed_datetime = datetime.combine(target_date, parsed_time)
                except ValueError:
                    try:
                        parsed_time = datetime.strptime(value, '%H:%M:%S').time()
                        parsed_datetime = datetime.combine(target_date, parsed_time)
                    except ValueError:
                        try:
                            parsed_datetime = datetime.fromisoformat(value.replace('Z', '+00:00'))
                        except ValueError:
                            raise ValueError(f'Invalid {field_name} format. Use HH:MM.')

                if timezone.is_naive(parsed_datetime):
                    parsed_datetime = timezone.make_aware(parsed_datetime, timezone.get_current_timezone())

                return parsed_datetime

            try:
                parsed_check_in = parse_attendance_time(check_in_value, 'check_in_time') if has_check_in_time else None
                parsed_check_out = parse_attendance_time(check_out_value, 'check_out_time') if has_check_out_time else None
            except ValueError as exc:
                return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

            
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
                    'source': 'manual',
                    'manual_override': True,
                }
            )

            old_values = {
                'check_in': attendance.check_in_time,
                'check_out': attendance.check_out_time,
                'status': attendance.status,
                'day_status': attendance.day_status,
            }

            effective_check_in = parsed_check_in if has_check_in_time else attendance.check_in_time
            effective_check_out = parsed_check_out if has_check_out_time else attendance.check_out_time
            if effective_check_in and effective_check_out and effective_check_out < effective_check_in:
                return Response(
                    {'error': 'Check-out time cannot be earlier than check-in time'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if attendance.is_locked and not request.user.is_superuser:
                AttendanceAuditLog.objects.create(
                    attendance=attendance,
                    employee=attendance.user,
                    date=attendance.date,
                    old_check_in=old_values['check_in'],
                    new_check_in=attendance.check_in_time,
                    old_check_out=old_values['check_out'],
                    new_check_out=attendance.check_out_time,
                    old_status=old_values['status'],
                    new_status=attendance.status,
                    old_day_status=old_values['day_status'],
                    new_day_status=attendance.day_status,
                    change_type='locked_modification_attempt',
                    source='admin_correction',
                    was_locked=True,
                    changed_by=request.user,
                    reason=reason or 'Attempted manual update on locked payroll attendance.',
                )
                return Response(
                    {'error': 'Attendance is locked because payroll was generated for this month. Super admin permission and reason are required.'},
                    status=status.HTTP_403_FORBIDDEN
                )

            if attendance.is_locked and request.user.is_superuser and not reason:
                return Response(
                    {'error': 'Reason is required to modify locked attendance.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if has_check_in_time or has_check_out_time:
                if has_check_in_time:
                    attendance.check_in_time = parsed_check_in
                if has_check_out_time:
                    attendance.check_out_time = parsed_check_out

                attendance.source = 'admin_correction'
                attendance.manual_override = True
                attendance.notes = notes
                attendance.save()
            
            if not created:
                # Update existing record using manual method to bypass automatic calculations
                attendance.manual_update_status(
                    new_status=new_status,
                    new_day_status=new_day_status,
                    notes=notes,
                    source='admin_correction'
                )
            else:
                # For newly created records, also update using manual method to ensure consistency
                attendance.manual_update_status(
                    new_status=new_status,
                    new_day_status=new_day_status,
                    notes=notes,
                    source='manual'
                )

            AttendanceAuditLog.objects.create(
                attendance=attendance,
                employee=attendance.user,
                date=attendance.date,
                old_check_in=old_values['check_in'],
                new_check_in=attendance.check_in_time,
                old_check_out=old_values['check_out'],
                new_check_out=attendance.check_out_time,
                old_status=old_values['status'],
                new_status=attendance.status,
                old_day_status=old_values['day_status'],
                new_day_status=attendance.day_status,
                change_type='locked_modification' if attendance.is_locked else 'manual_update',
                source=attendance.source,
                was_locked=attendance.is_locked,
                changed_by=request.user,
                reason=reason,
            )
            
            # Return updated attendance data
            response_data = {
                'id': str(attendance.id),
                'date': attendance.date.isoformat(),
                'status': attendance.status,
                'day_status': attendance.day_status,
                'check_in_time': attendance.check_in_time.isoformat() if attendance.check_in_time else None,
                'check_out_time': attendance.check_out_time.isoformat() if attendance.check_out_time else None,
                'total_hours': float(attendance.total_hours) if attendance.total_hours is not None else None,
                'is_late': attendance.is_late,
                'late_minutes': attendance.late_minutes,
                'notes': attendance.notes,
                'updated_at': attendance.updated_at.isoformat(),
                'message': 'Attendance updated successfully'
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
    def unmatched_punches(self, request):
        """Review biometric punches that could not be mapped safely to an employee."""
        queryset = UnmatchedBiometricPunch.objects.select_related('device', 'resolved_user').all()
        review_status = request.query_params.get('review_status')
        if review_status:
            queryset = queryset.filter(review_status=review_status)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = UnmatchedBiometricPunchSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = UnmatchedBiometricPunchSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def duplicate_punches(self, request):
        """Review duplicate punch attempts ignored by final attendance processing."""
        queryset = DuplicatePunchAttempt.objects.select_related('device', 'existing_log').all()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = DuplicatePunchAttemptSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = DuplicatePunchAttemptSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def missing_checkout(self, request):
        """Attendance records that have check-in but no checkout and need review."""
        queryset = self.get_queryset().filter(check_in_time__isnull=False, check_out_time__isnull=True)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def locked_attempts(self, request):
        """Audit records for blocked edits on locked attendance."""
        queryset = AttendanceAuditLog.objects.select_related('attendance', 'employee', 'changed_by').filter(
            change_type='locked_modification_attempt'
        )
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = AttendanceAuditLogSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = AttendanceAuditLogSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def audit_history(self, request):
        """Manual/system attendance audit history with optional employee/date filters."""
        queryset = AttendanceAuditLog.objects.select_related('attendance', 'employee', 'changed_by').all()
        user_id = request.query_params.get('user_id')
        date_value = request.query_params.get('date')
        if user_id:
            queryset = queryset.filter(employee_id=user_id)
        if date_value:
            queryset = queryset.filter(date=date_value)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = AttendanceAuditLogSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = AttendanceAuditLogSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def unlock(self, request, pk=None):
        """Unlock a payroll-locked attendance record. Super admin only."""
        attendance = self.get_object()
        reason = request.data.get('reason') or request.data.get('remarks')
        if not request.user.is_superuser:
            return Response({'error': 'Only super admin can unlock attendance.'}, status=status.HTTP_403_FORBIDDEN)
        if not reason:
            return Response({'error': 'Reason is required to unlock attendance.'}, status=status.HTTP_400_BAD_REQUEST)

        AttendanceAuditLog.objects.create(
            attendance=attendance,
            employee=attendance.user,
            date=attendance.date,
            old_check_in=attendance.check_in_time,
            new_check_in=attendance.check_in_time,
            old_check_out=attendance.check_out_time,
            new_check_out=attendance.check_out_time,
            old_status=attendance.status,
            new_status=attendance.status,
            old_day_status=attendance.day_status,
            new_day_status=attendance.day_status,
            change_type='unlock',
            source='admin_correction',
            was_locked=attendance.is_locked,
            changed_by=request.user,
            reason=reason,
        )
        attendance.is_locked = False
        attendance.lock_reason = ''
        attendance.locked_at = None
        attendance.locked_by = None
        attendance.save(update_fields=['is_locked', 'lock_reason', 'locked_at', 'locked_by', 'updated_at'])
        return Response({'message': 'Attendance unlocked successfully.'})

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
                    employment_status__in=['active', 'notice_period']
                )
            else:
                # If no office specified, get users from manager's office
                if request.user.is_manager and request.user.office:
                    office_users = CustomUser.objects.filter(
                        office=request.user.office, 
                        role='employee', 
                        employment_status__in=['active', 'notice_period']
                    )
                else:
                    office_users = CustomUser.objects.filter(role='employee', employment_status__in=['active', 'notice_period'])
            
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

    def _enqueue_job(self, job_type, payload, task):
        job = AsyncJob.objects.create(
            job_type=job_type,
            requested_by=self.request.user,
            payload=payload,
        )
        async_result = task.delay(str(job.id))
        job.task_id = async_result.id
        job.save(update_fields=['task_id', 'updated_at'])
        return Response({
            'message': 'Request accepted and queued for background processing',
            'job_id': str(job.id),
            'task_id': async_result.id,
            'status': job.status,
        }, status=status.HTTP_202_ACCEPTED)
    
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

            if start_date:
                datetime.strptime(start_date, '%Y-%m-%d')
            if end_date:
                datetime.strptime(end_date, '%Y-%m-%d')

            payload = {
                'device_ip': device_ip,
                'device_port': device_port,
                'start_date': start_date,
                'end_date': end_date,
            }
            return self._enqueue_job('zkteco_sync_device', payload, sync_zkteco_device_task)
            
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
            devices = Device.objects.filter(
                device_type='zkteco',
                is_active=True
            )
            
            if not devices:
                return Response(
                    {'error': 'No active ZKTeco devices found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            start_date = request.data.get('start_date')
            end_date = request.data.get('end_date')
            
            if start_date:
                datetime.strptime(start_date, '%Y-%m-%d')
            if end_date:
                datetime.strptime(end_date, '%Y-%m-%d')

            payload = {'start_date': start_date, 'end_date': end_date}
            return self._enqueue_job('zkteco_sync_all_devices', payload, sync_all_zkteco_devices_task)
            
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
            devices = Device.objects.select_related('office').filter(
                device_type='zkteco',
                is_active=True
            )
            
            device_status = []
            for device in devices:
                is_online = device.device_status == 'online'
                status_info = {
                    'id': device.id,
                    'name': device.name,
                    'ip_address': device.ip_address,
                    'port': device.port,
                    'office': device.office.name if device.office else None,
                    'is_online': is_online,
                    'last_sync': device.last_sync.isoformat() if device.last_sync else None,
                    'connection_error': None if is_online else 'Last known device status is not online'
                }
                
                device_status.append(status_info)
            
            return Response({
                'devices': device_status,
                'total_devices': len(device_status),
                'online_devices': len([d for d in device_status if d['is_online']]),
                'offline_devices': len([d for d in device_status if not d['is_online']]),
                'source': 'cached_device_status'
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

    @action(detail=False, methods=['get'], url_path='jobs/(?P<job_id>[^/.]+)')
    def job_status(self, request, job_id=None):
        """Poll a background ZKTeco job."""
        job = get_object_or_404(AsyncJob, id=job_id)
        if not (request.user.is_admin or request.user.is_hr or request.user.is_manager or job.requested_by_id == request.user.id):
            return Response({'error': 'You do not have access to this job'}, status=status.HTTP_403_FORBIDDEN)
        return Response({
            'job_id': str(job.id),
            'job_type': job.job_type,
            'status': job.status,
            'task_id': job.task_id,
            'result': job.result,
            'error': job.error,
            'created_at': job.created_at,
            'started_at': job.started_at,
            'completed_at': job.completed_at,
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

class AttendanceLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for AttendanceLog model - Read only"""
    serializer_class = AttendanceLogSerializer
    permission_classes = [IsAdminOrManagerOrHR]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at']

    def get_queryset(self):
        user = self.request.user
        if user.is_admin or user.is_hr:
            return AttendanceLog.objects.all()
        elif user.is_manager:
            return AttendanceLog.objects.filter(attendance__user__office=user.office)
        else:
            return AttendanceLog.objects.none()


# Dashboard Views
