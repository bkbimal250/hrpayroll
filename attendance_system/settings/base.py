import os
from pathlib import Path
from datetime import timedelta
from django.utils.translation import gettext_lazy as _
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
# Note: Since this is in settings/base.py, we go up THREE levels
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# =============================================================================
# ENVIRONMENT CONFIGURATION
# =============================================================================
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'development')

# =============================================================================
# SECURITY SETTINGS
# =============================================================================
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-eg&hkh!w@e(%wx6aztj4+flb*fcl&a)*2zeh8rzzf^#n31!vb^')

# =============================================================================
# APPLICATION CONFIGURATION
# =============================================================================

# Django Core Apps
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]
    
# Third Party Apps
THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'channels',
]

# Admin Theme Apps (must be loaded before django.contrib.admin)
ADMIN_THEME_APPS = [
    'unfold',
    'unfold.contrib.filters',
    'unfold.contrib.forms',
    'unfold.contrib.import_export',
]
    
# Local Apps
LOCAL_APPS = [
    'core.apps.CoreConfig',
    'coreapp.apps.CoreappConfig',
]

# Combine all apps
INSTALLED_APPS = ADMIN_THEME_APPS + DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# =============================================================================
# MIDDLEWARE CONFIGURATION
# =============================================================================

DJANGO_MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

THIRD_PARTY_MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
]

CUSTOM_MIDDLEWARE = [
    'core.middleware.AdminCSPMiddleware',
    'core.middleware.APIAuthenticationDebugMiddleware',
]

MIDDLEWARE = THIRD_PARTY_MIDDLEWARE + DJANGO_MIDDLEWARE + CUSTOM_MIDDLEWARE

ROOT_URLCONF = 'attendance_system.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'attendance_system.wsgi.application'
ASGI_APPLICATION = 'attendance_system.asgi.application'

# =============================================================================
# PASSWORD VALIDATION
# =============================================================================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# =============================================================================
# INTERNATIONALIZATION
# =============================================================================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# =============================================================================
# STATIC AND MEDIA FILES
# =============================================================================
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

MEDIA_URL = os.environ.get('MEDIA_URL', '/media/')
MEDIA_ROOT = os.environ.get('MEDIA_ROOT', BASE_DIR / 'media')

# =============================================================================
# AUTHENTICATION AND USER MODEL
# =============================================================================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'core.CustomUser'

AUTHENTICATION_BACKENDS = [
    'core.authentication_backend.CustomAuthenticationBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# =============================================================================
# REST FRAMEWORK CONFIGURATION
# =============================================================================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ],
    'EXCEPTION_HANDLER': 'core.exception_handlers.custom_exception_handler',
}

# =============================================================================
# JWT CONFIGURATION
# =============================================================================
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': False,
    'JTI_CLAIM': 'jti',
    'SIGNING_KEY': SECRET_KEY,
    'ALGORITHM': 'HS256',
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# =============================================================================
# CORS CONFIGURATION
# =============================================================================
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    'https://dosemployees.dishaonlinesolution.in',
    'https://dosmanagers.dishaonlinesolution.in',
    'https://admindos.dishaonlinesolution.in',
    'https://dosaccounts.dishaonlinesolution.in',
    'https://res.cloudinary.com',
    'http://localhost:5173',
    'http://127.0.0.1:5174',
    'http://localhost:3000',
    'http://127.0.0.1:3000',
]
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://.*\.dishaonlinesolution\.in$",
    r"^http://localhost:\d+$",
    r"^http://127\.0\.0\.1:\d+$",
    r"^https://res\.cloudinary\.com$",  
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ['DELETE', 'GET', 'OPTIONS', 'PATCH', 'POST', 'PUT', 'HEAD']
CORS_ALLOW_HEADERS = [
    'accept', 'accept-encoding', 'authorization', 'content-type', 'dnt', 'origin', 
    'user-agent', 'x-csrftoken', 'x-requested-with', 'cache-control', 'pragma', 'expires'
]
CORS_ALLOW_ALL_HEADERS = True

# =============================================================================
# SECURITY SETTINGS (GENERAL)
# =============================================================================
X_FRAME_OPTIONS = 'SAMEORIGIN'
SILENCED_SYSTEM_CHECKS = ['security.W019']

# =============================================================================
# DJANGO-UNFOLD CONFIGURATION
# =============================================================================
def environment_callback(request):
    return os.environ.get('ENVIRONMENT', 'development')

UNFOLD = {
    "SITE_TITLE": "Disha Online Solution",
    "SITE_HEADER": "Disha Online Solution",
    "SITE_URL": "/",
    "SITE_SYMBOL": "settings",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "ENVIRONMENT": environment_callback,
    "COLORS": {
        "primary": {
            "50": "250 245 255", "100": "243 232 255", "200": "233 213 255",
            "300": "216 180 254", "400": "192 132 252", "500": "168 85 247",
            "600": "147 51 234", "700": "126 34 206", "800": "107 33 168", "900": "88 28 135",
        },
    },
}

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================
os.makedirs(BASE_DIR / 'logs', exist_ok=True)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}', 'style': '{'},
        'simple': {'format': '{levelname} {message}', 'style': '{'},
    },
    'handlers': {
        'console': {'level': 'DEBUG', 'class': 'logging.StreamHandler', 'formatter': 'simple'},
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
    },
    'root': {'handlers': ['console', 'file'], 'level': 'INFO'},
}

# =============================================================================
# EMAIL CONFIGURATION
# =============================================================================
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = os.environ.get('EMAIL_PORT', 587)
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', True)
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'info.dishaonlinesoution@gmail.com')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', 'ktrc uzzy upkr ftbv')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'Disha Online Solution <info.dishaonlinesoution@gmail.com>')

# =============================================================================
# SESSION AND CACHE CONFIGURATION
# =============================================================================
SESSION_ENGINE = os.environ.get('SESSION_ENGINE', 'django.contrib.sessions.backends.db')
CACHES = {
    'default': {
        'BACKEND': os.environ.get('CACHES_BACKEND', 'django.core.cache.backends.locmem.LocMemCache'),
        'LOCATION': 'unique-snowflake',
    }
}

# =============================================================================
# APPLICATION-SPECIFIC SETTINGS
# =============================================================================
COMPANY_NAME = "Disha Online Solution"
SITE_URL = os.environ.get('SITE_URL', 'https://dosapi.attendance.dishaonliesolution.workspa.in')
