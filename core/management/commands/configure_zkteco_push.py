#!/usr/bin/env python3
"""
Management command to configure ZKTeco devices for auto push
"""

import os
import sys
import django
import logging
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'attendance_system.settings')
django.setup()

from core.models import Device, Office
from core.zkteco_push_service import zkteco_push_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Configure ZKTeco devices for auto push attendance data'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--device-id',
            type=str,
            help='Configure specific device by ID'
        )
        parser.add_argument(
            '--device-ip',
            type=str,
            help='Configure specific device by IP address'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Configure all ZKTeco devices'
        )
        parser.add_argument(
            '--status',
            action='store_true',
            help='Show current push configuration status'
        )
        parser.add_argument(
            '--server-url',
            type=str,
            help='Server URL for push endpoints (default: auto-detect)'
        )
        parser.add_argument(
            '--test-push',
            action='store_true',
            help='Test push functionality with sample data'
        )
    
    def handle(self, *args, **options):
        if options['status']:
            self.show_status()
            return
        
        if options['test_push']:
            self.test_push_functionality()
            return
        
        # Get server URL
        server_url = options.get('server_url')
        if not server_url:
            server_url = getattr(settings, 'SERVER_URL', 'http://localhost:8000')
        
        # Configure devices
        if options['all']:
            self.configure_all_devices(server_url)
        elif options['device_id']:
            self.configure_device_by_id(options['device_id'], server_url)
        elif options['device_ip']:
            self.configure_device_by_ip(options['device_ip'], server_url)
        else:
            self.stdout.write(
                self.style.ERROR('Please specify --all, --device-id, or --device-ip')
            )
    
    def configure_all_devices(self, server_url):
        """Configure all ZKTeco devices for push"""
        self.stdout.write("🔧 Configuring all ZKTeco devices for auto push...")
        
        devices = Device.objects.filter(device_type='zkteco', is_active=True)
        
        if not devices.exists():
            self.stdout.write(
                self.style.WARNING('No active ZKTeco devices found in database')
            )
            return
        
        configured_count = 0
        for device in devices:
            if self.configure_single_device(device, server_url):
                configured_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'Configured {configured_count}/{devices.count()} ZKTeco devices')
        )
    
    def configure_device_by_id(self, device_id, server_url):
        """Configure specific device by ID"""
        try:
            device = Device.objects.get(id=device_id, device_type='zkteco')
            if self.configure_single_device(device, server_url):
                self.stdout.write(
                    self.style.SUCCESS(f'Configured device {device.name}')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'Failed to configure device {device.name}')
                )
        except Device.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'ZKTeco device with ID {device_id} not found')
            )
    
    def configure_device_by_ip(self, device_ip, server_url):
        """Configure specific device by IP"""
        try:
            device = Device.objects.get(ip_address=device_ip, device_type='zkteco')
            if self.configure_single_device(device, server_url):
                self.stdout.write(
                    self.style.SUCCESS(f'Configured device {device.name}')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'Failed to configure device {device.name}')
                )
        except Device.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'ZKTeco device with IP {device_ip} not found')
            )
        except Device.MultipleObjectsReturned:
            self.stdout.write(
                self.style.ERROR(f'Multiple ZKTeco devices found with IP {device_ip}')
            )
    
    def configure_single_device(self, device, server_url):
        """Configure a single device for push"""
        try:
            push_url = f"{server_url}/api/device/push-attendance/"
            
            # Register device in push service
            success = zkteco_push_service.register_device_for_push(device, push_url)
            
            if success:
                self.stdout.write(f"Device: {device.name}")
                self.stdout.write(f"   IP: {device.ip_address}:{device.port}")
                self.stdout.write(f"   Office: {device.office.name if device.office else 'No Office'}")
                self.stdout.write(f"   Push URL: {push_url}")
                self.stdout.write("")
                
                # Update device settings for push
                device.device_status = 'online'
                device.sync_interval = 1  # Push every minute
                device.save(update_fields=['device_status', 'sync_interval'])
                
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Error configuring device {device.name}: {str(e)}")
            return False
    
    def show_status(self):
        """Show current push configuration status"""
        self.stdout.write("ZKTeco Push Configuration Status")
        self.stdout.write("=" * 50)
        
        # Get all ZKTeco devices
        devices = Device.objects.filter(device_type='zkteco')
        
        if not devices.exists():
            self.stdout.write(
                self.style.WARNING('No ZKTeco devices found in database')
            )
            return
        
        # Get push service status
        push_status = zkteco_push_service.get_all_push_status()
        
        self.stdout.write(f"Total ZKTeco devices: {devices.count()}")
        self.stdout.write(f"Registered for push: {push_status['total_devices']}")
        self.stdout.write("")
        
        for device in devices:
            status_icon = "Active" if device.is_active else "Inactive"
            push_status_text = "Push Enabled" if str(device.id) in push_status['devices'] else "Push Disabled"
            
            self.stdout.write(f"{status_icon} {push_status_text} {device.name}")
            self.stdout.write(f"   IP: {device.ip_address}:{device.port}")
            self.stdout.write(f"   Office: {device.office.name if device.office else 'No Office'}")
            self.stdout.write(f"   Status: {device.device_status}")
            self.stdout.write(f"   Last Sync: {device.last_sync or 'Never'}")
            
            if str(device.id) in push_status['devices']:
                device_push_info = push_status['devices'][str(device.id)]
                self.stdout.write(f"   Push URL: {device_push_info['push_url']}")
                self.stdout.write(f"   Last Push: {device_push_info['last_push'] or 'Never'}")
                self.stdout.write(f"   Push Count: {device_push_info['push_count']}")
            
            self.stdout.write("")
    
    def test_push_functionality(self):
        """Test push functionality with sample data"""
        self.stdout.write("Testing ZKTeco push functionality...")
        
        # Get first active ZKTeco device
        device = Device.objects.filter(device_type='zkteco', is_active=True).first()
        
        if not device:
            self.stdout.write(
                self.style.ERROR('No active ZKTeco devices found for testing')
            )
            return
        
        # Create sample attendance data
        sample_data = [
            {
                'user_id': '1',
                'timestamp': timezone.now().isoformat(),
                'type': 'check_in',
                'status': 0
            }
        ]
        
        # Test push processing
        result = zkteco_push_service.process_push_data(device, sample_data)
        
        if result['success']:
            self.stdout.write(
                self.style.SUCCESS(f"Push test successful for {device.name}")
            )
            self.stdout.write(f"   Processed: {result['processed_count']} records")
            self.stdout.write(f"   Errors: {result['error_count']} records")
        else:
            self.stdout.write(
                self.style.ERROR(f"Push test failed for {device.name}")
            )
            self.stdout.write(f"   Error: {result.get('error', 'Unknown error')}")
