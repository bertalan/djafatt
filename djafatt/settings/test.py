"""Test settings — fast and isolated."""
from .base import *  # noqa: F401, F403

DEBUG = False

# Faster password hasher for tests
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# In-memory email
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# SQLite for faster tests if needed (but PostgreSQL is default via DATABASE_URL)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "djafatt_test",
        "USER": "djafatt",
        "PASSWORD": "djafatt",
        "HOST": "db",
        "PORT": "5432",
    }
}

# Vite in production mode (no dev server needed)
DJANGO_VITE = {
    "default": {
        "dev_mode": False,
        "manifest_path": BASE_DIR / "static" / "dist" / ".vite" / "manifest.json",  # noqa: F405
    }
}

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# Celery eager mode for tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
