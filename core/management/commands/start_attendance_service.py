#!/usr/bin/env python3
"""
Management command to start the attendance service
This can be used for development or manual service management
"""

import os
import sys
import django
import logging
import signal
import time
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'attendance_system.settings')
django.setup()

from core.management.commands.auto_fetch_attendance import AutoAttendanceService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Start the automatic attendance fetching service'
    
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
            '--foreground',
            action='store_true',
            help='Run in foreground (default)'
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
        interval = options['interval']
        daemon_mode = options['daemon']
        foreground_mode = options['foreground']
        stop_service = options['stop']
        show_status = options['status']
        
        if show_status:
            self.show_service_status()
            return
        
        if stop_service:
            self.stop_service()
            return
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Create service instance
        self.service = AutoAttendanceService(interval=interval)
        
        if daemon_mode:
            self.run_daemon_mode()
        else:
            self.run_foreground_mode()
    
    def run_foreground_mode(self):
        """Run service in foreground mode"""
        self.stdout.write(
            self.style.SUCCESS(f"Starting attendance service (interval: {self.service.interval}s)")
        )
        self.stdout.write("Press Ctrl+C to stop")
        
        try:
            self.service.start()
            
            # Keep running until interrupted
            while self.service.running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.stdout.write("\nStopping service...")
            self.service.stop()
            self.stdout.write(
                self.style.SUCCESS("Service stopped")
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Service error: {str(e)}")
            )
            self.service.stop()
    
    def run_daemon_mode(self):
        """Run service in daemon mode"""
        try:
            import daemon
            import daemon.pidfile
            
            # Create PID file
            pid_file = '/tmp/attendance_service.pid'
            
            with daemon.DaemonContext(
                pidfile=daemon.pidfile.TimeoutPIDLockFile(pid_file),
                stdout=open('/tmp/attendance_service.out', 'w'),
                stderr=open('/tmp/attendance_service.err', 'w')
            ):
                self.service.start()
                
                # Keep running
                while self.service.running:
                    time.sleep(1)
                    
        except ImportError:
            self.stdout.write(
                self.style.ERROR("python-daemon library not available. Install with: pip install python-daemon")
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Daemon error: {str(e)}")
            )
    
    def stop_service(self):
        """Stop the running service"""
        try:
            # Try to read PID file
            pid_file = '/tmp/attendance_service.pid'
            if os.path.exists(pid_file):
                with open(pid_file, 'r') as f:
                    pid = int(f.read().strip())
                
                # Send SIGTERM to the process
                os.kill(pid, signal.SIGTERM)
                self.stdout.write(
                    self.style.SUCCESS(f"Sent stop signal to service (PID: {pid})")
                )
            else:
                self.stdout.write(
                    self.style.WARNING("No PID file found. Service may not be running.")
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error stopping service: {str(e)}")
            )
    
    def show_service_status(self):
        """Show service status"""
        try:
            # Check if PID file exists
            pid_file = '/tmp/attendance_service.pid'
            if os.path.exists(pid_file):
                with open(pid_file, 'r') as f:
                    pid = int(f.read().strip())
                
                # Check if process is running
                try:
                    os.kill(pid, 0)  # This will raise an exception if process doesn't exist
                    self.stdout.write(
                        self.style.SUCCESS(f"Service is running (PID: {pid})")
                    )
                except OSError:
                    self.stdout.write(
                        self.style.WARNING("PID file exists but process is not running")
                    )
            else:
                self.stdout.write(
                    self.style.WARNING("Service is not running (no PID file)")
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error checking service status: {str(e)}")
            )
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        if hasattr(self, 'service'):
            self.service.stop()
        sys.exit(0)
