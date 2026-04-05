"""Celery tasks for SDI operations.

All HTTP calls to the SDI API run asynchronously via Celery,
never in the Django request thread.
"""
import logging

from celery import shared_task
from django.utils import timezone

from apps.common.exceptions import SdiClientError

logger = logging.getLogger("apps.sdi")


@shared_task(bind=True, max_retries=2, default_retry_delay=120, retry_backoff=True)
def batch_send_and_sync(self, user_id: int | None = None) -> dict:
    """Batch send all outbox invoices + sync incoming invoices.

    Single task to minimise OpenAPI calls:
    - 1 send_invoice call per outbox invoice
    - 1 get_supplier_invoices call to sync inbox
    """
    from apps.invoices.models import Invoice, InvoiceStatus, SdiStatus
    from apps.sdi.models import SdiLog, SdiLogEvent
    from apps.sdi.services.openapi_client import OpenApiSdiClient
    from apps.sdi.services.xml_generator import InvoiceXmlGenerator

    client = OpenApiSdiClient()
    generator = InvoiceXmlGenerator()
    results = {"sent": 0, "failed": 0, "synced": 0}

    # ── Phase 1: send outbox invoices ──
    outbox_qs = (
        Invoice.all_types
        .filter(status=InvoiceStatus.OUTBOX)
        .select_related("contact", "sequence")
        .order_by("date", "number")
    )

    for invoice in outbox_qs:
        try:
            xml_content = generator.generate(invoice)
            result = client.send_invoice(xml_content)

            invoice.sdi_uuid = result.get("uuid", "")
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
            logger.info("Batch: invoice %s sent, uuid=%s", invoice.number, invoice.sdi_uuid)

        except SdiClientError as exc:
            SdiLog.objects.create(
                invoice=invoice,
                event=SdiLogEvent.SEND_FAILED,
                error_message=str(exc)[:500],
            )
            results["failed"] += 1
            logger.error("Batch: invoice %s failed: %s", invoice.number, exc)
            # Continue with next invoice — don't abort the batch

        except Exception as exc:
            logger.exception("Batch: unexpected error for invoice %s", invoice.number)
            SdiLog.objects.create(
                invoice=invoice,
                event=SdiLogEvent.SEND_FAILED,
                error_message="Internal error (see logs)",
            )
            results["failed"] += 1

    # ── Phase 2: sync incoming invoices ──
    try:
        from apps.sdi.services.xml_importer import import_supplier_invoices
        synced = import_supplier_invoices(client)
        results["synced"] = synced
        logger.info("Batch: synced %d incoming invoices", synced)
    except Exception:
        logger.exception("Batch: failed to sync incoming invoices")

    logger.info("Batch complete: %s", results)
    return results
