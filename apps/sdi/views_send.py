"""Views for SDI invoice workflow: seal → outbox → batch send."""
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.invoices.models import Invoice, InvoiceStatus, SdiStatus

from .models import SdiLog, SdiLogEvent
from .tasks import batch_send_and_sync

logger = logging.getLogger("apps.sdi")


def _get_client_ip(request):
    """Extract client IP, respecting X-Forwarded-For from nginx."""
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _redirect_to_edit(invoice):
    """Redirect to the appropriate edit view for the invoice type."""
    if invoice.type == "self_invoice":
        return redirect("self-invoices-edit", pk=invoice.pk)
    return redirect("invoices-edit", pk=invoice.pk)


@login_required
@permission_required("invoices.change_invoice", raise_exception=True)
def seal_invoice_view(request, pk):
    """Seal an invoice: lock content, mark as sealed."""
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    with transaction.atomic():
        invoice = Invoice.all_types.select_for_update().get(pk=pk)

        if not invoice.can_seal():
            messages.error(request, f"Fattura {invoice.number} non può essere sigillata.")
            return _redirect_to_edit(invoice)

        invoice.status = InvoiceStatus.SEALED
        invoice.sealed_at = timezone.now()
        invoice.save(update_fields=["status", "sealed_at", "updated_at"])

    messages.success(request, f"Fattura {invoice.number} sigillata.")
    return _redirect_to_edit(invoice)


@login_required
@permission_required("invoices.change_invoice", raise_exception=True)
def unseal_invoice_view(request, pk):
    """Unseal an invoice: revert to draft for editing."""
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    with transaction.atomic():
        invoice = Invoice.all_types.select_for_update().get(pk=pk)

        if not invoice.can_unseal():
            messages.error(request, f"Fattura {invoice.number} non può essere dissigillata.")
            return _redirect_to_edit(invoice)

        invoice.status = InvoiceStatus.DRAFT
        invoice.sealed_at = None
        invoice.save(update_fields=["status", "sealed_at", "updated_at"])

    messages.success(request, f"Fattura {invoice.number} riportata in bozza.")
    return _redirect_to_edit(invoice)


@login_required
@permission_required("invoices.change_invoice", raise_exception=True)
def queue_invoice_view(request, pk):
    """Move a sealed invoice to the outbox."""
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    with transaction.atomic():
        invoice = Invoice.all_types.select_for_update().get(pk=pk)

        if not invoice.can_queue():
            messages.error(request, f"Fattura {invoice.number} non può essere messa in uscita.")
            return _redirect_to_edit(invoice)

        invoice.status = InvoiceStatus.OUTBOX
        invoice.sdi_status = SdiStatus.PENDING
        invoice.save(update_fields=["status", "sdi_status", "updated_at"])

        SdiLog.objects.create(
            invoice=invoice,
            event=SdiLogEvent.SEND_QUEUED,
            user=request.user,
            ip_address=_get_client_ip(request),
        )

    messages.success(request, f"Fattura {invoice.number} in casella di uscita.")
    return _redirect_to_edit(invoice)


@login_required
@permission_required("invoices.change_invoice", raise_exception=True)
def unqueue_invoice_view(request, pk):
    """Remove an invoice from the outbox back to sealed."""
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    with transaction.atomic():
        invoice = Invoice.all_types.select_for_update().get(pk=pk)

        if not invoice.can_unqueue():
            messages.error(request, f"Fattura {invoice.number} non può essere rimossa dalla coda.")
            return _redirect_to_edit(invoice)

        invoice.status = InvoiceStatus.SEALED
        invoice.sdi_status = ""
        invoice.save(update_fields=["status", "sdi_status", "updated_at"])

    messages.success(request, f"Fattura {invoice.number} rimossa dalla casella di uscita.")
    return _redirect_to_edit(invoice)


@login_required
@permission_required("invoices.change_invoice", raise_exception=True)
def outbox_view(request):
    """Show outbox: invoices ready to send + batch send button."""
    outbox_invoices = (
        Invoice.all_types
        .filter(status=InvoiceStatus.OUTBOX)
        .select_related("contact", "sequence")
        .order_by("date", "number")
    )
    sealed_invoices = (
        Invoice.all_types
        .filter(status=InvoiceStatus.SEALED)
        .select_related("contact", "sequence")
        .order_by("date", "number")
    )
    return render(request, "sdi/outbox.html", {
        "outbox_invoices": outbox_invoices,
        "sealed_invoices": sealed_invoices,
    })


@login_required
@permission_required("invoices.change_invoice", raise_exception=True)
def batch_send_view(request):
    """Trigger batch send of all outbox invoices + sync incoming."""
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    outbox_count = Invoice.all_types.filter(status=InvoiceStatus.OUTBOX).count()
    if outbox_count == 0:
        messages.warning(request, "Nessuna fattura in casella di uscita.")
        return redirect("sdi-outbox")

    try:
        batch_send_and_sync.delay(user_id=request.user.pk)
    except Exception:
        logger.exception("Failed to queue batch_send_and_sync task")
        messages.error(request, "Impossibile avviare l'invio: il servizio di coda non è raggiungibile.")
        return redirect("sdi-outbox")

    messages.success(
        request,
        f"Invio batch avviato: {outbox_count} fattur{'a' if outbox_count == 1 else 'e'} + sincronizzazione arrivi.",
    )
    return redirect("sdi-outbox")
