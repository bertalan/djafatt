"""Tests for SDI two-phase workflow: seal → outbox → batch send."""
from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest
import respx
from django.test import Client
from httpx import Response

from apps.contacts.models import Contact
from apps.invoices.models import Invoice, InvoiceLine, InvoiceStatus, Sequence, SdiStatus, VatRate


@pytest.fixture
def _sdi_invoice(db):
    """Sales invoice with a line, ready to seal."""
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


# ── Seal / Unseal views ──


@pytest.mark.django_db
class TestSealInvoiceView:
    def test_seal_requires_login(self, _sdi_invoice):
        client = Client()
        response = client.post(f"/sdi/invoices/{_sdi_invoice.pk}/seal/")
        assert response.status_code == 302
        assert "/login/" in response.url

    def test_seal_requires_post(self, auth_client, _sdi_invoice):
        response = auth_client.get(f"/sdi/invoices/{_sdi_invoice.pk}/seal/")
        assert response.status_code == 400

    def test_seal_draft_invoice(self, auth_client, _sdi_invoice):
        response = auth_client.post(f"/sdi/invoices/{_sdi_invoice.pk}/seal/")
        assert response.status_code == 302
        _sdi_invoice.refresh_from_db()
        assert _sdi_invoice.status == InvoiceStatus.SEALED
        assert _sdi_invoice.sealed_at is not None

    def test_seal_rejects_empty_invoice(self, auth_client, db):
        contact = Contact.objects.create(
            name="Empty SRL", vat_number="IT22222222222",
            country_code="IT", is_customer=True,
        )
        inv = Invoice.all_types.create(
            type="sales", number="9999/2026", date=date(2026, 1, 1),
            contact=contact, document_type="TD01",
        )
        response = auth_client.post(f"/sdi/invoices/{inv.pk}/seal/")
        assert response.status_code == 302
        inv.refresh_from_db()
        assert inv.status == InvoiceStatus.DRAFT

    def test_seal_rejects_already_sealed(self, auth_client, _sdi_invoice):
        _sdi_invoice.status = InvoiceStatus.SEALED
        _sdi_invoice.save(update_fields=["status"])
        response = auth_client.post(f"/sdi/invoices/{_sdi_invoice.pk}/seal/")
        assert response.status_code == 302  # redirect with error message

    def test_unseal_sealed_invoice(self, auth_client, _sdi_invoice):
        _sdi_invoice.status = InvoiceStatus.SEALED
        _sdi_invoice.save(update_fields=["status"])
        response = auth_client.post(f"/sdi/invoices/{_sdi_invoice.pk}/unseal/")
        assert response.status_code == 302
        _sdi_invoice.refresh_from_db()
        assert _sdi_invoice.status == InvoiceStatus.DRAFT
        assert _sdi_invoice.sealed_at is None

    def test_unseal_rejects_draft(self, auth_client, _sdi_invoice):
        response = auth_client.post(f"/sdi/invoices/{_sdi_invoice.pk}/unseal/")
        assert response.status_code == 302  # redirect with error
        _sdi_invoice.refresh_from_db()
        assert _sdi_invoice.status == InvoiceStatus.DRAFT


# ── Queue / Unqueue views ──


@pytest.mark.django_db
class TestQueueInvoiceView:
    def test_queue_sealed_invoice(self, auth_client, _sdi_invoice):
        _sdi_invoice.status = InvoiceStatus.SEALED
        _sdi_invoice.save(update_fields=["status"])
        response = auth_client.post(f"/sdi/invoices/{_sdi_invoice.pk}/queue/")
        assert response.status_code == 302
        _sdi_invoice.refresh_from_db()
        assert _sdi_invoice.status == InvoiceStatus.OUTBOX
        assert _sdi_invoice.sdi_status == SdiStatus.PENDING

    def test_queue_rejects_draft(self, auth_client, _sdi_invoice):
        response = auth_client.post(f"/sdi/invoices/{_sdi_invoice.pk}/queue/")
        assert response.status_code == 302
        _sdi_invoice.refresh_from_db()
        assert _sdi_invoice.status == InvoiceStatus.DRAFT

    def test_unqueue_outbox_invoice(self, auth_client, _sdi_invoice):
        _sdi_invoice.status = InvoiceStatus.OUTBOX
        _sdi_invoice.sdi_status = SdiStatus.PENDING
        _sdi_invoice.save(update_fields=["status", "sdi_status"])
        response = auth_client.post(f"/sdi/invoices/{_sdi_invoice.pk}/unqueue/")
        assert response.status_code == 302
        _sdi_invoice.refresh_from_db()
        assert _sdi_invoice.status == InvoiceStatus.SEALED
        assert _sdi_invoice.sdi_status == ""

    def test_unqueue_rejects_sdi_locked(self, auth_client, _sdi_invoice):
        _sdi_invoice.status = InvoiceStatus.OUTBOX
        _sdi_invoice.sdi_status = SdiStatus.DELIVERED
        _sdi_invoice.save(update_fields=["status", "sdi_status"])
        response = auth_client.post(f"/sdi/invoices/{_sdi_invoice.pk}/unqueue/")
        assert response.status_code == 302
        _sdi_invoice.refresh_from_db()
        assert _sdi_invoice.status == InvoiceStatus.OUTBOX  # unchanged


# ── Outbox view ──


@pytest.mark.django_db
class TestOutboxView:
    def test_outbox_requires_login(self):
        client = Client()
        response = client.get("/sdi/outbox/")
        assert response.status_code == 302
        assert "/login/" in response.url

    def test_outbox_shows_queued_and_sealed(self, auth_client, _sdi_invoice):
        response = auth_client.get("/sdi/outbox/")
        assert response.status_code == 200
        assert "outbox_invoices" in response.context
        assert "sealed_invoices" in response.context


# ── Batch send view ──


@pytest.mark.django_db
class TestBatchSendView:
    def test_batch_send_requires_post(self, auth_client):
        response = auth_client.get("/sdi/batch-send/")
        assert response.status_code == 400

    @patch("apps.sdi.views_send.batch_send_and_sync")
    def test_batch_send_queues_task(self, mock_task, auth_client, _sdi_invoice):
        _sdi_invoice.status = InvoiceStatus.OUTBOX
        _sdi_invoice.save(update_fields=["status"])
        response = auth_client.post("/sdi/batch-send/")
        assert response.status_code == 302
        mock_task.delay.assert_called_once_with(user_id=auth_client.user.pk)

    @patch("apps.sdi.views_send.batch_send_and_sync")
    def test_batch_send_rejects_empty_outbox(self, mock_task, auth_client):
        response = auth_client.post("/sdi/batch-send/")
        assert response.status_code == 302
        mock_task.delay.assert_not_called()

    @patch("apps.sdi.views_send.run_batch_send_and_sync", return_value={"sent": 1, "failed": 0, "synced": 0})
    @patch("apps.sdi.views_send.batch_send_and_sync")
    def test_batch_send_falls_back_to_sync(self, mock_task, mock_run, auth_client, _sdi_invoice):
        """If Celery broker is unreachable, batch runs synchronously."""
        _sdi_invoice.status = InvoiceStatus.OUTBOX
        _sdi_invoice.save(update_fields=["status"])
        mock_task.delay.side_effect = ConnectionError("broker down")
        response = auth_client.post("/sdi/batch-send/")
        assert response.status_code == 302
        mock_run.assert_called_once()


# ── Batch task ──


@pytest.mark.django_db
class TestBatchSendAndSyncTask:
    @respx.mock
    def test_task_sends_outbox_invoices(self, _sdi_invoice, settings, company_settings):
        settings.OPENAPI_SDI_TOKEN = "test-token"
        settings.OPENAPI_SDI_SANDBOX = True

        _sdi_invoice.status = InvoiceStatus.OUTBOX
        _sdi_invoice.sdi_status = SdiStatus.PENDING
        _sdi_invoice.save(update_fields=["status", "sdi_status"])

        respx.post("https://test.sdi.openapi.it/invoices").mock(
            return_value=Response(200, json={
                "success": True,
                "data": {"uuid": "sdi-uuid-001", "status": "queued"},
            })
        )

        # Mock supplier invoices sync (no incoming)
        respx.get("https://test.sdi.openapi.it/invoices/supplier").mock(
            return_value=Response(200, json={"success": True, "data": {"items": []}})
        )

        from apps.sdi.tasks import batch_send_and_sync

        result = batch_send_and_sync()

        assert result["sent"] == 1
        assert result["failed"] == 0

        _sdi_invoice.refresh_from_db()
        assert _sdi_invoice.sdi_uuid == "sdi-uuid-001"
        assert _sdi_invoice.sdi_status == SdiStatus.SENT
        assert _sdi_invoice.status == InvoiceStatus.SENT

    @respx.mock
    def test_task_continues_on_failure(self, _sdi_invoice, settings, company_settings):
        """A single invoice failure does not abort the batch."""
        settings.OPENAPI_SDI_TOKEN = "test-token"
        settings.OPENAPI_SDI_SANDBOX = True

        _sdi_invoice.status = InvoiceStatus.OUTBOX
        _sdi_invoice.sdi_status = SdiStatus.PENDING
        _sdi_invoice.save(update_fields=["status", "sdi_status"])

        respx.post("https://test.sdi.openapi.it/invoices").mock(
            return_value=Response(200, json={
                "success": False,
                "message": "XML non valido",
            })
        )
        respx.get("https://test.sdi.openapi.it/invoices/supplier").mock(
            return_value=Response(200, json={"success": True, "data": {"items": []}})
        )

        from apps.sdi.tasks import batch_send_and_sync

        result = batch_send_and_sync()

        assert result["failed"] == 1
        assert result["sent"] == 0

    @respx.mock
    def test_task_sends_valid_xml(self, _sdi_invoice, settings, company_settings):
        """Verify the XML sent contains FatturaElettronica root."""
        settings.OPENAPI_SDI_TOKEN = "test-token"
        settings.OPENAPI_SDI_SANDBOX = True

        _sdi_invoice.status = InvoiceStatus.OUTBOX
        _sdi_invoice.sdi_status = SdiStatus.PENDING
        _sdi_invoice.save(update_fields=["status", "sdi_status"])

        route = respx.post("https://test.sdi.openapi.it/invoices").mock(
            return_value=Response(200, json={
                "success": True,
                "data": {"uuid": "sdi-uuid-002", "status": "queued"},
            })
        )
        respx.get("https://test.sdi.openapi.it/invoices/supplier").mock(
            return_value=Response(200, json={"success": True, "data": {"items": []}})
        )

        from apps.sdi.tasks import batch_send_and_sync

        batch_send_and_sync()

        sent_body = route.calls[0].request.content.decode("utf-8")
        assert "FatturaElettronica" in sent_body
