#!/usr/bin/env python3
"""
Improved Automatic ZKTeco Data Fetching Service
24/7 background service that properly handles check-in and check-out times
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/zkteco_auto_fetch_improved.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

try:
    from zk import ZK
except ImportError:
    logger.error("pyzk library not found. Please install it with: pip install pyzk")
    ZK = None

class ImprovedAutoFetchService:
    """Improved automatic ZKTeco data fetching service with proper check-in/check-out handling"""
    
    def __init__(self, interval=30, fetch_days=10):
        self.interval = interval
        self.fetch_days = fetch_days  # Number of days to fetch (default: 10)
        self.running = False
        self.thread = None
        self.devices = []
        self.last_fetch_times = {}
        self.device_connections = {}
        self.last_attendance_data = {}  # Store last known attendance data per device
        
    def start(self):
        """Start the automatic fetching service"""
        if self.running:
            logger.warning("Service is already running")
            return
            
        logger.info(" Starting improved automatic ZKTeco data fetching service...")
        self.running = True
        
        # Get all active ZKTeco devices
        self.devices = list(Device.objects.filter(
            device_type='zkteco',
            is_active=True
        ))
        
        logger.info(f" Found {len(self.devices)} active ZKTeco devices")
        
        # Initialize device connections
        for device in self.devices:
            self.device_connections[device.id] = None
        
        # Start the background thread
        self.thread = threading.Thread(target=self._run_service, daemon=True)
        self.thread.start()
        
        logger.info(f"[START] Service started. Fetching data every {self.interval} seconds (last {self.fetch_days} days only)")
        
    def stop(self):
        """Stop the automatic fetching service"""
        logger.info("[STOP] Stopping improved automatic ZKTeco data fetching service...")
        self.running = False
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
            
        # Cleanup device connections
        self.cleanup_connections()
        logger.info("[STOP] Service stopped")
        
    def cleanup_connections(self):
        """Clean up all device connections"""
        for device_id, conn in self.device_connections.items():
            if conn:
                try:
                    conn.disconnect()
                    logger.info(f"[DISCONNECT] Disconnected from device {device_id}")
                except:
                    pass
                self.device_connections[device_id] = None
        
    def connect_to_device(self, device):
        """Connect to a ZKTeco device with improved error handling"""
        try:
            if not ZK:
                logger.error("pyzk library not available")
                return None
                
            # Check if we already have a connection
            if self.device_connections.get(device.id):
                try:
                    # Test if connection is still alive
                    self.device_connections[device.id].get_time()
                    return self.device_connections[device.id]
                except:
                    # Connection is dead, remove it
                    logger.warning(f"[WARNING] Dead connection detected for {device.name}, reconnecting...")
                    self.device_connections[device.id] = None
                
            # Create new connection with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    zk = ZK(device.ip_address, port=device.port, timeout=10)
                    conn = zk.connect()
                    
                    if conn:
                        self.device_connections[device.id] = conn
                        logger.info(f"[CONNECT] Connected to {device.name} ({device.ip_address}:{device.port})")
                        return conn
                    else:
                        logger.warning(f"[WARNING] Failed to connect to {device.name} (attempt {attempt + 1}/{max_retries})")
                        
                except Exception as e:
                    logger.warning(f"[WARNING] Connection attempt {attempt + 1} failed for {device.name}: {str(e)}")
                    if attempt < max_retries - 1:
                        time.sleep(2)  # Wait before retry
                        
            logger.error(f"[ERROR] Failed to connect to {device.name} after {max_retries} attempts")
            return None
                
        except Exception as e:
            logger.error(f"[ERROR] Connection error to {device.name}: {str(e)}")
            return None
    
    def get_device_attendance(self, conn, device):
        """Get attendance records from device (last 10 days only)"""
        try:
            # Get all attendance logs from device
            all_attendance_logs = conn.get_attendance()
            logger.info(f"[DATA] Found {len(all_attendance_logs)} total attendance records on {device.name}")
            
            # Filter to last N days only (configurable)
            from datetime import datetime, timedelta
            cutoff_date = datetime.now() - timedelta(days=self.fetch_days)
            
            filtered_logs = []
            for log in all_attendance_logs:
                if log.timestamp >= cutoff_date:
                    filtered_logs.append(log)
            
            logger.info(f"[DATA] Filtered to {len(filtered_logs)} records from last {self.fetch_days} days on {device.name}")
            return filtered_logs
            
        except Exception as e:
            logger.error(f"[ERROR] Error getting attendance from {device.name}: {str(e)}")
            return []
    
    def process_attendance_records(self, logs, device):
        """Process attendance records with proper check-in/check-out logic"""
        if not logs:
            return 0, 0
            
        synced_count = 0
        error_count = 0
        
        # Group logs by user and date
        user_date_logs = {}
        
        for log in logs:
            user_id = log.user_id
            date = log.timestamp.date()
            key = (user_id, date)
            
            if key not in user_date_logs:
                user_date_logs[key] = []
            user_date_logs[key].append(log)
        
        # Process each user's logs for each date
        for (user_id, date), user_logs in user_date_logs.items():
            try:
                # Find user in database
                try:
                    user = CustomUser.objects.get(employee_id=str(user_id))
                except CustomUser.DoesNotExist:
                    logger.warning(f"[WARNING] User with employee_id {user_id} not found")
                    error_count += 1
                    continue
                
                # Sort logs by timestamp
                user_logs.sort(key=lambda x: x.timestamp)
                
                # Get or create attendance record
                attendance, created = Attendance.objects.get_or_create(
                    user=user,
                    date=date,
                    defaults={
                        'status': 'Present',
                        'device': device
                    }
                )
                
                # Process check-in and check-out times with improved logic
                check_in_time = None
                check_out_time = None
                
                # Sort logs by timestamp to ensure proper order
                user_logs.sort(key=lambda x: x.timestamp)
                
                if len(user_logs) == 1:
                    # Single log - determine by time of day
                    timestamp = user_logs[0].timestamp
                    if timestamp.hour < 12:  # Morning - likely check-in
                        check_in_time = timestamp
                    else:  # Afternoon/Evening - likely check-out
                        check_out_time = timestamp
                else:
                    # Multiple logs - use alternating pattern
                    for i, log in enumerate(user_logs):
                        timestamp = log.timestamp
                        
                        if i == 0:
                            # First log is always check-in
                            check_in_time = timestamp
                        elif i == len(user_logs) - 1:
                            # Last log is always check-out
                            check_out_time = timestamp
                        else:
                            # Middle logs - determine by time gap
                            prev_log = user_logs[i-1]
                            time_gap = (timestamp - prev_log.timestamp).total_seconds() / 3600  # hours
                            
                            if time_gap > 1:  # More than 1 hour gap - likely check-out then check-in
                                if not check_out_time:
                                    check_out_time = prev_log.timestamp
                                check_in_time = timestamp
                            else:
                                # Short gap - might be multiple check-ins or check-outs
                                # Keep the latest times
                                if timestamp.hour < 12:
                                    check_in_time = timestamp
                                else:
                                    check_out_time = timestamp
                
                # Update attendance record with improved logic
                updated = False
                
                # Update check-in time (allow updates if new time is earlier)
                if check_in_time:
                    # Make timezone-aware for comparison
                    if timezone.is_naive(check_in_time):
                        check_in_time = timezone.make_aware(check_in_time, timezone.get_current_timezone())
                    
                    if not attendance.check_in_time:
                        attendance.check_in_time = check_in_time
                        updated = True
                        logger.info(f"[CHECKIN] {user.get_full_name()} at {check_in_time.strftime('%H:%M')}")
                    else:
                        # Make existing time timezone-aware for comparison
                        existing_checkin = attendance.check_in_time
                        if timezone.is_naive(existing_checkin):
                            existing_checkin = timezone.make_aware(existing_checkin, timezone.get_current_timezone())
                        
                        if check_in_time < existing_checkin:
                            attendance.check_in_time = check_in_time
                            updated = True
                            logger.info(f"[CHECKIN] {user.get_full_name()} at {check_in_time.strftime('%H:%M')}")
                
                # Update check-out time (allow updates if new time is later)
                if check_out_time:
                    # Make timezone-aware for comparison
                    if timezone.is_naive(check_out_time):
                        check_out_time = timezone.make_aware(check_out_time, timezone.get_current_timezone())
                    
                    if not attendance.check_out_time:
                        attendance.check_out_time = check_out_time
                        updated = True
                        logger.info(f"[CHECKOUT] {user.get_full_name()} at {check_out_time.strftime('%H:%M')}")
                    else:
                        # Make existing time timezone-aware for comparison
                        existing_checkout = attendance.check_out_time
                        if timezone.is_naive(existing_checkout):
                            existing_checkout = timezone.make_aware(existing_checkout, timezone.get_current_timezone())
                        
                        if check_out_time > existing_checkout:
                            attendance.check_out_time = check_out_time
                            updated = True
                            logger.info(f"[CHECKOUT] {user.get_full_name()} at {check_out_time.strftime('%H:%M')}")
                
                # Calculate total hours if both times are available
                if attendance.check_in_time and attendance.check_out_time:
                    # Ensure both times are timezone-aware
                    checkin_time = attendance.check_in_time
                    checkout_time = attendance.check_out_time
                    
                    if timezone.is_naive(checkin_time):
                        checkin_time = timezone.make_aware(checkin_time, timezone.get_current_timezone())
                    if timezone.is_naive(checkout_time):
                        checkout_time = timezone.make_aware(checkout_time, timezone.get_current_timezone())
                    
                    time_diff = checkout_time - checkin_time
                    total_hours = time_diff.total_seconds() / 3600
                    attendance.total_hours = round(total_hours, 2)
                    updated = True
                
                if updated:
                    attendance.device = device
                    attendance.save()
                    synced_count += 1
                
            except Exception as e:
                logger.error(f"[ERROR] Error processing attendance for user {user_id}: {str(e)}")
                error_count += 1
        
        return synced_count, error_count
    
    def should_fetch_from_device(self, device):
        """Check if we should fetch data from this device based on last fetch time"""
        current_time = datetime.now()
        last_fetch = self.last_fetch_times.get(device.id)
        
        if not last_fetch:
            return True
            
        # Check if enough time has passed since last fetch
        time_since_last_fetch = (current_time - last_fetch).seconds
        return time_since_last_fetch >= self.interval
    
    def _run_service(self):
        """Main service loop"""
        logger.info("[SERVICE] Starting main service loop...")
        
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
                
    def _fetch_all_devices(self):
        """Fetch data from all devices"""
        current_time = timezone.now()
        
        for device in self.devices:
            try:
                # Check if we should fetch from this device
                if not self.should_fetch_from_device(device):
                    continue
                    
                logger.info(f"[FETCH] Fetching data from device: {device.name} ({device.ip_address})")
                
                # Connect to device
                conn = self.connect_to_device(device)
                if not conn:
                    continue
                
                # Get attendance data
                attendance_logs = self.get_device_attendance(conn, device)
                
                if attendance_logs:
                    # Process attendance records
                    synced_count, error_count = self.process_attendance_records(attendance_logs, device)
                    
                    logger.info(f"[SYNC] {device.name}: {synced_count} synced, {error_count} errors")
                    
                    # Update device last sync time
                    device.last_sync = current_time
                    device.save(update_fields=['last_sync'])
                    
                else:
                    logger.warning(f"[WARNING] No data fetched from device {device.name}")
                    
                # Update last fetch time
                self.last_fetch_times[device.id] = current_time
                
            except Exception as e:
                logger.error(f"[ERROR] Error fetching from device {device.name}: {str(e)}")
                
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
            'interval': self.interval,
            'fetch_days': self.fetch_days,
            'active_connections': len([conn for conn in self.device_connections.values() if conn])
        }

# Global service instance with optimized settings
improved_auto_fetch_service = ImprovedAutoFetchService(interval=30, fetch_days=10)

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    improved_auto_fetch_service.stop()
    sys.exit(0)

class Command(BaseCommand):
    help = 'Improved automatic ZKTeco data fetching service with proper check-in/check-out handling'
    
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
            status = improved_auto_fetch_service.get_status()
            self.stdout.write(
                self.style.SUCCESS(f"Service Status: {'Running' if status['running'] else 'Stopped'}")
            )
            self.stdout.write(f"Devices: {status['devices_count']}")
            self.stdout.write(f"Active Connections: {status['active_connections']}")
            self.stdout.write(f"Interval: {status['interval']} seconds")
            return
            
        if stop_service:
            improved_auto_fetch_service.stop()
            self.stdout.write(
                self.style.SUCCESS("Service stopped")
            )
            return
            
        # Configure service
        improved_auto_fetch_service.interval = interval
        
        if daemon_mode:
            # Run as daemon
            import daemon
            with daemon.DaemonContext():
                improved_auto_fetch_service.start()
                try:
                    while improved_auto_fetch_service.running:
                        time.sleep(1)
                except KeyboardInterrupt:
                    improved_auto_fetch_service.stop()
        else:
            # Run in foreground
            self.stdout.write(
                self.style.SUCCESS(f"Starting improved automatic ZKTeco data fetching (interval: {interval}s)")
            )
            self.stdout.write("Press Ctrl+C to stop")
            
            improved_auto_fetch_service.start()
            
            try:
                while improved_auto_fetch_service.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.stdout.write("\nStopping service...")
                improved_auto_fetch_service.stop()
                self.stdout.write(
                    self.style.SUCCESS("Service stopped")
                )
