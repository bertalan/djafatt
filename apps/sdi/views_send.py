"""Views for sending invoices to SDI."""
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect

from apps.invoices.models import Invoice

from .tasks import send_invoice_to_sdi

logger = logging.getLogger("apps.sdi")


@login_required
@permission_required("invoices.change_invoice", raise_exception=True)
def send_to_sdi_view(request, pk):
    """Queue an invoice for SDI submission via Celery."""
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    invoice = get_object_or_404(Invoice.all_types, pk=pk)

    if not invoice.is_sdi_editable():
        messages.error(request, f"Fattura {invoice.number} già inviata allo SDI.")
        return redirect("invoices-edit", pk=pk)

    if not invoice.lines.exists():
        messages.error(request, "La fattura non ha righe — impossibile inviare.")
        return redirect("invoices-edit", pk=pk)

    send_invoice_to_sdi.delay(invoice.pk)
    messages.success(request, f"Fattura {invoice.number} in coda per invio SDI.")

    # Redirect back to the appropriate list based on invoice type
    return redirect("invoices-index")
