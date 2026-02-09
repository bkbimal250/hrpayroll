# GitHub Push & VPS Pull Guide

##  Complete Guide for GitHub Push and VPS Deployment

This guide will help you push your project to GitHub and then pull it on your VPS for deployment.

---

## 📋 Pre-Push Checklist

###  Files to Keep in Repository
- [x] **Core Django Application**: All Django code and models
- [x] **Backend API**: Django REST API endpoints
- [x] **Requirements**: `requirements.txt` with WeasyPrint
- [x] **Configuration Templates**: `env.example`, Apache configs
- [x] **Deployment Scripts**: `deploy_apache2_vps.sh`
- [x] **Documentation**: All `.md` files
- [x] **Static Files**: Django static files (not collected)

###  Files Excluded (in .gitignore)
- [x] **Frontend**: `frontend/` (deployed separately)
- [x] **Environment Files**: `.env` (contains sensitive data)
- [x] **Virtual Environment**: `venv/` (will be created on VPS)
- [x] **Collected Static Files**: `staticfiles/` (generated on VPS)
- [x] **Media Files**: `media/` (user uploads)
- [x] **Log Files**: `logs/` (runtime logs)
- [x] **Database Files**: `*.db`, `*.sqlite3`
- [x] **Test Scripts**: `test_*.py`, `check_*.py`, etc.

---

## 🔧 Step 1: Prepare for GitHub Push

### 1.1 Check Git Status
```bash
# Check what files will be committed
git status

# Check what files are ignored
git status --ignored
```

### 1.2 Add All Files
```bash
# Add all files (respecting .gitignore)
git add .

# Check what will be committed
git status
```

### 1.3 Commit Changes
```bash
# Commit with descriptive message
git commit -m "Production-ready Employee Attendance System

- WeasyPrint-only PDF generation (Ubuntu optimized)
- Complete Apache2 VPS deployment configuration
- Auto-attendance fetching service
- Document generation with HTML fallback
- ZKTeco device integration (push & fetch)
- WebSocket support with Redis
- Role-based authentication system
- Production security configurations
- Comprehensive deployment guides and scripts"
```

### 1.4 Push to GitHub
```bash
# Push to main branch
git push origin main

# Or if using master branch
git push origin master
```

---

## 🖥️ Step 2: VPS Setup and Pull

### 2.1 Connect to Your VPS
```bash
# SSH into your VPS
ssh root@your-vps-ip
# or
ssh username@your-vps-ip
```

### 2.2 Install Git (if not installed)
```bash
# Update system
sudo apt update

# Install git
sudo apt install -y git
```

### 2.3 Clone Repository
```bash
# Navigate to web directory
cd /var/www/

# Clone your repository
git clone https://github.com/your-username/your-repo-name.git EmployeeAttandance

# Set proper ownership
sudo chown -R www-data:www-data /var/www/EmployeeAttandance
```

### 2.4 Alternative: Pull into Existing Directory
```bash
# If you already have the directory
cd /var/www/EmployeeAttandance

# Pull latest changes
git pull origin main
# or
git pull origin master
```

---

## ⚙️ Step 3: VPS Configuration

### 3.1 Create Environment File
```bash
cd /var/www/EmployeeAttandance

# Copy environment template
cp env.example .env

# Edit environment file
nano .env
```

**Update the .env file with your production values:**
```env
# Django Settings
ENVIRONMENT=production
DEBUG=False
SECRET_KEY=your-super-secret-key-here-change-this-in-production
ALLOWED_HOSTS=your-domain.com,www.your-domain.com,your-vps-ip

# Database Configuration
DB_ENGINE=django.db.backends.mysql
DB_NAME=u434975676_DOS
DB_USER=u434975676_bimal
DB_PASSWORD=DishaSolution@8989
DB_HOST=193.203.184.215
DB_PORT=3306

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Email Configuration
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=creatorbimal@gmail.com
EMAIL_HOST_PASSWORD=zdduqixnlkencxsy

# Security Settings
CORS_ALLOWED_ORIGINS=https://your-domain.com,https://www.your-domain.com

# Static and Media Files
STATIC_ROOT=/var/www/EmployeeAttandance/staticfiles
MEDIA_ROOT=/var/www/EmployeeAttandance/media

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/attendance/django.log
```

### 3.2 Set Environment File Permissions
```bash
sudo chown www-data:www-data .env
sudo chmod 600 .env
```

---

## 🐍 Step 4: Python Environment Setup

### 4.1 Create Virtual Environment
```bash
cd /var/www/EmployeeAttandance

# Create virtual environment
python3 -m venv venv

# Set ownership
sudo chown -R www-data:www-data venv
```

### 4.2 Install Dependencies
```bash
# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

# Deactivate virtual environment
deactivate
```

### 4.3 Install WeasyPrint Dependencies
```bash
# Install system dependencies for WeasyPrint
sudo apt install -y python3-cffi python3-brotli libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0
sudo apt install -y libffi-dev libjpeg-dev libpng-dev libgif-dev librsvg2-dev
sudo apt install -y build-essential libssl-dev libffi-dev
```

### 4.4 Test WeasyPrint Installation
```bash
# Test WeasyPrint
sudo -u www-data /var/www/EmployeeAttandance/venv/bin/python -c "import weasyprint; print('WeasyPrint version:', weasyprint.__version__)"
```

---

## 🗄️ Step 5: Database Setup

### 5.1 Run Migrations
```bash
cd /var/www/EmployeeAttandance

# Run Django migrations
sudo -u www-data /var/www/EmployeeAttandance/venv/bin/python manage.py migrate
```

### 5.2 Create Superuser
```bash
# Create Django superuser
sudo -u www-data /var/www/EmployeeAttandance/venv/bin/python manage.py createsuperuser
```

### 5.3 Collect Static Files
```bash
# Collect static files
sudo -u www-data /var/www/EmployeeAttandance/venv/bin/python manage.py collectstatic --noinput
```

---

## 🌐 Step 6: Apache2 Configuration

### 6.1 Run Deployment Script
```bash
cd /var/www/EmployeeAttandance

# Make script executable
chmod +x deploy_apache2_vps.sh

# Run deployment script (this will configure Apache2)
./deploy_apache2_vps.sh
```

### 6.2 Manual Apache Configuration (Alternative)
```bash
# Copy Apache configuration
sudo cp apache2_virtualhost.conf /etc/apache2/sites-available/employee-attendance.conf

# Edit configuration with your domain
sudo nano /etc/apache2/sites-available/employee-attendance.conf

# Enable site and modules
sudo a2enmod ssl rewrite headers wsgi
sudo a2ensite employee-attendance.conf
sudo a2dissite 000-default.conf

# Test configuration
sudo apache2ctl configtest

# Restart Apache
sudo systemctl restart apache2
```

---

## 🔧 Step 7: Services Setup

### 7.1 Create Attendance Service
```bash
# Copy service file
sudo cp attendance_service.service /etc/systemd/system/

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable attendance-service
sudo systemctl start attendance-service

# Check status
sudo systemctl status attendance-service
```

### 7.2 Setup Redis
```bash
# Enable and start Redis
sudo systemctl enable redis-server
sudo systemctl start redis-server
sudo systemctl status redis-server
```

---

## 🔒 Step 8: SSL Certificate

### 8.1 Install Certbot
```bash
sudo apt install -y certbot python3-certbot-apache
```

### 8.2 Obtain SSL Certificate
```bash
# Replace with your domain
sudo certbot --apache -d your-domain.com -d www.your-domain.com
```

---

##  Step 9: Final Verification

### 9.1 Test Django Application
```bash
cd /var/www/EmployeeAttandance

# Run Django checks
sudo -u www-data /var/www/EmployeeAttandance/venv/bin/python manage.py check --deploy
```

### 9.2 Test WeasyPrint
```bash
# Test WeasyPrint functionality
sudo -u www-data /var/www/EmployeeAttandance/venv/bin/python -c "
import weasyprint
print(' WeasyPrint version:', weasyprint.__version__)
print(' WeasyPrint is working correctly!')
"
```

### 9.3 Check Services
```bash
# Check all services
sudo systemctl status apache2
sudo systemctl status attendance-service
sudo systemctl status redis-server
```

### 9.4 Test Website
```bash
# Test HTTP (should redirect to HTTPS)
curl -I http://your-domain.com

# Test HTTPS
curl -I https://your-domain.com
```

---

##  Step 10: Future Updates

### 10.1 Update Code on VPS
```bash
# Navigate to project directory
cd /var/www/EmployeeAttandance

# Pull latest changes
git pull origin main

# Run migrations (if any)
sudo -u www-data /var/www/EmployeeAttandance/venv/bin/python manage.py migrate

# Collect static files (if changed)
sudo -u www-data /var/www/EmployeeAttandance/venv/bin/python manage.py collectstatic --noinput

# Restart services
sudo systemctl restart apache2
sudo systemctl restart attendance-service
```

### 10.2 Update Dependencies
```bash
# Activate virtual environment
source /var/www/EmployeeAttandance/venv/bin/activate

# Update requirements
pip install -r requirements.txt

# Deactivate
deactivate

# Restart services
sudo systemctl restart apache2
sudo systemctl restart attendance-service
```

---

## 📋 Quick Commands Summary

### GitHub Push Commands
```bash
git add .
git commit -m "Production-ready Employee Attendance System"
git push origin main
```

### VPS Pull Commands
```bash
cd /var/www/EmployeeAttandance
git pull origin main
sudo -u www-data /var/www/EmployeeAttandance/venv/bin/python manage.py migrate
sudo -u www-data /var/www/EmployeeAttandance/venv/bin/python manage.py collectstatic --noinput
sudo systemctl restart apache2
sudo systemctl restart attendance-service
```

---

## 🚨 Important Notes

### Security
-  **Never commit `.env` files** - they contain sensitive data
-  **Use strong SECRET_KEY** in production
-  **Enable HTTPS** with SSL certificates
-  **Set proper file permissions** (600 for .env, 755 for directories)

### Performance
-  **WeasyPrint works only on Linux/Ubuntu** - perfect for VPS
-  **Redis required** for WebSocket functionality
-  **MySQL database** configured for production
-  **Static files** collected and served efficiently

### Monitoring
-  **Check logs regularly**: `/var/log/apache2/employee_attendance_error.log`
-  **Monitor services**: `systemctl status attendance-service`
-  **Test WeasyPrint**: Regular PDF generation tests

---

## 🎉 Deployment Complete!

Your Employee Attendance System is now deployed with:

 **GitHub Repository**: Code safely stored and version controlled  
 **VPS Deployment**: Production-ready Ubuntu server  
 **WeasyPrint PDF Generation**: Professional document generation  
 **Auto-Services**: Background attendance fetching  
 **SSL Security**: HTTPS enabled  
 **Real-time Features**: WebSocket support  
 **Device Integration**: ZKTeco biometric support  

**Access your application at: `https://your-domain.com`** 
