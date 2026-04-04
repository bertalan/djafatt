from django.urls import path

from .views_webhook import webhook_handler

urlpatterns = [
    path("sdi/", webhook_handler, name="sdi-webhook"),
]
