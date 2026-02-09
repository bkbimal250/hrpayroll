# Salary Management System Documentation

## Overview

The Salary Management System is a comprehensive module integrated into the Employee Attendance System that provides automated salary calculation, approval workflows, and detailed reporting capabilities. The system automatically calculates salaries based on attendance data and supports role-based access control.

## 🏗️ System Architecture

### Core Components

1. **Salary Model** - Main salary data structure with auto-calculation
2. **SalaryTemplate Model** - Templates for different designations/offices
3. **Serializers** - Data validation and serialization
4. **Views** - API endpoints with role-based permissions
5. **Permissions** - Access control for different user roles

### Key Features

-  **Auto-calculation from attendance data**
-  **Role-based permissions (Admin/Manager/Accountant/Employee)**
-  **Salary templates for different designations**
-  **Approval workflow (Draft → Approved → Paid)**
-  **Bulk salary creation and processing**
-  **Comprehensive reporting and statistics**
-  **REST API endpoints for all operations**

##  Database Models

### Salary Model

```python
class Salary(models.Model):
    # Basic Information
    employee = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    basic_pay = models.DecimalField(max_digits=10, decimal_places=2)
    increment = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_days = models.PositiveIntegerField(default=30)
    worked_days = models.PositiveIntegerField(default=30)
    
    # Allowances
    house_rent_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    transport_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    medical_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_allowances = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Deductions
    deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    provident_fund = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    professional_tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    income_tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    balance_loan = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Status and Dates
    salary_month = models.DateField()
    pay_date = models.DateField(null=True, blank=True)
    paid_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=SALARY_STATUS_CHOICES, default='draft')
    
    # Auto-calculation
    is_auto_calculated = models.BooleanField(default=False)
    attendance_based = models.BooleanField(default=True)
```

### Auto-calculated Properties

The Salary model includes several auto-calculated properties:

- `final_salary` = basic_pay + increment
- `per_day_salary` = final_salary / total_days
- `gross_salary` = per_day_salary * worked_days
- `total_allowances` = sum of all allowances
- `total_deductions` = sum of all deductions
- `net_salary` = gross_salary + total_allowances - total_deductions
- `final_payable_amount` = net_salary - balance_loan

### SalaryTemplate Model

```python
class SalaryTemplate(models.Model):
    name = models.CharField(max_length=200)
    designation = models.ForeignKey(Designation, on_delete=models.CASCADE)
    office = models.ForeignKey(Office, on_delete=models.CASCADE)
    basic_pay = models.DecimalField(max_digits=10, decimal_places=2)
    house_rent_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    transport_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    medical_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_allowances = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    provident_fund_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=12.0)
    professional_tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
```

## 🔐 Role-Based Permissions

### User Roles and Access

| Role | Salary Access | Template Access | Approval Rights |
|------|---------------|-----------------|-----------------|
| **Admin** | All salaries | All templates | Can approve/reject |
| **Manager** | Office salaries only | Office templates only | Can approve/reject office salaries |
| **Accountant** | All salaries | All templates | Cannot approve/reject |
| **Employee** | Own salaries only | None | Cannot approve/reject |

### Permission Classes

- `IsAdminOrManager` - Admin and Manager only
- `IsAdminOrManagerOrAccountant` - Admin, Manager, and Accountant
- `IsAdminOrManagerOrEmployee` - Admin, Manager, and Employee
- `IsAdminOnly` - Admin only

##  API Endpoints

### Salary Management

| Method | Endpoint | Description | Permissions |
|--------|----------|-------------|-------------|
| GET | `/api/salaries/` | List all salaries | Admin/Manager/Accountant |
| POST | `/api/salaries/` | Create new salary | Admin/Manager/Accountant |
| GET | `/api/salaries/{id}/` | Get salary details | Admin/Manager/Accountant/Employee |
| PUT/PATCH | `/api/salaries/{id}/` | Update salary | Admin/Manager/Accountant |
| DELETE | `/api/salaries/{id}/` | Delete salary | Admin only |
| PATCH | `/api/salaries/{id}/approve/` | Approve/reject salary | Admin/Manager |
| PATCH | `/api/salaries/{id}/payment/` | Mark as paid | Admin/Manager/Accountant |

### Bulk Operations

| Method | Endpoint | Description | Permissions |
|--------|----------|-------------|-------------|
| POST | `/api/salaries/bulk-create/` | Create multiple salaries | Admin/Manager/Accountant |
| POST | `/api/salaries/auto-calculate/` | Auto-calculate from attendance | Admin/Manager/Accountant |
| PATCH | `/api/salaries/{id}/recalculate/` | Recalculate specific salary | Admin/Manager/Accountant |

### Reports and Statistics

| Method | Endpoint | Description | Permissions |
|--------|----------|-------------|-------------|
| GET | `/api/salaries/reports/` | Generate salary reports | Admin/Manager/Accountant |
| GET | `/api/salaries/summary/` | Get salary summary | Admin/Manager/Accountant |
| GET | `/api/salaries/statistics/` | Get detailed statistics | Admin/Manager/Accountant |
| GET | `/api/salaries/employee/{id}/history/` | Employee salary history | Admin/Manager/Employee |

### Salary Templates

| Method | Endpoint | Description | Permissions |
|--------|----------|-------------|-------------|
| GET | `/api/salary-templates/` | List templates | Admin/Manager/Accountant |
| POST | `/api/salary-templates/` | Create template | Admin/Manager/Accountant |
| GET | `/api/salary-templates/{id}/` | Get template details | Admin/Manager/Accountant |
| PUT/PATCH | `/api/salary-templates/{id}/` | Update template | Admin/Manager/Accountant |
| DELETE | `/api/salary-templates/{id}/` | Delete template | Admin only |

## 💼 Usage Examples

### 1. Creating a Salary

```python
# Using API
POST /api/salaries/
{
    "employee": "employee-uuid",
    "basic_pay": "50000.00",
    "increment": "5000.00",
    "total_days": 30,
    "worked_days": 28,
    "house_rent_allowance": "10000.00",
    "transport_allowance": "5000.00",
    "medical_allowance": "2000.00",
    "provident_fund": "6000.00",
    "professional_tax": "200.00",
    "salary_month": "2024-01-01",
    "attendance_based": true
}
```

### 2. Auto-calculating Salaries from Attendance

```python
# Using API
POST /api/salaries/auto-calculate/
{
    "salary_month": "2024-01-01",
    "office_id": "office-uuid",
    "template_id": "template-uuid"
}
```

### 3. Bulk Salary Creation

```python
# Using API
POST /api/salaries/bulk-create/
{
    "employee_ids": ["emp1-uuid", "emp2-uuid", "emp3-uuid"],
    "salary_month": "2024-01-01",
    "basic_pay": "50000.00",
    "increment": "5000.00",
    "attendance_based": true
}
```

### 4. Salary Approval Workflow

```python
# Step 1: Create salary (status: draft)
POST /api/salaries/ { ... }

# Step 2: Approve salary (status: approved)
PATCH /api/salaries/{id}/approve/
{
    "status": "approved"
}

# Step 3: Mark as paid (status: paid)
PATCH /api/salaries/{id}/payment/
{
    "paid_date": "2024-01-15",
    "payment_method": "bank_transfer"
}
```

### 5. Creating Salary Templates

```python
# Using API
POST /api/salary-templates/
{
    "name": "Senior Developer Template",
    "designation": "designation-uuid",
    "office": "office-uuid",
    "basic_pay": "70000.00",
    "house_rent_allowance": "14000.00",
    "transport_allowance": "7000.00",
    "medical_allowance": "3500.00",
    "provident_fund_percentage": "12.00",
    "professional_tax": "200.00"
}
```

##  Auto-calculation Logic

### Worked Days Calculation

The system automatically calculates worked days from attendance records:

```python
def calculate_worked_days_from_attendance(self):
    # Get attendance records for the salary month
    attendance_records = Attendance.objects.filter(
        user=self.employee,
        date__range=[start_date, end_date]
    )
    
    worked_days = 0
    for record in attendance_records:
        if record.status == 'present':
            if record.day_status == 'complete_day':
                worked_days += 1
            elif record.day_status == 'half_day':
                worked_days += 0.5
    
    self.worked_days = int(worked_days)
```

### Salary Calculation Formula

```
Final Salary = Basic Pay + Increment
Per Day Salary = Final Salary / Total Days
Gross Salary = Per Day Salary × Worked Days
Total Allowances = HRA + Transport + Medical + Other
Total Deductions = General + PF + Professional Tax + Income Tax + Other
Net Salary = Gross Salary + Total Allowances - Total Deductions
Final Payable = Net Salary - Loan Balance
```

##  Reporting Features

### Salary Summary

```python
GET /api/salaries/summary/
{
    "total_salaries": 150,
    "total_amount": 7500000.00,
    "paid_salaries": 120,
    "paid_amount": 6000000.00,
    "pending_salaries": 30,
    "pending_amount": 1500000.00,
    "average_salary": 50000.00,
    "highest_salary": 100000.00,
    "lowest_salary": 25000.00
}
```

### Salary Reports

```python
GET /api/salaries/reports/?year=2024&month=1&office_id=uuid&status=paid
{
    "summary": {
        "total_salaries": 50,
        "total_amount": 2500000.00,
        "paid_salaries": 45,
        "paid_amount": 2250000.00
    },
    "details": [
        {
            "employee_name": "John Doe",
            "basic_pay": 50000.00,
            "net_salary": 45000.00,
            "status": "paid"
        }
    ]
}
```

## 🔧 Configuration

### Environment Variables

```bash
# Database settings (already configured)
DB_ENGINE=django.db.backends.mysql
DB_NAME=your_database_name
DB_USER=your_username
DB_PASSWORD=your_password
DB_HOST=your_host
DB_PORT=3306

# JWT settings (already configured)
SECRET_KEY=your_secret_key
```

### Django Settings

The salary system integrates with existing Django settings:

```python
# In settings.py
INSTALLED_APPS = [
    'core.apps.CoreConfig',  # Already included
    # ... other apps
]

# Custom User Model (already configured)
AUTH_USER_MODEL = 'core.CustomUser'
```

##  Deployment

### 1. Database Migration

```bash
# Create and apply migrations
python manage.py makemigrations core
python manage.py migrate
```

### 2. Create Superuser

```bash
python manage.py createsuperuser
```

### 3. Test the System

```bash
# Run the test script
python test_salary_system.py
```

### 4. API Testing

```bash
# Test API endpoints
curl -H "Authorization: Bearer your-jwt-token" \
     -H "Content-Type: application/json" \
     http://localhost:8001/api/salaries/
```

##  Best Practices

### 1. Salary Creation

- Always use salary templates for consistent salary structures
- Enable `attendance_based` for automatic worked days calculation
- Set appropriate `total_days` based on company policy (usually 30)

### 2. Approval Workflow

- Create salaries in `draft` status
- Review and approve before marking as paid
- Use bulk operations for monthly salary processing

### 3. Data Validation

- Ensure `worked_days` never exceeds `total_days`
- Validate salary month is always the first day of the month
- Check employee role is 'employee' before creating salary

### 4. Performance Optimization

- Use `select_related()` for foreign key relationships
- Implement pagination for large salary lists
- Cache frequently accessed salary templates

## 🐛 Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all models are properly imported in `serializers.py`
2. **Permission Errors**: Check user roles and permissions
3. **Calculation Errors**: Verify attendance data exists for the salary month
4. **Template Errors**: Ensure designation and office match between template and employee

### Debug Commands

```bash
# Check salary calculations
python manage.py shell
>>> from core.models import Salary
>>> salary = Salary.objects.first()
>>> print(salary.get_salary_breakdown())

# Test auto-calculation
>>> salary.calculate_worked_days_from_attendance()
>>> print(salary.worked_days)
```

## 📚 API Documentation

### Authentication

All API endpoints require JWT authentication:

```bash
# Get JWT token
curl -X POST http://localhost:8001/api/token/ \
     -H "Content-Type: application/json" \
     -d '{"username": "your_username", "password": "your_password"}'

# Use token in requests
curl -H "Authorization: Bearer your-jwt-token" \
     http://localhost:8001/api/salaries/
```

### Response Formats

All API responses follow REST conventions:

```json
{
    "id": "uuid",
    "employee": "uuid",
    "basic_pay": "50000.00",
    "net_salary": "45000.00",
    "status": "approved",
    "created_at": "2024-01-01T00:00:00Z"
}
```

##  Future Enhancements

### Planned Features

1. **Salary Slip Generation** - PDF generation for salary slips
2. **Email Notifications** - Automatic salary notifications
3. **Advanced Reporting** - More detailed analytics and charts
4. **Payroll Integration** - Integration with external payroll systems
5. **Mobile App Support** - Mobile-friendly salary views

### Customization Options

1. **Custom Salary Components** - Add company-specific allowances/deductions
2. **Multiple Currency Support** - Support for different currencies
3. **Tax Calculations** - Advanced tax calculation modules
4. **Bonus Management** - Performance-based bonus calculations

---

## 📞 Support

For technical support or questions about the Salary Management System:

1. Check the test script: `python test_salary_system.py`
2. Review API documentation above
3. Check Django logs for error messages
4. Verify database migrations are applied

The Salary Management System is now fully integrated and ready for production use! 🎉
