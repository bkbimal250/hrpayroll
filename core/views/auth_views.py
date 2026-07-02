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
    CustomUserSerializer, CustomUserListSerializer, EmployeeSelfSerializer, ManagerEmployeeListSerializer,
    HREmployeeDetailSerializer, AdminEmployeeDetailSerializer, OfficeSerializer, DeviceSerializer, DeviceUserSerializer,
    DeviceUserCreateSerializer, DeviceUserMappingSerializer, DeviceUserBulkCreateSerializer,
    AttendanceSerializer, AttendanceCreateSerializer, BulkAttendanceSerializer, WorkingHoursSettingsSerializer,
    ESSLAttendanceLogSerializer, LeaveSerializer, LeaveListSerializer, LeaveCreateSerializer, LeaveApprovalSerializer,
    DocumentSerializer, DocumentListSerializer, DocumentCreateSerializer,
    NotificationSerializer, NotificationListSerializer, SystemSettingsSerializer,
    UserRegistrationSerializer, UserProfileSerializer, PasswordChangeSerializer,
    LoginUserResponseSerializer,
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
        if request.user.is_superuser or request.user.is_admin:
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

class OfficeViewSet(viewsets.ModelViewSet):
    """ViewSet for Office model"""
    queryset = Office.objects.all()
    serializer_class = OfficeSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'address', 'email']
    ordering_fields = ['name', 'created_at']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminOrHRNoDelete()]
        elif self.action in ['list', 'retrieve']:
            return [IsAdminOrManagerOrAccountantOrHR()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        """Get queryset based on user role"""
        user = self.request.user
        
        if user.is_admin or user.is_hr:
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
            'total_employees': CustomUser.objects.filter(office=office, role='employee', employment_status__in=['active', 'notice_period']).count(),
            'present_today': Attendance.objects.filter(
                user__office=office, 
                user__employment_status__in=['active', 'notice_period'],
                date=timezone.now().date(), 
                status='present'
            ).count(),
            'absent_today': Attendance.objects.filter(
                user__office=office, 
                user__employment_status__in=['active', 'notice_period'],
                date=timezone.now().date(), 
                status='absent'
            ).count(),
            'pending_leaves': Leave.objects.filter(
                user__office=office, 
                user__employment_status__in=['active', 'notice_period'],
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
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.OrderingFilter, DjangoFilterBackend]
    ordering_fields = ['username', 'first_name', 'last_name', 'created_at']
    filterset_class = CustomUserFilter
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_throttles(self):
        if self.action in ['login', 'register']:
            return [AuthLoginThrottle()]
        return super().get_throttles()

    def get_serializer_class(self):
        if self.action == 'list':
            if self.request.user.is_manager:
                return ManagerEmployeeListSerializer
            if self.request.user.is_employee:
                return EmployeeSelfSerializer
            if self.request.user.is_hr:
                return HREmployeeDetailSerializer
            if self.request.user.is_admin:
                return AdminEmployeeDetailSerializer
            return ManagerEmployeeListSerializer
        if self.action in ['retrieve', 'profile']:
            if self.request.user.is_employee:
                return EmployeeSelfSerializer
            if self.request.user.is_manager:
                return ManagerEmployeeListSerializer
            if self.request.user.is_hr:
                return HREmployeeDetailSerializer
            if self.request.user.is_admin:
                return AdminEmployeeDetailSerializer
        return CustomUserSerializer
    
    def get_queryset(self):
        user = self.request.user
        queryset = CustomUser.objects.select_related('office', 'department', 'designation')
        
        logger.info(f"CustomUserViewSet.get_queryset - User: {user.username}, Role: {user.role}, Is Manager: {user.is_manager}")
        logger.info(f"CustomUserViewSet.get_queryset - User office: {user.office}")
        
        if user.is_admin or user.is_hr:
            queryset = queryset.all()
            logger.info("CustomUserViewSet.get_queryset - Admin/HR: returning all users")
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
        
        if self.action == 'list':
            active_resignations = Resignation.objects.filter(
                user=OuterRef('pk'),
                status__in=['pending', 'approved']
            )
            latest_resignation_status = Resignation.objects.filter(
                user=OuterRef('pk')
            ).order_by('-created_at').values('status')[:1]

            queryset = queryset.annotate(
                has_active_resignation=Exists(active_resignations),
                latest_resignation_status=Subquery(latest_resignation_status),
            ).only(
                'id',
                'username',
                'email',
                'first_name',
                'last_name',
                'role',
                'employee_id',
                'biometric_id',
                'phone',
                'profile_picture',
                'office',
                'office__name',
                'department',
                'department__name',
                'designation',
                'designation__name',
                'joining_date',
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
            )

        logger.debug("CustomUserViewSet.get_queryset - Final queryset prepared")
        return queryset

    def get_permissions(self):
        if self.action in ['login', 'register']:
            return [permissions.AllowAny()]
        elif self.action in [
            'create', 'update', 'partial_update', 'destroy', 'mark_notice_period',
            'mark_resigned', 'mark_left', 'mark_terminated', 'suspend',
            'archive', 'restore'
        ]:
            return [IsAdminOrManagerOrHRNoDelete()]
        elif self.action in ['reset_password']:
            return [IsAdminOrManagerOrHR()]
        elif self.action in ['financial_details']:
            return [IsAdminOrHRNoDelete()]
        elif self.action in ['list', 'retrieve', 'by_status', 'all_search', 'full_history']:
            return [IsAdminOrManagerOrAccountantOrHR()]
        return [permissions.IsAuthenticated()]

    def _employee_history_counts(self, employee):
        """Return high-level history counts used to prevent accidental hard deletion."""
        return {
            'attendance': Attendance.objects.filter(user=employee).count(),
            'raw_biometric_logs': ESSLAttendanceLog.objects.filter(user=employee).count(),
            'leaves': Leave.objects.filter(user=employee).count(),
            'documents': Document.objects.filter(user=employee).count(),
            'generated_documents': GeneratedDocument.objects.filter(employee=employee).count(),
            'resignations': Resignation.objects.filter(user=employee).count(),
            'salaries': Salary.objects.filter(employee=employee).count(),
            'shift_assignments': EmployeeShiftAssignment.objects.filter(employee=employee).count(),
            'status_audit_logs': EmployeeStatusAuditLog.objects.filter(employee=employee).count(),
            'biometric_assignment_history': BiometricAssignmentHistory.objects.filter(employee=employee).count(),
            'password_change_history': PasswordChangeHistory.objects.filter(employee=employee).count(),
        }

    @action(detail=True, methods=['get'])
    def financial_details(self, request, pk=None):
        """Return unmasked bank details for HR/admin financial verification."""
        if not (request.user.is_superuser or request.user.is_admin or request.user.is_hr):
            return Response({'error': 'Admin or HR access required'}, status=status.HTTP_403_FORBIDDEN)

        employee = self.get_object()
        return Response({
            'id': str(employee.id),
            'account_holder_name': employee.account_holder_name or '',
            'bank_name': employee.bank_name or '',
            'account_number': employee.account_number or '',
            'ifsc_code': employee.ifsc_code or '',
            'bank_branch_name': employee.bank_branch_name or '',
            'bank_account_updated_at': employee.bank_account_updated_at,
        })

    def _change_employee_status(self, employee, new_status, request, **defaults):
        remarks = request.data.get('remarks') or request.data.get('reason') or request.data.get('status_change_remarks') or ''
        update_fields = dict(defaults)

        for date_field in ['resignation_date', 'last_working_date', 'exit_date']:
            if date_field in request.data:
                update_fields[date_field] = request.data.get(date_field) or None

        for text_field in ['exit_type', 'exit_reason', 'final_settlement_status']:
            if text_field in request.data:
                update_fields[text_field] = request.data.get(text_field) or ''

        if 'rehire_eligible' in request.data:
            update_fields['rehire_eligible'] = request.data.get('rehire_eligible')

        employee.set_employment_status(
            new_status,
            changed_by=request.user,
            remarks=remarks,
            **update_fields
        )
        serializer = CustomUserSerializer(employee, context={'request': request})
        return Response({
            'message': f'Employee status changed to {new_status}. History preserved.',
            'employee': serializer.data,
        })

    def destroy(self, request, *args, **kwargs):
        """Archive employees instead of permanently deleting linked HR history."""
        employee = self.get_object()
        employee.set_employment_status(
            'archived',
            changed_by=request.user,
            remarks=request.data.get('remarks', 'Archived through delete endpoint'),
            is_active=False,
            archived_at=timezone.now(),
            archived_by=request.user,
        )
        return Response({
            'message': 'Employee archived successfully, history preserved',
            'employee_id': str(employee.id),
            'history_counts': self._employee_history_counts(employee),
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def mark_notice_period(self, request, pk=None):
        employee = self.get_object()
        return self._change_employee_status(employee, 'notice_period', request, is_active=True)

    @action(detail=True, methods=['post'])
    def mark_resigned(self, request, pk=None):
        employee = self.get_object()
        return self._change_employee_status(employee, 'resigned', request)

    @action(detail=True, methods=['post'])
    def mark_left(self, request, pk=None):
        employee = self.get_object()
        return self._change_employee_status(
            employee,
            'left',
            request,
            is_active=False,
            exit_type=request.data.get('exit_type') or 'left',
        )

    @action(detail=True, methods=['post'])
    def mark_terminated(self, request, pk=None):
        employee = self.get_object()
        return self._change_employee_status(
            employee,
            'terminated',
            request,
            is_active=False,
            exit_type=request.data.get('exit_type') or 'terminated',
        )

    @action(detail=True, methods=['post'])
    def suspend(self, request, pk=None):
        employee = self.get_object()
        return self._change_employee_status(employee, 'suspended', request, is_active=False)

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        if request.user.is_hr:
            return Response({'error': 'HR users cannot archive employees'}, status=status.HTTP_403_FORBIDDEN)
        employee = self.get_object()
        return self._change_employee_status(
            employee,
            'archived',
            request,
            is_active=False,
            archived_at=timezone.now(),
            archived_by=request.user,
        )

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        employee = self.get_object()
        return self._change_employee_status(
            employee,
            'active',
            request,
            is_active=True,
            archived_at=None,
            archived_by=None,
            exit_type=None,
            exit_date=None,
        )

    @action(detail=True, methods=['post'])
    def reset_password(self, request, pk=None):
        """Privileged password reset for admin, HR, manager, or superuser users."""
        employee = self.get_object()
        actor = request.user

        if not (actor.is_superuser or actor.is_admin or actor.is_hr or actor.is_manager):
            return Response({'error': 'You do not have permission to reset passwords.'}, status=status.HTTP_403_FORBIDDEN)

        new_password = request.data.get('new_password') or request.data.get('password')
        confirm_password = request.data.get('confirm_password') or request.data.get('password_confirm') or new_password
        reason = (request.data.get('reason') or request.data.get('password_change_reason') or '').strip()

        if not new_password:
            return Response({'new_password': 'New password is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if new_password != confirm_password:
            return Response({'confirm_password': 'Passwords do not match.'}, status=status.HTTP_400_BAD_REQUEST)
        if not reason:
            return Response({'reason': 'Reason is required for password reset history.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_password(new_password, user=employee)
        except ValidationError as exc:
            return Response({'new_password': list(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)

        employee.set_password(new_password)
        employee.save(update_fields=['password', 'updated_at'])
        PasswordChangeHistory.objects.create(
            employee=employee,
            changed_by=actor,
            changed_by_role=getattr(actor, 'role', '') or ('superuser' if actor.is_superuser else ''),
            reason=reason,
        )

        return Response({
            'message': 'Password updated successfully. History preserved.',
            'employee_id': str(employee.id),
        })

    @action(detail=False, methods=['get'])
    def by_status(self, request):
        lifecycle_status = request.query_params.get('employment_status') or request.query_params.get('status')
        queryset = self.get_queryset()
        if lifecycle_status:
            queryset = queryset.filter(employment_status=lifecycle_status)
        page = self.paginate_queryset(queryset)
        serializer = CustomUserListSerializer(
            page if page is not None else queryset,
            many=True,
            context={'request': request},
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def all_search(self, request):
        queryset = self.get_queryset()
        search = request.query_params.get('search') or request.query_params.get('q')
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search) |
                Q(employee_id__icontains=search) |
                Q(biometric_id__icontains=search)
            )
        page = self.paginate_queryset(queryset)
        serializer = CustomUserListSerializer(
            page if page is not None else queryset,
            many=True,
            context={'request': request},
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def full_history(self, request, pk=None):
        employee = self.get_object()
        history = {
            'employee': CustomUserSerializer(employee, context={'request': request}).data,
            'counts': self._employee_history_counts(employee),
            'attendance': AttendanceSerializer(
                Attendance.objects.filter(user=employee).select_related('user', 'device')[:100],
                many=True,
                context={'request': request},
            ).data,
            'leaves': LeaveSerializer(
                Leave.objects.filter(user=employee).order_by('-created_at')[:100],
                many=True,
                context={'request': request},
            ).data,
            'documents': DocumentSerializer(
                Document.objects.filter(user=employee).order_by('-created_at')[:100],
                many=True,
                context={'request': request},
            ).data,
            'resignations': ResignationSerializer(
                Resignation.objects.filter(user=employee).order_by('-created_at'),
                many=True,
                context={'request': request},
            ).data,
            'salary_history_count': Salary.objects.filter(employee=employee).count(),
            'biometric_logs_count': ESSLAttendanceLog.objects.filter(user=employee).count(),
            'status_audit': EmployeeStatusAuditLogSerializer(
                EmployeeStatusAuditLog.objects.filter(employee=employee),
                many=True,
                context={'request': request},
            ).data,
            'biometric_assignment_history': BiometricAssignmentHistorySerializer(
                BiometricAssignmentHistory.objects.filter(employee=employee),
                many=True,
                context={'request': request},
            ).data,
            'password_change_history': PasswordChangeHistorySerializer(
                PasswordChangeHistory.objects.filter(employee=employee),
                many=True,
                context={'request': request},
            ).data,
        }
        return Response(history)

    @action(detail=False, methods=['get'])
    def user_stats(self, request):
        """Return per-employment-status counts for the current filtered queryset.

        Accepts the same query params as the list endpoint (search, department,
        office) so the HR dashboard lifecycle tab badges stay in sync with the
        active filters.
        """
        queryset = self.get_queryset()

        # Apply optional filters (mirrors CustomUserFilter behaviour)
        search = request.query_params.get('search') or request.query_params.get('q')
        if search:
            from django.db.models import Q as _Q
            queryset = queryset.filter(
                _Q(username__icontains=search) |
                _Q(first_name__icontains=search) |
                _Q(last_name__icontains=search) |
                _Q(email__icontains=search) |
                _Q(employee_id__icontains=search) |
                _Q(phone__icontains=search)
            )

        department = request.query_params.get('department')
        if department:
            queryset = queryset.filter(department_id=department)

        office = request.query_params.get('office')
        if office == 'null':
            queryset = queryset.filter(office__isnull=True)
        elif office:
            queryset = queryset.filter(office_id=office)

        statuses = ['active', 'notice_period', 'left', 'terminated', 'suspended', 'archived']
        grouped_counts = {
            item['employment_status']: item['total']
            for item in queryset.values('employment_status').annotate(total=Count('id'))
        }
        counts = {status_value: grouped_counts.get(status_value, 0) for status_value in statuses}
        counts['total'] = sum(grouped_counts.values())

        return Response({
            'totalUsers':        counts['total'],
            'activeUsers':       counts['active'],
            'noticePeriodUsers': counts['notice_period'],
            'leftUsers':         counts['left'],
            'terminatedUsers':   counts['terminated'],
            'suspendedUsers':    counts['suspended'],
            'archivedUsers':     counts['archived'],
        })

    @action(detail=False, methods=['post'])
    def register(self, request):
        """User registration endpoint"""
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = self._build_auth_refresh_token(user)
            response = Response({
                'user': self._auth_user_payload(user, request),
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_201_CREATED)
            set_refresh_cookie(response, str(refresh))
            log_auth_event("LOGIN_SUCCESS", request=request, user=user, action="register")
            return response
        log_auth_event("LOGIN_FAILED", request=request, action="register")
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
            elif dashboard_type == 'hr' and user.role != 'hr':
                return Response({
                    'error': 'Access denied. HR dashboard is only for HR users.'
                }, status=status.HTTP_403_FORBIDDEN)
            elif dashboard_type == 'employee' and user.role != 'employee':
                log_auth_event("LOGIN_FAILED", request=request, user=user, reason="dashboard_access_denied")
                return Response({
                    'error': 'Access denied. Employee dashboard is only for employee users.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            refresh = self._build_auth_refresh_token(user)
            response = Response({
                'user': self._auth_user_payload(user, request),
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            })
            set_refresh_cookie(response, str(refresh))
            log_auth_event("LOGIN_SUCCESS", request=request, user=user, dashboard_type=dashboard_type)
            return response
        log_auth_event("LOGIN_FAILED", request=request, username=request.data.get("username", ""))
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def _auth_user_payload(self, user, request):
        """Return only safe identity fields needed by dashboard shells."""
        return LoginUserResponseSerializer(user, context={'request': request}).data

    def _build_auth_refresh_token(self, user):
        """Create JWTs with small, non-sensitive user claims for frontend context."""
        refresh = RefreshToken.for_user(user)
        refresh['username'] = user.username
        refresh['employee_id'] = user.employee_id or ''
        refresh['full_name'] = user.get_full_name()
        refresh['role'] = user.role
        refresh['office'] = str(user.office_id) if user.office_id else ''
        refresh['office_name'] = user.office.name if user.office else ''
        refresh['department_name'] = user.department.name if user.department else ''
        refresh['designation_name'] = user.designation.name if user.designation else ''
        refresh['profile_picture_url'] = user.profile_picture.url if user.profile_picture else ''
        refresh['employment_status'] = user.employment_status
        refresh['is_active'] = user.is_active
        return refresh

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
        logger.info(
            "Profile update requested: user_id=%s authenticated=%s method=%s path=%s",
            request.user.id if request.user.is_authenticated else None,
            request.user.is_authenticated,
            request.method,
            request.path,
        )
        
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
                from ..notification_service import notify_bank_account_updated
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
                from ..notification_service import notify_bank_account_updated
                notify_bank_account_updated(instance, request.user, changed_fields)
        
        return response

    @action(detail=False, methods=['get'])
    def debug_auth(self, request):
        """Debug endpoint to test authentication. Admin-only and disabled in production."""
        from django.conf import settings

        if not request.user.is_authenticated or not request.user.is_admin:
            return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
        if getattr(settings, 'ENVIRONMENT', 'development') == 'production':
            return Response({'error': 'Debug endpoint is disabled in production'}, status=status.HTTP_404_NOT_FOUND)
        return Response({
            'authenticated': request.user.is_authenticated,
            'user_id': str(request.user.id) if request.user.is_authenticated else None,
            'username': request.user.username if request.user.is_authenticated else None,
            'role': request.user.role if request.user.is_authenticated else None,
            'has_auth_header': bool(request.headers.get('Authorization')),
        })

    @action(detail=False, methods=['get'])
    def updated_bank_accounts(self, request):
        """Get users with recently updated bank accounts"""
        from datetime import timedelta

        if not (request.user.is_admin or request.user.is_hr):
            return Response({'error': 'Admin or HR access required'}, status=status.HTTP_403_FORBIDDEN)
        
        # Get users updated in the last 30 days (configurable)
        days = int(request.query_params.get('days', 30))
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Filter by bank_account_updated_at field (more accurate)
        queryset = self.get_queryset().filter(
            bank_account_updated_at__gte=cutoff_date
        ).exclude(
            bank_account_updated_at__isnull=True
        ).order_by('-bank_account_updated_at')
        
        serializer_class = AdminEmployeeDetailSerializer if request.user.is_admin else HREmployeeDetailSerializer
        serializer = serializer_class(queryset, many=True, context={'request': request})
        return Response({
            'count': queryset.count(),
            'results': serializer.data
        })
    
    @action(detail=True, methods=['get'])
    def bank_account_history(self, request, pk=None):
        """Get bank account change history for a user"""
        from ..models import BankAccountHistory
        
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
