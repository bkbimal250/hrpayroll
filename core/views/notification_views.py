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
        
        if self.request.user.is_hr:
            queryset = Notification.objects.all()
        else:
            queryset = Notification.objects.filter(user=self.request.user)
        queryset = queryset.select_related('user', 'created_by')
        
        # Filter out expired notifications
        queryset = queryset.filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
        )
        
        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return NotificationListSerializer
        return NotificationSerializer

    def get_permissions(self):
        """Set permissions based on action"""
        if self.action in ['list', 'retrieve', 'mark_read', 'mark_all_read', 'unread_count']:
            permission_classes = [IsAuthenticated]
        elif self.action == 'destroy':
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAdminOrManagerOrAccountantOrHR]
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
        queryset = Notification.objects.filter(is_read=False)
        if not request.user.is_hr:
            queryset = queryset.filter(user=request.user)
        count = queryset.count()
        return Response({'unread_count': count})

    def destroy(self, request, pk=None):
        """Delete a notification"""
        if request.user.is_hr:
            return Response({'error': 'HR users cannot delete notifications'}, status=status.HTTP_403_FORBIDDEN)
        from .notification_service import NotificationService
        
        success = NotificationService.delete_notification(pk, request.user)
        if success:
            return Response({'message': 'Notification deleted'})
        return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'])
    def delete_expired(self, request):
        """Delete expired notifications"""
        if request.user.is_hr:
            return Response({'error': 'HR users cannot delete notifications'}, status=status.HTTP_403_FORBIDDEN)
        from .notification_service import NotificationService
        
        deleted_count = NotificationService.delete_expired_notifications()
        return Response({
            'message': f'{deleted_count} expired notifications deleted'
        })

    @action(detail=False, methods=['post'])
    def cleanup_old(self, request):
        """Clean up old notifications (admin only)"""
        if request.user.is_hr:
            return Response({'error': 'HR users cannot delete notifications'}, status=status.HTTP_403_FORBIDDEN)
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
        from ..models import Office
        
        offices = Office.objects.all().values('id', 'name')
        roles = CustomUser.objects.values_list('role', flat=True).distinct()
        
        return Response({
            'offices': list(offices),
            'roles': list(roles),
            'role_choices': [
                {'value': 'admin', 'label': 'Admin'},
                {'value': 'hr', 'label': 'HR'},
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
