#!/usr/bin/env python3
"""
Django Management Command: Map Device Users and Fetch Attendance
Maps users from ZKTeco devices to system users and fetches attendance data
"""

import os
import sys
import django
import logging
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional, Tuple

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.contrib.auth.hashers import make_password
from django.utils import timezone

from core.models import Device, DeviceUser, CustomUser, Attendance, ESSLAttendanceLog, Office, Department, Designation
from core.zkteco_service_improved import improved_zkteco_service

# Configure logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Map device users to system users and fetch attendance data from ZKTeco devices'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--map-only',
            action='store_true',
            help='Only map device users, do not fetch attendance'
        )
        parser.add_argument(
            '--fetch-only',
            action='store_true',
            help='Only fetch attendance, do not map users'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to fetch attendance for (default: 7)'
        )
        parser.add_argument(
            '--device-ip',
            type=str,
            help='Process only specific device by IP address'
        )
        parser.add_argument(
            '--create-users',
            action='store_true',
            help='Create new system users for unmapped device users'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('=' * 60)
        )
        self.stdout.write(
            self.style.SUCCESS('DEVICE USER MAPPING & ATTENDANCE FETCHING')
        )
        self.stdout.write(
            self.style.SUCCESS('=' * 60)
        )
        
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
        
        map_only = options['map_only']
        fetch_only = options['fetch_only']
        days = options['days']
        device_ip = options['device_ip']
        create_users = options['create_users']
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )
        
        # Step 1: Map device users (unless fetch-only)
        if not fetch_only:
            self.stdout.write(
                self.style.SUCCESS('\nStep 1: Mapping device users...')
            )
            
            mapping_result = self.map_device_users(device_ip, create_users, dry_run)
            
            self.stdout.write(
                self.style.SUCCESS(f"Mapping completed:")
            )
            self.stdout.write(f"   Devices processed: {mapping_result['devices_processed']}")
            self.stdout.write(f"   Users created: {mapping_result['users_created']}")
            self.stdout.write(f"   Users mapped: {mapping_result['users_mapped']}")
            self.stdout.write(f"   Errors: {mapping_result['errors']}")
        
        # Step 2: Fetch attendance (unless map-only)
        if not map_only:
            self.stdout.write(
                self.style.SUCCESS('\nStep 2: Fetching attendance data...')
            )
            
            end_date = timezone.now()
            start_date = end_date - timedelta(days=days)
            
            attendance_result = self.fetch_attendance_data(device_ip, start_date, end_date, dry_run)
            
            self.stdout.write(
                self.style.SUCCESS(f"Attendance fetching completed:")
            )
            self.stdout.write(f"   Devices processed: {attendance_result['devices_processed']}")
            self.stdout.write(f"   Records processed: {attendance_result['total_processed']}")
            self.stdout.write(f"   Errors: {attendance_result['total_errors']}")
        
        # Final summary
        self.stdout.write(
            self.style.SUCCESS('\nFinal Summary:')
        )
        
        # Show mapping summary
        mapping_summary = self.get_mapping_summary()
        if mapping_summary:
            self.stdout.write(f"   Total device users: {mapping_summary['total_device_users']}")
            self.stdout.write(f"   Mapped users: {mapping_summary['mapped_device_users']}")
            self.stdout.write(f"   Mapping percentage: {mapping_summary['mapping_percentage']:.1f}%")
        
        # Show attendance summary
        attendance_summary = self.get_attendance_summary(days)
        if attendance_summary:
            self.stdout.write(f"   Attendance records (last {days} days): {attendance_summary['total_records']}")
            self.stdout.write(f"   Users with attendance: {attendance_summary['users_with_attendance']}")
            self.stdout.write(f"   Attendance percentage: {attendance_summary['attendance_percentage']:.1f}%")
        
        self.stdout.write(
            self.style.SUCCESS('\nProcess completed successfully!')
        )
    
    def get_devices(self, device_ip: str = None) -> List[Device]:
        """Get devices to process"""
        try:
            queryset = Device.objects.filter(
                device_type='zkteco',
                is_active=True
            ).select_related('office')
            
            if device_ip:
                queryset = queryset.filter(ip_address=device_ip)
            
            devices = list(queryset)
            self.stdout.write(f"Found {len(devices)} active ZKTeco devices")
            return devices
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error fetching devices: {str(e)}")
            )
            return []
    
    def map_device_users(self, device_ip: str = None, create_users: bool = True, dry_run: bool = False) -> Dict:
        """Map device users to system users"""
        devices = self.get_devices(device_ip)
        if not devices:
            return {
                'devices_processed': 0,
                'users_created': 0,
                'users_mapped': 0,
                'errors': 0
            }
        
        total_created = 0
        total_mapped = 0
        total_errors = 0
        devices_processed = 0
        
        for device in devices:
            try:
                self.stdout.write(f"Processing device: {device.name} ({device.ip_address})")
                
                # Test connectivity
                if not improved_zkteco_service.test_device_connectivity(device.ip_address, device.port):
                    self.stdout.write(
                        self.style.WARNING(f"Device {device.name} is not reachable")
                    )
                    continue
                
                # Get device connection
                zk_device = improved_zkteco_service.get_device(device.ip_address, device.port)
                if not zk_device:
                    self.stdout.write(
                        self.style.ERROR(f"Failed to connect to device {device.name}")
                    )
                    continue
                
                # Fetch users from device
                device_users = zk_device.get_users()
                self.stdout.write(f"Found {len(device_users)} users on device {device.name}")
                
                device_created = 0
                device_mapped = 0
                device_errors = 0
                
                for device_user in device_users:
                    try:
                        result = self.map_single_device_user(device_user, device, create_users, dry_run)
                        if result['created']:
                            device_created += 1
                        if result['mapped']:
                            device_mapped += 1
                        if result['error']:
                            device_errors += 1
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"Error mapping user {device_user}: {str(e)}")
                        )
                        device_errors += 1
                
                self.stdout.write(f"Device {device.name}: {device_mapped} mapped, {device_created} created, {device_errors} errors")
                
                total_created += device_created
                total_mapped += device_mapped
                total_errors += device_errors
                devices_processed += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error processing device {device.name}: {str(e)}")
                )
                total_errors += 1
        
        return {
            'devices_processed': devices_processed,
            'users_created': total_created,
            'users_mapped': total_mapped,
            'errors': total_errors
        }
    
    def map_single_device_user(self, device_user: Dict, device: Device, create_users: bool, dry_run: bool) -> Dict:
        """Map a single device user to system user"""
        device_user_id = str(device_user.get('user_id', ''))
        device_user_name = device_user.get('name', '').strip()
        
        if not device_user_id or not device_user_name:
            return {'created': False, 'mapped': False, 'error': True}
        
        # Check if mapping already exists
        existing_mapping = DeviceUser.objects.filter(
            device=device,
            device_user_id=device_user_id
        ).first()
        
        if existing_mapping and existing_mapping.is_mapped:
            return {'created': False, 'mapped': True, 'error': False}
        
        # Find or create system user
        system_user = None
        
        # Try to find by biometric_id
        system_user = CustomUser.objects.filter(biometric_id=device_user_id).first()
        
        # Try to find by employee_id
        if not system_user:
            system_user = CustomUser.objects.filter(employee_id=device_user_id).first()
        
        # Create new user if not found and create_users is True
        if not system_user and create_users and not dry_run:
            system_user = self.create_system_user(device_user, device)
        
        if not system_user:
            return {'created': False, 'mapped': False, 'error': True}
        
        # Create or update DeviceUser mapping
        if not dry_run:
            if not existing_mapping:
                existing_mapping = DeviceUser.objects.create(
                    device=device,
                    device_user_id=device_user_id,
                    device_user_name=device_user_name,
                    device_user_privilege='admin' if device_user.get('privilege', 0) > 0 else 'user',
                    device_user_password=device_user.get('password', ''),
                    device_user_card=device_user.get('card_number', ''),
                    is_mapped=True,
                    system_user=system_user,
                    mapping_notes=f"Auto-mapped on {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
            else:
                existing_mapping.system_user = system_user
                existing_mapping.is_mapped = True
                existing_mapping.save()
        
        return {'created': system_user.biometric_id == device_user_id, 'mapped': True, 'error': False}
    
    def create_system_user(self, device_user: Dict, device: Device) -> Optional[CustomUser]:
        """Create a new system user from device user data"""
        try:
            device_user_id = str(device_user.get('user_id', ''))
            device_user_name = device_user.get('name', '').strip()
            
            # Generate username
            username = f"user_{device_user_id}" if device_user_id else f"user_{device_user_name.lower().replace(' ', '_')}"
            
            # Get default department and designation
            department = Department.objects.first() or Department.objects.create(
                name="General",
                description="Default department",
                is_active=True
            )
            
            designation = Designation.objects.first() or Designation.objects.create(
                name="Employee",
                department=department,
                description="Default designation",
                is_active=True
            )
            
            # Create new user
            user = CustomUser.objects.create(
                username=username,
                first_name=device_user_name.split()[0] if device_user_name.split() else device_user_name,
                last_name=' '.join(device_user_name.split()[1:]) if len(device_user_name.split()) > 1 else '',
                email=f"{username}@company.com",
                password=make_password("Dos@9999"),
                role='employee',
                office=device.office,
                department=department,
                designation=designation,
                biometric_id=device_user_id,
                employee_id=device_user_id,
                is_active=True,
                is_staff=False,
                is_superuser=False
            )
            
            self.stdout.write(f"Created new user: {user.username} ({user.get_full_name()})")
            return user
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error creating user for device user {device_user}: {str(e)}")
            )
            return None
    
    def fetch_attendance_data(self, device_ip: str = None, start_date: datetime = None, end_date: datetime = None, dry_run: bool = False) -> Dict:
        """Fetch attendance data from devices"""
        # Get devices that have mapped users
        queryset = Device.objects.filter(
            device_type='zkteco',
            is_active=True,
            device_users__is_mapped=True
        ).distinct().select_related('office')
        
        if device_ip:
            queryset = queryset.filter(ip_address=device_ip)
        
        devices = list(queryset)
        
        if not devices:
            self.stdout.write(
                self.style.WARNING("No devices with mapped users found")
            )
            return {
                'devices_processed': 0,
                'total_processed': 0,
                'total_errors': 0
            }
        
        total_processed = 0
        total_errors = 0
        devices_processed = 0
        
        for device in devices:
            try:
                self.stdout.write(f"Fetching attendance from device: {device.name} ({device.ip_address})")
                
                # Test connectivity
                if not improved_zkteco_service.test_device_connectivity(device.ip_address, device.port):
                    self.stdout.write(
                        self.style.WARNING(f"Device {device.name} is not reachable")
                    )
                    continue
                
                # Get device connection
                zk_device = improved_zkteco_service.get_device(device.ip_address, device.port)
                if not zk_device:
                    self.stdout.write(
                        self.style.ERROR(f"Failed to connect to device {device.name}")
                    )
                    continue
                
                # Fetch attendance logs
                attendance_logs = zk_device.get_attendance_logs(start_date, end_date)
                self.stdout.write(f"Retrieved {len(attendance_logs)} attendance logs from device {device.name}")
                
                if not dry_run:
                    # Process attendance logs
                    processed_count, error_count = self.process_attendance_logs(attendance_logs, device)
                    total_processed += processed_count
                    total_errors += error_count
                    
                    self.stdout.write(f"Device {device.name}: {processed_count} processed, {error_count} errors")
                else:
                    self.stdout.write(f"Device {device.name}: Would process {len(attendance_logs)} logs (dry run)")
                
                devices_processed += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error processing device {device.name}: {str(e)}")
                )
                total_errors += 1
        
        return {
            'devices_processed': devices_processed,
            'total_processed': total_processed,
            'total_errors': total_errors
        }
    
    def process_attendance_logs(self, attendance_logs: List[Dict], device: Device) -> Tuple[int, int]:
        """Process attendance logs and create attendance records"""
        processed_count = 0
        error_count = 0
        
        # Group logs by user and date
        user_date_logs = {}
        
        for log in attendance_logs:
            user_id = str(log.get('user_id', ''))
            punch_time = log.get('punch_time')
            punch_type = log.get('punch_type', 'in')
            
            if not user_id or not punch_time:
                continue
            
            # Convert punch_time to timezone-aware if needed
            if timezone.is_naive(punch_time):
                punch_time = timezone.make_aware(punch_time, timezone.get_current_timezone())
            
            log_date = punch_time.date()
            user_date_key = f"{user_id}_{log_date}"
            
            if user_date_key not in user_date_logs:
                user_date_logs[user_date_key] = {
                    'user_id': user_id,
                    'date': log_date,
                    'logs': []
                }
            
            user_date_logs[user_date_key]['logs'].append({
                'punch_time': punch_time,
                'punch_type': punch_type
            })
        
        # Process each user-date combination
        for user_date_key, user_data in user_date_logs.items():
            try:
                # Sort logs by time
                user_data['logs'].sort(key=lambda x: x['punch_time'])
                
                # Find check-in and check-out times
                check_in_time = None
                check_out_time = None
                
                for log in user_data['logs']:
                    if log['punch_type'] == 'in' and not check_in_time:
                        check_in_time = log['punch_time']
                    elif log['punch_type'] == 'out':
                        check_out_time = log['punch_time']
                
                # Find the system user
                system_user = None
                
                # Try to find by biometric_id
                system_user = CustomUser.objects.filter(biometric_id=user_data['user_id']).first()
                
                # Try to find by employee_id
                if not system_user:
                    system_user = CustomUser.objects.filter(employee_id=user_data['user_id']).first()
                
                # Try to find through device user mapping
                if not system_user:
                    device_user = DeviceUser.objects.filter(
                        device=device,
                        device_user_id=user_data['user_id'],
                        is_mapped=True
                    ).first()
                    
                    if device_user and device_user.system_user:
                        system_user = device_user.system_user
                
                if not system_user:
                    error_count += 1
                    continue
                
                # Create or update attendance record
                attendance, created = Attendance.objects.get_or_create(
                    user=system_user,
                    date=user_data['date'],
                    defaults={
                        'check_in_time': check_in_time,
                        'check_out_time': check_out_time,
                        'device': device,
                        'status': 'present' if check_in_time else 'absent'
                    }
                )
                
                if not created:
                    # Update existing record
                    attendance.check_in_time = check_in_time or attendance.check_in_time
                    attendance.check_out_time = check_out_time or attendance.check_out_time
                    attendance.device = device
                    attendance.save()
                
                # Create ESSLAttendanceLog record for raw data
                for log in user_data['logs']:
                    ESSLAttendanceLog.objects.get_or_create(
                        device=device,
                        biometric_id=user_data['user_id'],
                        punch_time=log['punch_time'],
                        defaults={
                            'user': system_user,
                            'punch_type': log['punch_type'],
                            'is_processed': True
                        }
                    )
                
                processed_count += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error processing attendance for user {user_data['user_id']} on {user_data['date']}: {str(e)}")
                )
                error_count += 1
        
        return processed_count, error_count
    
    def get_mapping_summary(self) -> Dict:
        """Get summary of current mappings"""
        try:
            total_device_users = DeviceUser.objects.count()
            mapped_device_users = DeviceUser.objects.filter(is_mapped=True).count()
            mapping_percentage = (mapped_device_users / total_device_users * 100) if total_device_users > 0 else 0
            
            return {
                'total_device_users': total_device_users,
                'mapped_device_users': mapped_device_users,
                'mapping_percentage': mapping_percentage
            }
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error getting mapping summary: {str(e)}")
            )
            return {}
    
    def get_attendance_summary(self, days: int = 7) -> Dict:
        """Get summary of attendance data"""
        try:
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=days)
            
            # Get attendance records in date range
            attendance_records = Attendance.objects.filter(
                date__range=[start_date, end_date]
            )
            
            total_records = attendance_records.count()
            users_with_attendance = attendance_records.values('user').distinct().count()
            total_users = CustomUser.objects.filter(role='employee', is_active=True).count()
            attendance_percentage = (users_with_attendance / total_users * 100) if total_users > 0 else 0
            
            return {
                'total_records': total_records,
                'users_with_attendance': users_with_attendance,
                'attendance_percentage': attendance_percentage
            }
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error getting attendance summary: {str(e)}")
            )
            return {}
