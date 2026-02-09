# Manual WebSocket Setup Guide

Since you're already in the virtual environment, here's the manual setup process:

##  **Quick Manual Setup**

### **Step 1: Install Daphne in Virtual Environment**
```bash
# You're already in the venv, so just install Daphne
pip install daphne
```

### **Step 2: Enable Apache2 Modules**
```bash
sudo a2enmod proxy
sudo a2enmod proxy_http
sudo a2enmod proxy_wstunnel
sudo a2enmod rewrite
sudo a2enmod headers
```

### **Step 3: Configure Apache2 Virtual Host**
```bash
# Backup existing config
sudo cp /etc/apache2/sites-available/employee-attendance.conf /etc/apache2/sites-available/employee-attendance.conf.backup

# Copy new config with WebSocket support
sudo cp apache2_websocket_virtualhost.conf /etc/apache2/sites-available/employee-attendance.conf

# Test configuration
sudo apache2ctl configtest
```

### **Step 4: Set Up Systemd Service**
```bash
# Copy systemd service file
sudo cp django-asgi.service /etc/systemd/system/

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable django-asgi.service
```

### **Step 5: Start Services**
```bash
# Start Django ASGI service
sudo systemctl start django-asgi.service

# Restart Apache2
sudo systemctl restart apache2
```

### **Step 6: Check Status**
```bash
# Check if services are running
sudo systemctl status django-asgi.service
sudo systemctl status apache2
```

## 🔧 **Quick Commands**

```bash
# Install Daphne (you're already in venv)
pip install daphne

# Enable Apache2 modules
sudo a2enmod proxy proxy_http proxy_wstunnel rewrite headers

# Copy configuration files
sudo cp apache2_websocket_virtualhost.conf /etc/apache2/sites-available/employee-attendance.conf
sudo cp django-asgi.service /etc/systemd/system/

# Test Apache2 config
sudo apache2ctl configtest

# Start services
sudo systemctl daemon-reload
sudo systemctl enable django-asgi.service
sudo systemctl start django-asgi.service
sudo systemctl restart apache2

# Check status
sudo systemctl status django-asgi.service apache2
```

## 🧪 **Test WebSocket Connection**

```bash
# Install wscat for testing
npm install -g wscat

# Test WebSocket connection
wscat -c wss://company.d0s369.co.in/ws/attendance/
```

##  **Expected Results**

After setup:
-  Django ASGI service running on port 8001
-  Apache2 proxying WebSocket requests to Daphne
-  WebSocket connections working
-  Real-time updates functional

## 🆘 **Troubleshooting**

If you encounter issues:

```bash
# Check service logs
sudo journalctl -u django-asgi.service -f
sudo tail -f /var/log/apache2/employee_attendance_error.log

# Restart services
sudo systemctl restart django-asgi.service
sudo systemctl restart apache2

# Check if port 8001 is listening
sudo netstat -tlnp | grep :8001
```

The manual setup should work perfectly since you're already in the virtual environment!
