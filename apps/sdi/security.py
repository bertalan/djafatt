"""Webhook security utilities for SDI integration.

HMAC-SHA256 signature verification, idempotency, and rate limiting.
"""
import hashlib
import hmac
import secrets

from django.conf import settings

from apps.common.exceptions import SdiWebhookSecurityError


def verify_webhook_signature(request_body: bytes, signature_header: str) -> None:
    """Verify HMAC-SHA256 signature on webhook request body.

    Raises SdiWebhookSecurityError if signature is invalid or missing.
    """
    webhook_secret = settings.OPENAPI_SDI_WEBHOOK_SECRET
    if not webhook_secret:
        raise SdiWebhookSecurityError("Webhook secret not configured")

    if len(webhook_secret) < 32:
        raise SdiWebhookSecurityError("Webhook secret too short (min 32 chars)")

    if not signature_header:
        raise SdiWebhookSecurityError("Missing signature header")

    expected = hmac.new(
        webhook_secret.encode("utf-8"),
        request_body,
        hashlib.sha256,
    ).hexdigest()

    if not secrets.compare_digest(expected, signature_header):
        raise SdiWebhookSecurityError("Invalid webhook signature")
