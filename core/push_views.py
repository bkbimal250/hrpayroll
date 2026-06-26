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
from json import JSONDecodeError

from .attendance_processing import record_raw_punch
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

            data = {}

            # Handle JSON data
            if request.content_type == 'application/json':
                try:
                    data = request.data if isinstance(request.data, dict) else {}
                except (JSONDecodeError, ValueError) as exc:
                    logger.warning("Malformed JSON from device IP %s: %s", device_ip, exc)
                    return Response({
                        'success': False,
                        'error': 'malformed_json',
                        'message': 'Request body must be valid JSON.'
                    }, status=status.HTTP_400_BAD_REQUEST)
                device_id = data.get('device_id') or data.get('deviceId') or data.get('SN')
                device_name = data.get('device_name') or data.get('deviceName')
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
                except Exception as exc:
                    logger.warning("Unable to parse device payload from IP %s: %s", device_ip, exc)
                    data = {}

            # Check if device exists in database
            device = self._get_existing_device(device_ip, device_id)
            
            if not device:
                logger.warning(f"Unknown device {device_id} from IP {device_ip} - Access denied")
                return Response({
                    'success': False,
                    'error': 'unknown_device',
                    'message': 'Device is not registered or is not allowed.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Only allow ZKTeco devices
            if device.device_type != 'zkteco':
                logger.warning(f"Non-ZKTeco device {device.name} (type: {device.device_type}) from IP {device_ip} - Only ZKTeco devices allowed, access denied")
                return Response({
                    'success': False,
                    'error': 'unsupported_device',
                    'message': 'Only registered ZKTeco devices are allowed.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Log device type for debugging
            logger.info(f"Processing data from {device.device_type} device: {device.name}")

            # ZKTeco devices might send a single JSON record instead of a list.
            if request.content_type == 'application/json' and 'attendance_records' not in data and 'records' not in data and 'data' not in data:
                data['attendance_records'] = [{
                    'user_id': data.get('user_id') or data.get('uid'),
                    'biometric_id': data.get('biometric_id') or data.get('biometricId'),
                    'timestamp': data.get('timestamp') or data.get('punch_time'),
                    'type': data.get('type') or data.get('punch_type', 'check_in'),
                    'status': data.get('status', 0)
                }]

            # Process attendance records
            attendance_records = data.get('attendance_records', [])
            if not attendance_records:
                attendance_records = data.get('records', [])
                if not attendance_records:
                    attendance_records = data.get('data', [])
            if isinstance(attendance_records, dict):
                attendance_records = [attendance_records]
            if not isinstance(attendance_records, list):
                return Response({
                    'success': False,
                    'error': 'invalid_records',
                    'message': 'Attendance records must be a list or object.'
                }, status=status.HTTP_400_BAD_REQUEST)

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
            logger.exception("Error processing pushed attendance data")
            return Response({
                'success': False,
                'error': 'ingest_failed',
                'message': 'Attendance data could not be processed.'
            }, status=status.HTTP_400_BAD_REQUEST)

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
            biometric_value = biometric_id or user_id
            raw_log, created, result = record_raw_punch(
                device=device,
                biometric_id=biometric_value,
                device_user_id=user_id or biometric_value,
                employee_id=user_id,
                punch_time=timestamp,
                punch_type=attendance_type,
                source='zkteco_push',
                raw_payload=record,
            )
            if result == 'unmatched':
                logger.warning(f"Unmatched ZKTeco push punch for ID: {user_id or biometric_id}")
            return result in ['processed', 'duplicate', 'unmatched']

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
