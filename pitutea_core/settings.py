import os
import environ
from pathlib import Path

env = environ.Env(
    DEBUG=(bool, False)
)

BASE_DIR = Path(__file__).resolve().parent.parent

# Leer .env file si existe (para desarrollo local)
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = env('SECRET_KEY', default='django-insecure-*zvh9@n%#=en^sv18b@zv6tw2-e0e7)4b60p$y%rsa4$b1p*r#')

#Debe queda en Defautl True para cPanel
DEBUG = env('DEBUG', default=True)

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['*'])

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'app_pitutea',
]

SITE_ID = 1

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'app_pitutea.middleware.BlockUserMiddleware',
]

ROOT_URLCONF = 'pitutea_core.urls'

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

WSGI_APPLICATION = 'pitutea_core.wsgi.application'

DATABASES = {
    'default': env.db('DATABASE_URL', default=f'sqlite:///{BASE_DIR / "db.sqlite3"}')
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = True

# ─────────────────────────────────────────────────────────────
# Sub-ruta de la aplicación (ej: /app cuando se despliega en
# pitutea.cl/app/). En producción, configurar en .env:
#   SCRIPT_NAME=/app
# En desarrollo local dejar vacío o no configurar.
# ─────────────────────────────────────────────────────────────
SCRIPT_NAME = env('SCRIPT_NAME', default='')

if SCRIPT_NAME:
    FORCE_SCRIPT_NAME = SCRIPT_NAME
    STATIC_URL = f'{SCRIPT_NAME}/static/'
    MEDIA_URL  = f'{SCRIPT_NAME}/media/'
else:
    STATIC_URL = 'static/'
    MEDIA_URL  = '/media/'

STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_ROOT  = BASE_DIR / 'media'

# Redirige al panel del oferente tras login
LOGIN_REDIRECT_URL = 'panel_oferente'

# Email (modo consola para desarrollo local)
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Email SMTP para producción (reemplaza tu_contraseña_de_correo con la real)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
DEFAULT_FROM_EMAIL = 'no-reply@pitutea.cl'
EMAIL_HOST = 'mail.pitutea.cl'
EMAIL_PORT = 587
EMAIL_HOST_USER = 'no-reply@pitutea.cl'
EMAIL_HOST_PASSWORD = 'Pitutea2026NoReply'
EMAIL_USE_TLS = True