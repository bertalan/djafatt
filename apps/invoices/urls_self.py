from django.urls import path

from .views_pdf import invoice_preview_pdf
from .views_self_invoice import (
    SelfInvoiceCreateView,
    SelfInvoiceDeleteView,
    SelfInvoiceDuplicateView,
    SelfInvoiceEditView,
    SelfInvoiceListView,
)

urlpatterns = [
    path("", SelfInvoiceListView.as_view(), name="self-invoices-index"),
    path("create/", SelfInvoiceCreateView.as_view(), name="self-invoices-create"),
    path("<int:pk>/edit/", SelfInvoiceEditView.as_view(), name="self-invoices-edit"),
    path("<int:pk>/delete/", SelfInvoiceDeleteView.as_view(), name="self-invoices-delete"),
    path("<int:pk>/duplicate/", SelfInvoiceDuplicateView.as_view(), name="self-invoices-duplicate"),
    path("<int:pk>/preview/", invoice_preview_pdf, name="self-invoices-preview"),
]
