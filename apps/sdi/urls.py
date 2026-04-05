from django.urls import path

from .views_send import (
    batch_send_view,
    outbox_view,
    queue_invoice_view,
    seal_invoice_view,
    unseal_invoice_view,
    unqueue_invoice_view,
)

urlpatterns = [
    path("invoices/<int:pk>/seal/", seal_invoice_view, name="sdi-seal"),
    path("invoices/<int:pk>/unseal/", unseal_invoice_view, name="sdi-unseal"),
    path("invoices/<int:pk>/queue/", queue_invoice_view, name="sdi-queue"),
    path("invoices/<int:pk>/unqueue/", unqueue_invoice_view, name="sdi-unqueue"),
    path("outbox/", outbox_view, name="sdi-outbox"),
    path("batch-send/", batch_send_view, name="sdi-batch-send"),
]
