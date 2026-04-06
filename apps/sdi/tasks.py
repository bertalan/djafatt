"""Celery tasks for SDI operations.

Supports two send methods (configured via SDI_SEND_METHOD env var):
- "pec"     — send XML via PEC email (free, default)
- "openapi" — send XML via OpenAPI REST API

Incoming invoice sync always uses OpenAPI (read-only, free tier).
"""
import logging

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from apps.common.exceptions import SdiClientError
from apps.invoices.models import SdiStatus

logger = logging.getLogger("apps.sdi")


def _send_via_openapi(invoice, xml_content, generator):
    """Send a single invoice via OpenAPI REST API. Returns update dict."""
    from apps.sdi.services.openapi_client import OpenApiSdiClient

    client = OpenApiSdiClient()
    result = client.send_invoice(xml_content)
    return {
        "sdi_uuid": result.get("uuid", ""),
        "log_extra": f"uuid={result.get('uuid', '')}",
    }


def _send_via_pec(invoice, xml_content, generator):
    """Send a single invoice via PEC email. Returns update dict."""
    from constance import config

    from apps.sdi.services.pec_sender import PecSdiSender

    sender = PecSdiSender()
    vat = config.COMPANY_VAT_NUMBER
    filename = PecSdiSender.build_filename(vat, invoice.sequential_number or 0)
    result = sender.send_invoice(xml_content, filename)
    return {
        "sdi_uuid": result.get("message_id", ""),
        "log_extra": f"pec_file={filename}",
    }


def run_batch_send_and_sync() -> dict:
    """Core logic: send all outbox invoices + sync incoming.

    Pure function — no Celery dependency.  Called by the Celery
    task *and* directly as synchronous fallback.
    """
    from apps.invoices.models import Invoice, InvoiceStatus
    from apps.sdi.models import SdiLog, SdiLogEvent
    from apps.sdi.services.xml_generator import InvoiceXmlGenerator

    generator = InvoiceXmlGenerator()
    send_method = getattr(settings, "SDI_SEND_METHOD", "pec")
    send_fn = _send_via_pec if send_method == "pec" else _send_via_openapi
    logger.info("Batch send using method: %s", send_method)

    results = {"sent": 0, "failed": 0, "synced": 0}

    # ── Phase 1: send outbox invoices ──
    outbox_qs = (
        Invoice.all_types
        .filter(status=InvoiceStatus.OUTBOX)
        .select_related("contact", "sequence")
        .order_by("date", "number")
    )

    for invoice in outbox_qs:
        # PA invoices require qualified digital signature — skip with warning
        if send_method == "pec" and invoice.contact and invoice.contact.is_pa:
            SdiLog.objects.create(
                invoice=invoice,
                event=SdiLogEvent.PA_SKIPPED,
                error_message=(
                    "Fattura verso PA: richiede firma digitale qualificata. "
                    "Firmare il file XML e caricarlo manualmente nella casella PEC."
                ),
            )
            results["failed"] += 1
            logger.warning(
                "Batch: invoice %s skipped — PA recipient (sdi_code=%s), "
                "requires qualified digital signature",
                invoice.number,
                invoice.contact.sdi_code,
            )
            continue

        try:
            xml_content = generator.generate(invoice)
            send_result = send_fn(invoice, xml_content, generator)

            invoice.sdi_uuid = send_result.get("sdi_uuid", "")
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
            )
            results["sent"] += 1
            logger.info(
                "Batch: invoice %s sent (%s)",
                invoice.number,
                send_result.get("log_extra", ""),
            )

        except SdiClientError as exc:
            SdiLog.objects.create(
                invoice=invoice,
                event=SdiLogEvent.SEND_FAILED,
                error_message=str(exc)[:500],
            )
            results["failed"] += 1
            logger.error("Batch: invoice %s failed: %s", invoice.number, exc)
            # Continue with next invoice — don't abort the batch

        except Exception:
            logger.exception("Batch: unexpected error for invoice %s", invoice.number)
            SdiLog.objects.create(
                invoice=invoice,
                event=SdiLogEvent.SEND_FAILED,
                error_message="Internal error (see logs)",
            )
            results["failed"] += 1

    # ── Phase 2 & 3: OpenAPI status check + incoming sync ──
    try:
        from apps.sdi.services.openapi_client import OpenApiSdiClient
        from apps.sdi.services.xml_importer import import_supplier_invoices

        client = OpenApiSdiClient()

        # Phase 2: check status of sent invoices
        try:
            _sync_sent_statuses(client, results)
        except Exception:
            logger.exception("Batch: failed to sync sent invoice statuses")

        # Phase 3: sync incoming invoices
        synced = import_supplier_invoices(client)
        results["synced"] = synced
        logger.info("Batch: synced %d incoming invoices", synced)
    except Exception:
        logger.exception("Batch: failed to init OpenAPI client or sync incoming")

    logger.info("Batch complete: %s", results)
    return results


# OpenAPI status → SdiStatus mapping
_OPENAPI_STATUS_MAP = {
    "delivered": SdiStatus.DELIVERED,
    "rejected": SdiStatus.REJECTED,
    "not_sent": SdiStatus.NOT_SENT,
    "RC": SdiStatus.RECEIVED,
    "MC": SdiStatus.UNABLE_TO_DELIVER,
    "DT": SdiStatus.DEADLINE,
    "NE": SdiStatus.OUTCOME_NEGATIVE,
    "AT": SdiStatus.ACCEPTED,
    "EC": SdiStatus.OUTCOME_POSITIVE,
}


def _sync_sent_statuses(client, results: dict) -> None:
    """Poll OpenAPI for status updates on invoices with an sdi_uuid."""
    from apps.invoices.models import Invoice
    from apps.sdi.models import SdiLog, SdiLogEvent

    sent_qs = (
        Invoice.all_types
        .filter(sdi_status=SdiStatus.SENT)
        .exclude(sdi_uuid="")
        .order_by("sdi_sent_at")[:50]
    )

    updated = 0
    for invoice in sent_qs:
        try:
            data = client.get_invoice_status(invoice.sdi_uuid)
            api_status = data.get("status", "")
            new_sdi_status = _OPENAPI_STATUS_MAP.get(api_status)

            if new_sdi_status and new_sdi_status != invoice.sdi_status:
                old_status = invoice.sdi_status
                invoice.sdi_status = new_sdi_status
                invoice.save(update_fields=["sdi_status", "updated_at"])

                SdiLog.objects.create(
                    invoice=invoice,
                    event=SdiLogEvent.STATUS_CHANGED,
                    sdi_uuid=invoice.sdi_uuid,
                    new_status=new_sdi_status,
                )
                updated += 1
                logger.info(
                    "Status update: invoice %s %s → %s",
                    invoice.number, old_status, new_sdi_status,
                )
        except SdiClientError:
            # Invoice sent via AdE/PEC won't be found on OpenAPI — skip silently
            logger.debug("Status check skipped for %s (uuid=%s)", invoice.number, invoice.sdi_uuid)
        except Exception:
            logger.exception("Status check failed for invoice %s", invoice.number)

    results["status_updated"] = updated
    if updated:
        logger.info("Batch: updated status of %d invoices via OpenAPI", updated)


@shared_task(bind=True, max_retries=2, default_retry_delay=120, retry_backoff=True)
def batch_send_and_sync(self, user_id: int | None = None) -> dict:
    """Celery wrapper around run_batch_send_and_sync."""
    return run_batch_send_and_sync()
