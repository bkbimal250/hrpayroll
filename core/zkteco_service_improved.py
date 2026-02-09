#!/usr/bin/env python3
"""
Improved ZKTeco Device Service using pyzk library
Handles real-time attendance data fetching from ZKTeco devices
"""

import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from django.utils import timezone
from django.conf import settings

try:
    from zk import ZK, const
    ZK_AVAILABLE = True
except ImportError:
    ZK_AVAILABLE = False
    logging.warning("pyzk library not available. Install with: pip install pyzk")

logger = logging.getLogger(__name__)

class ImprovedZKTecoDevice:
    """Improved ZKTeco device communication using pyzk library"""
    
    def __init__(self, ip_address: str, port: int = 4370, timeout: int = 10):
        self.ip_address = ip_address
        self.port = port
        self.timeout = timeout
        self.zk = None
        self.connected = False
        
    def connect(self) -> bool:
        """Connect to ZKTeco device using pyzk"""
        if not ZK_AVAILABLE:
            logger.error("pyzk library not available")
            return False
            
        try:
            self.zk = ZK(self.ip_address, port=self.port, timeout=self.timeout, force_udp=False, verbose=False)
            self.zk.connect()
            self.connected = True
            logger.info(f"Connected to ZKTeco device at {self.ip_address}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to ZKTeco device {self.ip_address}:{self.port} - {str(e)}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Disconnect from ZKTeco device"""
        if self.zk and self.connected:
            try:
                self.zk.disconnect()
                logger.info(f"Disconnected from ZKTeco device {self.ip_address}:{self.port}")
            except Exception as e:
                logger.warning(f"Error disconnecting from device {self.ip_address}:{self.port} - {str(e)}")
            finally:
                self.connected = False
                self.zk = None
    
    def get_device_info(self) -> Optional[Dict]:
        """Get device information"""
        if not self.connected or not self.zk:
            return None
            
        try:
            # Get device info
            info = self.zk.get_device_info()
            if info:
                return {
                    'ip_address': self.ip_address,
                    'port': self.port,
                    'status': 'online',
                    'device_name': getattr(info, 'device_name', 'Unknown'),
                    'firmware_version': getattr(info, 'firmware_version', 'Unknown'),
                    'serial_number': getattr(info, 'serial_number', 'Unknown'),
                    'platform': getattr(info, 'platform', 'Unknown'),
                    'fingerprint_algorithm': getattr(info, 'fingerprint_algorithm', 'Unknown'),
                    'face_algorithm': getattr(info, 'face_algorithm', 'Unknown'),
                    'device_function': getattr(info, 'device_function', 'Unknown')
                }
        except Exception as e:
            logger.error(f"Failed to get device info from {self.ip_address}:{self.port} - {str(e)}")
        
        return None
    
    def get_users(self) -> List[Dict]:
        """Get all users from device"""
        if not self.connected or not self.zk:
            return []
            
        users = []
        try:
            device_users = self.zk.get_users()
            for user in device_users:
                users.append({
                    'user_id': user.uid,
                    'name': user.name,
                    'privilege': user.privilege,
                    'password': user.password,
                    'group_id': user.group_id,
                    'fingerprint_count': len(user.fingerprints) if hasattr(user, 'fingerprints') else 0,
                    'face_count': len(user.faces) if hasattr(user, 'faces') else 0,
                    'card_number': user.card if hasattr(user, 'card') else None
                })
            logger.info(f"Retrieved {len(users)} users from device {self.ip_address}")
        except Exception as e:
            logger.error(f"Failed to get users from {self.ip_address}:{self.port} - {str(e)}")
        
        return users
    
    def get_attendance_data(self, start_date, end_date):
        """Get attendance data from device for a date range"""
        if not self.connected or not self.zk:
            return []
            
        try:
            # Get attendance logs from device
            attendance_logs = self.zk.get_attendance()
            
            # Filter logs within date range
            filtered_logs = []
            for log in attendance_logs:
                log_time = log.timestamp
                # Convert naive datetime to timezone-aware for comparison
                if timezone.is_naive(log_time):
                    log_time = timezone.make_aware(log_time, timezone.get_current_timezone())
                
                log_date = log_time.date()
                if start_date <= log_date <= end_date:
                    filtered_logs.append({
                        'user_id': log.user_id,
                        'timestamp': log.timestamp,
                        'punch_type': log.punch_type,
                        'status': log.status,
                        'uid': log.uid
                    })
            
            return filtered_logs
            
        except Exception as e:
            logger.error(f"Failed to get attendance data: {str(e)}")
            return []
    
    def get_attendance_logs(self, start_date: datetime = None, end_date: datetime = None) -> List[Dict]:
        """Get attendance logs from device"""
        if not self.connected or not self.zk:
            return []
            
        attendance_logs = []
        
        try:
            # Get all attendance logs
            logs = self.zk.get_attendance()
            
            # Filter by date range if provided
            if start_date or end_date:
                filtered_logs = []
                for log in logs:
                    log_time = log.timestamp
                    # Convert naive datetime to timezone-aware for comparison
                    if timezone.is_naive(log_time):
                        log_time = timezone.make_aware(log_time, timezone.get_current_timezone())
                    
                    if start_date and log_time < start_date:
                        continue
                    if end_date and log_time > end_date:
                        continue
                    filtered_logs.append(log)
                logs = filtered_logs
            
            # Convert to dictionary format
            for log in logs:
                attendance_logs.append({
                    'user_id': log.user_id,
                    'timestamp': int(log.timestamp.timestamp()),
                    'punch_time': log.timestamp,
                    'punch_type': 'in' if log.status == 0 else 'out',  # 0 = Check In, 1 = Check Out
                    'status': log.status,
                    'device_ip': self.ip_address,
                    'uid': log.uid
                })
            
            logger.info(f"Retrieved {len(attendance_logs)} attendance logs from device {self.ip_address}")
            
        except Exception as e:
            logger.error(f"Failed to get attendance logs from {self.ip_address}:{self.port} - {str(e)}")
        
        return attendance_logs
    
    def is_online(self) -> bool:
        """Check if device is online"""
        if not self.zk:
            return False
            
        try:
            # Try to get device info as a connectivity test
            info = self.zk.get_device_info()
            return info is not None
        except Exception as e:
            logger.debug(f"Device {self.ip_address} connectivity test failed: {str(e)}")
            return False

class ImprovedZKTecoService:
    """Improved service class for managing ZKTeco devices and attendance data"""
    
    def __init__(self):
        self.devices = {}
    
    def get_device(self, ip_address: str, port: int = 4370) -> Optional[ImprovedZKTecoDevice]:
        """Get or create device connection"""
        device_key = f"{ip_address}:{port}"
        
        if device_key not in self.devices:
            device = ImprovedZKTecoDevice(ip_address, port)
            if device.connect():
                self.devices[device_key] = device
            else:
                return None
        
        return self.devices[device_key]
    
    def test_device_connectivity(self, ip_address: str, port: int = 4370) -> bool:
        """Test if a device is reachable"""
        try:
            device = ImprovedZKTecoDevice(ip_address, port, timeout=5)
            if device.connect():
                device.disconnect()
                return True
            return False
        except Exception as e:
            logger.debug(f"Connectivity test failed for {ip_address}:{port} - {str(e)}")
            return False
    
    def fetch_attendance_from_device(self, device_ip: str, device_port: int = 4370, 
                                   start_date: datetime = None, end_date: datetime = None) -> List[Dict]:
        """Fetch attendance data from a specific device"""
        device = self.get_device(device_ip, device_port)
        if not device:
            logger.error(f"Failed to connect to device {device_ip}:{device_port}")
            return []
        
        try:
            # Get attendance logs
            attendance_logs = device.get_attendance_logs(start_date, end_date)
            logger.info(f"Fetched {len(attendance_logs)} attendance logs from {device_ip}")
            
            return attendance_logs
            
        except Exception as e:
            logger.error(f"Error fetching attendance from device {device_ip}: {str(e)}")
            return []
    
    def fetch_all_devices_attendance(self, devices: List[Dict], 
                                   start_date: datetime = None, end_date: datetime = None) -> Dict:
        """Fetch attendance from all devices"""
        all_attendance = {}
        
        for device_info in devices:
            device_ip = device_info.get('ip_address')
            device_port = device_info.get('port', 4370)
            device_name = device_info.get('name', f"Device_{device_ip}")
            
            if device_ip:
                logger.info(f"Fetching attendance from {device_name} ({device_ip}:{device_port})")
                attendance_logs = self.fetch_attendance_from_device(
                    device_ip, device_port, start_date, end_date
                )
                
                all_attendance[device_name] = {
                    'device_info': device_info,
                    'attendance_logs': attendance_logs,
                    'log_count': len(attendance_logs)
                }
        
        return all_attendance
    
    def get_device_status(self, devices: List[Dict]) -> Dict:
        """Get status of all devices"""
        device_status = []
        
        for device_info in devices:
            device_ip = device_info.get('ip_address')
            device_port = device_info.get('port', 4370)
            device_name = device_info.get('name', f"Device_{device_ip}")
            
            if device_ip:
                # Test connectivity
                is_online = self.test_device_connectivity(device_ip, device_port)
                
                status_info = {
                    'name': device_name,
                    'ip_address': device_ip,
                    'port': device_port,
                    'is_online': is_online,
                    'last_sync': None  # Will be updated from database
                }
                
                device_status.append(status_info)
        
        return {
            'devices': device_status,
            'total_devices': len(device_status),
            'online_devices': len([d for d in device_status if d['is_online']]),
            'offline_devices': len([d for d in device_status if not d['is_online']])
        }
    
    def process_attendance_for_user(self, user_biometric_id: str, attendance_logs: List[Dict]) -> List[Dict]:
        """Process attendance logs for a specific user"""
        user_logs = []
        
        for log in attendance_logs:
            if str(log.get('user_id')) == str(user_biometric_id):
                user_logs.append(log)
        
        # Sort by timestamp
        user_logs.sort(key=lambda x: x['timestamp'])
        
        return user_logs
    
    def sync_attendance_to_database(self, attendance_logs: List[Dict], device_info: Dict):
        """Sync attendance logs to database"""
        from core.models import ESSLAttendanceLog, CustomUser, Device
        
        synced_count = 0
        error_count = 0
        
        try:
            # Get device - only process if already registered in database
            try:
                device = Device.objects.get(
                    ip_address=device_info['ip_address'],
                    device_type='zkteco'
                )
                logger.info(f"Found registered ZKTeco device: {device.name} at {device.ip_address}")
            except Device.DoesNotExist:
                logger.warning(f"ZKTeco device at {device_info['ip_address']} not registered in database - skipping")
                return False
            
            # Process each attendance log
            for log in attendance_logs:
                try:
                    # Try to find user by biometric_id
                    user = None
                    try:
                        user = CustomUser.objects.get(biometric_id=log['user_id'])
                    except CustomUser.DoesNotExist:
                        # Try to find by employee_id
                        try:
                            user = CustomUser.objects.get(employee_id=str(log['user_id']))
                        except CustomUser.DoesNotExist:
                            logger.warning(f"User not found for biometric_id: {log['user_id']}")
                            error_count += 1
                            continue
                    
                    # Create or update attendance log
                    log_obj, created = ESSLAttendanceLog.objects.get_or_create(
                        user=user,
                        device=device,
                        timestamp=log['punch_time'],
                        defaults={
                            'punch_type': log['punch_type'],
                            'status': log.get('status', 0),
                            'uid': log.get('uid', 0)
                        }
                    )
                    
                    if created:
                        synced_count += 1
                        
                except Exception as e:
                    logger.error(f"Error processing attendance log: {str(e)}")
                    error_count += 1
            
            # Update device last sync time
            device.last_sync = timezone.now()
            device.save()
            
            logger.info(f"Synced {synced_count} attendance logs, {error_count} errors")
            
        except Exception as e:
            logger.error(f"Error syncing attendance to database: {str(e)}")
            error_count += len(attendance_logs)
        
        return synced_count, error_count
    
    def cleanup_connections(self):
        """Clean up all device connections"""
        for device_key, device in self.devices.items():
            try:
                device.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting device {device_key}: {str(e)}")
        
        self.devices.clear()

# Create global service instance
improved_zkteco_service = ImprovedZKTecoService()
