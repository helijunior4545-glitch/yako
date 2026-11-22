"""Standalone Django host for AI YAKO. PostgreSQL only."""
import os
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlsplit
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

def required(name):
    value = os.getenv(name, '').strip()
    if not value:
        raise ImproperlyConfigured(f'Missing environment variable: {name}')
    return value

def csv_env(name, default=''):
    return [x.strip() for x in os.getenv(name, default).split(',') if x.strip()]

SECRET_KEY = os.getenv('SECRET_KEY') or required('DJANGO_SECRET_KEY')
DEBUG = os.getenv('DJANGO_DEBUG', 'false').lower() == 'true'
ALLOWED_HOSTS = csv_env('ALLOWED_HOSTS') or csv_env('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost')
CSRF_TRUSTED_ORIGINS = csv_env('CSRF_TRUSTED_ORIGINS') or csv_env('DJANGO_CSRF_TRUSTED_ORIGINS')
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'app_qvac_financial.apps.AIYakoConfig',
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
ROOT_URLCONF = 'yako_project.urls'
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [],
    'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.debug',
        'django.template.context_processors.request',
        'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
    ]},
}]
WSGI_APPLICATION = 'yako_project.wsgi.application'
ASGI_APPLICATION = 'yako_project.asgi.application'
def postgres_settings():
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        return {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': required('POSTGRES_DB'),
            'USER': required('POSTGRES_USER'),
            'PASSWORD': required('POSTGRES_PASSWORD'),
            'HOST': os.getenv('POSTGRES_HOST', '127.0.0.1'),
            'PORT': os.getenv('POSTGRES_PORT', '5432'),
            'CONN_MAX_AGE': 60,
        }

    try:
        url = urlsplit(database_url)
        port = url.port
        if url.scheme not in {'postgresql', 'postgres'} or not url.hostname or not url.path.strip('/') or url.fragment:
            raise ValueError()
        options = dict(parse_qsl(url.query, strict_parsing=True))
        supported_options = {'sslmode', 'sslrootcert', 'connect_timeout'}
        if options.keys() - supported_options:
            raise ValueError()
    except ValueError:
        raise ImproperlyConfigured('DATABASE_URL must be a supported PostgreSQL URL.') from None
    return {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': unquote(url.path[1:]),
        'USER': unquote(url.username or ''),
        'PASSWORD': unquote(url.password or ''),
        'HOST': url.hostname,
        'PORT': port or 5432,
        'CONN_MAX_AGE': 60,
        'OPTIONS': options,
    }


DATABASES = {'default': postgres_settings()}
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = os.getenv('DJANGO_SECURE_SSL_REDIRECT', 'false').lower() == 'true'
