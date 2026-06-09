#!/usr/bin/env python3
"""
Automatic Attendance Fetching Service
24/7 background service that continuously fetches attendance data from all devices
Prevents duplicates and handles both historical and real-time data
"""

import os
import sys
import django
import logging
import time
import signal
import threading
import json
import multiprocessing
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import connection, close_old_connections
from django.conf import settings
from django.core.cache import cache

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'attendance_system.settings')
django.setup()

from core.attendance_processing import record_raw_punch
from core.models import Device, Attendance, Office, ESSLAttendanceLog

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/auto_fetch_attendance.log', encoding='utf-8'),
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


def _run_device_fetch_worker(device_id, result_queue, lookback_hours):
    """Fetch one device in an isolated process so a stuck device cannot block the service."""
    try:
        close_old_connections()
        device = Device.objects.get(id=device_id)
        service = AutoAttendanceService(
            interval=0,
            use_process_isolation=False,
            lookback_hours=lookback_hours,
        )
        service._fetch_device_data(device)
        result_queue.put({
            'success': True,
            'device_id': str(device_id),
            'stats': service.get_stats(),
        })
    except Exception as exc:
        result_queue.put({
            'success': False,
            'device_id': str(device_id),
            'error': str(exc),
        })
    finally:
        close_old_connections()


class AutoAttendanceService:
    """Automatic attendance fetching service with duplicate prevention"""
    
    def __init__(
        self,
        interval=30,
        max_workers=3,
        device_timeout=60,
        use_process_isolation=True,
        lookback_hours=24,
    ):
        self.interval = interval
        self.max_workers = max_workers
        self.device_timeout = device_timeout
        self.use_process_isolation = use_process_isolation
        self.lookback_hours = lookback_hours
        self.running = False
        self.thread = None
        self.devices = []
        self.device_connections = {}
        self.last_fetch_times = {}
        self.last_attendance_hashes = {}  # Store hashes to prevent duplicates
        self.processing_lock = threading.Lock()
        self.stats = {
            'total_fetches': 0,
            'total_records': 0,
            'duplicates_prevented': 0,
            'errors': 0,
            'last_successful_fetch': None
        }
        
    def start(self):
        """Start the automatic attendance fetching service"""
        if self.running:
            logger.warning("Service is already running")
            return
            
        logger.info("Starting automatic attendance fetching service...")
        self.running = True
        
        # Get all active devices
        self.devices = list(Device.objects.filter(is_active=True))
        logger.info(f"Found {len(self.devices)} active devices")
        
        # Initialize device connections and tracking
        for device in self.devices:
            self.device_connections[device.id] = None
            self.last_fetch_times[device.id] = None
            self.last_attendance_hashes[device.id] = set()
        
        # Start the background thread
        self.thread = threading.Thread(target=self._run_service, daemon=True)
        self.thread.start()
        
        logger.info(f"Service started. Fetching data every {self.interval} seconds")
        
    def stop(self):
        """Stop the automatic attendance fetching service"""
        logger.info("Stopping automatic attendance fetching service...")
        self.running = False
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
            
        # Cleanup device connections
        self.cleanup_connections()
        logger.info("Service stopped")
        
    def cleanup_connections(self):
        """Clean up all device connections"""
        for device_id, conn in self.device_connections.items():
            if conn:
                try:
                    if hasattr(conn, 'disconnect'):
                        conn.disconnect()
                    logger.info(f"Disconnected from device {device_id}")
                except Exception as e:
                    logger.warning(f"Error disconnecting from device {device_id}: {str(e)}")
                finally:
                    self.device_connections[device_id] = None
                    
    def _run_service(self):
        """Main service loop"""
        logger.info("Starting main service loop...")
        
        while self.running:
            try:
                with self.processing_lock:
                    self._fetch_all_devices()
                    
                # Update stats
                self.stats['total_fetches'] += 1
                self.stats['last_successful_fetch'] = timezone.now()
                
                # Log periodic stats
                if self.stats['total_fetches'] % 10 == 0:  # Every 10 fetches
                    self._log_stats()
                    
                time.sleep(self.interval)
                
            except KeyboardInterrupt:
                logger.info("Received interrupt signal")
                break
            except Exception as e:
                logger.error(f"Error in service loop: {str(e)}")
                self.stats['errors'] += 1
                time.sleep(self.interval)
                
    def _fetch_all_devices(self):
        """Fetch data from all devices"""
        current_time = timezone.now()
        
        for device in self.devices:
            try:
                # Check if device should be fetched (respect device-specific intervals)
                if self._should_fetch_device(device, current_time):
                    self._fetch_device_with_guard(device)
                    
            except Exception as e:
                logger.error(f"Error fetching from device {device.name}: {str(e)}")
                self.stats['errors'] += 1

    def _fetch_device_with_guard(self, device):
        """Fetch one device with a hard timeout so the next device still runs."""
        if not self.use_process_isolation:
            self._fetch_device_data(device)
            return

        start_method = 'fork' if 'fork' in multiprocessing.get_all_start_methods() else 'spawn'
        ctx = multiprocessing.get_context(start_method)
        result_queue = ctx.Queue(maxsize=1)
        process = ctx.Process(
            target=_run_device_fetch_worker,
            args=(device.id, result_queue, self.lookback_hours),
            daemon=True,
        )

        logger.info(f"Starting isolated fetch for {device.name} with {self.device_timeout}s timeout")
        process.start()
        process.join(self.device_timeout)

        if process.is_alive():
            logger.error(
                f"Device fetch timed out for {device.name} after {self.device_timeout}s. "
                "Skipping this device and continuing."
            )
            process.terminate()
            process.join(timeout=5)
            if process.is_alive():
                process.kill()
                process.join(timeout=2)

            self.stats['errors'] += 1
            self.last_fetch_times[device.id] = timezone.now()
            result_queue.close()
            close_old_connections()
            return

        result = None
        try:
            result = result_queue.get(timeout=1)
        except Exception:
            pass
        finally:
            result_queue.close()

        self.last_fetch_times[device.id] = timezone.now()
        close_old_connections()

        if not result:
            self.stats['errors'] += 1
            logger.error(f"Device fetch for {device.name} ended without a result")
            return

        if not result.get('success'):
            self.stats['errors'] += 1
            logger.error(f"Device fetch failed for {device.name}: {result.get('error', 'Unknown error')}")
            return

        child_stats = result.get('stats') or {}
        self.stats['total_records'] += child_stats.get('total_records', 0)
        self.stats['duplicates_prevented'] += child_stats.get('duplicates_prevented', 0)
        self.stats['errors'] += child_stats.get('errors', 0)
        logger.info(f"Device fetch completed for {device.name}")
                
    def _should_fetch_device(self, device, current_time):
        """Check if device should be fetched based on last fetch time"""
        last_fetch = self.last_fetch_times.get(device.id)
        
        if not last_fetch:
            return True
            
        # Device-specific fetch interval (default 30 seconds)
        device_interval = getattr(device, 'fetch_interval', self.interval)
        
        return (current_time - last_fetch).total_seconds() >= device_interval
        
    def _fetch_device_data(self, device):
        """Fetch data from a specific device"""
        try:
            logger.info(f"Fetching data from {device.name} ({device.device_type})")
            
            if device.device_type == 'zkteco':
                self._fetch_zkteco_data(device)
            elif device.device_type == 'essl':
                self._fetch_essl_data(device)
            else:
                logger.warning(f"Unknown device type: {device.device_type}")
                
            # Update last fetch time
            self.last_fetch_times[device.id] = timezone.now()
            
        except Exception as e:
            logger.error(f"Error fetching data from {device.name}: {str(e)}")
            raise
            
    def _fetch_zkteco_data(self, device):
        """Fetch data from ZKTeco device"""
        if not ZK_AVAILABLE:
            logger.error("pyzk library not available for ZKTeco device")
            return
            
        conn = None
        try:
            # Connect to device
            conn = self._connect_zkteco_device(device)
            if not conn:
                return
                
            # Get attendance data
            attendance_logs = conn.get_attendance()
            if not attendance_logs:
                logger.info(f"No new attendance data from {device.name}")
                return
                
            # Process attendance records
            self._process_zkteco_attendance(device, attendance_logs)
            
        except Exception as e:
            logger.error(f"Error fetching ZKTeco data from {device.name}: {str(e)}")
            raise
        finally:
            if conn:
                try:
                    conn.disconnect()
                except:
                    pass
                    
    def _connect_zkteco_device(self, device):
        """Connect to ZKTeco device"""
        try:
            zk = ZK(device.ip_address, port=device.port, timeout=10, force_udp=False, verbose=False)
            conn = zk.connect()
            if conn:
                logger.info(f"Connected to ZKTeco device {device.name}")
                return conn
            else:
                logger.error(f"Failed to connect to ZKTeco device {device.name}")
                return None
        except Exception as e:
            logger.error(f"Connection error to ZKTeco device {device.name}: {str(e)}")
            return None
            
    def _process_zkteco_attendance(self, device, attendance_logs):
        """Process ZKTeco attendance records with duplicate prevention"""
        if not attendance_logs:
            return
            
        logger.info(f"Processing {len(attendance_logs)} attendance records from {device.name}")
        
        new_records = 0
        duplicates = 0
        unmatched_users = {}
        
        cutoff_date = timezone.now() - timedelta(hours=self.lookback_hours)
        recent_logs = []
        
        for log in attendance_logs:
            try:
                log_timestamp = log.timestamp
                if timezone.is_naive(log_timestamp):
                    log_timestamp = timezone.make_aware(log_timestamp, timezone.get_current_timezone())
                
                if log_timestamp < cutoff_date:
                    continue

                recent_logs.append((log, log_timestamp))
            except Exception as e:
                logger.error(f"Error reading attendance timestamp from {device.name}: {str(e)}")

        recent_logs.sort(key=lambda item: item[1])
        logger.info(
            f"Found {len(recent_logs)} logs from the last {self.lookback_hours} hours on {device.name}"
        )

        for log, log_timestamp in recent_logs:
            try:
                save_result = self._save_zkteco_attendance(device, log, log_timestamp)
                if save_result == 'saved':
                    new_records += 1
                elif save_result == 'duplicate':
                    duplicates += 1
                elif save_result == 'unmatched':
                    biometric_id = str(getattr(log, 'user_id', 'unknown'))
                    unmatched_users[biometric_id] = unmatched_users.get(biometric_id, 0) + 1
            except Exception as e:
                logger.error(f"Error processing attendance record: {str(e)}")
                
        # Update stats
        self.stats['total_records'] += new_records
        self.stats['duplicates_prevented'] += duplicates
        
        logger.info(f"Processed {new_records} new records, skipped {duplicates} already-saved scans from {device.name}")
        if unmatched_users:
            unmatched_summary = ", ".join(
                f"{biometric_id} ({count} scans)" for biometric_id, count in sorted(unmatched_users.items())
            )
            logger.warning(f"Unmatched biometric IDs on {device.name}: {unmatched_summary}")
        
    def _create_attendance_hash(self, device_id, log, timestamp=None):
        """Create unique hash for attendance record"""
        # Use provided timestamp or fall back to log.timestamp
        ts = timestamp if timestamp is not None else log.timestamp
        # Create hash based on device, user, and timestamp
        hash_data = f"{device_id}_{log.user_id}_{ts}_{log.status}"
        return hash(hash_data)
        
    def _save_zkteco_attendance(self, device, log, timestamp=None):
        """Save ZKTeco attendance record to database with proper check-in/check-out logic"""
        try:
            # Use provided timestamp or make log.timestamp timezone-aware
            if timestamp is None:
                timestamp = log.timestamp
                if timezone.is_naive(timestamp):
                    timestamp = timezone.make_aware(timestamp, timezone.get_current_timezone())

            raw_log, created, result = record_raw_punch(
                device=device,
                biometric_id=log.user_id,
                device_user_id=getattr(log, 'uid', None) or log.user_id,
                employee_id=str(getattr(log, 'employee_id', '') or ''),
                punch_time=timestamp,
                punch_type='out' if getattr(log, 'status', 0) == 1 else 'in',
                source='zkteco_fetch',
                raw_payload={
                    'user_id': str(log.user_id),
                    'uid': getattr(log, 'uid', None),
                    'status': getattr(log, 'status', None),
                    'timestamp': timestamp.isoformat(),
                },
            )

            if result == 'unmatched':
                logger.warning(
                    f"Unmatched biometric ID {log.user_id} on {device.name} "
                    f"({device.ip_address}:{device.port}) at {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                )
                return 'unmatched'
            if result == 'duplicate':
                return 'duplicate'
            return 'saved'
                
        except Exception as e:
            logger.error(f"Error saving attendance record: {str(e)}")
            return 'error'
            
    def _fetch_essl_data(self, device):
        """Fetch data from ESSL device"""
        try:
            # Import ESSL service
            from core.essl_service import essl_service
            
            # Get attendance data from ESSL device
            attendance_data = essl_service.get_device_attendance(device)
            
            if attendance_data:
                self._process_essl_attendance(device, attendance_data)
            else:
                logger.info(f"No new attendance data from ESSL device {device.name}")
                
        except Exception as e:
            logger.error(f"Error fetching ESSL data from {device.name}: {str(e)}")
            raise
            
    def _process_essl_attendance(self, device, attendance_data):
        """Process ESSL attendance records"""
        logger.info(f" Processing {len(attendance_data)} ESSL attendance records from {device.name}")
        
        new_records = 0
        duplicates = 0
        unmatched_records = 0
        
        for record in attendance_data:
            try:
                save_result = self._save_essl_attendance(device, record)
                if save_result == 'saved':
                    new_records += 1
                elif save_result == 'duplicate':
                    duplicates += 1
                elif save_result == 'unmatched':
                    unmatched_records += 1
            except Exception as e:
                logger.error(f"Error processing ESSL attendance record: {str(e)}")
                
        self.stats['total_records'] += new_records
        self.stats['duplicates_prevented'] += duplicates
        logger.info(
            f"Processed {new_records} new ESSL records from {device.name}; "
            f"{duplicates} duplicates skipped, {unmatched_records} unmatched"
        )
        
    def _save_essl_attendance(self, device, record):
        """Save ESSL raw punch first, then derive final attendance through shared safety rules."""
        try:
            timestamp_str = record.get('timestamp')
            if not timestamp_str:
                return 'error'
                
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                if timezone.is_naive(timestamp):
                    timestamp = timezone.make_aware(timestamp, timezone.get_current_timezone())
            except:
                logger.error(f"Invalid timestamp format: {timestamp_str}")
                return 'error'

            biometric_id = str(
                record.get('biometric_id')
                or record.get('device_user_id')
                or record.get('employee_id')
                or ''
            )
            if not biometric_id:
                logger.warning(f"ESSL record missing biometric/device/employee ID at {timestamp_str}")
                return 'error'

            raw_log, created, result = record_raw_punch(
                device=device,
                biometric_id=biometric_id,
                device_user_id=str(record.get('device_user_id') or biometric_id),
                employee_id=str(record.get('employee_id') or ''),
                punch_time=timestamp,
                punch_type=record.get('punch_type') or record.get('status') or 'in',
                source='import',
                raw_payload={
                    **record,
                    'source_command': 'auto_fetch_attendance_essl',
                },
            )

            if result == 'unmatched':
                logger.warning(
                    f"Unmatched ESSL biometric ID {biometric_id} on {device.name} "
                    f"at {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                )
                return 'unmatched'
            if result == 'duplicate':
                return 'duplicate'
            return 'saved' if created else 'duplicate'
                
        except Exception as e:
            logger.error(f"Error saving ESSL attendance record: {str(e)}")
            return 'error'
            
    def _log_stats(self):
        """Log service statistics"""
        logger.info(f" Service Stats - Fetches: {self.stats['total_fetches']}, "
                   f"Records: {self.stats['total_records']}, "
                   f"Duplicates Prevented: {self.stats['duplicates_prevented']}, "
                   f"Errors: {self.stats['errors']}")
        
        # Log attendance logic summary
        logger.info(" ATTENDANCE LOGIC: First scan = Check-in, Last scan = Check-out")
        logger.info(" Every biometric scan is logged, but only first/last affect attendance times")
                    
    def get_stats(self):
        """Get current service statistics"""
        return self.stats.copy()

# Global service instance
auto_attendance_service = AutoAttendanceService()

class Command(BaseCommand):
    help = 'Start automatic attendance fetching service'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=30,
            help='Fetch interval in seconds (default: 30)'
        )
        parser.add_argument(
            '--device-timeout',
            type=int,
            default=60,
            help='Maximum seconds allowed for one device fetch before skipping it (default: 60)'
        )
        parser.add_argument(
            '--lookback-hours',
            type=int,
            default=24,
            help='Only process device scans from the last N hours (default: 24)'
        )
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='Run as daemon process'
        )
        parser.add_argument(
            '--stop',
            action='store_true',
            help='Stop the running service'
        )
        parser.add_argument(
            '--status',
            action='store_true',
            help='Show service status'
        )
        
    def handle(self, *args, **options):
        if options['stop']:
            self._stop_service()
        elif options['status']:
            self._show_status()
        else:
            self._start_service(options)
            
    def _start_service(self, options):
        """Start the automatic attendance fetching service"""
        try:
            interval = options['interval']
            daemon = options['daemon']
            device_timeout = options['device_timeout']
            lookback_hours = options['lookback_hours']
            
            logger.info(
                f"Starting automatic attendance fetching service with {interval}s interval "
                f"{device_timeout}s per-device timeout, and {lookback_hours}h lookback..."
            )
            
            # Initialize service
            auto_attendance_service.interval = interval
            auto_attendance_service.device_timeout = device_timeout
            auto_attendance_service.lookback_hours = lookback_hours
            auto_attendance_service.start()
            
            if daemon:
                logger.info("Service started in daemon mode")
                return
            else:
                # Run in foreground
                try:
                    while auto_attendance_service.running:
                        time.sleep(1)
                except KeyboardInterrupt:
                    logger.info("Received interrupt signal")
                    auto_attendance_service.stop()
                    
        except Exception as e:
            logger.error(f"Error starting service: {str(e)}")
            raise CommandError(f"Failed to start service: {str(e)}")
            
    def _stop_service(self):
        """Stop the automatic attendance fetching service"""
        try:
            auto_attendance_service.stop()
            self.stdout.write(
                self.style.SUCCESS('Automatic attendance fetching service stopped')
            )
        except Exception as e:
            logger.error(f"Error stopping service: {str(e)}")
            raise CommandError(f"Failed to stop service: {str(e)}")
            
    def _show_status(self):
        """Show service status"""
        stats = auto_attendance_service.get_stats()
        
        self.stdout.write(" Automatic Attendance Fetching Service Status")
        self.stdout.write("=" * 50)
        self.stdout.write(f"Running: {'Yes' if auto_attendance_service.running else 'No'}")
        self.stdout.write(f"Interval: {auto_attendance_service.interval} seconds")
        self.stdout.write(f"Total Fetches: {stats['total_fetches']}")
        self.stdout.write(f"Total Records: {stats['total_records']}")
        self.stdout.write(f"Duplicates Prevented: {stats['duplicates_prevented']}")
        self.stdout.write(f"Errors: {stats['errors']}")
        
        if stats['last_successful_fetch']:
            self.stdout.write(f"Last Successful Fetch: {stats['last_successful_fetch']}")
            
        # Show device status
        self.stdout.write("\n Device Status:")
        for device in auto_attendance_service.devices:
            last_fetch = auto_attendance_service.last_fetch_times.get(device.id)
            status = " Active" if last_fetch else " Inactive"
            self.stdout.write(f"  {device.name} ({device.device_type}): {status}")
            
        self.stdout.write("=" * 50)
