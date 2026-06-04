#!/usr/bin/env python3
"""
Continuous Attendance Service Runner
This script runs the attendance service continuously until stopped
"""

import os
import sys
import django
import time
import signal
import logging

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'attendance_system.settings')
django.setup()

from core.management.commands.auto_fetch_attendance import AutoAttendanceService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/continuous_attendance_service.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ContinuousAttendanceService:
    def __init__(self, interval=30, device_timeout=60):
        self.interval = interval
        self.device_timeout = device_timeout
        self.service = AutoAttendanceService(interval=interval, device_timeout=device_timeout)
        self.running = False
        
    def start(self):
        """Start the continuous attendance service"""
        logger.info("Starting Continuous Attendance Service...")
        logger.info(f"Fetch interval: {self.interval} seconds")
        logger.info(f"Per-device timeout: {self.device_timeout} seconds")
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        try:
            # Start the service
            self.service.start()
            self.running = True
            
            logger.info("Service started successfully!")
            logger.info("Monitoring devices for attendance data...")
            logger.info("Press Ctrl+C to stop the service")
            
            # Keep running until interrupted
            while self.running and self.service.running:
                time.sleep(1)
                
                # Log periodic status every 5 minutes
                if int(time.time()) % 300 == 0:
                    stats = self.service.get_stats()
                    logger.info(f"Service Status - Fetches: {stats['total_fetches']}, "
                              f"Records: {stats['total_records']}, "
                              f"Duplicates: {stats['duplicates_prevented']}, "
                              f"Errors: {stats['errors']}")
                
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Service error: {str(e)}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the continuous attendance service"""
        if self.running:
            logger.info("Stopping Continuous Attendance Service...")
            self.running = False
            self.service.stop()
            logger.info("Service stopped successfully")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)

if __name__ == "__main__":
    # Get interval and per-device timeout from command line arguments or use defaults
    interval = 30
    device_timeout = 60
    if len(sys.argv) > 1:
        try:
            interval = int(sys.argv[1])
        except ValueError:
            logger.warning(f"Invalid interval '{sys.argv[1]}', using default: {interval}")
    if len(sys.argv) > 2:
        try:
            device_timeout = int(sys.argv[2])
        except ValueError:
            logger.warning(f"Invalid device timeout '{sys.argv[2]}', using default: {device_timeout}")
    
    # Create and start the service
    service = ContinuousAttendanceService(interval=interval, device_timeout=device_timeout)
    service.start()
