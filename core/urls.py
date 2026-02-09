from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from .views import (
    OfficeViewSet,
    CustomUserViewSet,
    DeviceViewSet,
    DeviceUserViewSet,
    AttendanceViewSet,
    LeaveViewSet,
    DocumentViewSet,
    NotificationViewSet,
    SystemSettingsViewSet,
    AttendanceLogViewSet,
    DashboardViewSet,
    ZKTecoAttendanceViewSet,
    ReportsViewSet,
    ResignationViewSet,
    DepartmentViewSet,
    DesignationViewSet,
    debug_user_permissions,
    ShiftViewSet,
    EmployeeShiftAssignmentViewSet,
)
from .salary_views import (
    SalaryListView,
    SalaryDetailView,
    SalaryApprovalView,
    SalaryPaymentView,
    SalaryBulkCreateView,
    SalaryAutoCalculateView,
    SalaryTemplateListView,
    SalaryTemplateDetailView,
    SalaryReportView,
    SalarySummaryView,
    employee_salary_history,
    recalculate_salary,
    salary_statistics,
    salary_creation_status,
)
from .document_views import (
    DocumentTemplateViewSet,
    GeneratedDocumentViewSet,
    DocumentGenerationViewSet,
)
from coreapp.views import SalaryIncrementViewSet, SalaryIncrementHistoryViewSet
# ESSL views disabled - ZKTeco devices only
# from .essl_views import (
#     ESSLDeviceViewSet, ESSLAttendanceLogViewSet, WorkingHoursSettingsViewSet,
#     ESSLDeviceManagerView, UserRegistrationView, MonthlyAttendanceReportView,
#     GetAllUsersFromDevicesView, ExportUsersToCSVView
# )
from .push_views import (
    DevicePushDataView, receive_attendance_push, device_health_check
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'offices', OfficeViewSet)
router.register(r'users', CustomUserViewSet, basename='user')
router.register(r'devices', DeviceViewSet, basename='device')
router.register(r'device-users', DeviceUserViewSet, basename='device-user')
router.register(r'attendance', AttendanceViewSet, basename='attendance')
router.register(r'leaves', LeaveViewSet, basename='leave')
router.register(r'resignations', ResignationViewSet, basename='resignation')
router.register(r'documents', DocumentViewSet, basename='document')
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'settings', SystemSettingsViewSet)
router.register(r'attendance-logs', AttendanceLogViewSet, basename='attendance-log')
router.register(r'dashboard', DashboardViewSet, basename='dashboard')
router.register(r'zkteco-attendance', ZKTecoAttendanceViewSet, basename='zkteco-attendance')
router.register(r'reports', ReportsViewSet, basename='reports')
router.register(r'departments', DepartmentViewSet, basename='department')
router.register(r'designations', DesignationViewSet, basename='designation')
router.register(r'shifts', ShiftViewSet)
router.register(r'employee-shift-assignments', EmployeeShiftAssignmentViewSet)

# Document generation endpoints
router.register(r'document-templates', DocumentTemplateViewSet, basename='document-template')
router.register(r'generated-documents', GeneratedDocumentViewSet, basename='generated-document')
router.register(r'document-generation', DocumentGenerationViewSet, basename='document-generation')

# Salary increment endpoints (from coreapp)
router.register(r'salary-increments', SalaryIncrementViewSet, basename='salary-increment')
router.register(
    r'salary-increment-history',
    SalaryIncrementHistoryViewSet,
    basename='salary-increment-history',
)

# ESSL Device Management - DISABLED (ZKTeco devices only)
# router.register(r'essl-devices', ESSLDeviceViewSet, basename='essl-device')
# router.register(r'essl-attendance-logs', ESSLAttendanceLogViewSet, basename='essl-attendance-log')
# router.register(r'working-hours-settings', WorkingHoursSettingsViewSet, basename='working-hours-setting')

app_name = 'core'

urlpatterns = [
    # API endpoints
    path('api/', include(router.urls)),
    
    
    # JWT authentication endpoints
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    
    # Custom authentication endpoints
    path('api/auth/login/', CustomUserViewSet.as_view({'post': 'login'}), name='login'),
    path('api/auth/register/', CustomUserViewSet.as_view({'post': 'register'}), name='register'),
    path('api/auth/profile/', CustomUserViewSet.as_view({'get': 'profile', 'patch': 'update_profile'}), name='profile'),
    path('api/auth/profile/update/', CustomUserViewSet.as_view({'put': 'update_profile', 'patch': 'update_profile'}), name='update_profile'),
    path('api/auth/profile/upload_upi_qr/', CustomUserViewSet.as_view({'post': 'upload_upi_qr'}), name='upload_upi_qr'),
    path('api/auth/change-password/', CustomUserViewSet.as_view({'post': 'change_password'}), name='change_password'),
    path('api/auth/debug_auth/', CustomUserViewSet.as_view({'get': 'debug_auth'}), name='debug_auth'),
    
    # ESSL Device Management endpoints - DISABLED (ZKTeco devices only)
    # path('api/essl/device-manager/', ESSLDeviceManagerView.as_view(), name='essl-device-manager'),
    # path('api/essl/register-user/', UserRegistrationView.as_view(), name='register-user'),
    # path('api/essl/get-all-users/', GetAllUsersFromDevicesView.as_view(), name='get-all-users'),
    # path('api/essl/export-users-csv/', ExportUsersToCSVView.as_view(), name='export-users-csv'),
    # path('api/essl/monthly-report/', MonthlyAttendanceReportView.as_view(), name='monthly-report'),
    
    # Device Push Data endpoints (for receiving data from biometric devices)
    path('api/device/push-attendance/', DevicePushDataView.as_view(), name='device-push-attendance'),
    path('api/device/receive-attendance/', receive_attendance_push, name='receive-attendance-push'),
    path('api/device/health-check/', device_health_check, name='device-health-check'),
    
    # Salary Management endpoints
    path('api/salaries/', SalaryListView.as_view(), name='salary-list'),
    path('api/salaries/<uuid:pk>/', SalaryDetailView.as_view(), name='salary-detail'),
    path('api/salaries/<uuid:pk>/approve/', SalaryApprovalView.as_view(), name='salary-approval'),
    path('api/salaries/<uuid:pk>/payment/', SalaryPaymentView.as_view(), name='salary-payment'),
    path('api/salaries/bulk-create/', SalaryBulkCreateView.as_view(), name='salary-bulk-create'),
    path('api/salaries/auto-calculate/', SalaryAutoCalculateView.as_view(), name='salary-auto-calculate'),
    path('api/salaries/<uuid:salary_id>/recalculate/', recalculate_salary, name='salary-recalculate'),
    path('api/salaries/employee/<uuid:employee_id>/history/', employee_salary_history, name='employee-salary-history'),
    path('api/salaries/reports/', SalaryReportView.as_view(), name='salary-reports'),
    path('api/salaries/summary/', SalarySummaryView.as_view(), name='salary-summary'),
    path('api/salaries/statistics/', salary_statistics, name='salary-statistics'),
    path('api/salaries/creation-status/', salary_creation_status, name='salary-creation-status'),
    
    # Salary Template endpoints
    path('api/salary-templates/', SalaryTemplateListView.as_view(), name='salary-template-list'),
    path('api/salary-templates/<uuid:pk>/', SalaryTemplateDetailView.as_view(), name='salary-template-detail'),
    
    # Debug endpoint
    path('api/debug/user-permissions/', debug_user_permissions, name='debug-user-permissions'),
]
