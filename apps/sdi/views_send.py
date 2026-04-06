"""Views for SDI invoice workflow: seal → outbox → batch send."""
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.common.exceptions import SdiClientError
from apps.invoices.models import Invoice, InvoiceStatus, SdiStatus

from .models import SdiLog, SdiLogEvent
from .tasks import batch_send_and_sync, run_batch_send_and_sync

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

    # Try async (Celery) first; fall back to synchronous execution.
    try:
        batch_send_and_sync.delay(user_id=request.user.pk)
        logger.info("Batch send queued via Celery (%d invoices)", outbox_count)
        messages.success(
            request,
            f"Invio batch avviato: {outbox_count} fattur{'a' if outbox_count == 1 else 'e'} + sincronizzazione arrivi.",
        )
    except Exception:
        logger.warning("Celery broker unreachable — running batch send synchronously")
        results = run_batch_send_and_sync()
        sent, failed = results["sent"], results["failed"]
        synced = results["synced"]
        parts = []
        if sent:
            parts.append(f"{sent} inviat{'a' if sent == 1 else 'e'}")
        if failed:
            parts.append(f"{failed} fallite")
        if synced:
            parts.append(f"{synced} ricevute sincronizzate")
        summary = ", ".join(parts) if parts else "nessuna azione"
        if failed:
            messages.warning(request, f"Invio completato (sincrono): {summary}.")
        else:
            messages.success(request, f"Invio completato (sincrono): {summary}.")

    return redirect("sdi-outbox")


SIGNED_EXTENSIONS = (".xml", ".xml.p7m")
MAX_SIGNED_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


@login_required
@permission_required("invoices.change_invoice", raise_exception=True)
def upload_signed_view(request, pk):
    """Upload a digitally signed XML and send it via PEC to SDI."""
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    invoice = get_object_or_404(
        Invoice.all_types.select_related("contact"),
        pk=pk,
        status__in=(InvoiceStatus.SEALED, InvoiceStatus.OUTBOX),
    )

    uploaded = request.FILES.get("signed_file")
    if not uploaded:
        messages.error(request, "Nessun file selezionato.")
        return redirect("sdi-outbox")

    filename = uploaded.name.lower()
    if not any(filename.endswith(ext) for ext in SIGNED_EXTENSIONS):
        messages.error(
            request,
            "Formato non valido. Caricare un file .xml (XAdES) o .xml.p7m (CAdES).",
        )
        return redirect("sdi-outbox")

    if uploaded.size > MAX_SIGNED_FILE_SIZE:
        messages.error(request, "File troppo grande (max 5 MB).")
        return redirect("sdi-outbox")

    file_bytes = uploaded.read()

    from .services.pec_sender import PecSdiSender

    try:
        sender = PecSdiSender()
        result = sender.send_signed_file(file_bytes, uploaded.name)
    except SdiClientError as exc:
        logger.error("Signed upload PEC send failed for invoice %s: %s", invoice.number, exc)
        messages.error(request, f"Invio PEC fallito: {exc}")
        return redirect("sdi-outbox")

    with transaction.atomic():
        invoice = Invoice.all_types.select_for_update().get(pk=pk)
        invoice.sdi_uuid = result.get("message_id", "")
        invoice.sdi_status = SdiStatus.SENT
        invoice.status = InvoiceStatus.SENT
        invoice.sdi_sent_at = timezone.now()
        invoice.save(update_fields=[
            "sdi_uuid", "sdi_status", "status", "sdi_sent_at", "updated_at",
        ])

        SdiLog.objects.create(
            invoice=invoice,
            event=SdiLogEvent.SEND_SUCCESS,
            sdi_uuid=invoice.sdi_uuid,
            new_status=SdiStatus.SENT,
            user=request.user,
            ip_address=_get_client_ip(request),
        )

    messages.success(
        request,
        f"Fattura {invoice.number} firmata inviata via PEC ({uploaded.name}).",
    )
    return redirect("sdi-outbox")
