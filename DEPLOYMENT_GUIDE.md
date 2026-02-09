# Employee Attendance System - Ubuntu VPS Deployment Guide

This guide will help you deploy the Employee Attendance System on an Ubuntu VPS with Apache2.

## Prerequisites

- Ubuntu 20.04+ VPS
- Root or sudo access
- Domain name pointing to your VPS
- MySQL database (remote or local)

## Quick Deployment

### 1. Upload Project Files

```bash
# Upload your project files to the VPS
scp -r /path/to/EmployeeAttandance root@your-vps-ip:/var/www/
```

### 2. Run Deployment Script

```bash
# Make the script executable
chmod +x /var/www/EmployeeAttandance/deploy_ubuntu_vps.sh

# Run the deployment script
cd /var/www/EmployeeAttandance
./deploy_ubuntu_vps.sh
```

## Manual Deployment Steps

### 1. System Setup

```bash
# Update system
apt update && apt upgrade -y

# Install required packages
apt install -y python3 python3-pip python3-venv apache2 libapache2-mod-wsgi-py3 mysql-client redis-server git curl wget unzip
```

### 2. Python Environment

```bash
# Create virtual environment
cd /var/www/EmployeeAttandance
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration

Create `.env` file:

```bash
cat > .env << EOF
ENVIRONMENT=production
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
DB_ENGINE=django.db.backends.mysql
DB_NAME=u434975676_DOS
DB_USER=u434975676_bimal
DB_PASSWORD=DishaSolution@8989
DB_HOST=193.203.184.215
DB_PORT=3306
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
CORS_ALLOWED_ORIGINS=https://your-domain.com,https://www.your-domain.com
LOG_LEVEL=INFO
LOG_FILE=/var/www/EmployeeAttandance/logs/django.log
STATIC_ROOT=/var/www/EmployeeAttandance/staticfiles
MEDIA_ROOT=/var/www/EmployeeAttandance/media
EOF
```

### 4. Django Setup

```bash
# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Create superuser
python manage.py createsuperuser
```

### 5. Apache2 Configuration

```bash
# Enable required modules
a2enmod ssl rewrite headers wsgi

# Copy virtual host configuration
cp apache2_virtualhost.conf /etc/apache2/sites-available/employee-attendance.conf

# Update domain in configuration
sed -i 's/your-domain.com/your-actual-domain.com/g' /etc/apache2/sites-available/employee-attendance.conf

# Enable site
a2ensite employee-attendance.conf
a2dissite 000-default.conf
```

### 6. SSL Certificate

```bash
# Install Certbot
apt install -y certbot python3-certbot-apache

# Get SSL certificate
certbot --apache -d your-domain.com -d www.your-domain.com
```

### 7. Automatic Attendance Fetching

```bash
# Copy systemd service
cp attendance_fetcher.service /etc/systemd/system/

# Enable and start service
systemctl daemon-reload
systemctl enable attendance_fetcher.service
systemctl start attendance_fetcher.service
```

### 8. Start Services

```bash
# Start all services
systemctl start redis-server
systemctl enable redis-server
systemctl restart apache2
```

## Configuration Files

### Apache2 Virtual Host

The `apache2_virtualhost.conf` file contains the Apache2 configuration with:
- SSL/HTTPS setup
- Security headers
- Static file serving
- WSGI configuration

### Systemd Service

The `attendance_fetcher.service` file configures:
- Automatic attendance fetching
- Service restart on failure
- Proper user permissions
- Logging

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `ENVIRONMENT` | Environment type | `production` |
| `SECRET_KEY` | Django secret key | Auto-generated |
| `ALLOWED_HOSTS` | Allowed hostnames | `your-domain.com,www.your-domain.com` |
| `DB_NAME` | Database name | `u434975676_DOS` |
| `DB_USER` | Database user | `u434975676_bimal` |
| `DB_PASSWORD` | Database password | `DishaSolution@8989` |
| `DB_HOST` | Database host | `193.203.184.215` |
| `CORS_ALLOWED_ORIGINS` | CORS origins | `https://your-domain.com` |

## Security Considerations

### 1. Firewall Configuration

```bash
# Configure UFW
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw enable
```

### 2. File Permissions

```bash
# Set proper permissions
chown -R www-data:www-data /var/www/EmployeeAttandance
chmod -R 755 /var/www/EmployeeAttandance
chmod -R 775 /var/www/EmployeeAttandance/logs
chmod -R 775 /var/www/EmployeeAttandance/media
```

### 3. Environment File Security

```bash
# Secure environment file
chmod 600 /var/www/EmployeeAttandance/.env
chown www-data:www-data /var/www/EmployeeAttandance/.env
```

## Monitoring and Maintenance

### 1. Log Monitoring

```bash
# View application logs
tail -f /var/www/EmployeeAttandance/logs/django.log

# View Apache logs
tail -f /var/log/apache2/employee_attendance_error.log
tail -f /var/log/apache2/employee_attendance_access.log

# View attendance fetcher logs
journalctl -u attendance_fetcher.service -f
```

### 2. Service Status

```bash
# Check service status
systemctl status apache2
systemctl status attendance_fetcher.service
systemctl status redis-server
```

### 3. Database Backup

The deployment script creates a backup script at `/var/www/EmployeeAttandance/backup.sh` that:
- Backs up the database daily
- Backs up media files
- Keeps backups for 7 days
- Runs automatically via cron

## Troubleshooting

### Common Issues

1. **Permission Denied Errors**
   ```bash
   chown -R www-data:www-data /var/www/EmployeeAttandance
   chmod -R 755 /var/www/EmployeeAttandance
   ```

2. **Database Connection Issues**
   - Check database credentials in `.env`
   - Verify database server is accessible
   - Check firewall rules

3. **Static Files Not Loading**
   ```bash
   python manage.py collectstatic --noinput
   systemctl restart apache2
   ```

4. **Attendance Fetcher Not Working**
   ```bash
   systemctl status attendance_fetcher.service
   journalctl -u attendance_fetcher.service
   ```

### Log Locations

- Django logs: `/var/www/EmployeeAttandance/logs/django.log`
- Apache error logs: `/var/log/apache2/employee_attendance_error.log`
- Apache access logs: `/var/log/apache2/employee_attendance_access.log`
- Systemd service logs: `journalctl -u attendance_fetcher.service`

## Performance Optimization

### 1. Database Optimization

- Enable MySQL query cache
- Optimize database indexes
- Use connection pooling

### 2. Static Files

- Use CDN for static files
- Enable gzip compression
- Set proper cache headers

### 3. Caching

- Enable Redis caching
- Use Django cache framework
- Implement page caching

## Updates and Maintenance

### 1. Application Updates

```bash
# Pull latest changes
cd /var/www/EmployeeAttandance
git pull origin main

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Restart services
systemctl restart apache2
systemctl restart attendance_fetcher.service
```

### 2. System Updates

```bash
# Update system packages
apt update && apt upgrade -y

# Restart services if needed
systemctl restart apache2
systemctl restart attendance_fetcher.service
```

## Support

For issues and support:
1. Check the logs first
2. Verify configuration files
3. Test database connectivity
4. Check service status

## Security Checklist

- [ ] SSL certificate installed and working
- [ ] Firewall configured properly
- [ ] File permissions set correctly
- [ ] Environment variables secured
- [ ] Database credentials protected
- [ ] Regular backups configured
- [ ] Log monitoring in place
- [ ] Services running as non-root user