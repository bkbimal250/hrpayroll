"""
Management command to reset database connections.
Use this when you encounter connection limit issues.
"""

from django.core.management.base import BaseCommand
from django.db import connections
from core.db_connection_manager import reset_database_connections, get_database_status
import time

class Command(BaseCommand):
    help = 'Reset database connections to resolve connection limit issues'

    def add_arguments(self, parser):
        parser.add_argument(
            '--wait',
            type=int,
            default=5,
            help='Wait time in seconds before reconnecting (default: 5)'
        )
        parser.add_argument(
            '--status',
            action='store_true',
            help='Show database connection status'
        )

    def handle(self, *args, **options):
        if options['status']:
            self.show_status()
            return
        
        wait_time = options['wait']
        
        self.stdout.write(
            self.style.WARNING('🔄 Resetting database connections...')
        )
        
        # Show current status
        self.show_status()
        
        # Reset connections
        reset_database_connections()
        
        # Wait
        if wait_time > 0:
            self.stdout.write(f'⏳ Waiting {wait_time} seconds...')
            time.sleep(wait_time)
        
        # Show status after reset
        self.stdout.write(
            self.style.SUCCESS('✅ Database connections reset complete!')
        )
        self.show_status()
        
        self.stdout.write(
            self.style.SUCCESS('\n🚀 You can now try starting the Django server again.')
        )

    def show_status(self):
        """Show current database connection status."""
        self.stdout.write('\n📊 Database Connection Status:')
        self.stdout.write('-' * 50)
        
        status = get_database_status()
        for alias, info in status.items():
            status_icon = '✅' if info['connected'] else '❌'
            self.stdout.write(
                f'{status_icon} {alias}: {info["vendor"]} - '
                f'{info["settings"]["host"]}:{info["settings"]["port"]}'
            )
        
        self.stdout.write('-' * 50)
