# Employee Attendance System

A comprehensive Django-based web application for managing employee attendance, document generation, and real-time device integration with ZKTeco biometric devices.

##  Features

### Core Functionality
- **User Authentication & Authorization**: JWT-based authentication with role-based access control (Admin, Manager, Employee)
- **Multi-Office Support**: Office-based data filtering and management
- **Real-time Attendance Tracking**: Live attendance monitoring and updates
- **Document Generation**: Professional PDF generation with WeasyPrint (Ubuntu optimized)
- **Device Integration**: ZKTeco biometric device support (push & fetch data)
- **WebSocket Support**: Real-time updates and notifications
- **Auto-Services**: Background attendance fetching service

### Document Management
- **PDF Generation**: WeasyPrint-only implementation for Ubuntu servers
- **Document Templates**: Salary increment letters, offer letters, salary slips
- **HTML Fallback**: Graceful degradation for development environments
- **Professional Output**: High-quality, formatted documents

### Device Integration
- **ZKTeco Support**: Biometric device integration
- **Push Data Reception**: Real-time data from devices
- **Auto-Fetch Service**: Continuous attendance data retrieval
- **Device Management**: Device configuration and monitoring

## 🏗️ Technical Stack

### Backend
- **Framework**: Django 5.2.4
- **API**: Django REST Framework
- **Authentication**: JWT (Simple JWT)
- **Database**: MySQL with connection pooling
- **WebSocket**: Django Channels with Redis
- **PDF Generation**: WeasyPrint (Ubuntu optimized)
- **Background Tasks**: Custom service with threading

### Frontend (Deployed Separately)
- **Framework**: React.js
- **UI Components**: Custom components with Tailwind CSS
- **State Management**: React hooks
- **HTTP Client**: Axios
- **Real-time**: WebSocket connections
- **Note**: Frontend is deployed separately from this backend repository

### Infrastructure
- **Web Server**: Apache2 with mod_wsgi
- **Process Management**: systemd services
- **Caching**: Redis
- **SSL**: Let's Encrypt certificates
- **Logging**: Comprehensive logging system

## 📋 Prerequisites

- Ubuntu 20.04+ VPS
- Python 3.8+
- MySQL database
- Redis server
- Apache2 web server
- Domain name with SSL certificate

##  Quick Deployment

### 1. Clone Repository
```bash
git clone https://github.com/bkbimal250/hrpayroll.git
cd hrpayroll
```

### 2. Run Deployment Script
```bash
chmod +x deploy_from_github.sh
./deploy_from_github.sh
```

### 3. Create Environment File
```bash
cp env.example .env
nano .env  # Edit with your production values
```

### 4. Setup Django
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput
```

### 5. Configure Apache2
```bash
# Copy Apache configuration
sudo cp apache2_virtualhost.conf /etc/apache2/sites-available/employee-attendance.conf

# Enable site
sudo a2ensite employee-attendance.conf
sudo systemctl restart apache2
```

### 6. Setup SSL Certificate
```bash
sudo certbot --apache -d your-domain.com -d www.your-domain.com
```

## 📁 Project Structure

```
hrpayroll/
├── attendance_system/          # Django project settings
├── core/                       # Main Django app
│   ├── models.py              # Database models
│   ├── views.py               # API views
│   ├── document_views.py      # Document generation
│   ├── push_views.py          # Device push data
│   ├── authentication.py      # JWT authentication
│   └── management/commands/   # Django management commands
├── frontend/                   # React frontend
│   ├── AdminDashboard/        # Admin interface
│   └── ManagerDashboard/      # Manager interface
├── media/                      # User uploads
├── staticfiles/               # Collected static files
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables
└── deployment files...
```

## ⚙️ Configuration

### Environment Variables
Copy `env.example` to `.env` and configure:

```env
# Django Settings
ENVIRONMENT=production
DEBUG=False
SECRET_KEY=your-super-secret-key
ALLOWED_HOSTS=your-domain.com,www.your-domain.com

# Database Configuration
DB_ENGINE=django.db.backends.postgresql
DB_NAME=your_database_name
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_HOST=your_database_host
DB_PORT=5432

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

### WeasyPrint Dependencies (Ubuntu)
```bash
sudo apt install -y python3-cffi python3-brotli libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0
sudo apt install -y libffi-dev libjpeg-dev libpng-dev libgif-dev librsvg2-dev
```

## 🔧 Services

### Attendance Service
Auto-starts with Django to fetch attendance data from devices:
```bash
sudo systemctl start attendance-service
sudo systemctl status attendance-service
```

### Redis Service
Required for WebSocket support:
```bash
sudo systemctl start redis-server
sudo systemctl status redis-server
```

##  Features Overview

### Admin Dashboard
- User management
- Device management
- Reports and analytics
- Document generation
- System configuration

### Manager Dashboard
- Office-specific data
- Employee management
- Attendance reports
- Document generation

### Employee Portal
- Personal attendance view
- Document access
- Profile management

## 🔒 Security Features

- JWT token authentication
- Role-based permissions
- CORS configuration
- Security headers
- Environment variable protection
- Database connection security
- HTTPS enforcement

##  Performance Optimizations

- Database connection pooling
- Static file optimization
- Redis caching
- Query optimization
- Service monitoring

## 🐛 Troubleshooting

### Common Issues

#### WeasyPrint Installation
```bash
# Install missing dependencies
sudo apt install -y python3-cffi python3-brotli libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0

# Test installation
python -c "import weasyprint; print(weasyprint.__version__)"
```

#### Service Issues
```bash
# Check service status
sudo systemctl status attendance-service
sudo systemctl status apache2
sudo systemctl status redis-server

# Check logs
sudo tail -f /var/log/apache2/employee_attendance_error.log
sudo tail -f /var/log/attendance/django.log
```

## 📞 Support

For issues and support:
1. Check the logs: `/var/log/apache2/employee_attendance_error.log`
2. Verify service status: `systemctl status attendance-service`
3. Test WeasyPrint: `python -c "import weasyprint; print(weasyprint.__version__)"`

## 📄 License

This project is proprietary software. All rights reserved.

##  Production Ready

This system is production-ready with:
-  Ubuntu-optimized WeasyPrint PDF generation
-  Auto-attendance fetching service
-  Push data reception from devices
-  WebSocket support for real-time updates
-  Role-based authentication system
-  Production security configurations
-  Comprehensive deployment guides

**Deploy with confidence on your Apache2 VPS!** "# hrpayroll" 
