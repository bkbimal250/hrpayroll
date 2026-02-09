from django.core.management.base import BaseCommand
from core.models import Designation, Department
import uuid

class Command(BaseCommand):
    help = 'Check specific department designations'

    def handle(self, *args, **kwargs):
        dept_id = 'd861ce30-02ac-4b9e-984e-5532900b93d6'
        
        try:
            dept = Department.objects.get(id=dept_id)
            self.stdout.write(f"\n✅ Found Department: {dept.name}")
            self.stdout.write(f"   ID: {dept.id}")
            
            # Try different ways to get designations
            self.stdout.write(f"\n📊 Designation Counts:")
            self.stdout.write(f"   All designations: {Designation.objects.count()}")
            self.stdout.write(f"   Active designations: {Designation.objects.filter(is_active=True).count()}")
            self.stdout.write(f"   Designations for this dept (via FK): {Designation.objects.filter(department=dept).count()}")
            self.stdout.write(f"   Designations for this dept (via ID): {Designation.objects.filter(department_id=dept.id).count()}")
            self.stdout.write(f"   Active designations for this dept: {Designation.objects.filter(department=dept, is_active=True).count()}")
            
            # List all designations for this department
            self.stdout.write(f"\n📋 Designations for {dept.name}:")
            desigs = Designation.objects.filter(department=dept, is_active=True)
            if desigs.exists():
                for d in desigs:
                    self.stdout.write(f"   - {d.name} (ID: {d.id}, Active: {d.is_active})")
            else:
                self.stdout.write("   ⚠️  NO ACTIVE DESIGNATIONS FOUND!")
                
            # Check if there are ANY designations with this department
            all_desigs = Designation.objects.filter(department=dept)
            if all_desigs.exists():
                self.stdout.write(f"\n📋 ALL Designations (including inactive):")
                for d in all_desigs:
                    status = "✓ Active" if d.is_active else "✗ Inactive"
                    self.stdout.write(f"   {status} - {d.name}")
                    
        except Department.DoesNotExist:
            self.stdout.write(f"\n❌ Department with ID {dept_id} NOT FOUND!")
            
        # Show sample of all designations
        self.stdout.write(f"\n📋 Sample of ALL Designations in Database:")
        for d in Designation.objects.all()[:10]:
            self.stdout.write(f"   - {d.name} → Dept: {d.department.name} (Dept ID: {d.department_id})")
