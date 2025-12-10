import os
import warnings

from pathlib import Path
import environ
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _
from datetime import timedelta
import logging
warnings.filterwarnings("ignore", message="pkg_resources is deprecated as an API")

# ======================== Base Dir & Env ========================
BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = env('DJANGO_SECRET_KEY')

DEBUG = env.bool('DEBUG', default=True)
# Force DEBUG to False to avoid HTML debug pages in logs
DEBUG = False
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[
    "localhost", "127.0.0.1", "notifications-service", "0.0.0.0", "*", "notifications-service:3001"
])

GATEWAY_URL = env("API_GATEWAY_URL", default="https://server1.prolianceltd.com")

# ======================== Database ========================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('NOTIFICATIONS_DB_NAME', default='notifications_db'),
        'USER': env('DB_USER', default='postgres'),
        'PASSWORD': env('DB_PASSWORD', default='password'),
        'HOST': env('DB_HOST', default='notifications_postgres'),
        'PORT': env('DB_PORT', default='5432'),
        'CONN_MAX_AGE': 60,
        'OPTIONS': {
            'connect_timeout': 30,
        },
    }
}

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'rest_framework',
    'drf_spectacular',
    'drf_yasg',
    'django_filters',
    'channels',
    'django_extensions',
    'notifications',  # Main app for notification models/views
]



ASGI_APPLICATION = 'notification_service.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [env('REDIS_URL', default='redis://notifications_redis:6379/1')],
        },
    },
}

# ======================== Middleware ========================
MIDDLEWARE = [
    'notification_service.middleware.DatabaseConnectionMiddleware',
    'notification_service.middleware.MicroserviceRS256JWTMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

AUTHENTICATION_BACKENDS = ('django.contrib.auth.backends.ModelBackend',)

ROOT_URLCONF = 'notification_service.urls'
WSGI_APPLICATION = 'notification_service.wsgi.application'

# ======================== REST Framework ========================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (),
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.AllowAny',),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100
}

# ======================== External Services ========================
AUTH_SERVICE_URL = env('AUTH_SERVICE_URL', default='http://auth-service:8001')
API_GATEWAY_URL = env('API_GATEWAY_URL', default='http://api_gateway:9090')  # For auth calls through gateway
HR_SERVICE_URL = env('HR_SERVICE_URL', default='http://hr-service:8004')  # For integrations

SUPABASE_URL = env('SUPABASE_URL', default='')
SUPABASE_KEY = env('SUPABASE_KEY', default='')
SUPABASE_BUCKET = env('SUPABASE_BUCKET', default='')

STORAGE_TYPE = env('STORAGE_TYPE', default='supabase')

KAFKA_BOOTSTRAP_SERVERS = env('KAFKA_BOOTSTRAP_SERVERS', default='kafka:9092')
KAFKA_TOPICS = {
    'notification_events': 'notification-events',
    'tenant': 'tenant-events',
}

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://notifications_redis:6379/0")
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

# ======================== CORS ========================
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=['http://localhost:3000', 'http://localhost:5173'])
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ['DELETE', 'GET', 'OPTIONS', 'PATCH', 'POST', 'PUT']
CORS_ALLOW_HEADERS = ['accept', 'authorization', 'content-type', 'origin', 'x-csrftoken', 'x-requested-with']

# ======================== Static & Media ========================
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# ======================== Templates ========================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ======================== Logging ========================
LOG_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} [{levelname}] {name}: {message}',
            'style': '{'
        },
        'simple': {
            'format': '[{levelname}] {message}',
            'style': '{'
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOG_DIR, 'notifications_service.log'),
            'maxBytes': 5 * 1024 * 1024,
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],  # Remove console handler to avoid HTML debug output
            'level': 'INFO',
            'propagate': True,
        },
        'notifications': {
            'handlers': ['file'],  # Remove console handler
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# ======================== Defaults ========================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SPECTACULAR_SETTINGS = {
    'TITLE': 'Notification Service API',
    'DESCRIPTION': 'Multi-Tenant Notification System API',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SWAGGER_UI_SETTINGS': {
        'persistAuthorization': True,
    },
    'COMPONENT_SPLIT_REQUEST': True,
}

# Fix for host parsing (from your HR settings)
import django.http.request

def patched_split_domain_port(host):
    if host and host.count(':') == 1 and host.rfind(']') < host.find(':'):
        host, port = host.split(':', 1)
    else:
        port = ''
    return host, port

django.http.request.split_domain_port = patched_split_domain_port



KAFKA_TOPICS = {
    'notification_events': 'notification-events',
    'auth_events': 'auth-events',  # Consume from auth service
    'hr_events': 'hr-events',  # Consume from HR
    'tenant': 'tenant-events',
}

KAFKA_GROUP_ID = env('KAFKA_GROUP_ID', default='notifications-consumer-group')
KAFKA_AUTO_OFFSET_RESET = env('KAFKA_AUTO_OFFSET_RESET', default='latest')

# ======================== Default Notification Credentials ========================
# These are used as fallbacks when tenants don't have custom credentials configured

DEFAULT_EMAIL_CREDENTIALS = {
    'smtp_host': 'mailhog',
    'smtp_port': 1025,
    'username': '',
    'password': '',
    'from_email': 'test@example.com',
    'use_ssl': False
}



DEFAULT_SMS_CREDENTIALS = {
    'account_sid': env('DEFAULT_TWILIO_ACCOUNT_SID', default='ACtest1234567890'),
    'auth_token': env('DEFAULT_TWILIO_AUTH_TOKEN', default='test_auth_token'),
    'from_number': env('DEFAULT_TWILIO_FROM_NUMBER', default='+1234567890')
}

DEFAULT_PUSH_CREDENTIALS = {
    'type': 'service_account',
    'project_id': env('DEFAULT_FIREBASE_PROJECT_ID', default='test-project'),
    'private_key_id': env('DEFAULT_FIREBASE_PRIVATE_KEY_ID', default='test_key_id'),
    'private_key': env('DEFAULT_FIREBASE_PRIVATE_KEY', default='test_private_key'),
    'client_email': env('DEFAULT_FIREBASE_CLIENT_EMAIL', default='test@test-project.iam.gserviceaccount.com'),
    'client_id': env('DEFAULT_FIREBASE_CLIENT_ID', default='123456789'),
    'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
    'token_uri': 'https://oauth2.googleapis.com/token',
    'auth_provider_x509_cert_url': 'https://www.googleapis.com/oauth2/v1/certs',
    'client_x509_cert_url': env('DEFAULT_FIREBASE_CLIENT_X509_CERT_URL', default='https://www.googleapis.com/robot/v1/metadata/x509/test@test-project.iam.gserviceaccount.com')
}

# Encryption key for sensitive credential fields
ENCRYPTION_KEY = env('ENCRYPTION_KEY', default='your-32-character-encryption-key-here')

# ======================== Django Email Configuration ========================
# Global email settings (used by Django's email backend)
