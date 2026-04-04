"""WSGI config for djafatt project."""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "djafatt.settings.dev")

application = get_wsgi_application()
