# VPS Setup Steps - Complete Configuration Guide

##  **Step-by-Step VPS Configuration**

### **Step 1: Pull Latest Code**
```bash
cd /var/www/EmployeeAttendance
git pull origin main
```

### **Step 2: Setup Push Endpoint for ZKTeco Devices**
```bash
# Copy push configuration
sudo cp apache2_push_virtualhost.conf /etc/apache2/sites-available/attendance-push.conf

# Enable push site
sudo a2ensite attendance-push.conf

# Test configuration
sudo apache2ctl configtest

# Restart Apache2
sudo systemctl restart apache2
```

### **Step 3: Verify Apache2 Status**
```bash
# Check Apache2 status
sudo systemctl status apache2

# Check if ports are listening
sudo netstat -tlnp | grep :80
sudo netstat -tlnp | grep :443
sudo netstat -tlnp | grep :8081
```

### **Step 4: Test Endpoints**
```bash
# Test main website (HTTPS)
curl https://company.d0s369.co.in/

# Test push endpoint (HTTP on port 8081)
curl -X POST http://company.d0s369.co.in:8081/api/device/push-attendance/ \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'

# Test with IP address
curl -X POST http://82.25.109.137:8081/api/device/push-attendance/ \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

### **Step 5: Configure Environment Variables**
```bash
# Create .env file
nano /var/www/EmployeeAttendance/.env
```

**Add these variables to .env:**
```bash
# Database Configuration
DB_ENGINE=django.db.backends.mysql
DB_NAME=u434975676_DOS
DB_USER=u434975676_bimal
DB_PASSWORD=DishaSolution@8989
DB_HOST=193.203.184.215
DB_PORT=3306

# Django Configuration
SECRET_KEY=your-secret-key-here
DEBUG=False
ENVIRONMENT=production
ALLOWED_HOSTS=company.d0s369.co.in,www.company.d0s369.co.in,82.25.109.137,localhost,127.0.0.1

# CORS Configuration
CORS_ALLOWED_ORIGINS=https://your-frontend-domain.com,http://localhost:3000

# Attendance Service
AUTO_START_ATTENDANCE_SERVICE=false
```

### **Step 6: Install WeasyPrint Dependencies**
```bash
# Install system dependencies for PDF generation
sudo apt-get update
sudo apt-get install -y python3-dev python3-pip python3-cffi python3-brotli libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0

# Install WeasyPrint
source venv/bin/activate
pip install weasyprint
```

### **Step 7: Run Database Migrations**
```bash
# Activate virtual environment
source venv/bin/activate

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput
```

### **Step 8: Test Django Application**
```bash
# Test Django
python manage.py check

# Test management commands
python manage.py start_attendance_service --status
```

### **Step 9: Setup Systemd Service (Optional)**
```bash
# Copy service file
sudo cp attendance_service.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable attendance_service

# Start service
sudo systemctl start attendance_service

# Check status
sudo systemctl status attendance_service
```

### **Step 10: Configure File Permissions**
```bash
# Set proper ownership
sudo chown -R www-data:www-data /var/www/EmployeeAttendance

# Set proper permissions
sudo chmod -R 755 /var/www/EmployeeAttendance
sudo chmod -R 775 /var/www/EmployeeAttendance/media
sudo chmod -R 775 /var/www/EmployeeAttendance/staticfiles
sudo chmod -R 775 /var/www/EmployeeAttendance/logs
```

---

## 🧪 **Final Testing**

### **Test 1: Main Website**
```bash
curl https://company.d0s369.co.in/
# Should return Django application
```

### **Test 2: Push Endpoint**
```bash
curl -X POST http://company.d0s369.co.in:8081/api/device/push-attendance/ \
  -H "Content-Type: application/json" \
  -d '{"device_id": "test", "data": "test"}'
# Should return JSON response
```

### **Test 3: API Endpoints**
```bash
# Test offices API
curl https://company.d0s369.co.in/api/offices/

# Test users API
curl https://company.d0s369.co.in/api/users/
```

### **Test 4: ZKTeco Device Configuration**
**In your ZKTeco devices, set:**
- **Server Mode**: ADMS
- **Server Address**: `company.d0s369.co.in` or `82.25.109.137`
- **Server Port**: `8081`
- **Enable Domain Name**: NO

---

##  **Monitor the Setup**

### **Check Logs**
```bash
# Apache2 logs
sudo tail -f /var/log/apache2/error.log
sudo tail -f /var/log/apache2/device_push_access.log

# Django logs
tail -f /var/www/EmployeeAttendance/logs/django.log

# Systemd service logs
sudo journalctl -u attendance_service -f
```

### **Check Services**
```bash
# Check all services
sudo systemctl status apache2
sudo systemctl status attendance_service
sudo systemctl status redis-server
```

---

##  **Expected Results**

After completing all steps:

 **Main Website**: `https://company.d0s369.co.in/` - Working  
 **Push Endpoint**: `http://company.d0s369.co.in:8081/api/device/push-attendance/` - Working  
 **ZKTeco Devices**: Can push data to port 8081  
 **API Endpoints**: All working via HTTPS  
 **PDF Generation**: WeasyPrint working  
 **Database**: Connected and migrations applied  
 **SSL**: Let's Encrypt certificates working  

---

## 🚨 **Troubleshooting**

### **If Apache2 fails to start:**
```bash
sudo apache2ctl configtest
sudo systemctl status apache2
sudo journalctl -u apache2
```

### **If push endpoint doesn't work:**
```bash
# Check if port 8081 is listening
sudo netstat -tlnp | grep :8081

# Check Apache2 configuration
sudo apache2ctl -S
```

### **If Django errors occur:**
```bash
# Check Django logs
tail -f /var/www/EmployeeAttendance/logs/django.log

# Test Django
python manage.py check
```

---

**Follow these steps in order, and your VPS will be fully configured for production!** 
