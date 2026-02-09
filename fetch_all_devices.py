#!/usr/bin/env python3
"""
Simple script to fetch attendance from all configured devices
"""

import os
import sys
import django
import logging
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'attendance_system.settings')
django.setup()

from core.models import Device, CustomUser, Attendance
from django.utils import timezone

# Configure logging without emojis to avoid encoding issues
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/fetch_all_devices.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

try:
    from zk import ZK
    ZK_AVAILABLE = True
except ImportError:
    ZK_AVAILABLE = False
    logger.warning("pyzk library not available. Install with: pip install pyzk")

def fetch_zkteco_device(device):
    """Fetch attendance from ZKTeco device"""
    if not ZK_AVAILABLE:
        logger.error(f"pyzk library not available for device {device.name}")
        return 0, 0
    
    conn = None
    try:
        logger.info(f"Connecting to ZKTeco device: {device.name} ({device.ip_address}:{device.port})")
        
        # Connect to device
        zk = ZK(device.ip_address, port=device.port, timeout=10, force_udp=False, verbose=False)
        conn = zk.connect()
        
        if not conn:
            logger.error(f"Failed to connect to device {device.name}")
            return 0, 0
        
        logger.info(f"Successfully connected to {device.name}")
        
        # Get attendance data
        attendance_logs = conn.get_attendance()
        if not attendance_logs:
            logger.info(f"No attendance data found on {device.name}")
            return 0, 0
        
        logger.info(f"Found {len(attendance_logs)} attendance records on {device.name}")
        
        # Process attendance records
        new_records = 0
        errors = 0
        
        for log in attendance_logs:
            try:
                # Find user by biometric ID
                user = CustomUser.objects.filter(biometric_id=str(log.user_id)).first()
                if not user:
                    logger.warning(f"User with biometric ID {log.user_id} not found")
                    errors += 1
                    continue
                
                # Make timestamp timezone-aware
                timestamp = log.timestamp
                if timezone.is_naive(timestamp):
                    timestamp = timezone.make_aware(timestamp, timezone.get_current_timezone())
                
                # Get or create attendance record
                attendance, created = Attendance.objects.get_or_create(
                    user=user,
                    date=timestamp.date(),
                    defaults={
                        'check_in_time': timestamp,
                        'status': 'present',
                        'device': device
                    }
                )
                
                if created:
                    logger.info(f"New attendance record: {user.get_full_name()} at {timestamp.strftime('%H:%M:%S')}")
                    new_records += 1
                else:
                    # Update existing record if needed
                    updated = False
                    if not attendance.check_in_time or timestamp < attendance.check_in_time:
                        attendance.check_in_time = timestamp
                        updated = True
                    if not attendance.check_out_time or timestamp > attendance.check_out_time:
                        attendance.check_out_time = timestamp
                        updated = True
                    
                    if updated:
                        attendance.device = device
                        attendance.save()
                        logger.info(f"Updated attendance: {user.get_full_name()} at {timestamp.strftime('%H:%M:%S')}")
                        new_records += 1
                        
            except Exception as e:
                logger.error(f"Error processing attendance record: {str(e)}")
                errors += 1
        
        logger.info(f"Device {device.name}: {new_records} new/updated records, {errors} errors")
        return new_records, errors
        
    except Exception as e:
        logger.error(f"Error fetching from ZKTeco device {device.name}: {str(e)}")
        return 0, 1
    finally:
        if conn:
            try:
                conn.disconnect()
                logger.info(f"Disconnected from {device.name}")
            except:
                pass

def fetch_essl_device(device):
    """Fetch attendance from ESSL device"""
    try:
        logger.info(f"Fetching from ESSL device: {device.name}")
        
        # Import ESSL service
        from core.essl_service import essl_service
        
        # Get attendance data from ESSL device
        attendance_data = essl_service.get_device_attendance(device)
        
        if not attendance_data:
            logger.info(f"No attendance data found on ESSL device {device.name}")
            return 0, 0
        
        logger.info(f"Found {len(attendance_data)} ESSL attendance records on {device.name}")
        
        new_records = 0
        errors = 0
        
        for record in attendance_data:
            try:
                # Find user by employee ID
                user = CustomUser.objects.filter(
                    employee_id=record.get('employee_id')
                ).first()
                
                if not user:
                    logger.warning(f"User with employee ID {record.get('employee_id')} not found")
                    errors += 1
                    continue
                
                # Parse timestamp
                timestamp_str = record.get('timestamp')
                if not timestamp_str:
                    continue
                
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    if timezone.is_naive(timestamp):
                        timestamp = timezone.make_aware(timestamp, timezone.get_current_timezone())
                except:
                    logger.error(f"Invalid timestamp format: {timestamp_str}")
                    errors += 1
                    continue
                
                # Get or create attendance record
                attendance, created = Attendance.objects.get_or_create(
                    user=user,
                    date=timestamp.date(),
                    defaults={
                        'check_in_time': timestamp,
                        'status': 'present',
                        'device': device
                    }
                )
                
                if created:
                    logger.info(f"New ESSL attendance: {user.get_full_name()} at {timestamp.strftime('%H:%M:%S')}")
                    new_records += 1
                else:
                    # Update existing record if needed
                    updated = False
                    if not attendance.check_in_time or timestamp < attendance.check_in_time:
                        attendance.check_in_time = timestamp
                        updated = True
                    if not attendance.check_out_time or timestamp > attendance.check_out_time:
                        attendance.check_out_time = timestamp
                        updated = True
                    
                    if updated:
                        attendance.device = device
                        attendance.save()
                        logger.info(f"Updated ESSL attendance: {user.get_full_name()} at {timestamp.strftime('%H:%M:%S')}")
                        new_records += 1
                        
            except Exception as e:
                logger.error(f"Error processing ESSL attendance record: {str(e)}")
                errors += 1
        
        logger.info(f"ESSL Device {device.name}: {new_records} new/updated records, {errors} errors")
        return new_records, errors
        
    except Exception as e:
        logger.error(f"Error fetching from ESSL device {device.name}: {str(e)}")
        return 0, 1

def fetch_all_devices():
    """Fetch attendance from all active devices"""
    logger.info("Starting attendance fetch from all devices...")
    
    # Get all active devices
    devices = Device.objects.filter(is_active=True)
    logger.info(f"Found {len(devices)} active devices")
    
    total_new_records = 0
    total_errors = 0
    
    for device in devices:
        logger.info(f"Processing device: {device.name} ({device.device_type})")
        
        if device.device_type == 'zkteco':
            new_records, errors = fetch_zkteco_device(device)
        elif device.device_type == 'essl':
            new_records, errors = fetch_essl_device(device)
        else:
            logger.warning(f"Unknown device type: {device.device_type} for device {device.name}")
            continue
        
        total_new_records += new_records
        total_errors += errors
        
        # Update device last sync time
        device.last_sync = timezone.now()
        device.save(update_fields=['last_sync'])
        
        logger.info(f"Completed device {device.name}: {new_records} records, {errors} errors")
        logger.info("-" * 50)
    
    logger.info(f"ATTENDANCE FETCH COMPLETED")
    logger.info(f"Total new/updated records: {total_new_records}")
    logger.info(f"Total errors: {total_errors}")
    logger.info(f"Devices processed: {len(devices)}")
    
    return total_new_records, total_errors

if __name__ == "__main__":
    print("=" * 60)
    print("EMPLOYEE ATTENDANCE SYSTEM - FETCH ALL DEVICES")
    print("=" * 60)
    
    try:
        new_records, errors = fetch_all_devices()
        print(f"\nSUCCESS: Fetched {new_records} attendance records with {errors} errors")
    except Exception as e:
        print(f"\nERROR: Failed to fetch attendance: {str(e)}")
        logger.error(f"Fatal error: {str(e)}")
    
    print("=" * 60)
