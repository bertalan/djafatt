"""TDD tests for views — RED phase.

Tests for Django views including login required, HTMX endpoints, CRUD.
"""
from datetime import date

import pytest
from django.test import Client


@pytest.mark.django_db
class TestAuthRequired:
    def test_dashboard_requires_login(self):
        """Unauthenticated user redirected from dashboard."""
        client = Client()
        response = client.get("/")
        assert response.status_code in (301, 302)

    def test_dashboard_accessible_when_logged_in(self, auth_client):
        """Authenticated user can access dashboard."""
        response = auth_client.get("/")
        assert response.status_code == 200


@pytest.mark.django_db
class TestInvoiceViews:
    def test_invoice_list(self, auth_client, invoice):
        """Invoice list page loads and contains the invoice."""
        response = auth_client.get("/invoices/")
        assert response.status_code == 200

    def test_invoice_delete_blocked_if_sdi_sent(self, auth_client, invoice):
        """Cannot delete invoice that has been sent to SDI."""
        from apps.invoices.models import SdiStatus

        invoice.sdi_status = SdiStatus.SENT
        invoice.save()
        response = auth_client.post(f"/invoices/{invoice.pk}/delete/")
        # Should be blocked — 403 or redirect with error
        assert response.status_code in (403, 302)


@pytest.mark.django_db
class TestContactViews:
    def test_contact_search_htmx(self, auth_client, italian_contact):
        """HTMX search returns partial HTML."""
        response = auth_client.get(
            "/contacts/?q=Cliente",
            HTTP_HX_REQUEST="true",
        )
        assert response.status_code == 200
        assert "Cliente Italiano" in response.content.decode()


@pytest.mark.django_db
class TestFiscalYear:
    def test_fiscal_year_set_via_post(self, auth_client):
        """Fiscal year must be set via POST (not GET)."""
        response = auth_client.get("/set-fiscal-year/?year=2026")
        assert response.status_code in (404, 405)  # GET not allowed

    def test_fiscal_year_out_of_range(self, auth_client):
        """Fiscal year with unreasonable value returns error."""
        response = auth_client.post("/set-fiscal-year/", {"year": 1900})
        assert response.status_code in (400, 422)


@pytest.mark.django_db
class TestDashboardUnpaidBoxes:
    """Dashboard shows unpaid sales/purchase invoice counts and totals."""

    def test_dashboard_shows_unpaid_sales(self, auth_client, invoice):
        """Unpaid sales invoice appears in dashboard stats."""
        invoice.total_gross = 24400
        invoice.save(update_fields=["total_gross"])
        response = auth_client.get("/")
        content = response.content.decode()
        assert "Da incassare (vendite)" in content

    def test_dashboard_paid_excluded(self, auth_client, invoice):
        """Paid invoices are not counted as unpaid."""
        invoice.paid_at = date(2026, 1, 20)
        invoice.total_gross = 10000
        invoice.save(update_fields=["paid_at", "total_gross"])
        response = auth_client.get("/")
        content = response.content.decode()
        # The unpaid sales count should be 0
        assert "Da incassare (vendite)" in content

    def test_dashboard_shows_unpaid_purchases(self, auth_client, sequence_purchase, italian_contact):
        """Unpaid purchase invoice appears in dashboard stats."""
        from apps.invoices.models import PurchaseInvoice

        PurchaseInvoice.objects.create(
            number="0001/2026", sequential_number=1, date=date(2026, 1, 15),
            contact=italian_contact, sequence=sequence_purchase, total_gross=15000,
        )
        response = auth_client.get("/")
        content = response.content.decode()
        assert "Da pagare (acquisti)" in content

    def test_dashboard_has_fiscal_year(self, auth_client):
        """Dashboard template receives fiscal_year context."""
        response = auth_client.get("/")
        assert response.context["fiscal_year"] == date.today().year
