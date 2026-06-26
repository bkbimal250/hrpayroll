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
