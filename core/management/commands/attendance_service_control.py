#!/usr/bin/env python3
"""
Control attendance service and provide alternatives
"""

import os
import sys
import django
import signal
import psutil
from django.core.management.base import BaseCommand

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'attendance_system.settings')
django.setup()

class Command(BaseCommand):
    help = 'Control attendance service and provide alternatives'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--stop-service',
            action='store_true',
            help='Stop any running attendance service'
        )
        parser.add_argument(
            '--check-status',
            action='store_true',
            help='Check if attendance service is running'
        )
        parser.add_argument(
            '--show-alternatives',
            action='store_true',
            help='Show alternative commands for working with attendance data'
        )
        
    def handle(self, *args, **options):
        if options['stop_service']:
            self.stop_attendance_service()
        elif options['check_status']:
            self.check_service_status()
        elif options['show_alternatives']:
            self.show_alternatives()
        else:
            self.show_help()
            
    def stop_attendance_service(self):
        """Stop any running attendance service processes"""
        self.stdout.write(" Stopping attendance service...")
        
        # Look for Python processes running attendance service
        stopped_count = 0
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] == 'python.exe' or proc.info['name'] == 'python':
                    cmdline = ' '.join(proc.info['cmdline'])
                    if 'start_attendance_service' in cmdline:
                        self.stdout.write(f"Found attendance service process: PID {proc.info['pid']}")
                        proc.terminate()
                        stopped_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
                
        if stopped_count > 0:
            self.stdout.write(f"Stopped {stopped_count} attendance service process(es)")
        else:
            self.stdout.write("No running attendance service found")
            
    def check_service_status(self):
        """Check if attendance service is running"""
        self.stdout.write("Checking attendance service status...")
        
        running_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] == 'python.exe' or proc.info['name'] == 'python':
                    cmdline = ' '.join(proc.info['cmdline'])
                    if 'start_attendance_service' in cmdline:
                        running_processes.append({
                            'pid': proc.info['pid'],
                            'cmdline': cmdline
                        })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
                
        if running_processes:
            self.stdout.write("⚠️  Attendance service is running:")
            for proc in running_processes:
                self.stdout.write(f"  PID {proc['pid']}: {proc['cmdline']}")
        else:
            self.stdout.write("No attendance service is currently running")
            
    def show_alternatives(self):
        """Show alternative commands for working with attendance data"""
        self.stdout.write("\n Alternative Commands for Attendance Data")
        self.stdout.write("=" * 60)
        self.stdout.write("\n View Attendance Data:")
        self.stdout.write("  python manage.py view_attendance_data --today")
        self.stdout.write("  python manage.py view_attendance_data --date 2025-01-15")
        self.stdout.write("  python manage.py view_attendance_data --user john_doe")
        self.stdout.write("  python manage.py view_attendance_data --summary")
        self.stdout.write("  python manage.py view_attendance_data --recent 20")
        
        self.stdout.write("\n🔧 Manage Attendance Data:")
        self.stdout.write("  python manage.py manage_attendance_data --list-users")
        self.stdout.write("  python manage.py manage_attendance_data --attendance-stats")
        self.stdout.write("  python manage.py manage_attendance_data --fix-missing-checkouts")
        self.stdout.write("  python manage.py manage_attendance_data --export-today")
        self.stdout.write("  python manage.py manage_attendance_data --cleanup-duplicates")
        
        self.stdout.write("\n Device Management:")
        self.stdout.write("  python manage.py map_and_fetch_attendance --list-devices")
        self.stdout.write("  python manage.py map_and_fetch_attendance --map-users")
        
        self.stdout.write("\n💡 Why these alternatives?")
        self.stdout.write("  - No device connection required")
        self.stdout.write("  - Works with existing data")
        self.stdout.write("  - No biometric ID mismatch errors")
        self.stdout.write("  - Faster and more reliable")
        
    def show_help(self):
        """Show help information"""
        self.stdout.write("\n🎛️  Attendance Service Control")
        self.stdout.write("=" * 40)
        self.stdout.write("--stop-service        Stop running attendance service")
        self.stdout.write("--check-status        Check if service is running")
        self.stdout.write("--show-alternatives   Show alternative commands")
        self.stdout.write("\nExample usage:")
        self.stdout.write("python manage.py attendance_service_control --stop-service")
        self.stdout.write("python manage.py attendance_service_control --show-alternatives")
