# Push Attendance Testing Guide

## Overview
This guide provides comprehensive testing methods to verify that your push attendance functionality is working correctly and automatically saving data to the database.

## Testing Methods

### 1. Automated Testing (Recommended)

#### Run the comprehensive test suite:
```bash
# Test local development server
python test_push_functionality.py

# Test production server
python test_push_functionality.py --production

# Test custom URL
python test_push_functionality.py --url https://your-server.com:8081
```

#### What the automated tests check:
-  Health check endpoint functionality
-  Basic push endpoint connectivity
-  Real user data processing
-  Database record creation
-  Automatic device creation
-  Check-in/check-out flow
-  Error handling with invalid data

### 2. Manual Testing with curl

#### Test health check:
```bash
curl -X GET http://localhost:8081/api/device/health-check/
```

#### Test basic push:
```bash
curl -X POST http://localhost:8081/api/device/push-attendance/ \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "TEST_DEVICE_001",
    "device_name": "Test Device",
    "attendance_records": []
  }'
```

#### Test with real user data:
```bash
curl -X POST http://localhost:8081/api/device/push-attendance/ \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "TEST_DEVICE_002",
    "device_name": "Real Data Test Device",
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

#### Test complete check-in/check-out flow:
```bash
# Check-in
curl -X POST http://localhost:8081/api/device/push-attendance/ \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "FLOW_TEST_DEVICE",
    "device_name": "Flow Test Device",
    "attendance_records": [
      {
        "user_id": "201",
        "biometric_id": "201",
        "timestamp": "2024-01-15 09:00:00",
        "type": "check_in"
      }
    ]
  }'

# Check-out (after a few seconds)
curl -X POST http://localhost:8081/api/device/push-attendance/ \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "FLOW_TEST_DEVICE",
    "device_name": "Flow Test Device",
    "attendance_records": [
      {
        "user_id": "201",
        "biometric_id": "201",
        "timestamp": "2024-01-15 17:00:00",
        "type": "check_out"
      }
    ]
  }'
```

### 3. Database Verification

#### Run the database verification script:
```bash
python verify_database_records.py
```

#### Manual database checks:
```bash
# Check recent attendance records
python manage.py shell -c "
from core.models import Attendance
from django.utils import timezone
today = timezone.now().date()
recent = Attendance.objects.filter(date=today).order_by('-check_in_time')[:5]
for att in recent:
    print(f'{att.user.get_full_name()}: {att.check_in_time} - {att.check_out_time}')
"

# Check recent devices
python manage.py shell -c "
from core.models import Device
recent = Device.objects.order_by('-created_at')[:5]
for device in recent:
    print(f'{device.name} ({device.device_type}): {device.ip_address}:{device.port}')
"

# Check users with biometric IDs
python manage.py shell -c "
from core.models import CustomUser
users = CustomUser.objects.filter(biometric_id__isnull=False).exclude(biometric_id='')
print(f'Users with biometric IDs: {users.count()}')
for user in users[:5]:
    print(f'{user.get_full_name()}: {user.employee_id} -> {user.biometric_id}')
"
```

### 4. Log Monitoring

#### Monitor Django logs:
```bash
# Real-time log monitoring
tail -f logs/django.log

# Or if using system logging
tail -f /var/log/django/push_data.log
```

#### Monitor Apache2 logs:
```bash
# Push data access logs
tail -f /var/log/apache2/device_push_access.log

# Error logs
tail -f /var/log/apache2/device_push_error.log

# General Apache2 logs
tail -f /var/log/apache2/error.log
```

### 5. Real Device Testing

#### Test with actual biometric device:
1. **Configure device** with your server settings:
   - Server Mode: ADMS
   - Server Address: 82.25.109.137
   - Server Port: 8081
   - Enable Domain Name: NO
   - Enable Proxy Server: NO

2. **Have someone use the device** to scan their fingerprint

3. **Monitor logs** in real-time:
   ```bash
   tail -f /var/log/apache2/device_push_access.log
   ```

4. **Check database** for new records:
   ```bash
   python verify_database_records.py
   ```

## Expected Results

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

### Health Check Response:
```json
{
    "status": "healthy",
    "message": "Attendance server is running",
    "timestamp": "2024-01-15T10:30:00Z",
    "server_mode": "ADMS"
}
```

### Database Records Created:
- **Device record** (if new device)
- **Attendance record** for the user and date
- **ESSLAttendanceLog record** for audit trail

## Troubleshooting

### Common Issues:

1. **"No module named 'core.push_views'"**
   ```bash
   # Solution: Upload the push_views.py file to your server
   scp core/push_views.py user@server:/var/www/EmployeeAttendance/core/
   ```

2. **"User not found for ID"**
   ```bash
   # Solution: Ensure users have biometric_id set
   python manage.py shell -c "
   from core.models import CustomUser
   user = CustomUser.objects.get(employee_id='5')
   user.biometric_id = '5'
   user.save()
   "
   ```

3. **"Connection refused"**
   ```bash
   # Solution: Check if server is running on port 8081
   netstat -tlnp | grep 8081
   # Or check Apache2 configuration
   sudo apache2ctl configtest
   ```

4. **"No attendance records created"**
   ```bash
   # Solution: Check user biometric IDs and device configuration
   python verify_database_records.py
   ```

### Debug Commands:

```bash
# Check server status
systemctl status apache2

# Check port accessibility
curl -I http://localhost:8081/api/device/health-check/

# Check Django configuration
python manage.py check

# Test database connection
python manage.py shell -c "from django.db import connection; connection.ensure_connection(); print('DB OK')"
```

## Success Criteria

Your push attendance system is working correctly if:

- [ ] Health check endpoint returns 200 OK
- [ ] Push endpoint accepts POST requests
- [ ] Real user data is processed successfully
- [ ] Attendance records are created in database
- [ ] New devices are created automatically
- [ ] Check-in/check-out flow works correctly
- [ ] Error handling works with invalid data
- [ ] Logs show successful processing
- [ ] Real biometric device can push data

## Production Testing

For production testing:

1. **Use production URL:**
   ```bash
   python test_push_functionality.py --production
   ```

2. **Test with real devices:**
   - Configure devices with production server address
   - Test with actual employee biometric scans
   - Monitor logs for real-time data

3. **Verify data integrity:**
   - Check attendance records in database
   - Verify check-in/check-out times
   - Confirm device information is correct

## Monitoring in Production

Set up monitoring for:
- Server health (health check endpoint)
- Push data volume (log analysis)
- Error rates (error log monitoring)
- Database performance (query monitoring)
- Device connectivity (device sync times)

Your push attendance system is ready when all tests pass and real devices can successfully push data! 🎉
