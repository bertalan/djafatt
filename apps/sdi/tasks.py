"""Celery tasks for SDI operations.

All HTTP calls to the SDI API run asynchronously via Celery,
never in the Django request thread.
"""
import logging

from celery import shared_task
from django.utils import timezone

from apps.common.exceptions import SdiClientError

logger = logging.getLogger("apps.sdi")


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    retry_backoff=True,
)
def send_invoice_to_sdi(self, invoice_id: int) -> dict:
    """Generate XML and send a sales invoice to SDI.

    Sets sdi_status, sdi_uuid, sdi_sent_at on the Invoice.
    Returns {"uuid": ..., "status": ...} on success.
    """
    from apps.invoices.models import Invoice, SdiStatus
    from apps.sdi.models import SdiLog, SdiLogEvent
    from apps.sdi.services.openapi_client import OpenApiSdiClient
    from apps.sdi.services.xml_generator import InvoiceXmlGenerator

    invoice = Invoice.all_types.select_related("contact", "sequence").get(pk=invoice_id)

    if not invoice.is_sdi_editable() and invoice.sdi_uuid:
        logger.info("Invoice %s already sent (uuid=%s), skipping", invoice.number, invoice.sdi_uuid)
        return {"uuid": invoice.sdi_uuid, "status": invoice.sdi_status, "skipped": True}

    # Generate XML
    generator = InvoiceXmlGenerator()
    xml_content = generator.generate(invoice)

    # Send to SDI
    client = OpenApiSdiClient()
    try:
        result = client.send_invoice(xml_content)
    except SdiClientError as exc:
        SdiLog.objects.create(
            invoice=invoice,
            event=SdiLogEvent.SEND_FAILED,
            error_message=str(exc)[:500],
        )
        raise
    except Exception as exc:
        logger.exception("Unexpected error sending invoice %s", invoice.number)
        SdiLog.objects.create(
            invoice=invoice,
            event=SdiLogEvent.SEND_FAILED,
            error_message="Internal error (see logs)",
        )
        raise SdiClientError("Failed to send invoice") from exc

    # Update invoice
    invoice.sdi_uuid = result.get("uuid", "")
    invoice.sdi_status = SdiStatus.SENT
    invoice.status = "sent"
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

    logger.info("Invoice %s sent to SDI: uuid=%s", invoice.number, invoice.sdi_uuid)
    return {"uuid": invoice.sdi_uuid, "status": "sent"}
