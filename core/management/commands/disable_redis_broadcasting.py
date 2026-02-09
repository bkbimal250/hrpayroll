#!/usr/bin/env python3
"""
Disable Redis Broadcasting for Attendance Commands
This command temporarily disables Redis/WebSocket broadcasting to prevent connection issues
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'attendance_system.settings')
django.setup()

from django.core.management.base import BaseCommand
from django.db.models.signals import post_save
from core.signals import attendance_saved
from core.models import Attendance

class Command(BaseCommand):
    help = 'Disable Redis broadcasting for attendance commands'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--enable',
            action='store_true',
            help='Re-enable Redis broadcasting'
        )
        parser.add_argument(
            '--status',
            action='store_true',
            help='Show current status'
        )
    
    def handle(self, *args, **options):
        if options['enable']:
            self.enable_broadcasting()
        elif options['status']:
            self.show_status()
        else:
            self.disable_broadcasting()
    
    def disable_broadcasting(self):
        """Disable Redis broadcasting"""
        try:
            post_save.disconnect(attendance_saved, sender=Attendance)
            self.stdout.write(
                self.style.SUCCESS("Redis broadcasting disabled")
            )
            self.stdout.write("   Attendance updates will not be broadcast via WebSocket")
            self.stdout.write("   This prevents Redis connection errors during bulk operations")
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f" Broadcasting may already be disabled: {str(e)}")
            )
    
    def enable_broadcasting(self):
        """Re-enable Redis broadcasting"""
        try:
            post_save.connect(attendance_saved, sender=Attendance)
            self.stdout.write(
                self.style.SUCCESS("Redis broadcasting enabled")
            )
            self.stdout.write("   Attendance updates will be broadcast via WebSocket")
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"  Broadcasting may already be enabled: {str(e)}")
            )
    
    def show_status(self):
        """Show current broadcasting status"""
        # Check if signal is connected
        receivers = post_save._live_receivers(sender=Attendance)
        is_connected = any(
            receiver[1] == attendance_saved for receiver in receivers
        )
        
        if is_connected:
            self.stdout.write("Redis broadcasting: ENABLED")
            self.stdout.write("   Attendance updates will be broadcast via WebSocket")
        else:
            self.stdout.write("Redis broadcasting: DISABLED")
            self.stdout.write("   Attendance updates will NOT be broadcast via WebSocket")
        
        self.stdout.write("\nCommands:")
        self.stdout.write("  python manage.py disable_redis_broadcasting          # Disable")
        self.stdout.write("  python manage.py disable_redis_broadcasting --enable  # Enable")
        self.stdout.write("  python manage.py disable_redis_broadcasting --status  # Status")
