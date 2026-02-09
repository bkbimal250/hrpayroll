# GitHub Deployment Guide for Push Data Reception

## Overview
This guide helps you deploy the push data reception functionality to your Ubuntu server by pushing to GitHub and pulling directly on the server.

## Step 1: Prepare Files for GitHub

### Files to Commit to GitHub:
1.  `core/push_views.py` - Push data reception views
2.  `core/urls.py` - Updated with push endpoints
3.  `apache2_push_virtualhost.conf` - Apache2 configuration
4.  `deploy_from_github.sh` - Deployment script
5.  `requirements.txt` - Updated dependencies
6.  `PUSH_DEPLOYMENT_CHECKLIST.md` - Deployment checklist

### Files Already in Your Project:
-  `attendance_system/settings.py`
-  `core/models.py`
-  `core/views.py`
-  All other existing files

## Step 2: Push to GitHub

### Commands to run on your local machine:

```bash
# Navigate to your project directory
cd "C:\Users\DELL\Desktop\Bimal\python project\Django\EmployeeAttandance"

# Add all new files
git add core/push_views.py
git add core/urls.py
git add apache2_push_virtualhost.conf
git add deploy_from_github.sh
git add requirements.txt
git add PUSH_DEPLOYMENT_CHECKLIST.md
git add GITHUB_DEPLOYMENT_GUIDE.md

# Commit the changes
git commit -m "Add push data reception functionality for biometric devices

- Add push_views.py for receiving attendance data from devices
- Update urls.py with push endpoints
- Add Apache2 configuration for port 8081
- Add deployment script for GitHub pull
- Update requirements.txt with dependencies
- Add comprehensive deployment documentation"

# Push to GitHub
git push origin main
```

## Step 3: Deploy on Ubuntu Server

### SSH into your Ubuntu server:
```bash
ssh root@srv765319
```

### Navigate to project directory:
```bash
cd /var/www/EmployeeAttendance
```

### Make deployment script executable and run:
```bash
# Make the script executable
chmod +x deploy_from_github.sh

# Run the deployment script
./deploy_from_github.sh
```

## Step 4: Alternative Manual Deployment

If you prefer to do it manually:

### 1. Pull from GitHub:
```bash
cd /var/www/EmployeeAttendance
git pull origin main
```

### 2. Install dependencies:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Run migrations:
```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

### 4. Configure Apache2:
```bash
# Copy Apache2 configuration
sudo cp apache2_push_virtualhost.conf /etc/apache2/sites-available/employee-attendance-push.conf

# Enable the site
sudo a2ensite employee-attendance-push.conf

# Enable required modules
sudo a2enmod proxy proxy_http rewrite headers wsgi

# Test configuration
sudo apache2ctl configtest

# Restart Apache2
sudo systemctl restart apache2
```

### 5. Configure firewall:
```bash
sudo ufw allow 8081/tcp
```

## Step 5: Test the Deployment

### Test health check endpoint:
```bash
curl https://company.d0s369.co.in:8081/api/device/health-check/
```

### Expected response:
```json
{
    "status": "healthy",
    "message": "Attendance server is running",
    "timestamp": "2024-01-15T10:30:00Z",
    "server_mode": "ADMS"
}
```

### Test push endpoint:
```bash
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

## Step 6: Monitor Logs

### Check Apache2 logs:
```bash
# Push data access logs
sudo tail -f /var/log/apache2/device_push_access.log

# Error logs
sudo tail -f /var/log/apache2/device_push_error.log
```

### Check Django logs:
```bash
# Django application logs
sudo tail -f /var/log/django/push_data.log
```

## Troubleshooting

### Common Issues:

1. **Git pull fails:**
   ```bash
   # Check if you're in the right directory
   pwd
   # Should show: /var/www/EmployeeAttendance
   
   # Check git status
   git status
   
   # If there are conflicts, resolve them
   git stash
   git pull origin main
   ```

2. **Apache2 configuration errors:**
   ```bash
   # Test configuration
   sudo apache2ctl configtest
   
   # Check error logs
   sudo tail -f /var/log/apache2/error.log
   ```

3. **Python import errors:**
   ```bash
   # Check if push_views.py exists
   ls -la /var/www/EmployeeAttendance/core/push_views.py
   
   # Test Python import
   cd /var/www/EmployeeAttendance
   source venv/bin/activate
   python -c "import core.push_views; print('Import successful')"
   ```

4. **Port 8081 not accessible:**
   ```bash
   # Check if port is open
   sudo netstat -tlnp | grep 8081
   
   # Check firewall
   sudo ufw status
   ```

## Success Criteria

- [ ] Git pull completes successfully
- [ ] All Python dependencies installed
- [ ] Django migrations completed
- [ ] Apache2 configuration valid
- [ ] Apache2 restarted successfully
- [ ] Port 8081 accessible
- [ ] Health check endpoint returns 200 OK
- [ ] Push endpoint accepts test data
- [ ] No errors in logs

## Device Configuration

Your biometric devices should be configured with:
- **Server Mode:** ADMS
- **Server Address:** 82.25.109.137
- **Server Port:** 8081
- **Enable Domain Name:** NO
- **Enable Proxy Server:** NO

## Endpoints Available

1. **Push Attendance:** `POST https://company.d0s369.co.in:8081/api/device/push-attendance/`
2. **Receive Attendance:** `POST https://company.d0s369.co.in:8081/api/device/receive-attendance/`
3. **Health Check:** `GET https://company.d0s369.co.in:8081/api/device/health-check/`

## Next Steps

1. **Test with real devices:** Have someone use the biometric device to test data pushing
2. **Monitor logs:** Watch the logs to ensure data is being received and processed
3. **Verify database:** Check that attendance records are being created in the database
4. **Set up monitoring:** Consider setting up automated monitoring for the push endpoints

Your push data reception system should now be fully operational! 🎉

## Support

If you encounter any issues:
1. Check the logs first
2. Verify all files were pulled from GitHub
3. Test each component individually
4. Check Apache2 and Django configurations
5. Verify device configuration matches server settings
