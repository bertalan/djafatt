"""Signals for recalculating invoice totals on line changes."""
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Invoice, InvoiceLine


@receiver([post_save, post_delete], sender=InvoiceLine)
def recalculate_invoice_totals(sender, instance, **kwargs):
    """Recalculate parent invoice totals when a line is saved or deleted."""
    try:
        invoice = Invoice.all_types.get(pk=instance.invoice_id)
    except Invoice.DoesNotExist:
        return
    if invoice.is_sdi_editable():
        invoice.calculate_totals()
