#!/usr/bin/env python3
"""
Management command to check and fix Ace Track device issues
"""

import os
import sys
import django
import logging
import socket
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'attendance_system.settings')
django.setup()

from core.models import Device, DeviceUser, CustomUser, Office

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Check and fix Ace Track device issues'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ip',
            type=str,
            default='192.168.200.150',
            help='IP address of the Ace Track device'
        )
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Attempt to fix issues found'
        )

    def handle(self, *args, **options):
        ip_address = options['ip']
        fix_issues = options['fix']
        
        self.stdout.write(f"Checking Ace Track device at {ip_address}...")
        
        # Check if device exists in database
        try:
            device = Device.objects.get(ip_address=ip_address)
            self.stdout.write(f"✅ Device found in database: {device.name}")
        except Device.DoesNotExist:
            self.stdout.write(f"❌ Device not found in database")
            if fix_issues:
                self.create_device(ip_address)
            return
        
        # Check device connectivity
        self.check_connectivity(device)
        
        # Check device users
        self.check_device_users(device, fix_issues)
        
        # Check user mappings
        self.check_user_mappings(device, fix_issues)
        
        # Check attendance data
        self.check_attendance_data(device)

    def create_device(self, ip_address):
        """Create a new device entry"""
        try:
            # Get the first office or create a default one
            office = Office.objects.first()
            if not office:
                office = Office.objects.create(
                    name="Default Office",
                    address="Default Address",
                    phone="0000000000",
                    email="default@example.com"
                )
            
            device = Device.objects.create(
                name=f"Ace Track Device {ip_address}",
                device_type='other',  # Ace Track might not be ZKTeco or ESSL
                ip_address=ip_address,
                port=4370,
                office=office,
                is_active=True
            )
            
            self.stdout.write(f"✅ Created device: {device.name}")
            return device
            
        except Exception as e:
            self.stdout.write(f"❌ Error creating device: {e}")

    def check_connectivity(self, device):
        """Check if device is reachable on network"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((device.ip_address, device.port))
            sock.close()
            
            if result == 0:
                self.stdout.write(f"✅ Device is reachable on network")
                device.device_status = 'online'
                device.save()
            else:
                self.stdout.write(f"❌ Device is not reachable on network")
                device.device_status = 'offline'
                device.save()
                
        except Exception as e:
            self.stdout.write(f"❌ Network connectivity error: {e}")
            device.device_status = 'error'
            device.save()

    def check_device_users(self, device, fix_issues):
        """Check device users"""
        device_users = DeviceUser.objects.filter(device=device)
        self.stdout.write(f"Device users found: {device_users.count()}")
        
        if device_users.count() == 0:
            self.stdout.write("❌ No device users found")
            if fix_issues:
                self.stdout.write("💡 You may need to fetch users from the device first")
                self.stdout.write("   Try running: python manage.py auto_fetch_zkteco_improved")
        else:
            for du in device_users:
                status = "✅ Mapped" if du.is_mapped else "❌ Unmapped"
                self.stdout.write(f"  - {du.device_user_name} (ID: {du.device_user_id}) - {status}")

    def check_user_mappings(self, device, fix_issues):
        """Check user mappings"""
        unmapped_users = DeviceUser.objects.filter(device=device, is_mapped=False)
        
        if unmapped_users.count() > 0:
            self.stdout.write(f"❌ Found {unmapped_users.count()} unmapped users:")
            
            for du in unmapped_users:
                self.stdout.write(f"  - {du.device_user_name} (ID: {du.device_user_id})")
                
                if fix_issues:
                    # Try to find matching system user
                    system_user = self.find_matching_user(du)
                    if system_user:
                        du.system_user = system_user
                        du.is_mapped = True
                        du.save()
                        self.stdout.write(f"    ✅ Mapped to system user: {system_user.get_full_name()}")
                    else:
                        self.stdout.write(f"    ❌ No matching system user found")
        else:
            self.stdout.write("✅ All device users are mapped")

    def find_matching_user(self, device_user):
        """Find matching system user based on name or employee ID"""
        # Try to match by employee_id first
        if device_user.device_user_id:
            try:
                return CustomUser.objects.get(employee_id=device_user.device_user_id)
            except CustomUser.DoesNotExist:
                pass
        
        # Try to match by name
        name_parts = device_user.device_user_name.split()
        if len(name_parts) >= 2:
            first_name = name_parts[0]
            last_name = ' '.join(name_parts[1:])
            
            try:
                return CustomUser.objects.get(
                    first_name__iexact=first_name,
                    last_name__iexact=last_name
                )
            except CustomUser.DoesNotExist:
                pass
            except CustomUser.MultipleObjectsReturned:
                # Multiple users with same name, return first one
                return CustomUser.objects.filter(
                    first_name__iexact=first_name,
                    last_name__iexact=last_name
                ).first()
        
        return None

    def check_attendance_data(self, device):
        """Check attendance data for the device"""
        from core.models import Attendance
        
        # Check recent attendance records
        recent_date = timezone.now().date() - timedelta(days=7)
        attendance_count = Attendance.objects.filter(
            device=device,
            date__gte=recent_date
        ).count()
        
        self.stdout.write(f"Recent attendance records (last 7 days): {attendance_count}")
        
        if attendance_count == 0:
            self.stdout.write("❌ No recent attendance data found")
            self.stdout.write("💡 You may need to fetch attendance data from the device")
            self.stdout.write("   Try running: python manage.py auto_fetch_zkteco_improved")
        else:
            self.stdout.write("✅ Recent attendance data found")

    def show_recommendations(self, device):
        """Show recommendations for fixing issues"""
        self.stdout.write("\n📋 RECOMMENDATIONS:")
        self.stdout.write("1. Ensure the device is properly configured in the system")
        self.stdout.write("2. Check network connectivity to the device")
        self.stdout.write("3. Fetch users from the device: python manage.py auto_fetch_zkteco_improved")
        self.stdout.write("4. Map unmapped users to system users")
        self.stdout.write("5. Fetch attendance data: python manage.py auto_fetch_zkteco_improved")
        self.stdout.write("6. Check device logs for any errors")
