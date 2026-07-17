"""
Django settings for Flora e-commerce project.
"""

import os
from pathlib import Path
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import dj_database_url

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-flora-2024-change-in-production',
)

# SECURITY WARNING: don't run with debug turned on in production!
# On Render, the RENDER env var is always set.
DEBUG = os.environ.get('DEBUG', 'False').lower() in ('1', 'true', 'yes')
if 'RENDER' not in os.environ and 'DEBUG' not in os.environ:
    # Local default: easier development
    DEBUG = True

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get('ALLOWED_HOSTS', '*').split(',')
    if host.strip()
]

RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# CSRF trusted origins for HTTPS (Render)
CSRF_TRUSTED_ORIGINS = []
if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS.append(f'https://{RENDER_EXTERNAL_HOSTNAME}')
# Allow explicit extra origins via env (comma-separated full origins)
for origin in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(','):
    origin = origin.strip()
    if origin and origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(origin)
# Common Render service URL for this project
CSRF_TRUSTED_ORIGINS.append('https://floraecommerce.onrender.com')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'shop',
    'cart',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'flora_project.urls'

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
                'cart.context_processors.cart',
                'cart.context_processors.categories',
            ],
        },
    },
]

WSGI_APPLICATION = 'flora_project.wsgi.application'

# Database
# Prefer DATABASE_URL (Render Postgres). Fall back to discrete env vars / local defaults.
if os.environ.get('DATABASE_URL'):
    DATABASES = {
        'default': dj_database_url.config(
            default=os.environ['DATABASE_URL'],
            conn_max_age=600,
            ssl_require=os.environ.get('DB_SSL_REQUIRE', 'true').lower()
            in ('1', 'true', 'yes'),
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('POSTGRES_DB', 'flora_shop_db'),
            'USER': os.environ.get('POSTGRES_USER', 'flora_user'),
            'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'flora_pass'),
            'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
            'PORT': os.environ.get('POSTGRES_PORT', '5432'),
        }
    }

# Image upload compression
DEFAULT_IMAGE_QUALITY = 85
MAX_IMAGE_WIDTH = 1600
MAX_IMAGE_HEIGHT = 1600


def compress_image(
    uploaded_file,
    max_width=MAX_IMAGE_WIDTH,
    max_height=MAX_IMAGE_HEIGHT,
    quality=DEFAULT_IMAGE_QUALITY,
):
    if not uploaded_file:
        return uploaded_file

    image = Image.open(uploaded_file)
    image = image.convert('RGB')
    image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

    output = BytesIO()
    image.save(output, format='JPEG', quality=quality, optimize=True)
    output.seek(0)

    return InMemoryUploadedFile(
        output,
        'ImageField',
        f"{uploaded_file.name.rsplit('.', 1)[0]}.jpg",
        'image/jpeg',
        output.getbuffer().nbytes,
        None,
    )


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise for production static serving
if not DEBUG:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

# Media files (uploads). On free Render, these do not persist without a disk.
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Session settings
CART_SESSION_ID = 'cart'

# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'noreply@florafashion.com'
GOOGLE_PLACES_API_KEY = os.environ.get('GOOGLE_PLACES_API_KEY', '')
GOOGLE_PLACE_ID = os.environ.get('GOOGLE_PLACE_ID', '')
GOOGLE_PLACE_QUERY = os.environ.get('GOOGLE_PLACE_QUERY', 'Flora Thrissur, Kerala')

# Optional: Set max upload size for videos
DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800  # 50MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 52428800  # 50MB

# Behind Render's proxy
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Payments / order notifications
UPI_ID = os.environ.get('UPI_ID', '7591927789@fam')
# Keep merchant name short — some UPI apps fail on long names
UPI_MERCHANT_NAME = os.environ.get('UPI_MERCHANT_NAME', 'Flora')
WHATSAPP_ORDER_NUMBER = os.environ.get('WHATSAPP_ORDER_NUMBER', '919074860867')
