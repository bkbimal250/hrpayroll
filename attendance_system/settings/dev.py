from .base import *

DEBUG = True

ALLOWED_HOSTS = ['*']

LOCAL_DEV_ORIGINS = [
    'http://localhost:5173',
    'http://localhost:5174',
    'http://localhost:5175',
    'http://127.0.0.1:5173',
    'http://127.0.0.1:5174',
    'http://127.0.0.1:5175',
]

CSRF_TRUSTED_ORIGINS = list(dict.fromkeys(CSRF_TRUSTED_ORIGINS + LOCAL_DEV_ORIGINS))
CORS_ALLOWED_ORIGINS = list(dict.fromkeys(CORS_ALLOWED_ORIGINS + LOCAL_DEV_ORIGINS))

REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'core.authentication.CustomJWTAuthentication',
    ],
}

# Database configuration for development
DATABASES = {
    'default': {
        'ENGINE': os.environ.get('DB_ENGINE', 'django.db.backends.postgresql'),
        'NAME': os.environ.get('DB_NAME', 'dishasolutionattendance'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'Spajobs@8989'),
        'HOST': os.environ.get('DB_HOST', ''),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
