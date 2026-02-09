# Salary System Deployment Fix Guide

## 🚨 Issue: Foreign Key Constraint Error

**Error:** `django.db.utils.OperationalError: (1005, 'Can't create table core_salarytemplate (errno: 150 "Foreign key constraint is incorrectly formed")')`

## 🔧 Solution Steps

### Step 1: Connect to Your VPS Server

```bash
ssh root@your-vps-ip
cd /var/www/EmployeeAttendance
source venv/bin/activate
```

### Step 2: Drop Problematic Tables

```bash
# Connect to MySQL and drop the problematic tables
mysql -u u434975676_bimal -p'DishaSolution@8989' u434975676_DOS

# In MySQL console, run:
DROP TABLE IF EXISTS core_salarytemplate;
DROP TABLE IF EXISTS core_salary;
EXIT;
```

### Step 3: Clean Up Migration Files

```bash
# Remove any problematic migration files
rm -f core/migrations/0004_*.py
rm -f core/migrations/0005_*.py
```

### Step 4: Create Fresh Migration

```bash
# Create a new migration for salary models
python manage.py makemigrations core --name add_salary_models
```

### Step 5: Apply Migrations

```bash
# Apply the migration
python manage.py migrate core
```

### Step 6: Verify Installation

```bash
# Check if tables were created successfully
python manage.py dbshell
# In MySQL console:
SHOW TABLES LIKE 'core_salary%';
EXIT;
```

### Step 7: Test the System

```bash
# Test the salary models
python -c "
from core.models import Salary, SalaryTemplate
print(' Salary models imported successfully')
print(' Salary system is working!')
"
```

### Step 8: Restart Apache

```bash
sudo systemctl restart apache2
```

##  Alternative: Automated Fix Script

If you prefer an automated approach, use the provided script:

```bash
# Make the script executable
chmod +x deploy_salary_fix.sh

# Run the fix script
./deploy_salary_fix.sh
```

## Troubleshooting

### If Migration Still Fails:

1. **Check Database Connection:**
   ```bash
   python manage.py dbshell
   ```

2. **Check Existing Tables:**
   ```sql
   SHOW TABLES;
   ```

3. **Check Foreign Key Constraints:**
   ```sql
   SELECT * FROM information_schema.KEY_COLUMN_USAGE 
   WHERE TABLE_SCHEMA = 'u434975676_DOS' 
   AND TABLE_NAME IN ('core_salary', 'core_salarytemplate');
   ```

### If Tables Exist But Are Empty:

```bash
# Reset the migration
python manage.py migrate core 0003 --fake
python manage.py migrate core
```

## 📋 Verification Checklist

After running the fix, verify these components:

- [ ] `core_salary` table exists
- [ ] `core_salarytemplate` table exists
- [ ] Foreign key constraints are properly set
- [ ] Django models can be imported
- [ ] API endpoints are accessible
- [ ] Apache is running without errors

##  Expected Result

After successful deployment, you should be able to:

1. **Access Salary API endpoints:**
   ```bash
   curl -H "Authorization: Bearer your-jwt-token" \
        http://your-domain.com/api/salaries/
   ```

2. **Create salary records through Django admin or API**

3. **Use all salary management features**

## 📞 Support

If you encounter any issues:

1. Check Apache error logs: `sudo tail -f /var/log/apache2/error.log`
2. Check Django logs: `tail -f logs/django.log`
3. Verify database connection: `python manage.py dbshell`

The salary system should now be fully functional! 🎉
