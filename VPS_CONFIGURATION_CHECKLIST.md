# VPS Configuration Checklist

## 🔧 **Immediate Fix for Your VPS**

### **1. Pull the Missing Management Command**
```bash
cd /var/www/EmployeeAttendance
git pull origin main
```

### **2. Verify the File Exists**
```bash
ls -la core/management/commands/start_attendance_service.py
```

### **3. Test the Command**
```bash
python manage.py start_attendance_service --status
```

---

## 📋 **Complete VPS Configuration Checklist**

### **🔐 Environment Variables (.env file)**
Create `/var/www/EmployeeAttendance/.env` with:
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
ALLOWED_HOSTS=your-domain.com,www.your-domain.com,localhost,127.0.0.1

# CORS Configuration
CORS_ALLOWED_ORIGINS=https://your-frontend-domain.com,http://localhost:3000

# Redis Configuration (for WebSocket)
REDIS_HOST=localhost
REDIS_PORT=6379

# Attendance Service
AUTO_START_ATTENDANCE_SERVICE=true

# Email Configuration (optional)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

### **🗄️ Database Configuration**
```bash
# Test database connection
python manage.py dbshell

# Run migrations
python manage.py migrate

# Create superuser (if needed)
python manage.py createsuperuser
```

### **📦 Python Dependencies**
```bash
# Install/update requirements
pip install -r requirements.txt

# Install WeasyPrint dependencies (Ubuntu)
sudo apt-get update
sudo apt-get install -y python3-dev python3-pip python3-cffi python3-brotli libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0

# Install WeasyPrint
pip install weasyprint
```

### **🌐 Apache2 Configuration**
```bash
# Enable required modules
sudo a2enmod wsgi
sudo a2enmod ssl
sudo a2enmod rewrite
sudo a2enmod headers

# Copy virtual host configuration
sudo cp apache2_virtualhost.conf /etc/apache2/sites-available/attendance-system.conf

# Enable the site
sudo a2ensite attendance-system.conf

# Disable default site
sudo a2dissite 000-default.conf

# Test configuration
sudo apache2ctl configtest

# Restart Apache
sudo systemctl restart apache2
```

### ** Systemd Service (for Attendance Service)**
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

### **📁 File Permissions**
```bash
# Set proper ownership
sudo chown -R www-data:www-data /var/www/EmployeeAttendance

# Set proper permissions
sudo chmod -R 755 /var/www/EmployeeAttendance
sudo chmod -R 775 /var/www/EmployeeAttendance/media
sudo chmod -R 775 /var/www/EmployeeAttendance/staticfiles
sudo chmod -R 775 /var/www/EmployeeAttendance/logs

# Make scripts executable
chmod +x update_vps_fix.sh
chmod +x deploy_apache2_vps.sh
```

### **🔒 SSL Certificate (Let's Encrypt)**
```bash
# Install Certbot
sudo apt-get install certbot python3-certbot-apache

# Get SSL certificate
sudo certbot --apache -d your-domain.com -d www.your-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### ** Redis Installation (for WebSocket)**
```bash
# Install Redis
sudo apt-get install redis-server

# Start Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Test Redis
redis-cli ping
```

### ** Logging Configuration**
```bash
# Create logs directory
mkdir -p /var/www/EmployeeAttendance/logs

# Set permissions
sudo chown -R www-data:www-data /var/www/EmployeeAttendance/logs
sudo chmod -R 775 /var/www/EmployeeAttendance/logs
```

### **🧪 Testing Commands**
```bash
# Test Django
python manage.py check
python manage.py runserver 0.0.0.0:8000

# Test attendance service
python manage.py start_attendance_service --status
python manage.py start_attendance_service

# Test API endpoints
curl -X GET http://localhost:8001/api/offices/
curl -X GET http://localhost:8001/api/users/

# Test WebSocket (if configured)
# Check Redis connection
redis-cli ping
```

### **Monitoring & Maintenance**
```bash
# Check Apache logs
sudo tail -f /var/log/apache2/error.log
sudo tail -f /var/log/apache2/access.log

# Check Django logs
tail -f /var/www/EmployeeAttendance/logs/django.log

# Check system resources
htop
df -h
free -h

# Check running services
sudo systemctl status apache2
sudo systemctl status attendance_service
sudo systemctl status redis-server
```

---

## 🚨 **Common Issues & Solutions**

### **Issue: "populate() isn't reentrant"**
**Solution:** Already fixed in latest code. Pull latest changes.

### **Issue: "Unknown command: start_attendance_service"**
**Solution:** File was missing. Now fixed and pushed to GitHub.

### **Issue: WeasyPrint not working**
**Solution:** Install system dependencies:
```bash
sudo apt-get install python3-dev python3-pip python3-cffi python3-brotli libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0
pip install weasyprint
```

### **Issue: Database connection errors**
**Solution:** Check .env file and database credentials.

### **Issue: Permission denied errors**
**Solution:** Fix file permissions:
```bash
sudo chown -R www-data:www-data /var/www/EmployeeAttendance
sudo chmod -R 755 /var/www/EmployeeAttendance
```

---

##  **Final Verification**

After completing all configurations:

1. **Django Server:** `python manage.py runserver` (no errors)
2. **Management Commands:** `python manage.py start_attendance_service --status`
3. **API Endpoints:** Test with curl or browser
4. **Apache2:** `sudo systemctl status apache2`
5. **Attendance Service:** `sudo systemctl status attendance_service`
6. **WebSocket:** Test real-time features
7. **PDF Generation:** Test document generation
8. **Database:** All migrations applied

**Your VPS should be fully configured and ready for production!** 
