#!/usr/bin/env python3
"""
ZKTeco Push Service
Handles real-time attendance data pushing from ZKTeco devices
"""

import logging
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from django.utils import timezone
from django.db import transaction
from django.conf import settings

from .models import Device, CustomUser, Attendance, ESSLAttendanceLog

logger = logging.getLogger(__name__)

class ZKTecoPushService:
    """Service for handling ZKTeco device push data"""
    
    def __init__(self):
        self.active_devices = {}
        self.push_endpoints = {}
        
    def register_device_for_push(self, device: Device, push_url: str = None):
        """Register a ZKTeco device for push data"""
        if device.device_type != 'zkteco':
            logger.error(f"Device {device.name} is not a ZKTeco device")
            return False
            
        if not push_url:
            # Default push URL based on server configuration
            server_url = getattr(settings, 'SERVER_URL', 'http://localhost:8000')
            push_url = f"{server_url}/api/device/push-attendance/"
            
        self.push_endpoints[device.id] = {
            'device': device,
            'push_url': push_url,
            'last_push': None,
            'push_count': 0
        }
        
        logger.info(f"Registered ZKTeco device {device.name} for push data at {push_url}")
        return True
    
    def unregister_device(self, device_id):
        """Unregister a device from push service"""
        if device_id in self.push_endpoints:
            device_name = self.push_endpoints[device_id]['device'].name
            del self.push_endpoints[device_id]
            logger.info(f"Unregistered ZKTeco device {device_name} from push service")
            return True
        return False
    
    def get_registered_devices(self):
        """Get all registered devices"""
        return list(self.push_endpoints.values())
    
    def process_push_data(self, device: Device, attendance_data: List[Dict]) -> Dict:
        """Process pushed attendance data from ZKTeco device"""
        try:
            processed_count = 0
            error_count = 0
            
            logger.info(f"Processing {len(attendance_data)} attendance records from {device.name}")
            
            with transaction.atomic():
                for record in attendance_data:
                    try:
                        if self._process_single_record(device, record):
                            processed_count += 1
                        else:
                            error_count += 1
                    except Exception as e:
                        logger.error(f"Error processing record: {str(e)}")
                        error_count += 1
                
                # Update device last sync time
                device.last_sync = timezone.now()
                device.save(update_fields=['last_sync'])
                
                # Update push statistics
                if device.id in self.push_endpoints:
                    self.push_endpoints[device.id]['last_push'] = timezone.now()
                    self.push_endpoints[device.id]['push_count'] += 1
            
            result = {
                'success': True,
                'processed_count': processed_count,
                'error_count': error_count,
                'device_name': device.name,
                'timestamp': timezone.now().isoformat()
            }
            
            logger.info(f"Processed {processed_count} records, {error_count} errors from {device.name}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing push data from {device.name}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'device_name': device.name,
                'timestamp': timezone.now().isoformat()
            }
    
    def _process_single_record(self, device: Device, record: Dict) -> bool:
        """Process a single attendance record"""
        try:
            # Extract user information
            user_id = record.get('user_id') or record.get('uid') or record.get('employee_id')
            biometric_id = record.get('biometric_id') or record.get('biometricId')
            
            if not user_id and not biometric_id:
                logger.warning("No user ID or biometric ID found in record")
                return False
            
            # Find user
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
            timestamp_str = record.get('timestamp') or record.get('punch_time') or record.get('time')
            if not timestamp_str:
                logger.warning("No timestamp found in record")
                return False
            
            # Parse timestamp
            try:
                if isinstance(timestamp_str, str):
                    # Try different timestamp formats
                    for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S.%f']:
                        try:
                            timestamp = datetime.strptime(timestamp_str, fmt)
                            break
                        except ValueError:
                            continue
                    else:
                        # Try ISO format
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                else:
                    timestamp = timestamp_str
                
                # Make timezone-aware
                if timezone.is_naive(timestamp):
                    timestamp = timezone.make_aware(timestamp, timezone.get_current_timezone())
                    
            except Exception as e:
                logger.error(f"Error parsing timestamp {timestamp_str}: {str(e)}")
                return False
            
            # Extract attendance type
            attendance_type = record.get('type') or record.get('punch_type') or 'check_in'
            status = record.get('status', 0)
            
            # Determine check-in/check-out based on status or type
            if isinstance(status, int):
                punch_type = 'out' if status == 1 else 'in'
            else:
                punch_type = attendance_type.lower()
                if punch_type not in ['in', 'out', 'check_in', 'check_out']:
                    # Auto-detect based on time
                    punch_type = 'in' if timestamp.hour < 12 else 'out'
            
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
            
            if punch_type in ['in', 'check_in']:
                if not attendance.check_in_time or timestamp < attendance.check_in_time:
                    attendance.check_in_time = timestamp
                    updated = True
                    logger.info(f"Check-in: {user.get_full_name()} at {timestamp.strftime('%H:%M:%S')}")
            elif punch_type in ['out', 'check_out']:
                if not attendance.check_out_time or timestamp > attendance.check_out_time:
                    attendance.check_out_time = timestamp
                    updated = True
                    logger.info(f"Check-out: {user.get_full_name()} at {timestamp.strftime('%H:%M:%S')}")
            
            if updated:
                attendance.device = device
                attendance.save()
                
                # Log the attendance event
                ESSLAttendanceLog.objects.create(
                    device=device,
                    user=user,
                    timestamp=timestamp,
                    attendance_type=punch_type,
                    raw_data=json.dumps(record)
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing single record: {str(e)}")
            return False
    
    def get_device_push_status(self, device_id) -> Dict:
        """Get push status for a specific device"""
        if device_id not in self.push_endpoints:
            return {'registered': False}
        
        endpoint_info = self.push_endpoints[device_id]
        return {
            'registered': True,
            'device_name': endpoint_info['device'].name,
            'push_url': endpoint_info['push_url'],
            'last_push': endpoint_info['last_push'].isoformat() if endpoint_info['last_push'] else None,
            'push_count': endpoint_info['push_count']
        }
    
    def get_all_push_status(self) -> Dict:
        """Get push status for all registered devices"""
        status = {
            'total_devices': len(self.push_endpoints),
            'devices': {}
        }
        
        for device_id, endpoint_info in self.push_endpoints.items():
            status['devices'][str(device_id)] = {
                'device_name': endpoint_info['device'].name,
                'ip_address': endpoint_info['device'].ip_address,
                'push_url': endpoint_info['push_url'],
                'last_push': endpoint_info['last_push'].isoformat() if endpoint_info['last_push'] else None,
                'push_count': endpoint_info['push_count']
            }
        
        return status

# Global service instance
zkteco_push_service = ZKTecoPushService()
