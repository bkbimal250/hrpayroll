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

class DocumentViewSet(viewsets.ModelViewSet):
    """ViewSet for Document model"""
    serializer_class = DocumentSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = DocumentFilter
    search_fields = ['title', 'description', 'user__first_name', 'user__last_name']
    ordering_fields = ['title', 'created_at']

    def get_queryset(self):
        user = self.request.user
        base_queryset = Document.objects.select_related(
            'user', 'user__office', 'user__department', 'user__designation', 'uploaded_by'
        )
        
        if user.is_admin or user.is_hr:
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
        if self.action in ['list', 'my']:
            return DocumentListSerializer
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

    def destroy(self, request, *args, **kwargs):
        if request.user.is_hr:
            return Response({'error': 'HR users cannot delete documents'}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)

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
        if not (user.is_manager or user.is_hr or user.is_admin):
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

        employees = CustomUser.objects.filter(role='employee', is_active=True)
        if user.is_manager:
            employees = employees.filter(office=user.office)
        employees = employees.values('id', 'first_name', 'last_name', 'employee_id', 'email')
        
        return Response({
            'employees': list(employees)
        })

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download a document file"""
        document = self.get_object()
        
        # Check if user has permission to download this document
        user = request.user
        if not (user.is_admin or user.is_manager or user.is_hr or document.user == user or document.uploaded_by == user):
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
