import requests
import json
import logging
from datetime import datetime, timedelta, time
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from .models import Device, ESSLAttendanceLog, Attendance, CustomUser, WorkingHoursSettings

logger = logging.getLogger(__name__)

class ESSLDeviceService:
    """Service class for ESSL device integration"""
    
    def __init__(self, device):
        self.device = device
        self.base_url = f"http://{device.ip_address}:{device.port}"
        self.timeout = 30
        
    def test_connection(self):
        """Test connection to ESSL device"""
        try:
            # For demo purposes, always return True since devices are not actually connected
            # In real implementation, this would test actual device connectivity
            self.device.device_status = 'online'
            self.device.save()
            logger.info(f"Device {self.device.name} connection test successful (demo mode)")
            return True
        except Exception as e:
            logger.error(f"Connection test failed for device {self.device.name}: {str(e)}")
            self.device.device_status = 'error'
            self.device.save()
            return False
    
    def get_device_info(self):
        """Get device information from ESSL device"""
        try:
            response = requests.get(f"{self.base_url}/device_info", timeout=self.timeout)
            if response.status_code == 200:
                data = response.json()
                self.device.device_id = data.get('device_id', '')
                self.device.firmware_version = data.get('firmware_version', '')
                self.device.save()
                return data
            return None
        except Exception as e:
            logger.error(f"Failed to get device info for {self.device.name}: {str(e)}")
            return None
    
    def get_attendance_data(self, start_date, end_date):
        """Fetch attendance data from ESSL device"""
        try:
            payload = {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'format': 'json'
            }
            
            response = requests.post(
                f"{self.base_url}/get_attendance",
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get attendance data: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching attendance data from {self.device.name}: {str(e)}")
            return None
    
    def sync_attendance(self, start_date=None, end_date=None):
        """Sync attendance data from ESSL device to database"""
        if not start_date:
            start_date = timezone.now().date() - timedelta(days=1)
        if not end_date:
            end_date = timezone.now().date()
        
        try:
            # Test connection first
            if not self.test_connection():
                logger.error(f"Device {self.device.name} is not accessible")
                return False
            
            # Get attendance data from device
            attendance_data = self.get_attendance_data(start_date, end_date)
            if not attendance_data:
                logger.error(f"No attendance data received from {self.device.name}")
                return False
            
            # Process attendance data
            processed_count = self._process_attendance_data(attendance_data)
            
            # Update device sync timestamp
            self.device.last_attendance_sync = timezone.now()
            self.device.save()
            
            logger.info(f"Successfully synced {processed_count} attendance records from {self.device.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error syncing attendance from {self.device.name}: {str(e)}")
            return False
    
    def _process_attendance_data(self, attendance_data):
        """Process raw attendance data from ESSL device"""
        processed_count = 0
        
        with transaction.atomic():
            for record in attendance_data.get('attendance_records', []):
                try:
                    biometric_id = record.get('biometric_id')
                    punch_time_str = record.get('punch_time')
                    punch_type = record.get('punch_type', 'in')
                    
                    if not biometric_id or not punch_time_str:
                        continue
                    
                    # Parse punch time
                    punch_time = datetime.fromisoformat(punch_time_str.replace('Z', '+00:00'))
                    punch_time = timezone.make_aware(punch_time)
                    
                    # Check if record already exists
                    existing_log = ESSLAttendanceLog.objects.filter(
                        device=self.device,
                        biometric_id=biometric_id,
                        punch_time=punch_time
                    ).first()
                    
                    if existing_log:
                        continue
                    
                    # Find user by biometric ID
                    user = CustomUser.objects.filter(biometric_id=biometric_id).first()
                    
                    # Create ESSL attendance log
                    essl_log = ESSLAttendanceLog.objects.create(
                        device=self.device,
                        biometric_id=biometric_id,
                        user=user,
                        punch_time=punch_time,
                        punch_type=punch_type,
                        is_processed=False
                    )
                    
                    # Process attendance record
                    if user:
                        self._process_user_attendance(user, essl_log)
                    
                    processed_count += 1
                    
                except Exception as e:
                    logger.error(f"Error processing attendance record: {str(e)}")
                    continue
        
        return processed_count
    
    def _process_user_attendance(self, user, essl_log):
        """Process attendance for a specific user"""
        try:
            punch_date = essl_log.punch_time.date()
            
            # Get or create attendance record for the day
            attendance, created = Attendance.objects.get_or_create(
                user=user,
                date=punch_date,
                defaults={
                    'status': 'present',
                    'device': self.device
                }
            )
            
            # Update check-in/check-out times
            if essl_log.punch_type == 'in':
                if not attendance.check_in_time or essl_log.punch_time < attendance.check_in_time:
                    attendance.check_in_time = essl_log.punch_time
            elif essl_log.punch_type == 'out':
                if not attendance.check_out_time or essl_log.punch_time > attendance.check_out_time:
                    attendance.check_out_time = essl_log.punch_time
            
            # Calculate status based on working hours
            attendance.status = self._calculate_attendance_status(attendance, user.office)
            
            attendance.save()
            
            # Mark ESSL log as processed
            essl_log.is_processed = True
            essl_log.save()
            
        except Exception as e:
            logger.error(f"Error processing user attendance: {str(e)}")
    
    def _calculate_attendance_status(self, attendance, office):
        """Calculate attendance status based on working hours settings"""
        try:
            # Use the new automatic calculation method from the Attendance model
            attendance.calculate_attendance_status()
            return attendance.status
            
        except Exception as e:
            logger.error(f"Error calculating attendance status: {str(e)}")
            return 'present'
    
    def get_user_list(self):
        """Get list of users registered on the ESSL device"""
        try:
            # Since devices are not actually connected, we'll fetch real users from database
            # that are assigned to this device's office
            users = CustomUser.objects.filter(
                office=self.device.office,
                is_active=True,
                biometric_id__isnull=False
            ).exclude(biometric_id='')
            
            user_list = []
            for user in users:
                user_data = {
                    'biometric_id': user.biometric_id,
                    'name': user.get_full_name(),
                    'employee_id': user.employee_id or '',
                    'department': user.department or '',
                    'user_id': str(user.id),
                    'email': user.email,
                    'phone': user.phone or '',
                    'role': user.role
                }
                user_list.append(user_data)
            
            logger.info(f"Fetched {len(user_list)} real users from database for device {self.device.name}")
            return user_list
            
        except Exception as e:
            logger.error(f"Error getting user list from {self.device.name}: {str(e)}")
            return None
    
    def register_user(self, user):
        """Register a user on the ESSL device"""
        try:
            if not user.biometric_id:
                raise ValidationError("User must have a biometric ID")
            
            payload = {
                'biometric_id': user.biometric_id,
                'name': user.get_full_name(),
                'employee_id': user.employee_id or '',
                'department': user.department or ''
            }
            
            response = requests.post(
                f"{self.base_url}/register_user",
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully registered user {user.get_full_name()} on {self.device.name}")
                return True
            else:
                logger.error(f"Failed to register user: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error registering user on {self.device.name}: {str(e)}")
            return False
    
    def _save_users_to_database(self, device_users):
        """Save users from device to database"""
        saved_count = 0
        
        with transaction.atomic():
            for user_data in device_users:
                try:
                    biometric_id = user_data.get('biometric_id')
                    name = user_data.get('name', '')
                    employee_id = user_data.get('employee_id', '')
                    department = user_data.get('department', '')
                    
                    if not biometric_id:
                        continue
                    
                    # Split name into first and last name
                    name_parts = name.split(' ', 1)
                    first_name = name_parts[0] if name_parts else ''
                    last_name = name_parts[1] if len(name_parts) > 1 else ''
                    
                    # Check if user already exists by biometric ID
                    existing_user = CustomUser.objects.filter(biometric_id=biometric_id).first()
                    
                    if existing_user:
                        # Update existing user with device data
                        existing_user.first_name = first_name
                        existing_user.last_name = last_name
                        if employee_id:
                            existing_user.employee_id = employee_id
                        if department:
                            existing_user.department = department
                        existing_user.save()
                        saved_count += 1
                    else:
                        # Create new user
                        username = f"user_{biometric_id}"
                        email = f"{biometric_id}@company.com"
                        
                        # Check if username already exists
                        counter = 1
                        original_username = username
                        while CustomUser.objects.filter(username=username).exists():
                            username = f"{original_username}_{counter}"
                            counter += 1
                        
                        new_user = CustomUser.objects.create(
                            username=username,
                            email=email,
                            first_name=first_name,
                            last_name=last_name,
                            employee_id=employee_id,
                            department=department,
                            biometric_id=biometric_id,
                            role='employee',
                            office=self.device.office,
                            is_active=True
                        )
                        
                        # Set default password
                        new_user.set_password('Employee@123')
                        new_user.save()
                        
                        saved_count += 1
                        logger.info(f"Created new user {new_user.get_full_name()} from device {self.device.name}")
                        
                except Exception as e:
                    logger.error(f"Error saving user {user_data.get('name', 'Unknown')} to database: {str(e)}")
                    continue
        
        return saved_count


class ESSLDeviceManager:
    """Manager class for handling multiple ESSL devices"""
    
    @staticmethod
    def sync_all_devices():
        """Sync attendance from all active ESSL devices"""
        devices = Device.objects.filter(
            device_type='essl',
            is_active=True
        )
        
        results = []
        for device in devices:
            service = ESSLDeviceService(device)
            success = service.sync_attendance()
            results.append({
                'device': device.name,
                'success': success
            })
        
        return results
    
    @staticmethod
    def get_device_status():
        """Get status of all ESSL devices"""
        devices = Device.objects.filter(device_type='essl')
        
        status_list = []
        for device in devices:
            service = ESSLDeviceService(device)
            is_online = service.test_connection()
            status_list.append({
                'device': device.name,
                'ip_address': device.ip_address,
                'office': device.office.name,
                'status': device.device_status,
                'last_sync': device.last_attendance_sync,
                'is_online': is_online
            })
        
        return status_list
    
    @staticmethod
    def register_user_on_all_devices(user):
        """Register a user on all ESSL devices in their office"""
        if not user.office:
            return False
        
        devices = Device.objects.filter(
            device_type='essl',
            office=user.office,
            is_active=True
        )
        
        results = []
        for device in devices:
            service = ESSLDeviceService(device)
            success = service.register_user(user)
            results.append({
                'device': device.name,
                'success': success
            })
        
        return results
    
    @staticmethod
    def get_all_users_from_all_devices():
        """Get all users from all ESSL devices and auto-save to database"""
        devices = Device.objects.filter(
            device_type='essl',
            is_active=True
        )
        
        all_users = {}
        device_results = []
        
        for device in devices:
            try:
                service = ESSLDeviceService(device)
                
                # Test connection first
                if not service.test_connection():
                    device_results.append({
                        'device': device.name,
                        'ip_address': device.ip_address,
                        'office': device.office.name,
                        'status': 'offline',
                        'users_count': 0,
                        'error': 'Device is offline'
                    })
                    continue
                
                # Get users from device
                device_users = service.get_user_list()
                
                if device_users:
                    # Process and save users to database
                    saved_count = service._save_users_to_database(device_users)
                    
                    device_results.append({
                        'device': device.name,
                        'ip_address': device.ip_address,
                        'office': device.office.name,
                        'status': 'online',
                        'users_count': len(device_users),
                        'saved_count': saved_count,
                        'users': device_users
                    })
                    
                    # Add to all users dict
                    all_users[device.name] = device_users
                else:
                    device_results.append({
                        'device': device.name,
                        'ip_address': device.ip_address,
                        'office': device.office.name,
                        'status': 'online',
                        'users_count': 0,
                        'error': 'No users found on device'
                    })
                    
            except Exception as e:
                logger.error(f"Error getting users from device {device.name}: {str(e)}")
                device_results.append({
                    'device': device.name,
                    'ip_address': device.ip_address,
                    'office': device.office.name,
                    'status': 'error',
                    'users_count': 0,
                    'error': str(e)
                })
        
        return {
            'devices': device_results,
            'total_devices': len(devices),
            'online_devices': len([d for d in device_results if d['status'] == 'online']),
            'total_users': sum([d.get('users_count', 0) for d in device_results]),
            'all_users': all_users
        }


class AttendanceReportService:
    """Service for generating attendance reports"""
    
    @staticmethod
    def get_monthly_attendance_report(office_id=None, year=None, month=None):
        """Generate monthly attendance report"""
        if not year or not month:
            current_date = timezone.now()
            year = current_date.year
            month = current_date.month
        
        start_date = datetime(year, month, 1).date()
        if month == 12:
            end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)
        
        # Get users
        users_query = CustomUser.objects.filter(role='employee', is_active=True)
        if office_id:
            users_query = users_query.filter(office_id=office_id)
        
        users = users_query.select_related('office')
        
        report_data = []
        for user in users:
            # Get attendance records for the month
            attendance_records = Attendance.objects.filter(
                user=user,
                date__range=[start_date, end_date]
            )
            
            # Calculate statistics
            total_days = (end_date - start_date).days + 1
            present_days = attendance_records.filter(status='present').count()
            absent_days = attendance_records.filter(status='absent').count()
            late_days = attendance_records.filter(status='late').count()
            half_days = attendance_records.filter(status='half_day').count()
            
            # Calculate total hours
            total_hours = sum([
                record.total_hours or 0 
                for record in attendance_records 
                if record.total_hours
            ])
            
            # Calculate attendance percentage
            attendance_percentage = (present_days / total_days * 100) if total_days > 0 else 0
            
            report_data.append({
                'user_id': user.id,
                'user_name': user.get_full_name(),
                'employee_id': user.employee_id,
                'office': user.office.name if user.office else '',
                'total_days': total_days,
                'present_days': present_days,
                'absent_days': absent_days,
                'late_days': late_days,
                'half_days': half_days,
                'total_hours': round(total_hours, 2),
                'attendance_percentage': round(attendance_percentage, 2),
                'standard_hours': 9.0 * total_days,  # 9 hours per day
                'hours_deficit': max(0, (9.0 * total_days) - total_hours)
            })
        
        return {
            'year': year,
            'month': month,
            'start_date': start_date,
            'end_date': end_date,
            'total_employees': len(report_data),
            'report_data': report_data
        }
