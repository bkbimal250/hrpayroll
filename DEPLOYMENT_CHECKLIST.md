# Salary System Deployment Checklist

##  **LOCAL DEVELOPMENT SETUP**

### Step 1: Run the Fix Script
```bash
# Run the deployment script
python deploy_salary_system.py
```

### Step 2: Test the System
```bash
# Test everything works
python test_salary_local.py
```

### Step 3: Verify Database
```bash
# Check if tables were created
python manage.py dbshell
# In MySQL:
SHOW TABLES LIKE 'core_salary%';
EXIT;
```

## 📤 **PUSH TO GITHUB**

### Step 4: Commit and Push
```bash
# Add all files
git add .

# Commit changes
git commit -m "Add comprehensive salary management system with auto-calculation"

# Push to GitHub
git push origin main
```

## 🖥️ **VPS DEPLOYMENT**

### Step 5: Pull on VPS
```bash
# SSH into VPS
ssh root@your-vps-ip
cd /var/www/EmployeeAttendance

# Pull latest changes
git pull origin main

# Activate virtual environment
source venv/bin/activate

# Apply migrations
python manage.py migrate core

# Restart Apache
sudo systemctl restart apache2
```

##  **VERIFICATION**

### Step 6: Test on VPS
```bash
# Test API endpoints
curl -H "Authorization: Bearer your-jwt-token" \
     http://your-domain.com/api/salaries/

# Check Apache logs
sudo tail -f /var/log/apache2/error.log
```

##  **EXPECTED RESULT**

After successful deployment, you should have:

-  `core_salary` table created
-  `core_salarytemplate` table created
-  All foreign key constraints working
-  API endpoints accessible
-  No MySQL constraint errors
-  Salary management system fully functional

## 🚨 **TROUBLESHOOTING**

### If Migration Fails on VPS:
```bash
# Drop problematic tables
mysql -u u434975676_bimal -p'DishaSolution@8989' u434975676_DOS << EOF
DROP TABLE IF EXISTS core_salarytemplate;
DROP TABLE IF EXISTS core_salary;
EOF

# Run migration again
python manage.py migrate core
```

### If API Endpoints Don't Work:
```bash
# Check Apache configuration
sudo apache2ctl configtest

# Restart Apache
sudo systemctl restart apache2

# Check Django logs
tail -f logs/django.log
```

## 📋 **FILES TO PUSH**

Make sure these files are included in your commit:

-  `core/models.py` (updated with Salary models)
-  `core/serializers.py` (updated with Salary serializers)
-  `core/salary_views.py` (new file)
-  `core/permissions.py` (new file)
-  `core/urls.py` (updated with Salary URLs)
-  `core/migrations/0004_add_salary_models.py` (new migration)

## 🎉 **SUCCESS INDICATORS**

You'll know the deployment is successful when:

1.  No MySQL constraint errors
2.  Salary API endpoints return 200 status
3.  Can create salary records through API
4.  Can create salary templates
5.  Auto-calculation works
6.  Role-based permissions work

## 📞 **SUPPORT**

If you encounter any issues:

1. Check the error logs
2. Verify database connection
3. Ensure all migrations are applied
4. Test the system step by step

The salary management system should now be fully functional! 