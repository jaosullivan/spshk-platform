from .settings import *  # noqa

DEBUG = True
SECRET_KEY = 'local-dev-only-not-for-production'
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Use local filesystem for media in dev — no S3 needed
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# SQLite fallback if no PG env vars set
import os
if not os.environ.get('DB_HOST'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
