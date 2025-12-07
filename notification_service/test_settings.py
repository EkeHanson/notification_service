"""
Test configuration for Django notification service
Inherits from production settings but overrides for testing
"""
import os
from pathlib import Path
import environ

# Load environment variables
BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# ======================== Core Settings ========================
SECRET_KEY = 'test-secret-key-insecure-for-testing-only'
DEBUG = True
ALLOWED_HOSTS = ['*', 'localhost', '127.0.0.1', 'testserver']

# ======================== Database (SQLite for testing) ========================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# ======================== Installed Apps ========================
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

# ======================== Middleware ========================
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ======================== ASGI/URL ========================
ASGI_APPLICATION = 'notification_service.asgi.application'
ROOT_URLCONF = 'notification_service.urls'
WSGI_APPLICATION = 'notification_service.wsgi.application'

# ======================== Channel Layers (In-Memory for testing) ========================
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer'
    }
}

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

# ======================== Cache (In-Memory for testing) ========================
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'test-cache',
    }
}

# ======================== Templates ========================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

# ======================== Password Validation ========================
AUTH_PASSWORD_VALIDATORS = []  # Disabled for faster tests

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',  # Fast for testing
]

# ======================== Logging (Minimal for testing) ========================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
}

# ======================== External Services ========================
AUTH_SERVICE_URL = env('AUTH_SERVICE_URL', default='http://localhost:8001')
HR_SERVICE_URL = env('HR_SERVICE_URL', default='http://localhost:8004')
SUPABASE_URL = env('SUPABASE_URL', default='http://localhost')
SUPABASE_KEY = env('SUPABASE_KEY', default='test-key')
SUPABASE_BUCKET = env('SUPABASE_BUCKET', default='test-bucket')
STORAGE_TYPE = env('STORAGE_TYPE', default='supabase')
KAFKA_BOOTSTRAP_SERVERS = env('KAFKA_BOOTSTRAP_SERVERS', default='localhost:9092')
REDIS_URL = env('REDIS_URL', default='redis://localhost:6379/0')

# ======================== Celery (Eager mode for testing) ========================
CELERY_BROKER_URL = 'memory://'
CELERY_RESULT_BACKEND = 'cache+locmem://'
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

# ======================== CORS ========================
CORS_ALLOWED_ORIGINS = ['http://localhost:5173', 'http://localhost:3000']

# ======================== Security ========================
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False
CSRF_TRUSTED_ORIGINS = ['http://localhost:5173', 'http://localhost:3000']

# Encryption key for testing (proper Fernet key - 32 url-safe base64-encoded bytes)
ENCRYPTION_KEY = 'jNnudcc-1crloVUwrveiOO_Hn5tJ6ZfXsCEdPINOkZ4='

# ======================== Internationalization ========================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ======================== Static Files ========================
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# ======================== Default Auto Field ========================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
