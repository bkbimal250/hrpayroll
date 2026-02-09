from django.core.management.base import BaseCommand
from core.models import CustomUser
import uuid

class Command(BaseCommand):
    help = 'Add biometric IDs to existing users for ESSL device integration'

    def handle(self, *args, **options):
        self.stdout.write('Adding biometric IDs to existing users...')

        # Get all users without biometric IDs
        users_without_biometric = CustomUser.objects.filter(
            biometric_id__isnull=True
        ).exclude(role='admin')

        if not users_without_biometric.exists():
            self.stdout.write(self.style.SUCCESS('All users already have biometric IDs'))
            return

        updated_count = 0
        for user in users_without_biometric:
            # Generate a unique biometric ID based on user info
            if user.employee_id:
                biometric_id = f"{user.employee_id[:10]}{str(user.id)[-3:]}"
            else:
                biometric_id = f"EMP{str(user.id).zfill(3)}"
            
            user.biometric_id = biometric_id
            user.save()
            updated_count += 1
            
            self.stdout.write(f'Added biometric ID "{biometric_id}" to user "{user.get_full_name()}"')

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully added biometric IDs to {updated_count} users'
            )
        )
