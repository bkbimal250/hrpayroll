"""
WSGI config for attendance_system project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os
import sys
from pathlib import Path

# Add the project directory to the Python path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from django.core.wsgi import get_wsgi_application

# Set environment to production if not already set
if not os.environ.get('ENVIRONMENT'):
    os.environ.setdefault('ENVIRONMENT', 'production')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'attendance_system.settings')

application = get_wsgi_application()
