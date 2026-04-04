"""Shared view helpers."""
from django.urls import reverse

from apps.invoices.models import InvoiceType

_INVOICE_URL_MAP = {
    InvoiceType.SALES: ("invoices-edit", "invoices-delete"),
    InvoiceType.PURCHASE: ("purchase-invoices-edit", "purchase-invoices-delete"),
    InvoiceType.SELF_INVOICE: ("self-invoices-edit", "self-invoices-delete"),
}


def annotate_invoice_urls(invoices):
    """Add edit_url and delete_url attributes to each invoice."""
    result = []
    for inv in invoices:
        edit_name, delete_name = _INVOICE_URL_MAP.get(
            inv.type, ("invoices-edit", "invoices-delete")
        )
        inv.edit_url = reverse(edit_name, args=[inv.pk])
        inv.delete_url = reverse(delete_name, args=[inv.pk])
        result.append(inv)
    return result
