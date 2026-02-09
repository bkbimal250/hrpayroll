#!/usr/bin/env python3
"""
Automatic ZKTeco Data Fetching Service
Continuously fetches attendance data from all ZKTeco devices in the background
"""

import os
import sys
import django
import logging
import time
import signal
import threading
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'attendance_system.settings')
django.setup()

from core.models import Device, CustomUser, Attendance, Office
from core.zkteco_service import zkteco_service
from core.db_manager import db_manager, with_db_connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/zkteco_auto_fetch.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AutoFetchService:
    """Automatic ZKTeco data fetching service"""
    
    def __init__(self, interval=30):  # Fetch every 30 seconds
        self.interval = interval
        self.running = False
        self.thread = None
        self.devices = []
        self.last_fetch_times = {}
        
    def start(self):
        """Start the automatic fetching service"""
        if self.running:
            logger.warning("Service is already running")
            return
            
        logger.info("Starting automatic ZKTeco data fetching service...")
        self.running = True
        
        # Get all active ZKTeco devices
        self.devices = list(Device.objects.filter(
            device_type='zkteco',
            is_active=True
        ))
        
        logger.info(f"Found {len(self.devices)} active ZKTeco devices")
        
        # Start the background thread
        self.thread = threading.Thread(target=self._run_service, daemon=True)
        self.thread.start()
        
        logger.info(f"Service started. Fetching data every {self.interval} seconds")
        
    def stop(self):
        """Stop the automatic fetching service"""
        logger.info("Stopping automatic ZKTeco data fetching service...")
        self.running = False
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
            
        # Cleanup device connections
        zkteco_service.cleanup_connections()
        logger.info("Service stopped")
        
    def _run_service(self):
        """Main service loop"""
        while self.running:
            try:
                self._fetch_all_devices()
                time.sleep(self.interval)
            except KeyboardInterrupt:
                logger.info("Received interrupt signal")
                break
            except Exception as e:
                logger.error(f"Error in service loop: {str(e)}")
                time.sleep(self.interval)
                
    @with_db_connection
    def _fetch_all_devices(self):
        """Fetch data from all devices"""
        current_time = timezone.now()
        
        # Optimize connections before processing
        db_manager.optimize_connections()
        
        for device in self.devices:
            try:
                # Check if we should fetch from this device
                last_fetch = self.last_fetch_times.get(device.id)
                if last_fetch and (current_time - last_fetch).seconds < self.interval:
                    continue
                    
                logger.info(f"Fetching data from device: {device.name} ({device.ip_address})")
                
                # Fetch attendance data from device
                attendance_logs = zkteco_service.fetch_attendance_from_device(
                    device.ip_address, 
                    device.port
                )
                
                if attendance_logs:
                    # Sync to database
                    device_info = {
                        'ip_address': device.ip_address,
                        'port': device.port,
                        'name': device.name,
                        'office': device.office
                    }
                    
                    synced_count, error_count = zkteco_service.sync_attendance_to_database(
                        attendance_logs, device_info
                    )
                    
                    logger.info(f"Device {device.name}: Synced {synced_count} records, {error_count} errors")
                    
                    # Update device last sync time
                    device.last_sync = current_time
                    device.save(update_fields=['last_sync'])
                    
                else:
                    logger.warning(f"No data fetched from device {device.name}")
                    
                # Update last fetch time
                self.last_fetch_times[device.id] = current_time
                
            except Exception as e:
                logger.error(f"Error fetching from device {device.name}: {str(e)}")
        
        # Clean up connections after processing
        db_manager.close_idle_connections()
                
    def get_status(self):
        """Get service status"""
        # Load devices if not loaded
        if not hasattr(self, 'devices') or not self.devices:
            self.devices = list(Device.objects.filter(
                device_type='zkteco',
                is_active=True
            ))
            
        return {
            'running': self.running,
            'devices_count': len(self.devices),
            'last_fetch_times': self.last_fetch_times,
            'interval': self.interval
        }

# Global service instance
auto_fetch_service = AutoFetchService()

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    auto_fetch_service.stop()
    sys.exit(0)

class Command(BaseCommand):
    help = 'Automatically fetch attendance data from ZKTeco devices in the background'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=30,
            help='Fetch interval in seconds (default: 30)'
        )
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='Run as daemon (background process)'
        )
        parser.add_argument(
            '--status',
            action='store_true',
            help='Show service status'
        )
        parser.add_argument(
            '--stop',
            action='store_true',
            help='Stop the service'
        )
        
    def handle(self, *args, **options):
        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        interval = options['interval']
        daemon_mode = options['daemon']
        show_status = options['status']
        stop_service = options['stop']
        
        if show_status:
            status = auto_fetch_service.get_status()
            self.stdout.write(
                self.style.SUCCESS(f"Service Status: {'Running' if status['running'] else 'Stopped'}")
            )
            self.stdout.write(f"Devices: {status['devices_count']}")
            self.stdout.write(f"Interval: {status['interval']} seconds")
            return
            
        if stop_service:
            auto_fetch_service.stop()
            self.stdout.write(
                self.style.SUCCESS("Service stopped")
            )
            return
            
        # Configure service
        auto_fetch_service.interval = interval
        
        if daemon_mode:
            # Run as daemon
            import daemon
            with daemon.DaemonContext():
                auto_fetch_service.start()
                try:
                    while auto_fetch_service.running:
                        time.sleep(1)
                except KeyboardInterrupt:
                    auto_fetch_service.stop()
        else:
            # Run in foreground
            self.stdout.write(
                self.style.SUCCESS(f"Starting automatic ZKTeco data fetching (interval: {interval}s)")
            )
            self.stdout.write("Press Ctrl+C to stop")
            
            auto_fetch_service.start()
            
            try:
                while auto_fetch_service.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.stdout.write("\nStopping service...")
                auto_fetch_service.stop()
                self.stdout.write(
                    self.style.SUCCESS("Service stopped")
                )
