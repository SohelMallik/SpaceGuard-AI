"""
SpaceGuard AI — Django Settings
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

# Load environment variables from .env file
load_dotenv(Path(__file__).resolve().parent.parent.parent / '.env')

BASE_DIR = Path(__file__).resolve().parent.parent

# Security
INSECURE_DEV_SECRET = 'django-insecure-dev-key-change-in-production'
SECRET_KEY = os.environ.get('SECRET_KEY', INSECURE_DEV_SECRET)
DEBUG = os.environ.get('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = [h.strip() for h in os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if h.strip()]

# Production safety check: refuse to start without a real SECRET_KEY when DEBUG is off
if not DEBUG and SECRET_KEY == INSECURE_DEV_SECRET:
    raise ImproperlyConfigured(
        'SECRET_KEY is missing or set to the insecure development default. '
        'Set a strong SECRET_KEY environment variable in production.'
    )

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'rest_framework',
    # SpaceGuard apps
    'missions',
    'telemetry',
    'anomaly',
    'alerts',
    'assistant',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Rate limiting for API endpoints
    'spaceguard.middleware.RateLimitMiddleware',
]

ROOT_URLCONF = 'spaceguard.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR.parent / 'templates'],
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

WSGI_APPLICATION = 'spaceguard.wsgi.application'

# Database — SQLite for prototype; swap ENGINE for PostgreSQL in production
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static and media files
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR.parent / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework
API_RATE_LIMIT_ENABLED = os.environ.get('API_RATE_LIMIT_ENABLED', 'True') == 'True'
API_AUTH_REQUIRED = os.environ.get('API_AUTH_REQUIRED', 'False') == 'True'

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.FormParser',
    ],
    'EXCEPTION_HANDLER': 'spaceguard.exceptions.custom_exception_handler',
    # Authentication: browser requests (dashboard) use the Django session;
    # external clients can authenticate with HTTP Basic (user/password).
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    # API_AUTH_REQUIRED=True (production) enforces authentication on every endpoint.
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated' if API_AUTH_REQUIRED
        else 'rest_framework.permissions.AllowAny',
    ],
    # Throttling for expensive AI endpoints (analyze / assistant)
    'DEFAULT_THROTTLE_CLASSES': [
        'spaceguard.throttling.ActionScopedRateThrottle',
    ] if API_RATE_LIMIT_ENABLED else [],
    'DEFAULT_THROTTLE_RATES': {
        'ai': '10/min',
    },
}

# RateLimitMiddleware settings (applies to non-throttled API writes as a safety net)
RATELIMIT_API_WINDOW = 60        # seconds
RATELIMIT_API_MAX_WRITES = 120   # max write requests per IP per window

# IBM watsonx / Granite configuration (read-only from environment)
WATSONX_API_KEY = os.environ.get('WATSONX_API_KEY', '')
WATSONX_PROJECT_ID = os.environ.get('WATSONX_PROJECT_ID', '')
WATSONX_URL = os.environ.get('WATSONX_URL', 'https://us-south.ml.cloud.ibm.com')
WATSONX_MODEL_ID = os.environ.get('WATSONX_MODEL_ID', 'ibm/granite-13b-instruct-v2')

# ML model storage directory
ML_MODELS_DIR = BASE_DIR.parent / 'models'

# Logging — console output, one handler per level bucket
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} [{name}] {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'error_console': {
            'class': 'logging.StreamHandler',
            'level': 'ERROR',
            'formatter': 'verbose',
        },
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.server': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['error_console'],
            'filters': ['require_debug_false'],
            'level': 'ERROR',
            'propagate': False,
        },
        # App loggers (missions, ai.pipeline, alerts, telemetry use these)
        'missions': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'ai': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'alerts': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'telemetry': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'assistant': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

