"""Production settings — hardened."""
from .base import *  # noqa: F401, F403

DEBUG = False

# Security headers — SSL redirect handled by nginx, not Django
SECURE_SSL_REDIRECT = False  # nginx does HTTPS redirect
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True

# Cookies
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Strict"
SESSION_COOKIE_AGE = 3600  # 1 hour
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True

# X-Frame-Options
X_FRAME_OPTIONS = "DENY"

# Static files via WhiteNoise
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Vite production mode
DJANGO_VITE = {
    "default": {
        "dev_mode": False,
        "manifest_path": BASE_DIR / "static" / "dist" / ".vite" / "manifest.json",  # noqa: F405
    }
}

# Structured logging for production
LOGGING["formatters"]["json"] = {  # noqa: F405
    "()": "django.utils.log.ServerFormatter",
    "format": "[{server_time}] {message}",
    "style": "{",
}
