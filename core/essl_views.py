from rest_framework import status, viewsets, views
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db import transaction
from datetime import datetime, timedelta
import logging

from .models import Device, ESSLAttendanceLog, CustomUser, WorkingHoursSettings
from .serializers import (
    DeviceSerializer, ESSLAttendanceLogSerializer, 
    WorkingHoursSettingsSerializer, ESSLDeviceSyncSerializer,
    MonthlyAttendanceReportSerializer
)
from .essl_service import ESSLDeviceService, ESSLDeviceManager, AttendanceReportService

logger = logging.getLogger(__name__)


class ESSLDeviceViewSet(viewsets.ModelViewSet):
    """ViewSet for ESSL device management"""
    queryset = Device.objects.filter(device_type='essl')
    serializer_class = DeviceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter devices by user's office for managers"""
        user = self.request.user
        if user.role == 'manager' and user.office:
            return self.queryset.filter(office=user.office)
        elif user.role == 'admin':
            return self.queryset
        return Device.objects.none()
    
    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """Test connection to ESSL device"""
        try:
            device = self.get_object()
            service = ESSLDeviceService(device)
            is_connected = service.test_connection()
            
            return Response({
                'success': is_connected,
                'device_status': device.device_status,
                'message': 'Device is online' if is_connected else 'Device is offline'
            })
        except Exception as e:
            logger.error(f"Error testing device connection: {str(e)}")
            return Response({
                'success': False,
                'message': 'Error testing device connection'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def sync_attendance(self, request, pk=None):
        """Sync attendance data from ESSL device"""
        try:
            device = self.get_object()
            serializer = ESSLDeviceSyncSerializer(data=request.data)
            
            if serializer.is_valid():
                start_date = serializer.validated_data.get('start_date')
                end_date = serializer.validated_data.get('end_date')
                
                service = ESSLDeviceService(device)
                success = service.sync_attendance(start_date, end_date)
                
                return Response({
                    'success': success,
                    'message': 'Attendance synced successfully' if success else 'Failed to sync attendance',
                    'last_sync': device.last_attendance_sync
                })
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error syncing attendance: {str(e)}")
            return Response({
                'success': False,
                'message': 'Error syncing attendance'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def device_info(self, request, pk=None):
        """Get device information from ESSL device"""
        try:
            device = self.get_object()
            service = ESSLDeviceService(device)
            device_info = service.get_device_info()
            
            if device_info:
                return Response({
                    'success': True,
                    'device_info': device_info
                })
            else:
                return Response({
                    'success': False,
                    'message': 'Failed to get device information'
                })
                
        except Exception as e:
            logger.error(f"Error getting device info: {str(e)}")
            return Response({
                'success': False,
                'message': 'Error getting device information'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def user_list(self, request, pk=None):
        """Get list of users registered on the ESSL device"""
        try:
            device = self.get_object()
            service = ESSLDeviceService(device)
            user_list = service.get_user_list()
            
            if user_list:
                return Response({
                    'success': True,
                    'users': user_list
                })
            else:
                return Response({
                    'success': False,
                    'message': 'Failed to get user list'
                })
                
        except Exception as e:
            logger.error(f"Error getting user list: {str(e)}")
            return Response({
                'success': False,
                'message': 'Error getting user list'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def register_user(self, request, pk=None):
        """Register a user on the ESSL device"""
        try:
            device = self.get_object()
            user_id = request.data.get('user_id')
            
            if not user_id:
                return Response({
                    'success': False,
                    'message': 'User ID is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            user = CustomUser.objects.get(id=user_id)
            service = ESSLDeviceService(device)
            success = service.register_user(user)
            
            return Response({
                'success': success,
                'message': 'User registered successfully' if success else 'Failed to register user'
            })
            
        except CustomUser.DoesNotExist:
            return Response({
                'success': False,
                'message': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error registering user: {str(e)}")
            return Response({
                'success': False,
                'message': 'Error registering user'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ESSLAttendanceLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for ESSL attendance logs"""
    queryset = ESSLAttendanceLog.objects.all()
    serializer_class = ESSLAttendanceLogSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter logs by user's office for managers"""
        user = self.request.user
        if user.role == 'manager' and user.office:
            return self.queryset.filter(device__office=user.office)
        elif user.role == 'admin':
            return self.queryset
        return ESSLAttendanceLog.objects.none()
    
    @action(detail=False, methods=['get'])
    def unprocessed(self, request):
        """Get unprocessed attendance logs"""
        queryset = self.get_queryset().filter(is_processed=False)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def process_logs(self, request):
        """Process unprocessed attendance logs"""
        try:
            with transaction.atomic():
                unprocessed_logs = self.get_queryset().filter(is_processed=False)
                processed_count = 0
                
                for log in unprocessed_logs:
                    if log.user:
                        service = ESSLDeviceService(log.device)
                        service._process_user_attendance(log.user, log)
                        processed_count += 1
                
                return Response({
                    'success': True,
                    'processed_count': processed_count,
                    'message': f'Processed {processed_count} attendance logs'
                })
                
        except Exception as e:
            logger.error(f"Error processing attendance logs: {str(e)}")
            return Response({
                'success': False,
                'message': 'Error processing attendance logs'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class WorkingHoursSettingsViewSet(viewsets.ModelViewSet):
    """ViewSet for working hours settings"""
    queryset = WorkingHoursSettings.objects.all()
    serializer_class = WorkingHoursSettingsSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter settings by user's office for managers"""
        user = self.request.user
        if user.role == 'manager' and user.office:
            return self.queryset.filter(office=user.office)
        elif user.role == 'admin':
            return self.queryset
        return WorkingHoursSettings.objects.none()


class ESSLDeviceManagerView(views.APIView):
    """View for managing all ESSL devices"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get status of all ESSL devices"""
        try:
            status_list = ESSLDeviceManager.get_device_status()
            return Response({
                'success': True,
                'devices': status_list
            })
        except Exception as e:
            logger.error(f"Error getting device status: {str(e)}")
            return Response({
                'success': False,
                'message': 'Error getting device status'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request):
        """Sync all ESSL devices"""
        try:
            results = ESSLDeviceManager.sync_all_devices()
            success_count = sum(1 for result in results if result['success'])
            
            return Response({
                'success': True,
                'results': results,
                'success_count': success_count,
                'total_count': len(results),
                'message': f'Synced {success_count} out of {len(results)} devices'
            })
        except Exception as e:
            logger.error(f"Error syncing all devices: {str(e)}")
            return Response({
                'success': False,
                'message': 'Error syncing devices'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserRegistrationView(views.APIView):
    """View for registering users on ESSL devices"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Register a user on all ESSL devices in their office"""
        try:
            user_id = request.data.get('user_id')
            
            if not user_id:
                return Response({
                    'success': False,
                    'message': 'User ID is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            user = CustomUser.objects.get(id=user_id)
            
            if not user.biometric_id:
                return Response({
                    'success': False,
                    'message': 'User must have a biometric ID'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            results = ESSLDeviceManager.register_user_on_all_devices(user)
            success_count = sum(1 for result in results if result['success'])
            
            return Response({
                'success': True,
                'results': results,
                'success_count': success_count,
                'total_count': len(results),
                'message': f'Registered user on {success_count} out of {len(results)} devices'
            })
            
        except CustomUser.DoesNotExist:
            return Response({
                'success': False,
                'message': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error registering user: {str(e)}")
            return Response({
                'success': False,
                'message': 'Error registering user'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetAllUsersFromDevicesView(views.APIView):
    """View for getting all users from all ESSL devices"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get all users from all ESSL devices and auto-save to database"""
        try:
            # Check permissions
            user = request.user
            if user.role not in ['admin', 'manager']:
                return Response({
                    'success': False,
                    'message': 'Permission denied'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Get all users from all devices
            result = ESSLDeviceManager.get_all_users_from_all_devices()
            
            return Response({
                'success': True,
                'message': f'Retrieved users from {result["online_devices"]} out of {result["total_devices"]} devices. Total users: {result["total_users"]}',
                'data': result
            })
            
        except Exception as e:
            logger.error(f"Error getting users from devices: {str(e)}")
            return Response({
                'success': False,
                'message': 'Error getting users from devices'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ExportUsersToCSVView(views.APIView):
    """View for exporting users from ESSL devices to CSV files"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Export users from all ESSL devices to CSV files"""
        try:
            # Check permissions
            user = request.user
            if user.role not in ['admin', 'manager']:
                return Response({
                    'success': False,
                    'message': 'Permission denied'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Get export parameters
            output_dir = request.data.get('output_dir', 'exports')
            force_export = request.data.get('force', False)
            
            # Import and run the management command
            from django.core.management import call_command
            from io import StringIO
            from django.test.utils import override_settings
            
            # Capture command output
            out = StringIO()
            
            try:
                call_command(
                    'export_users_to_csv',
                    output_dir=output_dir,
                    force=force_export,
                    stdout=out
                )
                
                output = out.getvalue()
                
                return Response({
                    'success': True,
                    'message': 'Users exported to CSV files successfully',
                    'output': output,
                    'output_dir': output_dir
                })
                
            except Exception as cmd_error:
                logger.error(f"Error running export command: {str(cmd_error)}")
                return Response({
                    'success': False,
                    'message': f'Error exporting users: {str(cmd_error)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            logger.error(f"Error in CSV export view: {str(e)}")
            return Response({
                'success': False,
                'message': 'Error exporting users to CSV'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MonthlyAttendanceReportView(views.APIView):
    """View for generating monthly attendance reports"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Generate monthly attendance report"""
        try:
            serializer = MonthlyAttendanceReportSerializer(data=request.data)
            
            if serializer.is_valid():
                office_id = serializer.validated_data.get('office_id')
                year = serializer.validated_data.get('year')
                month = serializer.validated_data.get('month')
                
                # Check permissions
                user = request.user
                if user.role == 'manager' and user.office:
                    office_id = user.office.id
                elif user.role != 'admin':
                    return Response({
                        'success': False,
                        'message': 'Permission denied'
                    }, status=status.HTTP_403_FORBIDDEN)
                
                report_data = AttendanceReportService.get_monthly_attendance_report(
                    office_id=office_id,
                    year=year,
                    month=month
                )
                
                return Response({
                    'success': True,
                    'report': report_data
                })
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error generating monthly report: {str(e)}")
            return Response({
                'success': False,
                'message': 'Error generating report'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get(self, request):
        """Get current month's attendance report"""
        try:
            current_date = timezone.now()
            user = request.user
            
            # Check permissions
            office_id = None
            if user.role == 'manager' and user.office:
                office_id = user.office.id
            elif user.role != 'admin':
                return Response({
                    'success': False,
                    'message': 'Permission denied'
                }, status=status.HTTP_403_FORBIDDEN)
            
            report_data = AttendanceReportService.get_monthly_attendance_report(
                office_id=office_id,
                year=current_date.year,
                month=current_date.month
            )
            
            return Response({
                'success': True,
                'report': report_data
            })
            
        except Exception as e:
            logger.error(f"Error getting current month report: {str(e)}")
            return Response({
                'success': False,
                'message': 'Error getting report'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
