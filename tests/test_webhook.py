"""TDD tests for SDI webhook endpoint — RED phase.

Tests for webhook signature verification and status processing.
"""
import hashlib
import hmac
import json

import pytest
from django.test import Client


WEBHOOK_PAYLOAD = json.dumps({
    "event": "invoice.status_changed",
    "data": {
        "uuid": "abc-123",
        "status": "delivered",
        "timestamp": "2026-01-15T10:00:00Z",
    },
})


def _compute_signature(payload: str, secret: str) -> str:
    """Compute HMAC-SHA256 signature for testing."""
    return hmac.new(
        secret.encode(), payload.encode(), hashlib.sha256,
    ).hexdigest()


@pytest.mark.django_db
class TestWebhookSecurity:
    def test_valid_signature_accepted(self, settings):
        """Webhook with valid HMAC-SHA256 signature is accepted."""
        settings.OPENAPI_SDI_WEBHOOK_SECRET = "super-secret"
        sig = _compute_signature(WEBHOOK_PAYLOAD, "super-secret")

        client = Client()
        response = client.post(
            "/webhooks/sdi/",
            data=WEBHOOK_PAYLOAD,
            content_type="application/json",
            HTTP_X_WEBHOOK_SIGNATURE=sig,
        )
        assert response.status_code == 200

    def test_invalid_signature_rejected(self, settings):
        """Webhook with wrong signature is rejected 403."""
        settings.OPENAPI_SDI_WEBHOOK_SECRET = "super-secret"

        client = Client()
        response = client.post(
            "/webhooks/sdi/",
            data=WEBHOOK_PAYLOAD,
            content_type="application/json",
            HTTP_X_WEBHOOK_SIGNATURE="bad-signature",
        )
        assert response.status_code == 403

    def test_missing_signature_rejected(self, settings):
        """Webhook without signature header is rejected 403."""
        settings.OPENAPI_SDI_WEBHOOK_SECRET = "super-secret"

        client = Client()
        response = client.post(
            "/webhooks/sdi/",
            data=WEBHOOK_PAYLOAD,
            content_type="application/json",
        )
        assert response.status_code == 403

    def test_get_method_not_allowed(self):
        """GET requests to webhook endpoint are rejected."""
        client = Client()
        response = client.get("/webhooks/sdi/")
        assert response.status_code == 405

    def test_webhook_updates_invoice_status(self, settings, invoice):
        """Webhook updates invoice SDI status."""
        from apps.invoices.models import SdiStatus

        invoice.sdi_uuid = "abc-123"
        invoice.sdi_status = SdiStatus.SENT
        invoice.save()

        settings.OPENAPI_SDI_WEBHOOK_SECRET = "super-secret"
        sig = _compute_signature(WEBHOOK_PAYLOAD, "super-secret")

        client = Client()
        client.post(
            "/webhooks/sdi/",
            data=WEBHOOK_PAYLOAD,
            content_type="application/json",
            HTTP_X_WEBHOOK_SIGNATURE=sig,
        )
        invoice.refresh_from_db()
        assert invoice.sdi_status == SdiStatus.DELIVERED

    def test_timing_attack_protection(self, settings):
        """Signature verification uses constant-time comparison."""
        from apps.sdi.security import verify_webhook_signature

        # This test verifies the function exists and uses secrets.compare_digest
        import inspect
        source = inspect.getsource(verify_webhook_signature)
        assert "compare_digest" in source
