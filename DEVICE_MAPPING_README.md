# Device User Mapping and Attendance Fetching

This guide explains how to map users from ZKTeco devices to system users and fetch attendance data.

## Overview

The system includes three ZKTeco devices:
- **Ace Track** (192.168.200.150) - Office: Ace Track
- **Bootcamp** (192.168.150.74) - Office: Bootcamp  
- **DOS Attendance** (192.168.200.64) - Office: Disha online solution

## Files Created

### 1. `map_device_users.py`
Standalone script to map device users to system users.

**Features:**
- Fetches users from all ZKTeco devices
- Creates new system users for unmapped device users
- Maps device users to system users using DeviceUser model
- Sets default password: `Dos@9999`
- Assigns users to appropriate offices and departments

**Usage:**
```bash
python map_device_users.py
```

### 2. `fetch_attendance_from_devices.py`
Standalone script to fetch attendance data from mapped devices.

**Features:**
- Fetches attendance logs from all devices with mapped users
- Processes attendance data and creates Attendance records
- Creates ESSLAttendanceLog records for raw data
- Groups check-in/check-out times by user and date

**Usage:**
```bash
python fetch_attendance_from_devices.py
```

### 3. `core/management/commands/map_and_fetch_attendance.py`
Django management command that combines both operations.

**Features:**
- Maps device users to system users
- Fetches attendance data from devices
- Configurable options for different scenarios
- Dry-run mode for testing

**Usage:**
```bash
# Map users and fetch attendance (default: last 7 days)
python manage.py map_and_fetch_attendance --create-users

# Only map users (don't fetch attendance)
python manage.py map_and_fetch_attendance --map-only --create-users

# Only fetch attendance (don't map users)
python manage.py map_and_fetch_attendance --fetch-only --days 14

# Process specific device
python manage.py map_and_fetch_attendance --device-ip 192.168.200.150

# Dry run (show what would be done)
python manage.py map_and_fetch_attendance --dry-run
```

### 4. `run_device_mapping.py`
Simple wrapper script to run the mapping process.

**Usage:**
```bash
python run_device_mapping.py
```

## Process Flow

### Step 1: User Mapping
1. **Connect to devices**: Test connectivity to all ZKTeco devices
2. **Fetch device users**: Get all users registered on each device
3. **Create system users**: For each unmapped device user:
   - Generate username from device user ID or name
   - Set default password: `Dos@9999`
   - Assign to appropriate office (based on device location)
   - Set role as 'employee'
   - Assign to default department and designation
4. **Create mappings**: Link device users to system users via DeviceUser model

### Step 2: Attendance Fetching
1. **Connect to devices**: Test connectivity to devices with mapped users
2. **Fetch attendance logs**: Get attendance data for specified date range
3. **Process logs**: Group by user and date, determine check-in/check-out times
4. **Create records**: 
   - Create/update Attendance records
   - Create ESSLAttendanceLog records for raw data

## Database Models Used

### DeviceUser Model
Maps device users to system users:
- `device`: Foreign key to Device
- `device_user_id`: User ID from device
- `device_user_name`: Name from device
- `system_user`: Foreign key to CustomUser (mapped system user)
- `is_mapped`: Boolean indicating if mapping is complete

### CustomUser Model
System users with additional fields:
- `biometric_id`: Links to device user ID
- `employee_id`: Employee identifier
- `office`: Assigned office
- `department`: Assigned department
- `designation`: Job designation

### Attendance Model
Daily attendance records:
- `user`: Foreign key to CustomUser
- `date`: Attendance date
- `check_in_time`: Check-in timestamp
- `check_out_time`: Check-out timestamp
- `device`: Device used for attendance
- `status`: 'present' or 'absent'

### ESSLAttendanceLog Model
Raw attendance logs from devices:
- `device`: Foreign key to Device
- `biometric_id`: Device user ID
- `user`: Foreign key to CustomUser (if mapped)
- `punch_time`: Timestamp of punch
- `punch_type`: 'in' or 'out'

## Configuration

### Default Settings
- **Default password**: `Dos@9999`
- **Default role**: `employee`
- **Default department**: `General` (created if not exists)
- **Default designation**: `Employee` (created if not exists)
- **Attendance fetch period**: 7 days (configurable)

### Device Configuration
Devices are configured in the database with:
- IP addresses and ports
- Office assignments
- Device types (ZKTeco)
- Active status

## Logging

All scripts create detailed logs in the `logs/` directory:
- `device_user_mapping.log`: User mapping operations
- `attendance_fetching.log`: Attendance fetching operations

## Error Handling

The scripts include comprehensive error handling:
- Device connectivity issues
- User creation failures
- Attendance processing errors
- Database transaction rollbacks

## Monitoring

### Check Mapping Status
```python
from core.models import DeviceUser, CustomUser

# Total device users
total_device_users = DeviceUser.objects.count()

# Mapped users
mapped_users = DeviceUser.objects.filter(is_mapped=True).count()

# Mapping percentage
mapping_percentage = (mapped_users / total_device_users * 100) if total_device_users > 0 else 0
```

### Check Attendance Data
```python
from core.models import Attendance
from datetime import date, timedelta

# Last 7 days attendance
end_date = date.today()
start_date = end_date - timedelta(days=7)

attendance_records = Attendance.objects.filter(date__range=[start_date, end_date])
total_records = attendance_records.count()
```

## Troubleshooting

### Common Issues

1. **Device not reachable**
   - Check network connectivity
   - Verify IP addresses and ports
   - Ensure devices are powered on

2. **No users found on device**
   - Verify device has registered users
   - Check device configuration
   - Ensure proper device connection

3. **User mapping failures**
   - Check for duplicate usernames
   - Verify biometric_id uniqueness
   - Review database constraints

4. **Attendance processing errors**
   - Check date/time formats
   - Verify user mappings exist
   - Review attendance log structure

### Debug Mode
Use dry-run mode to test without making changes:
```bash
python manage.py map_and_fetch_attendance --dry-run
```

## Automation

For production use, consider setting up automated execution:

### Cron Job (Linux/Mac)
```bash
# Run every hour
0 * * * * cd /path/to/project && python manage.py map_and_fetch_attendance --create-users
```

### Windows Task Scheduler
Create a scheduled task to run `run_device_mapping.py` periodically.

### Systemd Service (Linux)
Create a systemd service for continuous operation:
```bash
# Run the existing auto_fetch_zkteco command
python manage.py auto_fetch_zkteco --daemon
```

## Security Notes

- Default password `Dos@9999` should be changed for production
- Ensure proper network security for device communication
- Regular backup of attendance data
- Monitor logs for suspicious activity

## Support

For issues or questions:
1. Check the logs in `logs/` directory
2. Review device connectivity
3. Verify database constraints
4. Test with dry-run mode first
