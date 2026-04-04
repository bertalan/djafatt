"""Tests for invoice date fix, payment defaults, and duplicate invoice."""
from datetime import date
from decimal import Decimal

import pytest

from apps.contacts.models import Contact
from apps.invoices.models import Invoice, InvoiceLine, Sequence, VatRate


@pytest.mark.django_db
class TestInvoiceDatePreservation:
    """Verify date is preserved during invoice edit (was being lost)."""

    def test_date_preserved_on_edit(self, auth_client, invoice, invoice_line):
        """Editing an invoice must preserve the date field."""
        original_date = invoice.date
        response = auth_client.post(
            f"/invoices/{invoice.pk}/edit/",
            {
                "sequence": invoice.sequence_id,
                "date": "2026-01-15",
                "contact": invoice.contact_id,
                "document_type": "TD01",
                "vat_payability": "I",
                "notes": "",
                "payment_method": "",
                "payment_terms": "",
                "bank_name": "",
                "bank_iban": "",
                "withholding_tax_percent": "0",
                # formset management
                "lines-TOTAL_FORMS": "1",
                "lines-INITIAL_FORMS": "1",
                "lines-MIN_NUM_FORMS": "0",
                "lines-MAX_NUM_FORMS": "1000",
                f"lines-0-id": invoice_line.pk,
                "lines-0-description": invoice_line.description,
                "lines-0-quantity": "1.00",
                "lines-0-unit_price_display": "100.00",
                "lines-0-vat_rate": invoice_line.vat_rate_id,
                "lines-0-unit_of_measure": "",
                "dues-TOTAL_FORMS": "0",
                "dues-INITIAL_FORMS": "0",
                "dues-MIN_NUM_FORMS": "0",
                "dues-MAX_NUM_FORMS": "1000",
            },
        )
        assert response.status_code == 302
        invoice.refresh_from_db()
        assert invoice.date == original_date

    def test_date_field_uses_iso_format(self):
        """InvoiceForm date widget must use ISO format for HTML5 input[type=date]."""
        from apps.invoices.forms import InvoiceForm

        form = InvoiceForm()
        widget = form.fields["date"].widget
        assert widget.format == "%Y-%m-%d"


@pytest.mark.django_db
class TestContactPaymentDefaults:
    """Payment defaults on Contact model and prefill in InvoiceForm."""

    def test_contact_has_payment_default_fields(self):
        """Contact model must have payment default fields."""
        contact = Contact(
            name="Test",
            default_payment_method="MP05",
            default_payment_terms="TP02",
            default_bank_name="Banca Test",
            default_bank_iban="IT60X0542811101000000123456",
        )
        assert contact.default_payment_method == "MP05"
        assert contact.default_payment_terms == "TP02"
        assert contact.default_bank_name == "Banca Test"
        assert contact.default_bank_iban == "IT60X0542811101000000123456"

    def test_invoice_form_prefills_from_constance(self, company_settings):
        """New invoice form pre-fills payment fields from Constance defaults."""
        from constance import config

        from apps.invoices.forms import InvoiceForm

        config.DEFAULT_PAYMENT_METHOD = "MP05"
        config.DEFAULT_PAYMENT_TERMS = "TP02"
        config.COMPANY_BANK_NAME = "UniCredit"
        config.COMPANY_BANK_IBAN = "IT60X0542811101000000123456"

        # Need at least one sequence for the form to work
        Sequence.objects.create(name="Test", type="sales", pattern="{SEQ}/{ANNO}")
        form = InvoiceForm()
        assert form.initial["payment_method"] == "MP05"
        assert form.initial["payment_terms"] == "TP02"
        assert form.initial["bank_name"] == "UniCredit"
        assert form.initial["bank_iban"] == "IT60X0542811101000000123456"

    def test_contact_defaults_endpoint(self, auth_client, italian_contact):
        """HTMX endpoint returns contact payment defaults as HX-Trigger JSON."""
        italian_contact.default_payment_method = "MP08"
        italian_contact.default_payment_terms = "TP01"
        italian_contact.default_bank_name = "Test Bank"
        italian_contact.default_bank_iban = "IT123"
        italian_contact.save()

        response = auth_client.get(
            f"/invoices/contact-defaults/{italian_contact.pk}/"
        )
        assert response.status_code == 200
        import json
        trigger = json.loads(response["HX-Trigger"])
        assert trigger["contactPaymentFill"]["payment_method"] == "MP08"
        assert trigger["contactPaymentFill"]["payment_terms"] == "TP01"
        assert trigger["contactPaymentFill"]["bank_name"] == "Test Bank"
        assert trigger["contactPaymentFill"]["bank_iban"] == "IT123"


@pytest.mark.django_db
class TestDuplicateInvoice:
    """Duplicate invoice feature — creates new invoice with same content."""

    def test_duplicate_sales_invoice(self, auth_client, invoice, invoice_line):
        """Duplicating a sales invoice creates a new draft with same lines."""
        response = auth_client.post(f"/invoices/{invoice.pk}/duplicate/")
        assert response.status_code == 302

        new_invoice = Invoice.all_types.exclude(pk=invoice.pk).latest("pk")
        assert new_invoice.type == "sales"
        assert new_invoice.status == "draft"
        assert new_invoice.date == date.today()
        assert new_invoice.contact == invoice.contact
        assert new_invoice.document_type == invoice.document_type
        assert new_invoice.number != invoice.number
        assert new_invoice.sdi_status == ""
        assert new_invoice.sdi_uuid == ""
        # Lines should be copied
        assert new_invoice.lines.count() == 1
        new_line = new_invoice.lines.first()
        assert new_line.description == invoice_line.description
        assert new_line.unit_price == invoice_line.unit_price
        assert new_line.quantity == invoice_line.quantity

    def test_duplicate_redirects_to_edit(self, auth_client, invoice, invoice_line):
        """Duplicate should redirect to edit page of the new invoice."""
        response = auth_client.post(f"/invoices/{invoice.pk}/duplicate/")
        new_invoice = Invoice.all_types.exclude(pk=invoice.pk).latest("pk")
        assert response.url == f"/invoices/{new_invoice.pk}/edit/"

    def test_duplicate_requires_login(self, invoice):
        """Unauthenticated user cannot duplicate an invoice."""
        from django.test import Client
        client = Client()
        response = client.post(f"/invoices/{invoice.pk}/duplicate/")
        assert response.status_code == 302
        assert "/login/" in response.url

    def test_duplicate_purchase_invoice(self, auth_client, purchase_invoice):
        """Duplicating a purchase invoice works correctly."""
        from apps.invoices.models import PurchaseInvoice

        # Add a line to the purchase invoice
        vat = VatRate.objects.create(name="IVA 22%", percent=Decimal("22.00"))
        InvoiceLine.objects.create(
            invoice=purchase_invoice,
            description="Purchase item",
            quantity=Decimal("2.00"),
            unit_price=5000,
            vat_rate=vat,
            total=10000,
        )

        response = auth_client.post(
            f"/purchase-invoices/{purchase_invoice.pk}/duplicate/"
        )
        assert response.status_code == 302
        new = PurchaseInvoice.objects.exclude(pk=purchase_invoice.pk).latest("pk")
        assert new.type == "purchase"
        assert new.status == "draft"
        assert new.lines.count() == 1

    def test_duplicate_only_post(self, auth_client, invoice):
        """GET request to duplicate URL should return 405."""
        response = auth_client.get(f"/invoices/{invoice.pk}/duplicate/")
        assert response.status_code == 405


@pytest.mark.django_db
class TestInvoiceNumberEditing:
    """Admin can edit the invoice number in the edit form."""

    def test_number_field_in_form(self):
        """InvoiceForm includes 'number' in its fields."""
        from apps.invoices.forms import InvoiceForm

        form = InvoiceForm()
        assert "number" in form.fields

    def test_number_field_not_required(self):
        """Number is not required (auto-generated on create)."""
        from apps.invoices.forms import InvoiceForm

        form = InvoiceForm()
        assert not form.fields["number"].required

    def test_edit_invoice_number(self, auth_client, invoice, invoice_line):
        """Editing the number field via POST updates the invoice."""
        response = auth_client.post(
            f"/invoices/{invoice.pk}/edit/",
            {
                "number": "CUSTOM/2026",
                "sequence": invoice.sequence_id,
                "date": "2026-01-15",
                "contact": invoice.contact_id,
                "document_type": "TD01",
                "vat_payability": "I",
                "notes": "",
                "payment_method": "",
                "payment_terms": "",
                "bank_name": "",
                "bank_iban": "",
                "withholding_tax_percent": "0",
                "lines-TOTAL_FORMS": "1",
                "lines-INITIAL_FORMS": "1",
                "lines-MIN_NUM_FORMS": "0",
                "lines-MAX_NUM_FORMS": "1000",
                f"lines-0-id": invoice_line.pk,
                "lines-0-description": invoice_line.description,
                "lines-0-quantity": "1.00",
                "lines-0-unit_price_display": "100.00",
                "lines-0-vat_rate": invoice_line.vat_rate_id,
                "lines-0-unit_of_measure": "",
                "dues-TOTAL_FORMS": "0",
                "dues-INITIAL_FORMS": "0",
                "dues-MIN_NUM_FORMS": "0",
                "dues-MAX_NUM_FORMS": "1000",
            },
        )
        assert response.status_code == 302
        invoice.refresh_from_db()
        assert invoice.number == "CUSTOM/2026"

    def test_number_shown_only_in_edit(self, auth_client, sequence_sales):
        """Number field is rendered only when editing an existing invoice."""
        # Create page — number field should NOT appear
        response = auth_client.get("/invoices/create/")
        assert response.status_code == 200
        content = response.content.decode()
        assert 'name="number"' not in content

    def test_number_shown_in_edit_template(self, auth_client, invoice, invoice_line):
        """Edit page renders the number input."""
        response = auth_client.get(f"/invoices/{invoice.pk}/edit/")
        assert response.status_code == 200
        content = response.content.decode()
        assert 'name="number"' in content


@pytest.mark.django_db
class TestInvoicePdfPreview:
    """PDF preview generation from invoice edit screen."""

    def test_preview_returns_pdf(self, auth_client, invoice, invoice_line, company_settings):
        """Preview endpoint returns a PDF response."""
        response = auth_client.get(f"/invoices/{invoice.pk}/preview/")
        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"
        assert "inline" in response["Content-Disposition"]

    def test_preview_requires_login(self, invoice):
        """Unauthenticated user cannot access preview."""
        from django.test import Client

        client = Client()
        response = client.get(f"/invoices/{invoice.pk}/preview/")
        assert response.status_code == 302
        assert "/login/" in response.url

    def test_preview_purchase_invoice(self, auth_client, purchase_invoice, company_settings):
        """Preview works for purchase invoices too."""
        response = auth_client.get(f"/purchase-invoices/{purchase_invoice.pk}/preview/")
        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"

    def test_preview_button_in_edit_template(self, auth_client, invoice, invoice_line):
        """Edit page shows the preview button."""
        response = auth_client.get(f"/invoices/{invoice.pk}/edit/")
        content = response.content.decode()
        assert "Anteprima PDF" in content
        assert f"/invoices/{invoice.pk}/preview/" in content

    def test_preview_404_for_missing_invoice(self, auth_client):
        """Preview returns 404 for non-existent invoice."""
        response = auth_client.get("/invoices/99999/preview/")
        assert response.status_code == 404
