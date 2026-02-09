# Push Data Reception Deployment Checklist

## Overview
This checklist ensures your Django attendance system is properly configured to receive pushed attendance data from biometric devices on your Ubuntu Apache2 server.

## Pre-Deployment Checklist

### 1. Server Requirements 
- [x] Ubuntu server with Apache2 installed
- [x] Python 3.8+ with Django 5.2.4
- [x] MySQL database configured
- [x] SSL certificates installed
- [x] Domain: `company.d0s369.co.in`

### 2. Device Configuration 
- [x] Server Mode: ADMS
- [x] Enable Domain Name: NO
- [x] Server Address: 82.25.109.137
- [x] Server Port: 8081
- [x] Enable Proxy Server: NO

## Deployment Steps

### Step 1: Upload Files to Server
```bash
# Upload these files to your Ubuntu server:
scp core/push_views.py user@your-server:/var/www/EmployeeAttendance/core/
scp core/urls.py user@your-server:/var/www/EmployeeAttendance/core/
scp apache2_push_virtualhost.conf user@your-server:/tmp/
scp deploy_push_to_ubuntu.sh user@your-server:/tmp/
```

### Step 2: Run Deployment Script
```bash
# SSH into your server
ssh user@your-server

# Make script executable and run
chmod +x /tmp/deploy_push_to_ubuntu.sh
sudo /tmp/deploy_push_to_ubuntu.sh
```

### Step 3: Manual Configuration (if needed)

#### Apache2 Configuration
```bash
# Copy Apache2 configuration
sudo cp /tmp/apache2_push_virtualhost.conf /etc/apache2/sites-available/employee-attendance-push.conf

# Enable the site
sudo a2ensite employee-attendance-push.conf

# Enable required modules
sudo a2enmod proxy proxy_http rewrite headers wsgi

# Test configuration
sudo apache2ctl configtest

# Restart Apache2
sudo systemctl restart apache2
```

#### Firewall Configuration
```bash
# Open port 8081
sudo ufw allow 8081/tcp

# Check firewall status
sudo ufw status
```

#### Django Configuration
```bash
# Navigate to project directory
cd /var/www/EmployeeAttendance

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install django-cors-headers

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput
```

## Testing the Deployment

### 1. Health Check Test
```bash
# Test health check endpoint
curl -X GET https://company.d0s369.co.in:8081/api/device/health-check/

# Expected response:
{
    "status": "healthy",
    "message": "Attendance server is running",
    "timestamp": "2024-01-15T10:30:00Z",
    "server_mode": "ADMS"
}
```

### 2. Push Data Test
```bash
# Test push endpoint with sample data
curl -X POST https://company.d0s369.co.in:8081/api/device/push-attendance/ \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "TEST_DEVICE_001",
    "device_name": "Test Device",
    "attendance_records": [
      {
        "user_id": "5",
        "biometric_id": "5",
        "timestamp": "2024-01-15 10:30:00",
        "type": "check_in"
      }
    ]
  }'
```

### 3. Log Monitoring
```bash
# Monitor push data logs
sudo tail -f /var/log/apache2/device_push_access.log

# Monitor error logs
sudo tail -f /var/log/apache2/device_push_error.log

# Monitor Django logs
sudo tail -f /var/log/django/push_data.log
```

## Production Configuration

### Environment Variables
Create `/var/www/EmployeeAttendance/.env`:
```env
# Database Configuration
DB_ENGINE=django.db.backends.mysql
DB_NAME=your_database_name
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_HOST=localhost
DB_PORT=3306

# Security
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=company.d0s369.co.in,www.company.d0s369.co.in,82.25.109.137

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# CORS Configuration
CORS_ALLOWED_ORIGINS=https://company.d0s369.co.in,http://82.25.109.137

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/django/push_data.log
```

### Systemd Service (Optional)
Create `/etc/systemd/system/django-push.service`:
```ini
[Unit]
Description=Django Push Data Service
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/var/www/EmployeeAttendance
Environment=DJANGO_SETTINGS_MODULE=attendance_system.settings
ExecStart=/var/www/EmployeeAttendance/venv/bin/python manage.py runserver 0.0.0.0:8081
Restart=always

[Install]
WantedBy=multi-user.target
```

## Monitoring and Maintenance

### 1. Log Rotation
Create `/etc/logrotate.d/django-push`:
```
/var/log/django/push_data.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 www-data www-data
    postrotate
        systemctl reload apache2
    endscript
}
```

### 2. Health Monitoring
```bash
# Create health check script
cat > /usr/local/bin/check-push-service.sh << 'EOF'
#!/bin/bash
response=$(curl -s -o /dev/null -w "%{http_code}" https://company.d0s369.co.in:8081/api/device/health-check/)
if [ "$response" != "200" ]; then
    echo "Push service is down! HTTP Code: $response"
    systemctl restart apache2
fi
EOF

chmod +x /usr/local/bin/check-push-service.sh

# Add to crontab for monitoring every 5 minutes
echo "*/5 * * * * /usr/local/bin/check-push-service.sh" | crontab -
```

## Troubleshooting

### Common Issues

1. **Port 8081 not accessible**
   ```bash
   # Check if port is open
   sudo netstat -tlnp | grep 8081
   
   # Check firewall
   sudo ufw status
   ```

2. **Apache2 configuration errors**
   ```bash
   # Test configuration
   sudo apache2ctl configtest
   
   # Check error logs
   sudo tail -f /var/log/apache2/error.log
   ```

3. **Django import errors**
   ```bash
   # Check Python path
   cd /var/www/EmployeeAttendance
   source venv/bin/activate
   python -c "import core.push_views"
   ```

4. **Database connection issues**
   ```bash
   # Test database connection
   python manage.py dbshell
   ```

## Security Considerations

1. **Rate Limiting**: Consider implementing rate limiting for push endpoints
2. **IP Whitelisting**: Restrict push endpoints to known device IPs
3. **Data Validation**: Ensure all incoming data is properly validated
4. **Logging**: Monitor logs for suspicious activity
5. **SSL/TLS**: Use HTTPS for all communications

## Success Criteria

- [ ] Health check endpoint responds with 200 OK
- [ ] Push endpoint accepts and processes test data
- [ ] Attendance records are created in database
- [ ] Logs show successful data processing
- [ ] Devices can successfully push data
- [ ] No errors in Apache2 or Django logs

## Support

If you encounter issues:
1. Check the logs first
2. Verify Apache2 configuration
3. Test endpoints manually
4. Check database connectivity
5. Verify device configuration

Your push data reception system should now be fully operational! 🎉
