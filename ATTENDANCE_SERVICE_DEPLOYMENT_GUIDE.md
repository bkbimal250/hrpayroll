#  Django Attendance Service - Auto-Start Deployment Guide

## 📋 Overview

This guide explains how to configure the Django Attendance System to automatically start the ZKTeco attendance fetching service when the server starts, ensuring real-time attendance data collection.

##  What's Configured

###  Auto-Start Features
- **Automatic Service Startup**: Service starts when Django server starts
- **Real-time Data Fetching**: Fetches attendance data every 30 seconds
- **Production Ready**: Includes systemd service and startup scripts
- **Error Handling**: Automatic restart on failures
- **Logging**: Comprehensive logging for monitoring

### 🔧 Fixed Issues
- **Timezone Issues**: Fixed datetime comparison errors
- **Unicode Encoding**: Removed emojis from logs for Windows compatibility
- **Service Management**: Added proper start/stop/status commands

##  Quick Start

### 1. Development Mode
```bash
# Start the service manually
python manage.py start_attendance_service

# Check service status
python manage.py start_attendance_service --status

# Stop the service
python manage.py start_attendance_service --stop
```

### 2. Production Mode
```bash
# Make scripts executable
chmod +x start_attendance_service.sh
chmod +x stop_attendance_service.sh

# Start the service
./start_attendance_service.sh

# Stop the service
./stop_attendance_service.sh
```

## ⚙️ Configuration Options

### Environment Variables
Add these to your Django settings or environment:

```bash
# Enable auto-start in production
ENVIRONMENT=production
AUTO_START_ATTENDANCE_SERVICE=true

# Or set in Django settings
AUTO_START_ATTENDANCE_SERVICE = True
```

### Service Configuration
```bash
# Adjust fetch interval (default: 30 seconds)
python manage.py start_attendance_service --interval 60

# Run as daemon
python manage.py start_attendance_service --daemon
```

## 🐧 Linux Production Deployment

### 1. Systemd Service (Recommended)

1. **Copy the service file**:
```bash
sudo cp attendance_service.service /etc/systemd/system/
```

2. **Edit the service file** with your actual paths:
```bash
sudo nano /etc/systemd/system/attendance_service.service
```

Update these paths:
- `WorkingDirectory=/path/to/your/django/project`
- `ExecStart=/path/to/your/venv/bin/python manage.py start_attendance_service --daemon`
- `ReadWritePaths=/path/to/your/django/project/logs`

3. **Enable and start the service**:
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable attendance_service

# Start the service
sudo systemctl start attendance_service

# Check status
sudo systemctl status attendance_service

# View logs
sudo journalctl -u attendance_service -f
```

### 2. Manual Startup Scripts

1. **Update the startup script**:
```bash
nano start_attendance_service.sh
```

Update these paths:
- `PROJECT_DIR="/path/to/your/django/project"`
- `VENV_DIR="/path/to/your/venv"`

2. **Make executable and start**:
```bash
chmod +x start_attendance_service.sh
chmod +x stop_attendance_service.sh

# Start service
./start_attendance_service.sh

# Check if running
ps aux | grep attendance_service
```

## 🪟 Windows Production Deployment

### 1. Windows Service (Using NSSM)

1. **Download NSSM**: https://nssm.cc/download

2. **Install the service**:
```cmd
nssm install AttendanceService
```

3. **Configure the service**:
- **Path**: `C:\path\to\your\venv\Scripts\python.exe`
- **Startup directory**: `C:\path\to\your\django\project`
- **Arguments**: `manage.py start_attendance_service --daemon`

4. **Start the service**:
```cmd
nssm start AttendanceService
```

### 2. Task Scheduler

1. **Open Task Scheduler**
2. **Create Basic Task**:
   - Name: "Django Attendance Service"
   - Trigger: "At startup"
   - Action: "Start a program"
   - Program: `C:\path\to\your\venv\Scripts\python.exe`
   - Arguments: `manage.py start_attendance_service --daemon`
   - Start in: `C:\path\to\your\django\project`

##  Monitoring and Logs

### Log Files
- **Service Logs**: `logs/attendance_service.out`
- **Error Logs**: `logs/attendance_service.err`
- **Django Logs**: `logs/django.log`
- **Auto-fetch Logs**: `logs/auto_fetch_attendance.log`

### Monitoring Commands
```bash
# Check service status
python manage.py start_attendance_service --status

# View real-time logs
tail -f logs/attendance_service.out

# Check systemd service
sudo systemctl status attendance_service

# View systemd logs
sudo journalctl -u attendance_service -f
```

### Health Checks
```bash
# Test device connectivity
python manage.py setup_zkteco_push --test-connection

# Check push configuration
python manage.py configure_zkteco_push --status

# View device status
python check_zkteco_devices.py
```

## 🔧 Troubleshooting

### Common Issues

1. **Service won't start**:
   - Check Python path and virtual environment
   - Verify Django settings
   - Check log files for errors

2. **Timezone errors**:
   - Ensure Django timezone settings are correct
   - Check device time synchronization

3. **Device connection issues**:
   - Verify network connectivity
   - Check device IP addresses and ports
   - Test with `python manage.py setup_zkteco_push --test-connection`

4. **Permission issues**:
   - Ensure proper file permissions
   - Check user permissions for service account

### Debug Commands
```bash
# Test service manually
python manage.py start_attendance_service --foreground

# Check device connectivity
python manage.py setup_zkteco_push --test-connection

# View detailed logs
tail -f logs/auto_fetch_attendance.log
```

##  Performance Tuning

### Optimization Settings
```python
# In Django settings
AUTO_START_ATTENDANCE_SERVICE = True
ATTENDANCE_FETCH_INTERVAL = 30  # seconds
ATTENDANCE_BATCH_SIZE = 50
ATTENDANCE_MAX_RETRIES = 3
```

### Resource Monitoring
```bash
# Monitor CPU and memory usage
top -p $(pgrep -f attendance_service)

# Monitor network connections
netstat -an | grep :4370

# Check disk usage
df -h logs/
```

##  Service Management

### Start/Stop Commands
```bash
# Manual start
python manage.py start_attendance_service

# Manual stop
python manage.py start_attendance_service --stop

# Systemd (Linux)
sudo systemctl start attendance_service
sudo systemctl stop attendance_service
sudo systemctl restart attendance_service

# Windows Service
net start AttendanceService
net stop AttendanceService
```

### Auto-Restart Configuration
The service is configured to automatically restart on failure:
- **Systemd**: `Restart=always`
- **NSSM**: Auto-restart enabled
- **Manual scripts**: Include restart logic

##  Verification

### Test Checklist
- [ ] Service starts automatically on server boot
- [ ] ZKTeco devices are connected and reachable
- [ ] Attendance data is being fetched every 30 seconds
- [ ] Logs show successful biometric scans
- [ ] Database is being updated with attendance records
- [ ] Service restarts automatically on failure

### Success Indicators
```
INFO Fetching data from Ace Track (zkteco)
INFO Connected to ZKTeco device Ace Track
INFO Processing 15 attendance records from Ace Track
INFO BIOMETRIC SCAN: John Doe (ID: 123) scanned at 14:30:15 on Ace Track
INFO Processed 15 new records, prevented 0 duplicates from Ace Track
```

## 🎉 Summary

The Django Attendance System is now configured for automatic real-time attendance data fetching:

1. ** Auto-Start**: Service starts when Django server starts
2. ** Real-Time**: Fetches data every 30 seconds
3. ** Production Ready**: Includes systemd service and startup scripts
4. ** Error Handling**: Automatic restart and comprehensive logging
5. ** Monitoring**: Full logging and status monitoring

The system will now automatically collect attendance data from all ZKTeco devices in real-time, ensuring your attendance records are always up-to-date.

**Status**:  **FULLY CONFIGURED FOR AUTO-START**
