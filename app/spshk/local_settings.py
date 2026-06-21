from .settings import *  # noqa
from pathlib import Path as _Path
from dotenv import load_dotenv as _load_dotenv

_load_dotenv(_Path(__file__).resolve().parent.parent.parent / 'secrets.env')

DEBUG = True
SECRET_KEY = 'local-dev-only-not-for-production'
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Use local filesystem for media in dev — no S3 needed
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Run Celery tasks synchronously in-process — no Redis/broker needed for local dev
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = False  # task errors don't crash the request

# Print emails to console instead of sending them
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

LOGIN_URL = '/members/login/'

# SQLite fallback if no PG env vars set
import os
if not os.environ.get('DB_HOST'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
