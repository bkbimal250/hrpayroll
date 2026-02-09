# WebSocket Connection Issue - Complete Solution

## 🚨 **Problem Identified**
Your frontend is showing multiple WebSocket connection failures:
```
WebSocket connection to 'wss://company.d0s369.co.in/ws/attendance/' failed:
```

## **Root Cause Analysis**
The issue is that your **Apache2 configuration only handles HTTP requests** through WSGI, but **WebSocket connections require special proxy configuration** to work with Django Channels (ASGI).

### Current Architecture (Broken)
```
Frontend → Apache2 → WSGI → Django (HTTP only)
                ↓
            WebSocket requests fail 
```

### Required Architecture (Fixed)
```
Frontend → Apache2 → WSGI → Django (HTTP requests)
         → Apache2 → Proxy → Daphne → Django Channels (WebSocket requests) 
```

## 🛠️ **Complete Solution**

### **Files Created for You:**

1. **`apache2_websocket_virtualhost.conf`** - Updated Apache2 configuration with WebSocket proxy support
2. **`django-asgi.service`** - Systemd service file for Django ASGI server
3. **`setup_websocket_production.sh`** - Automated setup script for Ubuntu VPS
4. **`test_websocket_connection.py`** - Test script to verify WebSocket connectivity
5. **`WEBSOCKET_TROUBLESHOOTING.md`** - Comprehensive troubleshooting guide

##  **Implementation Steps**

### **Step 1: Upload Files to Your Ubuntu VPS**
Upload these files to your Ubuntu VPS:
- `apache2_websocket_virtualhost.conf`
- `django-asgi.service`
- `setup_websocket_production.sh`

### **Step 2: Run the Setup Script**
```bash
# On your Ubuntu VPS
sudo chmod +x setup_websocket_production.sh
sudo ./setup_websocket_production.sh
```

### **Step 3: Verify Installation**
```bash
# Check if all services are running
sudo systemctl status django-asgi.service
sudo systemctl status apache2
sudo systemctl status redis-server
```

### **Step 4: Test WebSocket Connection**
```bash
# Test WebSocket endpoint
wscat -c wss://company.d0s369.co.in/ws/attendance/
```

## 📋 **What the Setup Script Does**

1. **Installs Required Apache2 Modules**
   - `mod_proxy`
   - `mod_proxy_http`
   - `mod_proxy_wstunnel`
   - `mod_rewrite`
   - `mod_headers`

2. **Configures WebSocket Proxy**
   - Routes `/ws/` requests to Daphne ASGI server
   - Handles WebSocket upgrade headers
   - Maintains SSL/TLS security

3. **Sets Up Django ASGI Service**
   - Installs Daphne (ASGI server)
   - Creates systemd service
   - Configures auto-restart and security

4. **Configures Redis**
   - Installs and starts Redis server
   - Enables for Django Channels

5. **Updates Environment**
   - Creates production environment file
   - Sets proper permissions
   - Configures firewall rules

## 🔧 **Key Configuration Changes**

### **Apache2 Virtual Host Updates**
```apache
# WebSocket Proxy Configuration
ProxyPreserveHost On
ProxyRequests Off

# WebSocket upgrade headers
RewriteEngine On
RewriteCond %{HTTP:Upgrade} websocket [NC]
RewriteCond %{HTTP:Connection} upgrade [NC]
RewriteRule ^/ws/(.*)$ "ws://127.0.0.1:8001/ws/$1" [P,L]

# Proxy WebSocket connections
ProxyPass /ws/ ws://127.0.0.1:8001/ws/
ProxyPassReverse /ws/ ws://127.0.0.1:8001/ws/
```

### **Django ASGI Service**
```ini
[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/var/www/EmployeeAttandance
ExecStart=/var/www/EmployeeAttandance/venv/bin/daphne -b 127.0.0.1 -p 8001 attendance_system.asgi:application
Restart=always
```

## 🧪 **Testing the Fix**

### **Local Testing (Windows)**
```bash
# Run the test script
python test_websocket_connection.py
```

### **Server Testing (Ubuntu VPS)**
```bash
# Test WebSocket connection
wscat -c wss://company.d0s369.co.in/ws/attendance/

# Check service logs
sudo journalctl -u django-asgi.service -f
sudo tail -f /var/log/apache2/employee_attendance_error.log
```

##  **Expected Results**

After implementing the fix:

 **WebSocket connections will succeed**  
 **Real-time attendance updates will work**  
 **No more connection failures in browser console**  
 **Frontend will receive live data updates**  
 **Resignation status updates will work in real-time**  

## **Monitoring and Maintenance**

### **Service Status Commands**
```bash
# Check all services
sudo systemctl status django-asgi.service apache2 redis-server

# Restart services if needed
sudo systemctl restart django-asgi.service
sudo systemctl restart apache2
```

### **Log Monitoring**
```bash
# Monitor all logs
sudo journalctl -u django-asgi.service -f &
sudo tail -f /var/log/apache2/employee_attendance_error.log &
sudo tail -f /var/log/redis/redis-server.log &
```

## ⚠️ **Important Notes**

1. **SSL Certificates**: Make sure your SSL certificates are properly configured in the Apache2 virtual host
2. **Environment Variables**: Update the `.env` file with your actual database and Redis credentials
3. **Firewall**: The script will configure UFW firewall rules for WebSocket ports
4. **Permissions**: All files will be set with proper ownership and permissions

## 🆘 **Troubleshooting**

If you encounter issues:

1. **Check service status**: `sudo systemctl status django-asgi.service`
2. **Review logs**: `sudo journalctl -u django-asgi.service -f`
3. **Test WebSocket**: `wscat -c wss://company.d0s369.co.in/ws/attendance/`
4. **Verify Apache2 config**: `sudo apache2ctl configtest`
5. **Check Redis**: `redis-cli ping`

## 📞 **Support**

The solution includes:
-  Complete Apache2 WebSocket proxy configuration
-  Django ASGI service setup
-  Redis configuration
-  Automated setup script
-  Test scripts for verification
-  Comprehensive troubleshooting guide

This should completely resolve your WebSocket connection issues and enable real-time features in your Employee Attendance System! 🎉
