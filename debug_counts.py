import os
import django
import uuid

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'attendance_system.settings')
django.setup()

from core.models import CustomUser, EmployeeShiftAssignment

def test():
    # Disha Office ID
    disha_id = "e0721755-bb9a-44bf-a49a-dc1a8777a51d"
    
    print(f"Debug Counts for Office ID: {disha_id}")
    
    total_emps = CustomUser.objects.filter(office__id=disha_id, role='employee', is_active=True).count()
    print(f"Total Active Employees in Office: {total_emps}")

    assigned_count = EmployeeShiftAssignment.objects.filter(shift__office__id=disha_id, is_active=True).count()
    print(f"Total Active Assignments in Office: {assigned_count}")
    
    unassigned_users = CustomUser.objects.filter(
        office__id=disha_id, 
        role='employee', 
        is_active=True
    ).exclude(
        shift_assignments__is_active=True
    )
    
    print(f"Unassigned Employees Query Count: {unassigned_users.count()}")
    
    if unassigned_users.count() > 0:
        print("Unassigned Employee Names:")
        for u in unassigned_users:
            print(f"- {u.get_full_name()} ({u.id})")
    else:
        print("No unassigned employees found.")

    # Check if any employees are assigned to MULTIPLE active shifts (which shouldn't happen but...)
    # or if employees are assigned to shifts in OTHER offices
    print("\nDeep Dive on 'Missing' Employees:")
    # Get all employees
    all_emps = CustomUser.objects.filter(office__id=disha_id, role='employee', is_active=True)
    for emp in all_emps:
        assignments = EmployeeShiftAssignment.objects.filter(employee=emp, is_active=True)
        if assignments.exists():
            for a in assignments:
                print(f"Emp {emp.get_full_name()} is assigned to {a.shift.name} (Office: {a.shift.office.name})")

if __name__ == "__main__":
    test()
