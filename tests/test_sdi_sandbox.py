"""Sandbox integration tests — hit the real SDI sandbox API.

Run only with: pytest -m sandbox
Requires OPENAPI_SDI_TOKEN env var set to a valid sandbox token.

These tests are NOT run in CI — they exist for manual acceptance testing
against the OpenAPI SDI sandbox environment.
"""
from datetime import date
from decimal import Decimal

import pytest
from django.conf import settings

from apps.contacts.models import Contact
from apps.invoices.models import Invoice, InvoiceLine, Sequence, VatRate


@pytest.fixture
def sandbox_invoice(db, company_settings):
    """Real-looking invoice for sandbox testing."""
    contact = Contact.objects.create(
        name="Sandbox Test SRL",
        vat_number="IT01234567890",
        tax_code="01234567890",
        address="Via Sandbox 1",
        city="Roma",
        postal_code="00100",
        province="RM",
        country_code="IT",
        sdi_code="0000000",
        is_customer=True,
    )
    seq = Sequence.objects.create(name="Sandbox vendita", type="sales", pattern="{SEQ}/{ANNO}")
    vat = VatRate.objects.create(name="Esente N2.2 (sandbox)", percent=Decimal("0.00"), nature="N2.2")

    inv = Invoice.all_types.create(
        type="sales",
        number="SANDBOX-0001/2026",
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
        description="Test sandbox — servizio consulenza",
        quantity=Decimal("1.00"),
        unit_price=10000,
        vat_rate=vat,
        total=10000,
    )
    inv.calculate_totals()
    return inv


@pytest.mark.sandbox
@pytest.mark.django_db
class TestSdiSandbox:
    """Tests that hit the real SDI sandbox. Run manually with `-m sandbox`."""

    def test_generate_xml_is_well_formed(self, sandbox_invoice):
        """Verify XML generation produces valid XML."""
        from apps.sdi.services.xml_generator import InvoiceXmlGenerator

        gen = InvoiceXmlGenerator()
        xml = gen.generate(sandbox_invoice)

        assert xml.startswith("<?xml")
        assert "FatturaElettronica" in xml
        assert "RF01" in xml  # from company_settings fixture
        assert "Test SRL" in xml or "Sandbox Test SRL" in xml
        assert "SANDBOX-0001/2026" in xml

    def test_send_to_sandbox_returns_uuid(self, sandbox_invoice):
        """Send XML to sandbox and verify UUID assignment.

        Requires OPENAPI_SDI_TOKEN to be a valid sandbox token.
        Skip if token is not set.
        """
        if not settings.OPENAPI_SDI_TOKEN:
            pytest.skip("OPENAPI_SDI_TOKEN not configured — set it to run sandbox tests")

        from apps.sdi.services.openapi_client import OpenApiSdiClient
        from apps.sdi.services.xml_generator import InvoiceXmlGenerator

        gen = InvoiceXmlGenerator()
        xml = gen.generate(sandbox_invoice)

        client = OpenApiSdiClient()
        result = client.send_invoice(xml)

        assert "uuid" in result, f"Expected 'uuid' in response, got: {result}"
        assert result["uuid"], "UUID should not be empty"

    def test_check_status_after_send(self, sandbox_invoice):
        """Send to sandbox, then poll status.

        Requires OPENAPI_SDI_TOKEN.
        """
        if not settings.OPENAPI_SDI_TOKEN:
            pytest.skip("OPENAPI_SDI_TOKEN not configured — set it to run sandbox tests")

        from apps.sdi.services.openapi_client import OpenApiSdiClient
        from apps.sdi.services.xml_generator import InvoiceXmlGenerator

        gen = InvoiceXmlGenerator()
        xml = gen.generate(sandbox_invoice)

        client = OpenApiSdiClient()
        send_result = client.send_invoice(xml)
        uuid = send_result["uuid"]

        status_result = client.get_invoice_status(uuid)
        assert "uuid" in status_result or "status" in status_result

    def test_full_celery_task_against_sandbox(self, sandbox_invoice):
        """Run the batch Celery task synchronously against sandbox.

        Requires OPENAPI_SDI_TOKEN.
        """
        if not settings.OPENAPI_SDI_TOKEN:
            pytest.skip("OPENAPI_SDI_TOKEN not configured — set it to run sandbox tests")

        # Move invoice to outbox state (required by batch task)
        sandbox_invoice.status = "outbox"
        sandbox_invoice.sdi_status = "Pending"
        sandbox_invoice.save(update_fields=["status", "sdi_status"])

        from apps.sdi.tasks import batch_send_and_sync

        result = batch_send_and_sync()

        assert result["sent"] == 1

        sandbox_invoice.refresh_from_db()
        assert sandbox_invoice.sdi_uuid
        assert sandbox_invoice.sdi_sent_at is not None
