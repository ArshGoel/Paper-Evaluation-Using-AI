import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

ENVIRONMENT = os.getenv("ENVIRONMENT")

dotenv_path = BASE_DIR / '.env'
if dotenv_path.exists():
    with dotenv_path.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' not in line:
                continue
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip().strip('"\'')
            os.environ.setdefault(key, value)

SECRET_KEY = 'django-insecure-cfixe)n(_^*d0%q%w!#87xp&dyoa8hm&0f-+l79z3twf_9-v90'

DEBUG = True

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'Accounts',
    'Exams',
    'Dashboards',
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

ROOT_URLCONF = 'Paper_Evaluation_Using_AI.urls'

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

WSGI_APPLICATION = 'Paper_Evaluation_Using_AI.wsgi.application'

import dj_database_url

import dj_database_url

ENVIRONMENT = os.getenv("ENVIRONMENT", "local")

if ENVIRONMENT == "local":
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': dj_database_url.parse(
            os.getenv("DATABASE_URL"),
            conn_max_age=600,
            ssl_require=True
        )
    }

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

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

STATIC_URL = 'static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


#Added Manually

STATICFILES_DIRS = [
    os.path.join(BASE_DIR,"static")
] 
STATIC_ROOT = os.path.join(BASE_DIR,'staticfiles_build',"static")

AUTH_USER_MODEL = 'Accounts.User'

if ENVIRONMENT == "local":

    MEDIA_URL = '/media/'
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
else:
    INSTALLED_APPS += ['cloudinary', 'cloudinary_storage']

    CLOUDINARY_STORAGE = {
        'CLOUD_NAME': os.getenv('CLOUD_NAME'),
        'API_KEY': os.getenv('API_KEY'),
        'API_SECRET': os.getenv('API_SECRET'),
    }

    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

    MEDIA_URL = f"https://res.cloudinary.com/{CLOUDINARY_STORAGE['CLOUD_NAME']}/"
LOGIN_URL = '/auth/slogin/'



GEMINI_API_KEYS = [
    os.getenv("GEMINI_API_KEY1"),
    os.getenv("GEMINI_API_KEY2"),
    os.getenv("GEMINI_API_KEY3"),
    os.getenv("GEMINI_API_KEY4"),
    os.getenv("GEMINI_API_KEY5"),
    os.getenv("GEMINI_API_KEY6"),
    os.getenv("GEMINI_API_KEY7"),
    os.getenv("GEMINI_API_KEY8"),
    os.getenv("GEMINI_API_KEY9"),
]
GEMINI_API_KEYS = [k for k in GEMINI_API_KEYS if k]
GEMINI_MODELS = [
    "gemini-2.5-flash", #Working Text, images, video, audio
    "gemini-3-flash-preview", #Working Text, Image, Video, Audio, and PDF
    "gemini-2.5-flash-lite", #Working Text, image, video, audio, PDF
    "gemini-3.1-flash-lite-preview", #Working Text, Image, Video, Audio, and PDF
]
GEMINI_MODEL_TEXT = os.getenv("GEMINI_MODEL_TEXT", "gemini-2.5-flash")
GEMINI_MODEL_VISION = os.getenv("GEMINI_MODEL_VISION", "gemini-3-flash-preview")