from django.urls import path

from .views_pdf import invoice_preview_pdf
from .views_purchase import (
    PurchaseInvoiceCreateView,
    PurchaseInvoiceDeleteView,
    PurchaseInvoiceDuplicateView,
    PurchaseInvoiceEditView,
    PurchaseInvoiceListView,
)

urlpatterns = [
    path("", PurchaseInvoiceListView.as_view(), name="purchase-invoices-index"),
    path("create/", PurchaseInvoiceCreateView.as_view(), name="purchase-invoices-create"),
    path("<int:pk>/edit/", PurchaseInvoiceEditView.as_view(), name="purchase-invoices-edit"),
    path("<int:pk>/delete/", PurchaseInvoiceDeleteView.as_view(), name="purchase-invoices-delete"),
    path("<int:pk>/duplicate/", PurchaseInvoiceDuplicateView.as_view(), name="purchase-invoices-duplicate"),
    path("<int:pk>/preview/", invoice_preview_pdf, name="purchase-invoices-preview"),
]
