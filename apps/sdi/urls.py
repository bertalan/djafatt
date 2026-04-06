from django.urls import path

from .views_send import (
    batch_send_view,
    mark_sent_view,
    outbox_view,
    queue_invoice_view,
    seal_invoice_view,
    unseal_invoice_view,
    unqueue_invoice_view,
    upload_signed_view,
)

urlpatterns = [
    path("invoices/<int:pk>/seal/", seal_invoice_view, name="sdi-seal"),
    path("invoices/<int:pk>/unseal/", unseal_invoice_view, name="sdi-unseal"),
    path("invoices/<int:pk>/queue/", queue_invoice_view, name="sdi-queue"),
    path("invoices/<int:pk>/unqueue/", unqueue_invoice_view, name="sdi-unqueue"),
    path("invoices/<int:pk>/upload-signed/", upload_signed_view, name="sdi-upload-signed"),
    path("invoices/<int:pk>/mark-sent/", mark_sent_view, name="sdi-mark-sent"),
    path("outbox/", outbox_view, name="sdi-outbox"),
    path("batch-send/", batch_send_view, name="sdi-batch-send"),
]
