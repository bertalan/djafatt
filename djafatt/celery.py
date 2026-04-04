"""Celery app configuration for djafatt."""
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "djafatt.settings.dev")

app = Celery("djafatt")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
