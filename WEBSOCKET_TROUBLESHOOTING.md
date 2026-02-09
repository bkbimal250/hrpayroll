# WebSocket Troubleshooting Guide

## Issue: WebSocket Connection Failures

### Problem Description
The frontend is showing multiple WebSocket connection failures:
```
WebSocket connection to 'wss://company.d0s369.co.in/ws/attendance/' failed:
```

### Root Cause Analysis
The issue is that your current Apache2 configuration only handles HTTP requests through WSGI, but **WebSocket connections require special proxy configuration** to work with Django Channels (ASGI).

## Solution Overview

### 1. **Apache2 Configuration Issue**
- **Current**: Only WSGI configuration for HTTP requests
- **Required**: WebSocket proxy configuration for ASGI connections
- **Fix**: Add WebSocket proxy rules to Apache2 virtual host

### 2. **Missing ASGI Server**
- **Current**: Only Django WSGI server running
- **Required**: Separate ASGI server (Daphne) for WebSocket connections
- **Fix**: Set up systemd service for Django ASGI server

### 3. **Redis Configuration**
- **Current**: May not be properly configured for production
- **Required**: Redis server for Django Channels
- **Fix**: Ensure Redis is running and accessible

## Implementation Steps

### Step 1: Update Apache2 Configuration
Replace your current Apache2 virtual host configuration with the new one that includes WebSocket proxy support:

```bash
# On your Ubuntu VPS
sudo cp apache2_websocket_virtualhost.conf /etc/apache2/sites-available/employee-attendance.conf
sudo a2enmod proxy
sudo a2enmod proxy_http
sudo a2enmod proxy_wstunnel
sudo a2enmod rewrite
sudo a2enmod headers
sudo systemctl reload apache2
```

### Step 2: Set Up ASGI Server
Install and configure Daphne (ASGI server) for WebSocket connections:

```bash
# Install Daphne
sudo pip3 install daphne

# Set up systemd service
sudo cp django-asgi.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable django-asgi.service
sudo systemctl start django-asgi.service
```

### Step 3: Configure Redis
Ensure Redis is running and accessible:

```bash
# Install Redis (if not already installed)
sudo apt update
sudo apt install redis-server

# Start and enable Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Test Redis connection
redis-cli ping
```

### Step 4: Update Environment Variables
Make sure your production environment has the correct settings:

```bash
# In /var/www/EmployeeAttandance/.env
ENVIRONMENT=production
REDIS_HOST=localhost
REDIS_PORT=6379
```

## Architecture Overview

### Before (Current Setup)
```
Frontend → Apache2 → WSGI → Django (HTTP only)
                ↓
            WebSocket requests fail
```

### After (Fixed Setup)
```
Frontend → Apache2 → WSGI → Django (HTTP requests)
         → Apache2 → Proxy → Daphne → Django Channels (WebSocket requests)
```

## Configuration Files

### 1. Apache2 Virtual Host (`apache2_websocket_virtualhost.conf`)
- WebSocket proxy configuration
- SSL/TLS support
- Security headers
- Static file serving

### 2. Systemd Service (`django-asgi.service`)
- Runs Daphne ASGI server
- Handles WebSocket connections
- Auto-restart on failure
- Security hardening

### 3. Environment Configuration
- Production settings
- Redis configuration
- Database settings
- SSL certificate paths

## Testing WebSocket Connection

### 1. Check Service Status
```bash
# Check if all services are running
sudo systemctl status django-asgi.service
sudo systemctl status apache2
sudo systemctl status redis-server
```

### 2. Test WebSocket Endpoint
```bash
# Test WebSocket connection
wscat -c wss://company.d0s369.co.in/ws/attendance/
```

### 3. Check Logs
```bash
# Apache2 logs
sudo tail -f /var/log/apache2/employee_attendance_error.log

# Django ASGI logs
sudo journalctl -u django-asgi.service -f

# Redis logs
sudo tail -f /var/log/redis/redis-server.log
```

## Common Issues and Solutions

### Issue 1: "WebSocket connection failed"
**Cause**: Apache2 not proxying WebSocket requests
**Solution**: Ensure `mod_proxy_wstunnel` is enabled and proxy rules are configured

### Issue 2: "Connection refused"
**Cause**: ASGI server not running
**Solution**: Start the Django ASGI service: `sudo systemctl start django-asgi.service`

### Issue 3: "Redis connection failed"
**Cause**: Redis server not running or not accessible
**Solution**: Start Redis: `sudo systemctl start redis-server`

### Issue 4: "SSL certificate errors"
**Cause**: Invalid or missing SSL certificates
**Solution**: Update certificate paths in Apache2 configuration

## Monitoring and Maintenance

### 1. Service Monitoring
```bash
# Check service health
sudo systemctl status django-asgi.service
sudo systemctl status apache2
sudo systemctl status redis-server
```

### 2. Log Monitoring
```bash
# Monitor all logs
sudo journalctl -u django-asgi.service -f &
sudo tail -f /var/log/apache2/employee_attendance_error.log &
sudo tail -f /var/log/redis/redis-server.log &
```

### 3. Performance Monitoring
```bash
# Check WebSocket connections
netstat -an | grep :8001
ss -tuln | grep :8001
```

## Security Considerations

### 1. Firewall Rules
```bash
# Allow WebSocket ports
sudo ufw allow 8001/tcp
sudo ufw allow 6379/tcp
```

### 2. SSL/TLS Configuration
- Ensure valid SSL certificates
- Use strong cipher suites
- Enable HSTS headers

### 3. Service Security
- Run services as non-root user
- Use systemd security features
- Restrict file system access

## Quick Fix Commands

If you need to quickly fix WebSocket issues:

```bash
# 1. Restart all services
sudo systemctl restart django-asgi.service
sudo systemctl restart apache2
sudo systemctl restart redis-server

# 2. Check status
sudo systemctl status django-asgi.service apache2 redis-server

# 3. Test WebSocket
wscat -c wss://company.d0s369.co.in/ws/attendance/
```

## Expected Results

After implementing the fix:

 **WebSocket connections should succeed**  
 **Real-time attendance updates should work**  
 **No more connection failures in browser console**  
 **Frontend should receive live data updates**  

## Support

If you continue to experience issues:

1. Check all service logs
2. Verify SSL certificate configuration
3. Test WebSocket connection manually
4. Ensure all required Apache2 modules are enabled
5. Verify Redis connectivity

The WebSocket functionality is essential for real-time features like live attendance updates, so fixing this will significantly improve your application's user experience.
