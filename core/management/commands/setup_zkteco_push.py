#!/usr/bin/env python3
"""
Management command to setup ZKTeco devices for automatic push
This command configures the devices to push attendance data to the server
"""

import os
import sys
import django
import logging
import time
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'attendance_system.settings')
django.setup()

from core.models import Device, CustomUser
from core.zkteco_service_improved import improved_zkteco_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from zk import ZK
    ZK_AVAILABLE = True
except ImportError:
    ZK_AVAILABLE = False
    logger.error("pyzk library not found. Please install it with: pip install pyzk")

class Command(BaseCommand):
    help = 'Setup ZKTeco devices to automatically push attendance data to server'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--device-id',
            type=str,
            help='Setup specific device by ID'
        )
        parser.add_argument(
            '--device-ip',
            type=str,
            help='Setup specific device by IP address'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Setup all ZKTeco devices'
        )
        parser.add_argument(
            '--server-url',
            type=str,
            help='Server URL for push endpoints'
        )
        parser.add_argument(
            '--push-interval',
            type=int,
            default=60,
            help='Push interval in seconds (default: 60)'
        )
        parser.add_argument(
            '--test-connection',
            action='store_true',
            help='Test connection to devices without configuring'
        )
    
    def handle(self, *args, **options):
        if not ZK_AVAILABLE:
            self.stdout.write(
                self.style.ERROR('❌ pyzk library not available. Install with: pip install pyzk')
            )
            return
        
        # Get server URL
        server_url = options.get('server_url')
        if not server_url:
            server_url = getattr(settings, 'SERVER_URL', 'http://localhost:8000')
        
        push_interval = options.get('push_interval', 60)
        
        if options['test_connection']:
            self.test_device_connections()
            return
        
        # Setup devices
        if options['all']:
            self.setup_all_devices(server_url, push_interval)
        elif options['device_id']:
            self.setup_device_by_id(options['device_id'], server_url, push_interval)
        elif options['device_ip']:
            self.setup_device_by_ip(options['device_ip'], server_url, push_interval)
        else:
            self.stdout.write(
                self.style.ERROR('Please specify --all, --device-id, or --device-ip')
            )
    
    def test_device_connections(self):
        """Test connection to all ZKTeco devices"""
        self.stdout.write("🔍 Testing connections to ZKTeco devices...")
        
        devices = Device.objects.filter(device_type='zkteco', is_active=True)
        
        if not devices.exists():
            self.stdout.write(
                self.style.WARNING('No active ZKTeco devices found')
            )
            return
        
        for device in devices:
            self.test_single_device_connection(device)
    
    def test_single_device_connection(self, device):
        """Test connection to a single device"""
        try:
            self.stdout.write(f"🔌 Testing connection to {device.name} ({device.ip_address}:{device.port})...")
            
            # Test connectivity
            is_online = improved_zkteco_service.test_device_connectivity(
                device.ip_address, device.port
            )
            
            if is_online:
                self.stdout.write(
                    self.style.SUCCESS(f"✅ {device.name} is online and reachable")
                )
                
                # Try to get device info
                try:
                    zk_device = ZK(device.ip_address, port=device.port, timeout=10)
                    conn = zk_device.connect()
                    
                    if conn:
                        info = conn.get_device_info()
                        if info:
                            self.stdout.write(f"   Device Name: {getattr(info, 'device_name', 'Unknown')}")
                            self.stdout.write(f"   Firmware: {getattr(info, 'firmware_version', 'Unknown')}")
                            self.stdout.write(f"   Serial: {getattr(info, 'serial_number', 'Unknown')}")
                        
                        conn.disconnect()
                        
                except Exception as e:
                    self.stdout.write(f"   ⚠️  Could not get device info: {str(e)}")
                    
            else:
                self.stdout.write(
                    self.style.ERROR(f"❌ {device.name} is offline or unreachable")
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error testing {device.name}: {str(e)}")
            )
    
    def setup_all_devices(self, server_url, push_interval):
        """Setup all ZKTeco devices for push"""
        self.stdout.write("🔧 Setting up all ZKTeco devices for auto push...")
        
        devices = Device.objects.filter(device_type='zkteco', is_active=True)
        
        if not devices.exists():
            self.stdout.write(
                self.style.WARNING('No active ZKTeco devices found')
            )
            return
        
        setup_count = 0
        for device in devices:
            if self.setup_single_device(device, server_url, push_interval):
                setup_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'✅ Setup {setup_count}/{devices.count()} ZKTeco devices')
        )
    
    def setup_device_by_id(self, device_id, server_url, push_interval):
        """Setup specific device by ID"""
        try:
            device = Device.objects.get(id=device_id, device_type='zkteco')
            if self.setup_single_device(device, server_url, push_interval):
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Setup device {device.name}')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'❌ Failed to setup device {device.name}')
                )
        except Device.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'❌ ZKTeco device with ID {device_id} not found')
            )
    
    def setup_device_by_ip(self, device_ip, server_url, push_interval):
        """Setup specific device by IP"""
        try:
            device = Device.objects.get(ip_address=device_ip, device_type='zkteco')
            if self.setup_single_device(device, server_url, push_interval):
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Setup device {device.name}')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'❌ Failed to setup device {device.name}')
                )
        except Device.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'❌ ZKTeco device with IP {device_ip} not found')
            )
        except Device.MultipleObjectsReturned:
            self.stdout.write(
                self.style.ERROR(f'❌ Multiple ZKTeco devices found with IP {device_ip}')
            )
    
    def setup_single_device(self, device, server_url, push_interval):
        """Setup a single device for push"""
        try:
            self.stdout.write(f"🔧 Setting up {device.name} ({device.ip_address}:{device.port})...")
            
            # Test connection first
            if not improved_zkteco_service.test_device_connectivity(device.ip_address, device.port):
                self.stdout.write(
                    self.style.ERROR(f"❌ Cannot connect to {device.name}")
                )
                return False
            
            # Connect to device
            zk_device = ZK(device.ip_address, port=device.port, timeout=10)
            conn = zk_device.connect()
            
            if not conn:
                self.stdout.write(
                    self.style.ERROR(f"❌ Failed to connect to {device.name}")
                )
                return False
            
            try:
                # Get device info
                info = conn.get_device_info()
                if info:
                    device_name = getattr(info, 'device_name', device.name)
                    firmware = getattr(info, 'firmware_version', 'Unknown')
                    serial = getattr(info, 'serial_number', 'Unknown')
                    
                    self.stdout.write(f"   Device: {device_name}")
                    self.stdout.write(f"   Firmware: {firmware}")
                    self.stdout.write(f"   Serial: {serial}")
                
                # Configure push settings
                push_url = f"{server_url}/api/device/push-attendance/"
                
                # Note: ZKTeco devices don't have built-in push functionality like ESSL devices
                # We need to configure them to work with our pull-based system
                # or implement a custom push mechanism
                
                self.stdout.write(f"   Push URL: {push_url}")
                self.stdout.write(f"   Push Interval: {push_interval} seconds")
                
                # Update device settings
                device.device_status = 'online'
                device.sync_interval = push_interval
                device.last_sync = timezone.now()
                
                # Update device info if available
                if info:
                    device.serial_number = getattr(info, 'serial_number', device.serial_number)
                    device.firmware_version = getattr(info, 'firmware_version', device.firmware_version)
                
                device.save()
                
                self.stdout.write(
                    self.style.SUCCESS(f"✅ {device.name} configured successfully")
                )
                
                return True
                
            finally:
                conn.disconnect()
                
        except Exception as e:
            logger.error(f"Error setting up device {device.name}: {str(e)}")
            self.stdout.write(
                self.style.ERROR(f"❌ Error setting up {device.name}: {str(e)}")
            )
            return False
    
    def show_device_info(self, device):
        """Show detailed device information"""
        self.stdout.write(f"📱 Device Information: {device.name}")
        self.stdout.write(f"   IP: {device.ip_address}:{device.port}")
        self.stdout.write(f"   Office: {device.office.name if device.office else 'No Office'}")
        self.stdout.write(f"   Status: {device.device_status}")
        self.stdout.write(f"   Serial: {device.serial_number or 'Not set'}")
        self.stdout.write(f"   Firmware: {device.firmware_version or 'Not set'}")
        self.stdout.write(f"   Last Sync: {device.last_sync or 'Never'}")
        self.stdout.write("")
