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
        
        if user.is_admin or user.is_hr:
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
        elif self.action in ['update', 'partial_update']:
            return ResignationAdminUpdateSerializer
        elif self.action in ['approve', 'reject']:
            return ResignationApprovalSerializer
        return ResignationSerializer

    def get_permissions(self):
        """Set permissions based on action"""
        if self.action in ['create']:
            # Only employees can create resignation requests
            permission_classes = [IsAuthenticated]
        elif self.action in ['approve', 'reject', 'update', 'partial_update']:
            # Only admin and manager can approve/reject
            permission_classes = [IsAdminOrManagerOrHR]
        elif self.action in ['destroy']:
            permission_classes = [IsAdminOrManager]
        else:
            # Default permissions
            permission_classes = [IsAuthenticated]
        
        return [permission() for permission in permission_classes]

    def perform_update(self, serializer):
        """Allow privileged users to edit resignation records and keep employee dates in sync."""
        resignation = serializer.save()
        if resignation.status in ['pending', 'approved']:
            resignation.user.set_employment_status(
                'notice_period',
                changed_by=self.request.user,
                remarks='Resignation updated',
                is_active=True,
                resignation_date=resignation.resignation_date,
                last_working_date=resignation.last_working_date,
                exit_type='resigned',
            )

    def update(self, request, *args, **kwargs):
        """Update privileged editable fields and return the full resignation record."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        instance.refresh_from_db()
        return Response(ResignationSerializer(instance).data)

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

        resignation.user.set_employment_status(
            'notice_period',
            changed_by=request.user,
            remarks='Resignation submitted',
            is_active=True,
            resignation_date=resignation.resignation_date,
            last_working_date=resignation.last_working_date,
            exit_type='resigned',
        )
        
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

        resignation.user.set_employment_status(
            'notice_period',
            changed_by=request.user,
            remarks='Resignation approved',
            is_active=True,
            resignation_date=resignation.resignation_date,
            last_working_date=resignation.last_working_date,
            exit_type='resigned',
        )
        
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

        if not Resignation.objects.filter(user=resignation.user, status__in=['pending', 'approved']).exclude(id=resignation.id).exists():
            resignation.user.set_employment_status(
                'active',
                changed_by=request.user,
                remarks='Resignation rejected',
            )
        
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
        """Cancel a resignation request.

        Employees can cancel their own pending request. Admin, manager, and HR can
        cancel pending or approved resignations visible to them.
        """
        resignation = self.get_object()
        is_privileged_user = request.user.is_admin or request.user.is_manager or request.user.is_hr
        
        if not is_privileged_user and resignation.user != request.user:
            return Response({
                'error': 'You can only cancel your own resignation requests'
            }, status=status.HTTP_403_FORBIDDEN)
        
        allowed_statuses = ['pending', 'approved'] if is_privileged_user else ['pending']
        if resignation.status not in allowed_statuses:
            return Response({
                'error': 'Only pending or approved resignations can be cancelled by admin, manager, or HR'
                if is_privileged_user
                else 'Only pending resignations can be cancelled by the employee'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        resignation.status = 'cancelled'
        cancellation_reason = request.data.get('cancellation_reason') or request.data.get('rejection_reason') or ''
        if cancellation_reason:
            resignation.rejection_reason = cancellation_reason
        if is_privileged_user:
            resignation.approved_by = request.user
            resignation.approved_at = timezone.now()
        resignation.save()

        if not Resignation.objects.filter(user=resignation.user, status__in=['pending', 'approved']).exclude(id=resignation.id).exists():
            resignation.user.set_employment_status(
                'active',
                changed_by=request.user,
                remarks='Resignation cancelled',
                resignation_date=None,
                last_working_date=None,
                exit_type=None,
            )
        
        try:
            from .consumers import broadcast_resignation_update_sync
            resignation_data = ResignationSerializer(resignation).data
            broadcast_resignation_update_sync(resignation_data)
        except Exception as e:
            print(f"Error broadcasting resignation update: {e}")
        
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
        if user.is_admin or user.is_hr:
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
                Q(role__in=['admin', 'hr'])
            ).distinct()
        else:
            # Notify all admins if user has no office
            managers = CustomUser.objects.filter(role__in=['admin', 'hr'])
        
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
            return [IsAdminOrManagerOrHRNoDelete()]
        elif self.action in ['list', 'retrieve']:
            return [IsAdminOrManagerOrAccountantOrHR()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        """Get queryset based on user role"""
        user = self.request.user
        
        if user.is_admin or user.is_hr:
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
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'bulk_assign']:
            return [IsAdminOrManagerOrHRNoDelete()]
        elif self.action in ['list', 'retrieve']:
            return [IsAdminOrManagerOrAccountantOrHR()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        """Get queryset based on user role"""
        user = self.request.user
        
        if user.is_admin or user.is_hr:
            # Admin can see all assignments
            queryset = EmployeeShiftAssignment.objects.all()
            logger.info(f"EmployeeShiftAssignmentViewSet - Admin/HR: returning {queryset.count()} assignments")
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
