from django.urls import path

from .views_invoice import InvoiceCreateView, InvoiceDeleteView, InvoiceDuplicateView, InvoiceEditView, InvoiceListView
from .views_lines import add_invoice_line, add_payment_due, calculate_totals_partial, contact_payment_defaults, product_autofill, remove_invoice_line, remove_payment_due
from .views_pdf import invoice_download_xml, invoice_preview_pdf

urlpatterns = [
    path("", InvoiceListView.as_view(), name="invoices-index"),
    path("create/", InvoiceCreateView.as_view(), name="invoices-create"),
    path("<int:pk>/edit/", InvoiceEditView.as_view(), name="invoices-edit"),
    path("<int:pk>/delete/", InvoiceDeleteView.as_view(), name="invoices-delete"),
    path("<int:pk>/duplicate/", InvoiceDuplicateView.as_view(), name="invoices-duplicate"),
    path("<int:pk>/preview/", invoice_preview_pdf, name="invoices-preview"),
    path("<int:pk>/xml/", invoice_download_xml, name="invoices-xml"),
    # HTMX line management (T12)
    path("lines/add/", add_invoice_line, name="invoices-add-line"),
    path("lines/<int:index>/remove/", remove_invoice_line, name="invoices-remove-line"),
    path("lines/totals/", calculate_totals_partial, name="invoices-totals"),
    path("lines/product-fill/<int:product_id>/", product_autofill, name="invoices-product-fill"),
    path("contact-defaults/<int:contact_id>/", contact_payment_defaults, name="invoices-contact-defaults"),
    # HTMX payment due management (T33)
    path("dues/add/", add_payment_due, name="invoices-add-due"),
    path("dues/<int:index>/remove/", remove_payment_due, name="invoices-remove-due"),
]
