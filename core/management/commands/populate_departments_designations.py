from django.core.management.base import BaseCommand
from core.models import Department, Designation


class Command(BaseCommand):
    help = 'Populate departments and designations with predefined data'

    def handle(self, *args, **options):
        self.stdout.write('Creating departments and designations...')
        
        # Department and designation data
        departments_data = {
            'Digital Marketing': [
                'Digital Marketing Executive',
                'Social Media Manager',
                'Content Strategist',
                'Performance Marketing Specialist',
                'Email Marketing Specialist',
                'PPC Specialist',
                'Digital Marketing Manager'
            ],
            'SEO (Search Engine Optimization)': [
                'SEO Executive',
                'SEO Analyst',
                'SEO Specialist',
                'Technical SEO Expert',
                'On-Page SEO Analyst',
                'Off-Page SEO Executive',
                'SEO Manager'
            ],
            'HR (Human Resources)': [
                'HR Executive',
                'Recruitment Specialist',
                'HR Generalist',
                'Payroll Executive',
                'HR Coordinator',
                'Talent Acquisition Executive',
                'HR Manager'
            ],
            'Back Office': [
                'Back Office Executive',
                'Operations Assistant',
                'Documentation Executive',
                'Record Management Officer',
                'Office Coordinator',
                'MIS Executive',
                'Back Office Manager'
            ],
            'Data Entry': [
                'Data Entry Operator',
                'Data Entry Executive',
                'Typist',
                'Data Processor',
                'Data Entry Clerk',
                'Junior Data Entry Operator',
                'Senior Data Entry Operator'
            ],
            'Housekeeping': [
                'Housekeeping Staff',
                'Office Boy / Office Assistant',
                'Cleaner',
                'Janitor',
                'Maintenance Assistant',
                'Housekeeping Supervisor',
                'Facility Manager'
            ],
            'IT (Information Technology)': [
                'IT Support Executive',
                'System Administrator',
                'Software Developer',
                'Web Developer',
                'Helpdesk Technician',
                'IT Technician',
                'IT Manager'
            ],
            'Networking': [
                'Network Engineer',
                'Network Support Technician',
                'Network Administrator',
                'Network Security Specialist',
                'Network Analyst',
                'Junior Network Engineer',
                'Senior Network Engineer'
            ],
            'Manager': [
                'Project Manager',
                'Operations Manager',
                'HR Manager',
                'Marketing Manager',
                'IT Manager',
                'Office Manager',
                'General Manager'
            ]
        }
        
        created_departments = 0
        created_designations = 0
        
        for dept_name, designations in departments_data.items():
            # Create or get department
            department, created = Department.objects.get_or_create(
                name=dept_name,
                defaults={
                    'description': f'Department for {dept_name}',
                    'is_active': True
                }
            )
            
            if created:
                created_departments += 1
                self.stdout.write(f'Created department: {dept_name}')
            else:
                self.stdout.write(f'Department already exists: {dept_name}')
            
            # Create designations for this department
            for designation_name in designations:
                designation, created = Designation.objects.get_or_create(
                    name=designation_name,
                    department=department,
                    defaults={
                        'description': f'{designation_name} in {dept_name}',
                        'is_active': True
                    }
                )
                
                if created:
                    created_designations += 1
                    self.stdout.write(f'  Created designation: {designation_name}')
                else:
                    self.stdout.write(f'  Designation already exists: {designation_name}')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {created_departments} departments and {created_designations} designations'
            )
        )
