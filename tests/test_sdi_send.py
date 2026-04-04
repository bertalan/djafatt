"""Tests for SDI send task and view — mock-based, CI-safe."""
from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest
import respx
from django.test import Client
from httpx import Response

from apps.contacts.models import Contact
from apps.invoices.models import Invoice, InvoiceLine, Sequence, SdiStatus, VatRate


@pytest.fixture
def _sdi_invoice(db):
    """Sales invoice with a line, ready to send."""
    contact = Contact.objects.create(
        name="Test Client SRL",
        vat_number="IT11111111111",
        tax_code="11111111111",
        address="Via Test 1",
        city="Roma",
        postal_code="00100",
        province="RM",
        country_code="IT",
        sdi_code="ABC1234",
        is_customer=True,
    )
    seq = Sequence.objects.create(name="Test vendita", type="sales", pattern="{SEQ}/{ANNO}")
    vat = VatRate.objects.create(name="Esente N2.2", percent=Decimal("0.00"), nature="N2.2")

    inv = Invoice.all_types.create(
        type="sales",
        number="0001/2026",
        sequential_number=1,
        date=date(2026, 3, 24),
        contact=contact,
        sequence=seq,
        document_type="TD01",
        payment_method="MP05",
        payment_terms="TP02",
    )
    InvoiceLine.objects.create(
        invoice=inv,
        description="Consulenza test",
        quantity=Decimal("1.00"),
        unit_price=10000,
        vat_rate=vat,
        total=10000,
    )
    inv.calculate_totals()
    return inv


@pytest.mark.django_db
class TestSendInvoiceToSdiTask:
    """Unit tests for the Celery task (respx mocking)."""

    @respx.mock
    def test_task_sends_xml_and_updates_invoice(self, _sdi_invoice, settings, company_settings):
        settings.OPENAPI_SDI_TOKEN = "test-token"
        settings.OPENAPI_SDI_SANDBOX = True

        respx.post("https://test.sdi.openapi.it/invoices").mock(
            return_value=Response(200, json={
                "success": True,
                "data": {"uuid": "sdi-uuid-001", "status": "queued"},
            })
        )

        from apps.sdi.tasks import send_invoice_to_sdi

        result = send_invoice_to_sdi(_sdi_invoice.pk)

        assert result["uuid"] == "sdi-uuid-001"
        assert result["status"] == "sent"

        _sdi_invoice.refresh_from_db()
        assert _sdi_invoice.sdi_uuid == "sdi-uuid-001"
        assert _sdi_invoice.sdi_status == SdiStatus.SENT
        assert _sdi_invoice.status == "sent"
        assert _sdi_invoice.sdi_sent_at is not None

    @respx.mock
    def test_task_skips_already_sent_invoice(self, _sdi_invoice, settings, company_settings):
        settings.OPENAPI_SDI_TOKEN = "test-token"
        settings.OPENAPI_SDI_SANDBOX = True

        _sdi_invoice.sdi_uuid = "existing-uuid"
        _sdi_invoice.sdi_status = SdiStatus.DELIVERED
        _sdi_invoice.save(update_fields=["sdi_uuid", "sdi_status"])

        from apps.sdi.tasks import send_invoice_to_sdi

        result = send_invoice_to_sdi(_sdi_invoice.pk)

        assert result["skipped"] is True
        assert result["uuid"] == "existing-uuid"

    @respx.mock
    def test_task_raises_on_api_error(self, _sdi_invoice, settings, company_settings):
        settings.OPENAPI_SDI_TOKEN = "test-token"
        settings.OPENAPI_SDI_SANDBOX = True

        respx.post("https://test.sdi.openapi.it/invoices").mock(
            return_value=Response(200, json={
                "success": False,
                "message": "XML non valido",
            })
        )

        from apps.common.exceptions import SdiClientError
        from apps.sdi.tasks import send_invoice_to_sdi

        with pytest.raises(SdiClientError, match="XML non valido"):
            send_invoice_to_sdi(_sdi_invoice.pk)

    @respx.mock
    def test_task_sends_valid_xml_to_api(self, _sdi_invoice, settings, company_settings):
        """Verify the XML sent contains FatturaElettronica root."""
        settings.OPENAPI_SDI_TOKEN = "test-token"
        settings.OPENAPI_SDI_SANDBOX = True

        route = respx.post("https://test.sdi.openapi.it/invoices").mock(
            return_value=Response(200, json={
                "success": True,
                "data": {"uuid": "sdi-uuid-002", "status": "queued"},
            })
        )

        from apps.sdi.tasks import send_invoice_to_sdi

        send_invoice_to_sdi(_sdi_invoice.pk)

        sent_body = route.calls[0].request.content.decode("utf-8")
        assert "FatturaElettronica" in sent_body
        assert "xml" in sent_body


@pytest.mark.django_db
class TestSendToSdiView:
    """Tests for the send_to_sdi_view."""

    def test_send_view_requires_login(self, _sdi_invoice):
        client = Client()
        response = client.post(f"/sdi/invoices/{_sdi_invoice.pk}/send-sdi/")
        assert response.status_code == 302
        assert "/login/" in response.url

    def test_send_view_requires_post(self, auth_client, _sdi_invoice):
        response = auth_client.get(f"/sdi/invoices/{_sdi_invoice.pk}/send-sdi/")
        assert response.status_code == 400

    @patch("apps.sdi.views_send.send_invoice_to_sdi")
    def test_send_view_queues_task(self, mock_task, auth_client, _sdi_invoice):
        response = auth_client.post(f"/sdi/invoices/{_sdi_invoice.pk}/send-sdi/")
        assert response.status_code == 302
        mock_task.delay.assert_called_once_with(_sdi_invoice.pk)

    @patch("apps.sdi.views_send.send_invoice_to_sdi")
    def test_send_view_rejects_already_sent(self, mock_task, auth_client, _sdi_invoice):
        _sdi_invoice.sdi_status = SdiStatus.DELIVERED
        _sdi_invoice.save(update_fields=["sdi_status"])

        response = auth_client.post(f"/sdi/invoices/{_sdi_invoice.pk}/send-sdi/")
        assert response.status_code == 302
        mock_task.delay.assert_not_called()

    @patch("apps.sdi.views_send.send_invoice_to_sdi")
    def test_send_view_rejects_empty_invoice(self, mock_task, auth_client, db):
        """Invoice with no lines cannot be sent."""
        contact = Contact.objects.create(
            name="Empty SRL", vat_number="IT22222222222",
            country_code="IT", is_customer=True,
        )
        inv = Invoice.all_types.create(
            type="sales", number="9999/2026", date=date(2026, 1, 1),
            contact=contact, document_type="TD01",
        )
        response = auth_client.post(f"/sdi/invoices/{inv.pk}/send-sdi/")
        assert response.status_code == 302
        mock_task.delay.assert_not_called()

    def test_send_view_404_for_missing_invoice(self, auth_client):
        response = auth_client.post("/sdi/invoices/99999/send-sdi/")
        assert response.status_code == 404
