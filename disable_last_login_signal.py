#!/usr/bin/env python3
"""
Script to disable the last_login update signal temporarily
"""

import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'attendance_system.settings')
django.setup()

from django.contrib.auth.models import update_last_login
from django.contrib.auth.signals import user_logged_in

# Disconnect the signal
user_logged_in.disconnect(update_last_login)

print(" Disconnected last_login update signal")

# Test login now
from django.test import Client

client = Client()
response = client.post('/admin/login/', {
    'username': 'dosadmin',
    'password': 'admin123',
    'next': '/admin/'
})

print(f'Login response status: {response.status_code}')
if response.status_code == 302:
    print(' Login successful - redirecting to admin')
    print(f'Redirect URL: {response.url}')
else:
    print(' Login still failing')
    if hasattr(response, 'content'):
        print(f'Response content: {response.content.decode()[:200]}...')
