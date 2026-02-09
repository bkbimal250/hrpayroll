#!/usr/bin/env python3
"""
Management command to fetch users from Ace Track device
"""

import os
import sys
import django
import logging
import socket
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'attendance_system.settings')
django.setup()

from core.models import Device, DeviceUser, CustomUser, Office

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Fetch users from Ace Track device'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ip',
            type=str,
            default='192.168.200.150',
            help='IP address of the Ace Track device'
        )
        parser.add_argument(
            '--port',
            type=int,
            default=4370,
            help='Port of the Ace Track device'
        )

    def handle(self, *args, **options):
        ip_address = options['ip']
        port = options['port']
        
        self.stdout.write(f"Fetching users from Ace Track device at {ip_address}:{port}...")
        
        # Get or create device
        try:
            device = Device.objects.get(ip_address=ip_address)
            self.stdout.write(f" Found device: {device.name}")
        except Device.DoesNotExist:
            self.stdout.write(f" Device not found. Creating new device...")
            device = self.create_device(ip_address, port)
            if not device:
                return
        
        # Check connectivity
        if not self.check_connectivity(device):
            self.stdout.write(" Cannot connect to device. Please check network connectivity.")
            return
        
        # Try to fetch users using different methods
        self.try_zkteco_method(device)
        self.try_essl_method(device)
        self.try_manual_method(device)

    def create_device(self, ip_address, port):
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
                port=port,
                office=office,
                is_active=True
            )
            
            self.stdout.write(f" Created device: {device.name}")
            return device
            
        except Exception as e:
            self.stdout.write(f" Error creating device: {e}")
            return None

    def check_connectivity(self, device):
        """Check if device is reachable on network"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((device.ip_address, device.port))
            sock.close()
            
            if result == 0:
                self.stdout.write(f" Device is reachable on network")
                device.device_status = 'online'
                device.save()
                return True
            else:
                self.stdout.write(f" Device is not reachable on network")
                device.device_status = 'offline'
                device.save()
                return False
                
        except Exception as e:
            self.stdout.write(f" Network connectivity error: {e}")
            device.device_status = 'error'
            device.save()
            return False

    def try_zkteco_method(self, device):
        """Try to fetch users using ZKTeco method"""
        self.stdout.write("\nTrying ZKTeco method...")
        
        try:
            from zk import ZK
            zk = ZK(device.ip_address, port=device.port, timeout=10)
            zk.connect()
            
            users = zk.get_users()
            self.stdout.write(f" Found {len(users)} users using ZKTeco method")
            
            for user in users:
                self.create_device_user(device, str(user.uid), user.name, 'user')
            
            zk.disconnect()
            device.device_type = 'zkteco'
            device.save()
            return True
            
        except ImportError:
            self.stdout.write(" pyzk library not available")
        except Exception as e:
            self.stdout.write(f" ZKTeco method failed: {e}")
        
        return False

    def try_essl_method(self, device):
        """Try to fetch users using ESSL method"""
        self.stdout.write("\nTrying ESSL method...")
        
        try:
            # ESSL devices typically use different protocols
            # This is a placeholder for ESSL-specific implementation
            self.stdout.write(" ESSL method not implemented for Ace Track devices")
        except Exception as e:
            self.stdout.write(f" ESSL method failed: {e}")
        
        return False

    def try_manual_method(self, device):
        """Try manual method to add common users"""
        self.stdout.write("\n Trying manual method...")
        
        # Get all system users and create device users for them
        system_users = CustomUser.objects.filter(is_active=True)
        
        if system_users.count() == 0:
            self.stdout.write(" No system users found")
            return False
        
        self.stdout.write(f"Found {system_users.count()} system users")
        
        created_count = 0
        for user in system_users:
            # Use employee_id if available, otherwise use user ID
            device_user_id = user.employee_id or str(user.id)
            device_user_name = user.get_full_name() or user.username
            
            device_user, created = DeviceUser.objects.get_or_create(
                device=device,
                device_user_id=device_user_id,
                defaults={
                    'device_user_name': device_user_name,
                    'device_user_privilege': 'user',
                    'system_user': user,
                    'is_mapped': True
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(f"   Created device user: {device_user_name} (ID: {device_user_id})")
            else:
                # Update existing device user
                if not device_user.is_mapped:
                    device_user.system_user = user
                    device_user.is_mapped = True
                    device_user.save()
                    self.stdout.write(f"   Mapped existing device user: {device_user_name}")
        
        self.stdout.write(f" Created/mapped {created_count} device users")
        return True

    def create_device_user(self, device, user_id, user_name, privilege='user'):
        """Create a device user entry"""
        try:
            device_user, created = DeviceUser.objects.get_or_create(
                device=device,
                device_user_id=user_id,
                defaults={
                    'device_user_name': user_name,
                    'device_user_privilege': privilege,
                    'is_mapped': False
                }
            )
            
            if created:
                self.stdout.write(f"   Created device user: {user_name} (ID: {user_id})")
            else:
                self.stdout.write(f"    Device user already exists: {user_name} (ID: {user_id})")
                
        except Exception as e:
            self.stdout.write(f"   Error creating device user {user_name}: {e}")

    def show_next_steps(self):
        """Show next steps after fetching users"""
        self.stdout.write("\n NEXT STEPS:")
        self.stdout.write("1. Review the device users created")
        self.stdout.write("2. Map unmapped users to system users if needed")
        self.stdout.write("3. Test attendance data fetching")
        self.stdout.write("4. Run: python manage.py check_ace_track_device --fix")
