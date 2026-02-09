from django.core.management.base import BaseCommand
from django.db import connection
from core.models import Attendance
from django.utils import timezone

class Command(BaseCommand):
    help = 'Clean up duplicate attendance records for the same user on the same date'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No records will be deleted'))
        
        try:
            with connection.cursor() as cursor:
                # Find duplicate records
                cursor.execute("""
                    SELECT user_id, date, COUNT(*) as count
                    FROM core_attendance 
                    GROUP BY user_id, date 
                    HAVING COUNT(*) > 1
                    ORDER BY user_id, date
                """)
                
                duplicate_groups = cursor.fetchall()
                
                if not duplicate_groups:
                    self.stdout.write(self.style.SUCCESS('No duplicate records found'))
                    return
                
                self.stdout.write(f'Found {len(duplicate_groups)} duplicate attendance groups:')
                
                total_to_delete = 0
                for user_id, date, count in duplicate_groups:
                    self.stdout.write(f'   User {user_id} on {date}: {count} records')
                    total_to_delete += (count - 1)  # Keep 1, delete the rest
                
                if not dry_run:
                    self.stdout.write('\n🧹 Cleaning up duplicates...')
                    
                    cleaned_count = 0
                    for user_id, date, count in duplicate_groups:
                        # Get all records for this user on this date
                        records = Attendance.objects.filter(
                            user_id=user_id, 
                            date=date
                        ).order_by('-created_at')
                        
                        if records.count() > 1:
                            # Keep the most recent record, delete others
                            keep_record = records.first()  # Most recent
                            delete_records = records.exclude(id=keep_record.id)
                            delete_count = delete_records.count()
                            
                            if not dry_run:
                                delete_records.delete()
                            
                            cleaned_count += delete_count
                            self.stdout.write(
                                f'   Kept record {keep_record.id}, would delete {delete_count} duplicates'
                            )
                    
                    self.stdout.write(self.style.SUCCESS(f'Cleaned up {cleaned_count} duplicate records'))
                else:
                    self.stdout.write(f'\nWould delete {total_to_delete} duplicate records')
                    self.stdout.write(self.style.WARNING('Run without --dry-run to actually delete duplicates'))
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {e}'))
            return False
        
        return True
