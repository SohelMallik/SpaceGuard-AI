"""
SpaceGuard AI — Django Settings

This is the central configuration file for the whole Django project.
Everything the project needs to run is configured here: security keys,
installed apps, middleware, the database, the REST API behaviour
(throttling, pagination, authentication), IBM watsonx credentials,
and logging.

Most sensitive values (secret key, API keys, debug flag) are read from
environment variables so they are never hard-coded into the source code.
The environment variables usually live in a `.env` file in the project root.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

# Load environment variables from .env file
# `load_dotenv` reads a `.env` file (key=value lines) and puts the values
# into process environment variables, so `os.environ.get(...)` below can
# find them. The path walks up three levels from this file:
#   backend/spaceguard/settings.py -> backend/spaceguard -> backend -> project root
load_dotenv(Path(__file__).resolve().parent.parent.parent / '.env')

# BASE_DIR points at the `backend/` folder. Every other path in this file
# (database, static files, models directory) is built relative to it, so the
# project works no matter where it is checked out on disk.
BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
# SECRET_KEY: Django uses this to sign sessions, password reset tokens, CSRF
# tokens, etc. It MUST be secret in production, so we read it from the
# environment. The hard-coded fallback below is only safe for local development.
INSECURE_DEV_SECRET = 'django-insecure-dev-key-change-in-production'
SECRET_KEY = os.environ.get('SECRET_KEY', INSECURE_DEV_SECRET)

# DEBUG: when True, Django shows detailed error pages and serves static files
# for us. Debug mode must NEVER be enabled in production (it leaks secrets).
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

# ALLOWED_HOSTS: the hostnames Django is allowed to serve. This protects
# against "Host header" attacks. Comma-separated in the environment, e.g.
#   ALLOWED_HOSTS=spaceguard.example.com,api.spaceguard.example.com
ALLOWED_HOSTS = [h.strip() for h in os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if h.strip()]

# Production safety check: refuse to start without a real SECRET_KEY when DEBUG is off
# This is a "fail fast" guard: if someone deploys with DEBUG=False but forgot
# to set a strong SECRET_KEY, Django refuses to boot instead of running with
# a key the whole internet knows (it was published in this file).
if not DEBUG and SECRET_KEY == INSECURE_DEV_SECRET:
    raise ImproperlyConfigured(
        'SECRET_KEY is missing or set to the insecure development default. '
        'Set a strong SECRET_KEY environment variable in production.'
    )

# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------
# INSTALLED_APPS is the list of Django "apps" (reusable feature modules) that
# this project loads. Each entry contributes models, views, templates, or
# management commands:
INSTALLED_APPS = [
    # --- Django built-in apps (the framework's core features) ---
    'django.contrib.admin',        # The /admin/ back-office UI
    'django.contrib.auth',         # User accounts, login, permissions (User model)
    'django.contrib.contenttypes', # Tracks which models exist (used by auth/admin)
    'django.contrib.sessions',     # Server-side sessions (remember logged-in users)
    'django.contrib.messages',     # One-time flash messages shown after redirects
    'django.contrib.staticfiles',  # Serves CSS/JS/image static files in development
    # Third-party
    'rest_framework',              # Django REST Framework: the JSON API toolkit
    # SpaceGuard apps — the project's own feature modules
    'missions',     # Spacecraft/mission records and the dashboard UI
    'telemetry',    # Ingests and stores spacecraft telemetry readings
    'anomaly',      # AI anomaly detection on telemetry + stored analyses
    'alerts',       # Alert records generated when anomalies are found
    'assistant',    # AI assistant endpoint backed by IBM watsonx
]

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
# MIDDLEWARE is a stack of hooks every request passes through (top to bottom)
# and every response passes through (bottom to top). ORDER MATTERS:
# e.g. sessions must run before authentication, because auth needs the session.
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',            # Security headers, redirects, SSL helpers
    'django.contrib.sessions.middleware.SessionMiddleware',     # Attaches request.session to each request
    'django.middleware.common.CommonMiddleware',                # URL normalisation, ETags, etc.
    'django.middleware.csrf.CsrfViewMiddleware',                # Blocks cross-site request forgery on POSTs
    'django.contrib.auth.middleware.AuthenticationMiddleware',  # Attaches request.user using the session
    'django.contrib.messages.middleware.MessageMiddleware',     # Flash-message support
    'django.middleware.clickjacking.XFrameOptionsMiddleware',   # Stops pages being framed by other sites
    # Rate limiting for API endpoints (our own middleware, see spaceguard/middleware.py)
    'spaceguard.middleware.RateLimitMiddleware',
]

# ROOT_URLCONF tells Django which module holds the master URL routing table.
ROOT_URLCONF = 'spaceguard.urls'

# ---------------------------------------------------------------------------
# Templates (HTML rendering)
# ---------------------------------------------------------------------------
# TEMPLATES configures how Django renders HTML pages.
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # DIRS: extra folders to search for templates. Here we point at a
        # project-wide `templates/` folder that sits next to `backend/`.
        'DIRS': [BASE_DIR.parent / 'templates'],
        # APP_DIRS: also look inside each installed app's own
        # `templates/` subfolder (e.g. missions/templates/missions/...).
        'APP_DIRS': True,
        'OPTIONS': {
            # Context processors: helper objects injected into every template.
            'context_processors': [
                'django.template.context_processors.request',   # `request` variable
                'django.contrib.auth.context_processors.auth',  # `user`, `perms`
                'django.contrib.messages.context_processors.messages',  # flash messages
            ],
        },
    },
]

# Where the WSGI application callable lives (used by classic sync servers
# such as gunicorn; see spaceguard/wsgi.py).
WSGI_APPLICATION = 'spaceguard.wsgi.application'

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
# Database — SQLite for prototype; swap ENGINE for PostgreSQL in production
# SQLite stores the whole database in a single file (db.sqlite3) with zero
# setup, which is perfect for a prototype. For production you would change
# ENGINE to 'django.db.backends.postgresql' and add HOST/USER/PASSWORD keys.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
# Rules enforced when a user registers or changes their password, to stop
# trivially weak passwords (too short, all numbers, same as the username...).
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalisation: language and timezone defaults.
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'          # All datetimes stored/stamped in UTC
USE_I18N = True            # Enable Django's translation system
USE_TZ = True              # Make datetimes timezone-aware (recommended)

# ---------------------------------------------------------------------------
# Static and media files
# ---------------------------------------------------------------------------
# STATIC_* covers developer-authored assets (CSS, JS, images shipped with the code).
# MEDIA_* covers files uploaded by users at runtime (e.g. datasets).
STATIC_URL = '/static/'                          # URL prefix for static files
STATICFILES_DIRS = [BASE_DIR.parent / 'static']  # Source folders to collect files from
STATIC_ROOT = BASE_DIR / 'staticfiles'           # Where `collectstatic` copies them for production

MEDIA_URL = '/media/'          # URL prefix for uploaded files
MEDIA_ROOT = BASE_DIR / 'media'  # Folder where uploads are stored

# Default primary key type for new models (64-bit integer instead of the
# old 32-bit int — avoids running out of IDs on busy tables).
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# Django REST Framework (the JSON API)
# ---------------------------------------------------------------------------
# Two feature switches read from the environment:
#   API_RATE_LIMIT_ENABLED — turn API throttling (rate limiting) on/off.
#   API_AUTH_REQUIRED      — force login on every API endpoint (production mode).
API_RATE_LIMIT_ENABLED = os.environ.get('API_RATE_LIMIT_ENABLED', 'True') == 'True'
API_AUTH_REQUIRED = os.environ.get('API_AUTH_REQUIRED', 'False') == 'True'

REST_FRAMEWORK = {
    # Pagination: list endpoints are split into pages instead of returning
    # every row at once. ?page=2 selects the page; PAGE_SIZE limits each
    # page to 50 items.
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    # Renderers: how responses are formatted. JSON is the default; the
    # BrowsableAPIRenderer also gives human visitors an HTML view of the API.
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    # Parsers: request body formats the API can accept (JSON, file uploads
    # via multipart, and classic HTML form data).
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.FormParser',
    ],
    # Custom error handler: every API error is returned as structured JSON
    # like {"error": true, "status_code": ..., "detail": ...} — see
    # spaceguard/exceptions.py.
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
    # The custom throttle class allows per-action scopes: each ViewSet action
    # can declare which throttle bucket it belongs to (see spaceguard/throttling.py).
    # When API_RATE_LIMIT_ENABLED is False the throttle list is emptied, which
    # switches rate limiting off completely.
    'DEFAULT_THROTTLE_CLASSES': [
        'spaceguard.throttling.ActionScopedRateThrottle',
    ] if API_RATE_LIMIT_ENABLED else [],
    # Named throttle buckets and their rates. The 'ai' scope allows at most
    # 10 requests per minute (per user if logged in, per IP if anonymous).
    'DEFAULT_THROTTLE_RATES': {
        'ai': '10/min',
    },
}

# RateLimitMiddleware settings (applies to non-throttled API writes as a safety net)
RATELIMIT_API_WINDOW = 60        # seconds
RATELIMIT_API_MAX_WRITES = 120   # max write requests per IP per window

# ---------------------------------------------------------------------------
# IBM watsonx / Granite configuration (read-only from environment)
# ---------------------------------------------------------------------------
# Credentials used by the `assistant` app to call IBM's Granite LLM and
# generate natural-language explanations of anomalies. All values come from
# environment variables (the .env file), so real keys are never in git.
#   WATSONX_API_KEY    — IBM Cloud API key (required for real calls)
#   WATSONX_PROJECT_ID — the watsonx.ai project the model runs in
#   WATSONX_URL        — regional endpoint of the watsonx service
#   WATSONX_MODEL_ID   — which foundation model to use (Granite 13B here)
WATSONX_API_KEY = os.environ.get('WATSONX_API_KEY', '')
WATSONX_PROJECT_ID = os.environ.get('WATSONX_PROJECT_ID', '')
WATSONX_URL = os.environ.get('WATSONX_URL', 'https://us-south.ml.cloud.ibm.com')
WATSONX_MODEL_ID = os.environ.get('WATSONX_MODEL_ID', 'ibm/granite-13b-instruct-v2')

# ML model storage directory
# Trained/serialised machine-learning models (e.g. the anomaly detector) are
# saved here and loaded at runtime. Lives outside `backend/`, next to the
# templates and static folders.
ML_MODELS_DIR = BASE_DIR.parent / 'models'

# ---------------------------------------------------------------------------
# Logging — console output, one handler per level bucket
# ---------------------------------------------------------------------------
# LOGGING configures Python's logging system as Django uses it.
# Concept map:
#   loggers   = named sources of log messages (one per app, e.g. 'missions')
#   handlers  = where messages go (console, file, ...)
#   formatters= how a message is rendered (timestamp, level, ...)
#   filters   = extra conditions a message must pass (e.g. only in production)
LOGGING = {
    'version': 1,                       # Logging config schema version (always 1)
    'disable_existing_loggers': False,  # Keep loggers defined elsewhere
    'formatters': {
        # Verbose format includes level, time, logger name, and the message.
        'verbose': {
            'format': '{levelname} {asctime} [{name}] {message}',
            'style': '{',
        },
        # Simple format is just level + message.
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'filters': {
        # Only lets messages through when DEBUG is False (i.e. in production),
        # so error emails/console spam don't duplicate during development.
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        # General-purpose console output for INFO and above.
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        # Separate stream for errors so they stand out in the logs.
        'error_console': {
            'class': 'logging.StreamHandler',
            'level': 'ERROR',
            'formatter': 'verbose',
        },
        # Discards messages (used as a safe default for noisy libraries).
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    # Root logger: the catch-all for any logger without its own config.
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
        # Each SpaceGuard app logs to its own named logger so its output can
        # be traced and tuned independently.
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

