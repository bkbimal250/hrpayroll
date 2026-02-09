from django.core.management.base import BaseCommand
from core.models import Designation, Department

class Command(BaseCommand):
    help = 'Check designation-department relationships'

    def handle(self, *args, **kwargs):
        self.stdout.write("=" * 70)
        self.stdout.write("DESIGNATION-DEPARTMENT RELATIONSHIP CHECK")
        self.stdout.write("=" * 70)
        
        # The department IDs from the API logs
        dept_ids = [
            'd861ce30-02ac-4b9e-984e-5532900b93d6',
            '4a5e9f01-9599-4069-baab-720cac7538fb'
        ]
        
        for dept_id in dept_ids:
            try:
                dept = Department.objects.get(id=dept_id)
                active_desigs = dept.designations.filter(is_active=True)
                count = active_desigs.count()
                
                self.stdout.write(f"\n{dept.name} (ID: {dept_id})")
                self.stdout.write(f"  Active Designations: {count}")
                
                if count > 0:
                    for desig in active_desigs:
                        self.stdout.write(f"    - {desig.name}")
                else:
                    self.stdout.write("    ⚠️  NO DESIGNATIONS FOUND!")
                    
            except Department.DoesNotExist:
                self.stdout.write(f"\n❌ Department {dept_id} NOT FOUND in database")
        
        # Show all departments with their designation counts
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write("ALL DEPARTMENTS:")
        self.stdout.write("=" * 70)
        
        for dept in Department.objects.all():
            count = dept.designations.filter(is_active=True).count()
            self.stdout.write(f"{dept.name:40} | {count:2} designations | ID: {dept.id}")
