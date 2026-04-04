"""
Base settings for djafatt project.
Shared across all environments (dev, prod, test).
"""
import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get("SECRET_KEY", "insecure-dev-key-change-me")

DEBUG = False

ALLOWED_HOSTS = [
    h.strip() for h in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()
]

CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()
]

# --- Apps ---
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "django_htmx",
    "django_vite",
    "constance",
    "constance.backends.database",
    "django_celery_results",
    "django_celery_beat",
    # Project apps
    "apps.common",
    "apps.core",
    "apps.contacts",
    "apps.invoices",
    "apps.products",
    "apps.notifications",
    "apps.sdi",
]

# --- Middleware ---
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "apps.core.middleware.request_id.RequestIdMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "djafatt.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.fiscal_year_context",
            ],
        },
    },
]

WSGI_APPLICATION = "djafatt.wsgi.application"
ASGI_APPLICATION = "djafatt.asgi.application"

# --- Database ---
DATABASES = {
    "default": dj_database_url.config(
        default="postgres://djafatt:djafatt@db:5432/djafatt",
        conn_max_age=600,
    )
}

# --- Auth ---
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"

# --- I18N ---
LANGUAGE_CODE = os.environ.get("LANGUAGE_CODE", "it")
LANGUAGES = [("it", "Italiano"), ("en", "English")]
USE_I18N = True
USE_L10N = True
TIME_ZONE = "Europe/Rome"
USE_TZ = True
LOCALE_PATHS = [BASE_DIR / "locale"]

# --- Static / Media ---
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [
    BASE_DIR / "static",
    BASE_DIR / "static" / "dist",
]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Django 6.0: use STORAGES, not STATICFILES_STORAGE
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Django Vite ---
DJANGO_VITE = {
    "default": {
        "dev_mode": os.environ.get("VITE_DEV_MODE", "true").lower() == "true",
        "dev_server_host": "localhost",
        "dev_server_port": 5173,
        "manifest_path": BASE_DIR / "static" / "dist" / ".vite" / "manifest.json",
    }
}

# --- Constance (dynamic settings) ---
CONSTANCE_BACKEND = "constance.backends.database.DatabaseBackend"
CONSTANCE_CONFIG = {
    "COMPANY_NAME": ("", "Company legal name"),
    "COMPANY_VAT_NUMBER": ("", "VAT number (P.IVA)"),
    "COMPANY_TAX_CODE": ("", "Tax code (Codice Fiscale)"),
    "COMPANY_ADDRESS": ("", "Street address"),
    "COMPANY_CITY": ("", "City"),
    "COMPANY_POSTAL_CODE": ("", "Postal code (CAP)"),
    "COMPANY_PROVINCE": ("", "Province code (2 letters)"),
    "COMPANY_COUNTRY_CODE": ("IT", "Country code ISO 3166-1 alpha-2"),
    "COMPANY_FISCAL_REGIME": ("RF01", "Regime fiscale SDI"),
    "COMPANY_ATECO_CODE": ("", "Codice ATECO prevalente"),
    "COMPANY_ATECO_CODE_2": ("", "Codice ATECO secondario"),
    "COMPANY_PEC": ("", "PEC email"),
    "COMPANY_SDI_CODE": ("", "SDI code (Codice Destinatario)"),
    "COMPANY_PHONE": ("", "Phone"),
    "COMPANY_EMAIL": ("", "Email"),
    "COMPANY_LOGO_URL": ("", "Company logo URL"),
    "SETUP_COMPLETED": (False, "Initial setup wizard completed"),
    "DEFAULT_WITHHOLDING_TAX_PERCENT": (20.0, "Default withholding tax %"),
    "DEFAULT_PAYMENT_METHOD": ("MP05", "Default payment method code"),
    "DEFAULT_PAYMENT_TERMS": ("TP02", "Default payment terms code"),
    "COMPANY_BANK_NAME": ("", "Bank name"),
    "COMPANY_BANK_IBAN": ("", "IBAN"),
}

# --- Celery ---
CELERY_BROKER_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = "django-db"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "Europe/Rome"
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# --- SDI ---
OPENAPI_SDI_TOKEN = os.environ.get("OPENAPI_SDI_TOKEN", "")
OPENAPI_SDI_SANDBOX = os.environ.get("OPENAPI_SDI_SANDBOX", "true").lower() == "true"
OPENAPI_SDI_WEBHOOK_SECRET = os.environ.get("OPENAPI_SDI_WEBHOOK_SECRET", "")

# --- Logging ---
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} {message}",
            "style": "{",
        },
    },
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "apps": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "apps.sdi": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}
