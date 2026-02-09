"""
Views for receiving pushed attendance data from biometric devices
Only accepts data from devices that exist in the database
"""

from rest_framework import status, views
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.utils import timezone
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import JsonResponse, HttpResponse
import json
import logging
from datetime import datetime

from .models import Device, CustomUser, Attendance, ESSLAttendanceLog

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class DevicePushDataView(views.APIView):
    """
    API endpoint to receive pushed attendance data from biometric devices
    Only accepts data from devices that exist in the database
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """Handle GET requests - ESSL devices not supported"""
        try:
            logger.info(f"GET request from device: {request.META.get('REMOTE_ADDR', 'Unknown IP')}")
            logger.info(f"GET params: {request.GET}")
            
            # Reject ESSL getrequest.aspx requests
            if 'getrequest.aspx' in request.path:
                device_id = request.GET.get('SN', 'UNKNOWN')
                logger.warning(f"ESSL device {device_id} from IP {request.META.get('REMOTE_ADDR')} - ESSL not supported, access denied")
                return HttpResponse("ESSL devices not supported", status=403)
            
            # Handle health check
            return JsonResponse({
                'status': 'healthy',
                'message': 'Attendance server is running - ZKTeco devices only',
                'timestamp': timezone.now().isoformat(),
                'server_mode': 'ZKTECO_ONLY'
            })
            
        except Exception as e:
            logger.error(f"Error in GET request: {str(e)}")
            return HttpResponse("Access Denied", status=403)

    def head(self, request):
        """Handle HEAD requests"""
        try:
            logger.info(f"HEAD request from: {request.META.get('REMOTE_ADDR', 'Unknown IP')}")
            return HttpResponse("", status=200)
        except Exception as e:
            logger.error(f"Error in HEAD request: {str(e)}")
            return HttpResponse("", status=200)

    def post(self, request):
        """Receive pushed attendance data from devices"""
        try:
            # Log the incoming request
            logger.info(f"Received push data from device: {request.META.get('REMOTE_ADDR', 'Unknown IP')}")
            logger.info(f"Request content type: {request.content_type}")
            logger.info(f"Request GET params: {request.GET}")
            logger.info(f"Request body: {request.body}")

            # Extract device information
            device_ip = request.META.get('REMOTE_ADDR')
            device_id = None
            device_name = None

            # Reject ESSL devices sending text/plain
            if request.content_type == 'text/plain':
                device_id = request.GET.get('SN', 'UNKNOWN')
                table = request.GET.get('table', '')
                stamp = request.GET.get('Stamp') or request.GET.get('OpStamp', '')
                
                logger.warning(f"ESSL device {device_id} from IP {device_ip} sent {table} data with stamp {stamp} - ESSL not supported, access denied")
                return HttpResponse("ESSL devices not supported", status=403)

            # Handle JSON data
            elif request.content_type == 'application/json':
                data = request.data
                device_id = data.get('device_id') or data.get('deviceId') or data.get('SN')
                device_name = data.get('device_name') or data.get('deviceName')
                
                # Handle ZKTeco specific data format
                if device.device_type == 'zkteco':
                    logger.info(f"Processing ZKTeco push data from {device.name}")
                    # ZKTeco devices might send data in different formats
                    if 'attendance_records' not in data and 'records' not in data:
                        # Single record format
                        single_record = {
                            'user_id': data.get('user_id') or data.get('uid'),
                            'timestamp': data.get('timestamp') or data.get('punch_time'),
                            'type': data.get('type') or data.get('punch_type', 'check_in'),
                            'status': data.get('status', 0)
                        }
                        data['attendance_records'] = [single_record]
            else:
                # Try to parse as form data
                try:
                    from urllib.parse import parse_qs
                    parsed = parse_qs(request.body.decode('utf-8'))
                    data = {}
                    for key, value in parsed.items():
                        data[key] = value[0] if len(value) == 1 else value
                    device_id = data.get('device_id') or data.get('deviceId') or data.get('SN')
                    device_name = data.get('device_name') or data.get('deviceName')
                except:
                    data = {}

            # Check if device exists in database
            device = self._get_existing_device(device_ip, device_id)
            
            if not device:
                logger.warning(f"Unknown device {device_id} from IP {device_ip} - Access denied")
                return HttpResponse("Access Denied", status=403)
            
            # Only allow ZKTeco devices
            if device.device_type != 'zkteco':
                logger.warning(f"Non-ZKTeco device {device.name} (type: {device.device_type}) from IP {device_ip} - Only ZKTeco devices allowed, access denied")
                return HttpResponse("Only ZKTeco devices allowed", status=403)
            
            # Log device type for debugging
            logger.info(f"Processing data from {device.device_type} device: {device.name}")

            # Process attendance records
            attendance_records = data.get('attendance_records', [])
            if not attendance_records:
                attendance_records = data.get('records', [])
                if not attendance_records:
                    attendance_records = data.get('data', [])

            processed_count = 0
            error_count = 0

            for record in attendance_records:
                try:
                    if self._process_attendance_record(device, record):
                        processed_count += 1
                    else:
                        error_count += 1
                except Exception as e:
                    logger.error(f"Error processing attendance record: {str(e)}")
                    error_count += 1

            # Update device last sync time
            device.last_sync = timezone.now()
            device.save(update_fields=['last_sync'])

            logger.info(f"Processed {processed_count} records, {error_count} errors from device {device.name}")

            return Response({
                'success': True,
                'message': 'Attendance data received successfully',
                'processed_records': processed_count,
                'error_count': error_count,
                'device_id': device.id
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error processing pushed attendance data: {str(e)}")
            return HttpResponse("Access Denied", status=403)

    def _get_existing_device(self, device_ip, device_id):
        """Get existing device from database - NO AUTO CREATION"""
        try:
            device = None
            
            # For testing purposes, if IP is localhost, try to find by device_id first
            if device_ip in ['127.0.0.1', 'localhost', '::1'] and device_id:
                logger.info(f"Localhost request detected, searching by device_id: {device_id}")
                device = Device.objects.filter(device_id=device_id).first()
                if device:
                    logger.info(f"Found device by ID for localhost request: {device.name}")
                    return device
            
            # First try to find by IP address
            if not device:
                device = Device.objects.filter(ip_address=device_ip).first()
                logger.info(f"Searching for device with IP: {device_ip}")

            if not device and device_id:
                # Try to find by device ID
                device = Device.objects.filter(device_id=device_id).first()
                logger.info(f"Searching for device with ID: {device_id}")

            # If still not found, try case-insensitive search
            if not device and device_id:
                device = Device.objects.filter(device_id__iexact=device_id).first()
                logger.info(f"Case-insensitive search for device ID: {device_id}")

            # If still not found, try partial match
            if not device and device_id:
                device = Device.objects.filter(device_id__icontains=device_id).first()
                logger.info(f"Partial match search for device ID: {device_id}")

            if device:
                logger.info(f"Found existing device: {device.name} (IP: {device.ip_address}, ID: {device.device_id})")
                return device
            else:
                logger.warning(f"No existing device found for IP {device_ip} or ID {device_id}")
                # Log all devices for debugging
                all_devices = Device.objects.all()
                logger.info(f"Available devices: {[(d.name, d.ip_address, d.device_id) for d in all_devices]}")
                return None

        except Exception as e:
            logger.error(f"Error getting existing device: {str(e)}")
            return None

    def _process_attendance_record(self, device, record):
        """Process individual attendance record"""
        try:
            # Extract user information
            user_id = record.get('user_id') or record.get('userId') or record.get('employee_id')
            biometric_id = record.get('biometric_id') or record.get('biometricId')
            
            # For ZKTeco devices, also check for uid field
            if not user_id and not biometric_id:
                user_id = record.get('uid') or record.get('user_id')

            if not user_id and not biometric_id:
                logger.warning("No user ID or biometric ID found in record")
                return False

            # Find user - try multiple approaches for ZKTeco devices
            user = None
            if biometric_id:
                user = CustomUser.objects.filter(biometric_id=str(biometric_id)).first()
            if not user and user_id:
                # Try employee_id first
                user = CustomUser.objects.filter(employee_id=str(user_id)).first()
                # If not found, try biometric_id with the same value
                if not user:
                    user = CustomUser.objects.filter(biometric_id=str(user_id)).first()

            if not user:
                logger.warning(f"User not found for ID: {user_id or biometric_id}")
                return False

            # Extract timestamp
            timestamp_str = record.get('timestamp') or record.get('time') or record.get('datetime')
            if not timestamp_str:
                logger.warning("No timestamp found in record")
                return False

            # Parse timestamp
            try:
                if isinstance(timestamp_str, str):
                    for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S.%f']:
                        try:
                            timestamp = datetime.strptime(timestamp_str, fmt)
                            break
                        except ValueError:
                            continue
                    else:
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                else:
                    timestamp = timestamp_str

                if timezone.is_naive(timestamp):
                    timestamp = timezone.make_aware(timestamp, timezone.get_current_timezone())

            except Exception as e:
                logger.error(f"Error parsing timestamp {timestamp_str}: {str(e)}")
                return False

            # Extract attendance type
            attendance_type = record.get('type') or record.get('attendance_type') or 'check_in'

            # Get or create attendance record
            attendance, created = Attendance.objects.get_or_create(
                user=user,
                date=timestamp.date(),
                defaults={
                    'status': 'present',
                    'device': device
                }
            )

            # Update attendance record
            updated = False

            if attendance_type.lower() in ['check_in', 'checkin', 'in']:
                if not attendance.check_in_time or timestamp < attendance.check_in_time:
                    attendance.check_in_time = timestamp
                    updated = True
                    logger.info(f"Check-in: {user.get_full_name()} at {timestamp.strftime('%H:%M:%S')}")
            elif attendance_type.lower() in ['check_out', 'checkout', 'out']:
                if not attendance.check_out_time or timestamp > attendance.check_out_time:
                    attendance.check_out_time = timestamp
                    updated = True
                    logger.info(f"Check-out: {user.get_full_name()} at {timestamp.strftime('%H:%M:%S')}")
            else:
                # Auto-detect based on time
                if not attendance.check_in_time:
                    attendance.check_in_time = timestamp
                    updated = True
                    logger.info(f"Auto check-in: {user.get_full_name()} at {timestamp.strftime('%H:%M:%S')}")
                elif timestamp > attendance.check_in_time:
                    if not attendance.check_out_time or timestamp > attendance.check_out_time:
                        attendance.check_out_time = timestamp
                        updated = True
                        logger.info(f"Auto check-out: {user.get_full_name()} at {timestamp.strftime('%H:%M:%S')}")

            if updated:
                attendance.device = device
                attendance.save()

                # Log the attendance event
                ESSLAttendanceLog.objects.create(
                    device=device,
                    user=user,
                    timestamp=timestamp,
                    attendance_type=attendance_type,
                    raw_data=json.dumps(record)
                )

            return True

        except Exception as e:
            logger.error(f"Error processing attendance record: {str(e)}")
            return False

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def receive_attendance_push(request):
    """Simple function-based view for receiving pushed attendance data"""
    try:
        logger.info(f"Received push data from: {request.META.get('REMOTE_ADDR', 'Unknown IP')}")
        view = DevicePushDataView()
        return view.post(request)
    except Exception as e:
        logger.error(f"Error in receive_attendance_push: {str(e)}")
        return HttpResponse("Access Denied", status=403)

@csrf_exempt
@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def device_health_check(request):
    """Health check endpoint for devices"""
    if request.method == 'GET':
        return JsonResponse({
            'status': 'healthy',
            'message': 'Attendance server is running',
            'timestamp': timezone.now().isoformat(),
            'server_mode': 'ADMS'
        })
    elif request.method == 'POST':
        device_ip = request.META.get('REMOTE_ADDR')
        logger.info(f"Device health check from {device_ip}")
        return JsonResponse({
            'status': 'healthy',
            'message': 'Device health check received',
            'device_ip': device_ip,
            'timestamp': timezone.now().isoformat()
        })