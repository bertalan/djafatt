from django.urls import path

from .views_send import send_to_sdi_view

urlpatterns = [
    path("invoices/<int:pk>/send-sdi/", send_to_sdi_view, name="sdi-send"),
]
