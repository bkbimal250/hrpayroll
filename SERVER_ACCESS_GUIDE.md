# Server Access Guide for Push Attendance Testing

## Step-by-Step Server Access Instructions

### 1. Access Your Server

Open your terminal/command prompt and run:
```bash
ssh root@82.25.109.137
```

If this is your first time connecting, you'll see a message like:
```
The authenticity of host '82.25.109.137' can't be established.
Are you sure you want to continue connecting (yes/no)?
```
Type `yes` and press Enter.

### 2. Navigate to Project Directory

Once connected, run:
```bash
cd /var/www/EmployeeAttendance/
```

### 3. Check Current Status

First, let's see what's currently on your server:
```bash
# List files in the project directory
ls -la

# Check if push_views.py exists
ls -la core/push_views.py

# Check if Django is working
python3 manage.py check

# Check if server is running
systemctl status apache2
```

### 4. Upload Missing Files (if needed)

If `core/push_views.py` is missing, you'll need to upload it. From your local Windows machine, run:
```bash
scp core/push_views.py root@82.25.109.137:/var/www/EmployeeAttendance/core/
```

### 5. Upload Testing Files

From your local Windows machine, upload the testing files:
```bash
scp test_push_functionality.py root@82.25.109.137:/var/www/EmployeeAttendance/
scp manual_test_commands.sh root@82.25.109.137:/var/www/EmployeeAttendance/
scp verify_database_records.py root@82.25.109.137:/var/www/EmployeeAttendance/
scp TESTING_GUIDE.md root@82.25.109.137:/var/www/EmployeeAttendance/
```

### 6. Set Permissions on Server

Back on your server, set executable permissions:
```bash
cd /var/www/EmployeeAttendance/
chmod +x test_push_functionality.py
chmod +x manual_test_commands.sh
chmod +x verify_database_records.py
```

### 7. Run Tests

Now you can run the tests:

#### Quick Health Check:
```bash
curl -X GET http://localhost:8081/api/device/health-check/
```

#### Database Verification:
```bash
python3 verify_database_records.py
```

#### Automated Tests:
```bash
python3 test_push_functionality.py --production
```

#### Manual Tests:
```bash
./manual_test_commands.sh
```

### 8. Monitor Logs

While testing, monitor the logs:
```bash
# Watch Apache2 logs
tail -f /var/log/apache2/device_push_access.log

# Watch Django logs
tail -f /var/www/EmployeeAttendance/logs/django.log

# Watch error logs
tail -f /var/log/apache2/error.log
```

## Troubleshooting Common Issues

### Issue 1: "No module named 'core.push_views'"
**Solution:** Upload the missing file:
```bash
# From your local machine:
scp core/push_views.py root@82.25.109.137:/var/www/EmployeeAttendance/core/
```

### Issue 2: "Permission denied"
**Solution:** Set proper permissions:
```bash
# On the server:
chmod +x test_push_functionality.py
chmod +x manual_test_commands.sh
chmod +x verify_database_records.py
```

### Issue 3: "Connection refused" on port 8081
**Solution:** Check if Apache2 is configured for port 8081:
```bash
# Check if port 8081 is listening
netstat -tlnp | grep 8081

# Check Apache2 configuration
apache2ctl configtest

# Restart Apache2
systemctl restart apache2
```

### Issue 4: "No users with biometric IDs"
**Solution:** Check and update user records:
```bash
# Check users with biometric IDs
python3 manage.py shell -c "
from core.models import CustomUser
users = CustomUser.objects.filter(biometric_id__isnull=False).exclude(biometric_id='')
print(f'Users with biometric IDs: {users.count()}')
for user in users[:5]:
    print(f'{user.get_full_name()}: {user.employee_id} -> {user.biometric_id}')
"
```

## Expected Results

When everything is working correctly, you should see:

### Health Check Response:
```json
{
    "status": "healthy",
    "message": "Attendance server is running",
    "timestamp": "2024-01-15T10:30:00Z",
    "server_mode": "ADMS"
}
```

### Successful Push Response:
```json
{
    "success": true,
    "message": "Attendance data received successfully",
    "processed_records": 1,
    "error_count": 0,
    "device_id": "uuid-here"
}
```

### Database Records:
- New attendance records created
- Device records created automatically
- ESSL attendance logs created

## Next Steps After Testing

1. **If tests pass:** Your push attendance system is ready for production!
2. **If tests fail:** Check the error messages and fix the issues
3. **Configure real devices:** Set up your biometric devices with the server settings
4. **Monitor in production:** Set up log monitoring and alerts

## Quick Commands Summary

```bash
# Access server
ssh root@82.25.109.137

# Navigate to project
cd /var/www/EmployeeAttendance/

# Check status
python3 manage.py check
systemctl status apache2

# Run tests
python3 test_push_functionality.py --production
python3 verify_database_records.py

# Monitor logs
tail -f /var/log/apache2/device_push_access.log
```

Your push attendance system will be ready once all tests pass! 🎉
