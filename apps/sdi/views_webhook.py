"""Webhook handler for SDI notifications (T20).

Public endpoint — security relies on HMAC signature verification.
"""
import json
import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.common.exceptions import SdiWebhookSecurityError
from apps.invoices.models import Invoice, SdiStatus

from .models import SdiLog, SdiLogEvent
from .security import verify_webhook_signature

logger = logging.getLogger("djafatt.sdi")

# Max payload size: 1 MB
MAX_PAYLOAD_SIZE = 1 * 1024 * 1024

# Map webhook status strings to SdiStatus enum values
SDI_STATUS_MAP = {
    "delivered": SdiStatus.DELIVERED,
    "rejected": SdiStatus.REJECTED,
    "sent": SdiStatus.SENT,
    "pending": SdiStatus.PENDING,
    "NS": SdiStatus.NOT_SENT,
    "RC": SdiStatus.RECEIVED,
    "MC": SdiStatus.UNABLE_TO_DELIVER,
    "DT": SdiStatus.DEADLINE,
    "NE": SdiStatus.OUTCOME_NEGATIVE,
    "AT": SdiStatus.ACCEPTED,
    "EC": SdiStatus.OUTCOME_POSITIVE,
}


def _get_client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


@csrf_exempt
@require_POST
def webhook_handler(request):
    """Handle inbound SDI webhook notifications."""
    # Size check — safe integer parsing
    try:
        content_length = int(request.META.get("CONTENT_LENGTH", 0))
        if content_length < 0 or content_length > MAX_PAYLOAD_SIZE:
            return JsonResponse({"error": "Payload too large"}, status=413)
    except (ValueError, TypeError):
        return JsonResponse({"error": "Invalid Content-Length"}, status=400)

    if request.content_type != "application/json":
        return JsonResponse({"error": "Content-Type must be application/json"}, status=415)

    body = request.body
    client_ip = _get_client_ip(request)

    # HMAC verification — header: X-Webhook-Signature
    signature = request.META.get("HTTP_X_WEBHOOK_SIGNATURE", "")
    try:
        verify_webhook_signature(body, signature)
    except SdiWebhookSecurityError as exc:
        logger.warning("Webhook signature verification failed: %s", exc)
        SdiLog.objects.create(
            event=SdiLogEvent.WEBHOOK_REJECTED,
            error_message=str(exc)[:500],
            ip_address=client_ip,
        )
        return JsonResponse({"error": "Forbidden"}, status=403)

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    event = payload.get("event")
    data = payload.get("data", {})

    if not isinstance(data, dict):
        return JsonResponse({"error": "Invalid data field"}, status=400)

    handlers = {
        "invoice.status_changed": _handle_status_changed,
        "supplier-invoice": _handle_supplier_invoice,
        "customer-notification": _handle_customer_notification,
        "customer-invoice": _handle_customer_invoice,
    }
    handler = handlers.get(event)
    if not handler:
        logger.warning("Unknown webhook event: %s", str(event)[:100] if event else "(empty)")
        SdiLog.objects.create(
            event=SdiLogEvent.WEBHOOK_REJECTED,
            error_message="Unknown event type",
            ip_address=client_ip or None,
        )
        return JsonResponse({"error": "Unknown event"}, status=400)

    try:
        handler(data, client_ip=client_ip)
    except Exception:
        logger.exception("Error handling webhook event %s", event)
        return JsonResponse({"error": "Internal error"}, status=500)

    return JsonResponse({"status": "ok"})


def _handle_status_changed(data: dict, *, client_ip: str = "") -> None:
    """Handle invoice.status_changed event: update invoice SDI status."""
    uuid = data.get("uuid", "")
    status_str = data.get("status", "")

    if not uuid:
        return

    try:
        invoice = Invoice.all_types.get(sdi_uuid=uuid)
    except Invoice.DoesNotExist:
        logger.warning("Status changed for unknown UUID: %s", uuid)
        SdiLog.objects.create(
            event=SdiLogEvent.WEBHOOK_RECEIVED,
            sdi_uuid=uuid,
            payload=data,
            error_message=f"Unknown UUID: {uuid}",
            ip_address=client_ip or None,
        )
        return

    old_status = invoice.sdi_status
    new_status = SDI_STATUS_MAP.get(status_str)
    if new_status:
        invoice.sdi_status = new_status
        invoice.save(update_fields=["sdi_status", "updated_at"])
        SdiLog.objects.create(
            invoice=invoice,
            event=SdiLogEvent.STATUS_CHANGED,
            sdi_uuid=uuid,
            old_status=old_status,
            new_status=new_status,
            payload=data,
            ip_address=client_ip or None,
        )
        logger.info("Updated SDI status for invoice %s: %s → %s", invoice.number, status_str, new_status)


def _handle_supplier_invoice(data: dict, *, client_ip: str = "") -> None:
    """Handle supplier-invoice event: download and import XML."""
    uuid = data.get("uuid", "")
    if not uuid:
        return

    SdiLog.objects.create(
        event=SdiLogEvent.WEBHOOK_RECEIVED,
        sdi_uuid=uuid,
        payload=data,
        ip_address=client_ip or None,
    )
    logger.info("Received supplier invoice webhook: uuid=%s", uuid)


def _handle_customer_notification(data: dict, *, client_ip: str = "") -> None:
    """Handle customer-notification: update invoice SDI status."""
    uuid = data.get("uuid", "")
    notification_type = data.get("notification_type", "")
    description = data.get("notification_description", "")

    if not uuid or not notification_type:
        return

    try:
        invoice = Invoice.all_types.get(sdi_uuid=uuid)
    except Invoice.DoesNotExist:
        logger.warning("Customer notification for unknown UUID: %s", uuid)
        SdiLog.objects.create(
            event=SdiLogEvent.WEBHOOK_RECEIVED,
            sdi_uuid=uuid,
            payload=data,
            error_message=f"Unknown UUID: {uuid}",
            ip_address=client_ip or None,
        )
        return

    old_status = invoice.sdi_status
    new_status = SDI_STATUS_MAP.get(notification_type)
    if new_status:
        invoice.sdi_status = new_status
        invoice.sdi_message = description
        invoice.save(update_fields=["sdi_status", "sdi_message", "updated_at"])
        SdiLog.objects.create(
            invoice=invoice,
            event=SdiLogEvent.STATUS_CHANGED,
            sdi_uuid=uuid,
            old_status=old_status,
            new_status=new_status,
            payload=data,
            ip_address=client_ip or None,
        )
        logger.info("Updated SDI status for invoice %s: %s → %s", invoice.number, notification_type, new_status)


def _handle_customer_invoice(data: dict, *, client_ip: str = "") -> None:
    """Handle customer-invoice: update SDI ID after successful send."""
    uuid = data.get("uuid", "")
    sdi_id = data.get("sdi_id", "")

    if not uuid:
        return

    try:
        invoice = Invoice.all_types.get(sdi_uuid=uuid)
    except Invoice.DoesNotExist:
        logger.warning("Customer invoice confirmation for unknown UUID: %s", uuid)
        return

    if sdi_id:
        invoice.sdi_id = sdi_id
        invoice.save(update_fields=["sdi_id", "updated_at"])
        SdiLog.objects.create(
            invoice=invoice,
            event=SdiLogEvent.WEBHOOK_RECEIVED,
            sdi_uuid=uuid,
            payload=data,
            ip_address=client_ip or None,
        )
        logger.info("Updated SDI ID for invoice %s: %s", invoice.number, sdi_id)
