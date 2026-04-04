"""TDD Security tests — CSRF and permissions — RED phase.

Tests for Django CSRF protection and permission enforcement.
"""
import pytest
from django.test import Client


@pytest.mark.django_db
class TestCsrfProtection:
    def test_post_without_csrf_rejected(self, auth_client, italian_contact):
        """POST to form endpoint without CSRF token is rejected."""
        client = Client(enforce_csrf_checks=True)
        client.login(username="testuser", password="testpass123!")
        response = client.post(
            f"/contacts/{italian_contact.pk}/edit/",
            data={"name": "Hacked"},
        )
        assert response.status_code == 403

    def test_htmx_requests_require_csrf(self):
        """HTMX POST requests also need CSRF token."""
        client = Client(enforce_csrf_checks=True)
        response = client.post(
            "/contacts/",
            data={"name": "Test"},
            HTTP_HX_REQUEST="true",
        )
        # 403 because not logged in or missing CSRF
        assert response.status_code in (302, 403)


@pytest.mark.django_db
class TestPermissions:
    def test_unauthenticated_redirect(self):
        """Unauthenticated request to protected view redirects."""
        client = Client()
        for url in ["/", "/invoices/", "/contacts/", "/products/"]:
            response = client.get(url)
            assert response.status_code in (301, 302), f"Failed for {url}"

    def test_system_vat_rate_deletion_blocked(self, auth_client, vat_rate_system):
        """Cannot delete a system VatRate via the UI."""
        response = auth_client.post(f"/vat-rates/{vat_rate_system.pk}/delete/")
        assert response.status_code in (403, 302)  # Blocked

    def test_sdi_locked_invoice_edit_saves_only_payments(self, auth_client, invoice):
        """Locked invoice POST saves only payment dues, not invoice fields."""
        from apps.invoices.models import SdiStatus

        invoice.sdi_status = SdiStatus.DELIVERED
        invoice.save()
        original_number = invoice.number
        response = auth_client.post(
            f"/invoices/{invoice.pk}/edit/",
            data={
                "number": "EDITED",
                "dues-TOTAL_FORMS": "0",
                "dues-INITIAL_FORMS": "0",
                "dues-MIN_NUM_FORMS": "0",
                "dues-MAX_NUM_FORMS": "1000",
            },
        )
        assert response.status_code == 302
        invoice.refresh_from_db()
        assert invoice.number == original_number

    def test_webhook_endpoint_no_auth_needed(self, settings):
        """Webhook endpoint doesn't require login (uses HMAC instead)."""
        settings.OPENAPI_SDI_WEBHOOK_SECRET = "secret"
        client = Client()
        response = client.post(
            "/webhooks/sdi/",
            data="{}",
            content_type="application/json",
        )
        # 403 because bad signature, NOT 302 redirect to login
        assert response.status_code == 403


@pytest.mark.django_db
class TestSecurityHeaders:
    def test_x_content_type_options(self, auth_client):
        """Response includes X-Content-Type-Options: nosniff."""
        response = auth_client.get("/")
        assert response.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options(self, auth_client):
        """Response includes X-Frame-Options header."""
        response = auth_client.get("/")
        assert response.get("X-Frame-Options") in ("DENY", "SAMEORIGIN")
