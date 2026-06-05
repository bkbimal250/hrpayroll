import os
from django.core.exceptions import ImproperlyConfigured

from .base import *


ENVIRONMENT = 'production'
DEBUG = False

if not os.environ.get('SECRET_KEY'):
    raise ImproperlyConfigured('SECRET_KEY must be set in production.')

SECRET_KEY = os.environ['SECRET_KEY']

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get(
        'ALLOWED_HOSTS',
        'dosapi.attendance.dishaonliesolution.workspa.in'
    ).split(',')
    if host.strip()
]

DATABASES = {
    'default': {
        'ENGINE': os.environ.get('DB_ENGINE', 'django.db.backends.postgresql'),
        'NAME': os.environ['DB_NAME'],
        'USER': os.environ['DB_USER'],
        'PASSWORD': os.environ['DB_PASSWORD'],
        'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'CONN_MAX_AGE': int(os.environ.get('DB_CONN_MAX_AGE', '60')),
    }
}

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'true').lower() == 'true'
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', '31536000'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.environ.get('SECURE_HSTS_INCLUDE_SUBDOMAINS', 'true').lower() == 'true'
SECURE_HSTS_PRELOAD = os.environ.get('SECURE_HSTS_PRELOAD', 'true').lower() == 'true'
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'SAMEORIGIN'

JWT_REFRESH_COOKIE_SAMESITE = os.environ.get('JWT_REFRESH_COOKIE_SAMESITE', 'None')

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        'CORS_ALLOWED_ORIGINS',
        (
            'https://dosemployees.dishaonlinesolution.in,'
            'https://dosmanagers.dishaonlinesolution.in,'
            'https://admindos.dishaonlinesolution.in,'
            'https://dosaccounts.dishaonlinesolution.in'
        )
    ).split(',')
    if origin.strip()
]
CORS_ALLOWED_ORIGIN_REGEXES = [
    r'^https://.*\.dishaonlinesolution\.in$',
]
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        'CSRF_TRUSTED_ORIGINS',
        (
            'https://dosapi.attendance.dishaonliesolution.workspa.in,'
            'https://dosemployees.dishaonlinesolution.in,'
            'https://dosmanagers.dishaonlinesolution.in,'
            'https://admindos.dishaonlinesolution.in,'
            'https://dosaccounts.dishaonlinesolution.in'
        )
    ).split(',')
    if origin.strip()
]

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
if 'django.middleware.security.SecurityMiddleware' in MIDDLEWARE and 'whitenoise.middleware.WhiteNoiseMiddleware' not in MIDDLEWARE:
    security_index = MIDDLEWARE.index('django.middleware.security.SecurityMiddleware')
    MIDDLEWARE.insert(security_index + 1, 'whitenoise.middleware.WhiteNoiseMiddleware')

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('CACHE_REDIS_URL', os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/2')),
    }
}

REDIS_URL = os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1')
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [REDIS_URL],
            'capacity': int(os.environ.get('CHANNEL_LAYER_CAPACITY', '1500')),
            'expiry': int(os.environ.get('CHANNEL_LAYER_EXPIRY', '60')),
        },
    },
}

WEBSOCKET_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        'WEBSOCKET_ALLOWED_ORIGINS',
        (
            'https://dosemployees.dishaonlinesolution.in,'
            'https://dosmanagers.dishaonlinesolution.in,'
            'https://admindos.dishaonlinesolution.in,'
            'https://dosaccounts.dishaonlinesolution.in'
        )
    ).split(',')
    if origin.strip()
]

LOGGING['handlers']['console']['level'] = os.environ.get('CONSOLE_LOG_LEVEL', 'INFO')
LOGGING['root']['level'] = os.environ.get('DJANGO_LOG_LEVEL', 'INFO')
