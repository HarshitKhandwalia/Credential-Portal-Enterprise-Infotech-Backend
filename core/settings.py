"""
Django settings for core project.
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')


def _env(name, default=None):
    value = os.getenv(name, default)
    if value is None:
        return default
    value = value.strip()
    if value == '':
        return default
    return value


def _env_bool(name, default='False'):
    return _env(name, default).lower() in ('true', '1', 'yes')


def _env_list(name, default=''):
    raw = _env(name, default)
    if not raw:
        return []
    return [item.strip() for item in raw.split(',') if item.strip()]


DEBUG = _env_bool('DEBUG', 'True')
SECRET_KEY = _env('SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'django-insecure-dev-only-change-me'
    else:
        raise ImproperlyConfigured('SECRET_KEY is required when DEBUG is False.')

ALLOWED_HOSTS = _env_list('ALLOWED_HOSTS', 'localhost,127.0.0.1')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'credentials',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

CORS_ALLOWED_ORIGINS = _env_list(
    'CORS_ALLOWED_ORIGINS',
    'http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173',
)
CSRF_TRUSTED_ORIGINS = _env_list('CSRF_TRUSTED_ORIGINS', '')

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'core.wsgi.application'

if _env('POSTGRES_HOST'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': _env('POSTGRES_DB', 'credentials'),
            'USER': _env('POSTGRES_USER', 'credentials'),
            'PASSWORD': _env('POSTGRES_PASSWORD', ''),
            'HOST': _env('POSTGRES_HOST'),
            'PORT': _env('POSTGRES_PORT', '5432'),
            'CONN_MAX_AGE': int(_env('DB_CONN_MAX_AGE', '60')),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

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

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

EMAIL_BACKEND = _env(
    'EMAIL_BACKEND',
    'django.core.mail.backends.smtp.EmailBackend',
)
EMAIL_HOST = _env('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(_env('EMAIL_PORT', '587'))
EMAIL_USE_TLS = _env_bool('EMAIL_USE_TLS', 'True')
EMAIL_HOST_USER = _env('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = _env('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = _env('DEFAULT_FROM_EMAIL')

GOOGLE_PASS_SERVICE_URL = _env(
    'GOOGLE_PASS_SERVICE_URL',
    'http://127.0.0.1:8001',
)
APPLE_PASS_SERVICE_URL = _env(
    'APPLE_PASS_SERVICE_URL',
    'http://127.0.0.1:8000',
)
PASS_SERVICE_TIMEOUT_SECONDS = float(_env('PASS_SERVICE_TIMEOUT_SECONDS', '10'))

FRONTEND_BASE_URL = _env('FRONTEND_BASE_URL', 'http://localhost:5173')
WALLET_TOKEN_EXPIRY_DAYS = int(_env('WALLET_TOKEN_EXPIRY_DAYS', '7'))
WALLET_TOKEN_EXPIRY_SECONDS = WALLET_TOKEN_EXPIRY_DAYS * 24 * 60 * 60

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = _env_bool('SECURE_SSL_REDIRECT', 'False')
