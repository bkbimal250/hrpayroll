#!/usr/bin/env python3
"""
ZKTeco Device Service
Handles real-time attendance data fetching from ZKTeco devices
"""

import socket
import struct
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from django.utils import timezone
from django.conf import settings
from django.db import close_old_connections

logger = logging.getLogger(__name__)

class ZKTecoDevice:
    """ZKTeco device communication class"""
    
    def __init__(self, ip_address: str, port: int = 4370, timeout: int = 5):
        self.ip_address = ip_address
        self.port = port
        self.timeout = timeout
        self.session_id = 0
        self.reply_id = 0
        self.socket = None
        
    def connect(self) -> bool:
        """Connect to ZKTeco device"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.ip_address, self.port))
            logger.info(f"Connected to ZKTeco device at {self.ip_address}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to ZKTeco device {self.ip_address}:{self.port} - {str(e)}")
            return False
    
    def disconnect(self):
        """Disconnect from ZKTeco device"""
        if self.socket:
            try:
                self.socket.close()
                logger.info(f"Disconnected from ZKTeco device {self.ip_address}:{self.port}")
            except:
                pass
            finally:
                self.socket = None
    
    def _create_command(self, command: int, data: bytes = b'') -> bytes:
        """Create ZKTeco command packet"""
        # ZKTeco protocol header
        header = struct.pack('<I', 0x5050827D)  # Magic number
        command_bytes = struct.pack('<H', command)
        checksum = struct.pack('<H', 0)
        session_id = struct.pack('<I', self.session_id)
        reply_id = struct.pack('<I', self.reply_id)
        
        # Calculate packet size
        packet_size = len(header) + len(command_bytes) + len(checksum) + len(session_id) + len(reply_id) + len(data)
        size_bytes = struct.pack('<I', packet_size)
        
        # Build packet
        packet = header + size_bytes + command_bytes + checksum + session_id + reply_id + data
        
        # Calculate checksum
        checksum_value = sum(packet) & 0xFFFF
        packet = packet[:8] + struct.pack('<H', checksum_value) + packet[10:]
        
        return packet
    
    def _send_command(self, command: int, data: bytes = b'') -> Optional[bytes]:
        """Send command to device and get response"""
        try:
            packet = self._create_command(command, data)
            self.socket.send(packet)
            
            # Receive response
            response = self.socket.recv(1024)
            if len(response) >= 8:
                # Parse response header
                magic = struct.unpack('<I', response[:4])[0]
                if magic == 0x5050827D:
                    return response
            return None
        except Exception as e:
            logger.error(f"Failed to send command to device: {str(e)}")
            return None
    
    def get_device_info(self) -> Optional[Dict]:
        """Get device information"""
        try:
            response = self._send_command(0x0001)  # Get device info command
            if response:
                # Parse device info from response
                # This is a simplified version - actual parsing depends on device model
                return {
                    'ip_address': self.ip_address,
                    'port': self.port,
                    'status': 'online',
                    'response_size': len(response)
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get device info: {str(e)}")
            return None
    
    def get_users(self) -> List[Dict]:
        """Get all users from device"""
        users = []
        try:
            # Get user count first
            response = self._send_command(0x0002)  # Get user count
            if response and len(response) >= 12:
                user_count = struct.unpack('<I', response[8:12])[0]
                logger.info(f"Found {user_count} users on device")
                
                # Get user data (simplified - actual implementation would iterate through users)
                for i in range(min(user_count, 100)):  # Limit to 100 users for safety
                    user_data = self._send_command(0x0003, struct.pack('<I', i))  # Get user data
                    if user_data and len(user_data) >= 16:
                        # Parse user data (simplified)
                        user_id = struct.unpack('<I', user_data[8:12])[0]
                        users.append({
                            'user_id': user_id,
                            'name': f"User_{user_id}",  # Simplified name
                            'privilege': 0,
                            'password': '',
                            'group_id': 0,
                            'fingerprint_count': 0
                        })
        except Exception as e:
            logger.error(f"Failed to get users: {str(e)}")
        
        return users
    
    def get_attendance_logs(self, start_date: datetime = None, end_date: datetime = None) -> List[Dict]:
        """Get attendance logs from device"""
        attendance_logs = []
        
        try:
            if not start_date:
                start_date = timezone.now() - timedelta(days=7)  # Default to last 7 days
            if not end_date:
                end_date = timezone.now()
            
            # Convert dates to device format
            start_timestamp = int(start_date.timestamp())
            end_timestamp = int(end_date.timestamp())
            
            # Get attendance logs
            data = struct.pack('<II', start_timestamp, end_timestamp)
            response = self._send_command(0x0004, data)  # Get attendance logs
            
            if response and len(response) >= 12:
                log_count = struct.unpack('<I', response[8:12])[0]
                logger.info(f"Found {log_count} attendance logs on device")
                
                # Parse attendance logs (simplified)
                offset = 12
                for i in range(min(log_count, 1000)):  # Limit to 1000 logs for safety
                    if offset + 16 <= len(response):
                        # Parse log entry (simplified structure)
                        user_id = struct.unpack('<I', response[offset:offset+4])[0]
                        timestamp = struct.unpack('<I', response[offset+4:offset+8])[0]
                        punch_type = struct.unpack('<B', response[offset+8:offset+9])[0]
                        
                        attendance_logs.append({
                            'user_id': user_id,
                            'timestamp': timestamp,
                            'punch_time': datetime.fromtimestamp(timestamp),
                            'punch_type': 'in' if punch_type == 0 else 'out',
                            'device_ip': self.ip_address
                        })
                        
                        offset += 16
                    else:
                        break
                        
        except Exception as e:
            logger.error(f"Failed to get attendance logs: {str(e)}")
        
        return attendance_logs

class ZKTecoService:
    """Service class for managing ZKTeco devices and attendance data"""
    
    def __init__(self):
        self.devices = {}
    
    def get_device(self, ip_address: str, port: int = 4370) -> Optional[ZKTecoDevice]:
        """Get or create device connection"""
        device_key = f"{ip_address}:{port}"
        
        if device_key not in self.devices:
            device = ZKTecoDevice(ip_address, port)
            if device.connect():
                self.devices[device_key] = device
            else:
                return None
        
        return self.devices[device_key]
    
    def fetch_attendance_from_device(self, device_ip: str, device_port: int = 4370, 
                                   start_date: datetime = None, end_date: datetime = None) -> List[Dict]:
        """Fetch attendance data from a specific device"""
        device = self.get_device(device_ip, device_port)
        if not device:
            logger.error(f"Failed to connect to device {device_ip}:{device_port}")
            return []
        
        try:
            # Get device info
            device_info = device.get_device_info()
            if not device_info:
                logger.error(f"Failed to get device info from {device_ip}")
                return []
            
            # Get attendance logs
            attendance_logs = device.get_attendance_logs(start_date, end_date)
            logger.info(f"Fetched {len(attendance_logs)} attendance logs from {device_ip}")
            
            return attendance_logs
            
        except Exception as e:
            logger.error(f"Error fetching attendance from device {device_ip}: {str(e)}")
            return []
        finally:
            # Don't disconnect here - keep connection for reuse
            pass
    
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
            # Close old connections before database operations
            close_old_connections()
            
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
            
            # Process logs in batches to reduce memory usage
            batch_size = 50
            for i in range(0, len(attendance_logs), batch_size):
                batch = attendance_logs[i:i + batch_size]
                
                for log in batch:
                    try:
                        # Find user by biometric ID
                        user = CustomUser.objects.filter(biometric_id=str(log['user_id'])).first()
                        
                        if user:
                            # Check if log already exists
                            existing_log = ESSLAttendanceLog.objects.filter(
                                device=device,
                                biometric_id=str(log['user_id']),
                                punch_time=log['punch_time']
                            ).first()
                            
                            if not existing_log:
                                # Create new attendance log
                                ESSLAttendanceLog.objects.create(
                                    device=device,
                                    biometric_id=str(log['user_id']),
                                    user=user,
                                    punch_time=log['punch_time'],
                                    punch_type=log['punch_type'],
                                    is_processed=False
                                )
                                synced_count += 1
                        else:
                            logger.warning(f"User with biometric ID {log['user_id']} not found")
                            
                    except Exception as e:
                        logger.error(f"Error processing attendance log: {str(e)}")
                        error_count += 1
                
                # Close connections after each batch
                close_old_connections()
            
            logger.info(f"Synced {synced_count} attendance logs, {error_count} errors")
            return synced_count, error_count
            
        except Exception as e:
            logger.error(f"Error syncing attendance to database: {str(e)}")
            return 0, len(attendance_logs)
        finally:
            # Always close connections
            close_old_connections()
    
    def cleanup_connections(self):
        """Clean up all device connections"""
        for device_key, device in self.devices.items():
            try:
                device.disconnect()
            except:
                pass
        
        self.devices.clear()
        logger.info("Cleaned up all device connections")

# Global service instance
zkteco_service = ZKTecoService()
