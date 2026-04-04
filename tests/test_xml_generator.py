"""TDD tests for XML generator — RED phase.

Tests for InvoiceXmlGenerator that produces FatturaPA v1.2.2 XML.
"""
from datetime import date
from decimal import Decimal

import pytest

from apps.invoices.models import PaymentDue


@pytest.mark.django_db
class TestXmlGenerator:
    def test_generates_xml_string(self, invoice, invoice_line, company_settings):
        """Generator returns a non-empty XML string."""
        from apps.sdi.services.xml_generator import InvoiceXmlGenerator

        xml = InvoiceXmlGenerator().generate(invoice)
        assert isinstance(xml, str)
        assert len(xml) > 0
        assert "<?xml" in xml or "<FatturaElettronica" in xml

    def test_italian_client_sdi_code(self, invoice, invoice_line, company_settings):
        """Italian client uses actual SDI code (not XXXXXXX)."""
        from apps.sdi.services.xml_generator import InvoiceXmlGenerator

        xml = InvoiceXmlGenerator().generate(invoice)
        assert "ABC1234" in xml
        assert "XXXXXXX" not in xml

    def test_foreign_client_sdi_code(self, db, foreign_contact, sequence_sales,
                                      vat_rate_22, company_settings):
        """Foreign client gets XXXXXXX as SDI code."""
        from apps.invoices.models import Invoice, InvoiceLine
        from apps.sdi.services.xml_generator import InvoiceXmlGenerator

        inv = Invoice.all_types.create(
            type="sales", number="0002/2026", sequential_number=2,
            date=date(2026, 1, 15), contact=foreign_contact,
            sequence=sequence_sales, document_type="TD01",
        )
        InvoiceLine.objects.create(
            invoice=inv, description="Svc", quantity=1,
            unit_price=10000, vat_rate=vat_rate_22, total=10000,
        )
        xml = InvoiceXmlGenerator().generate(inv)
        assert "XXXXXXX" in xml

    def test_eu_client_vat_info(self, db, eu_contact, sequence_sales,
                                 vat_rate_22, company_settings):
        """EU client includes IdFiscaleIVA with correct country code."""
        from apps.invoices.models import Invoice, InvoiceLine
        from apps.sdi.services.xml_generator import InvoiceXmlGenerator

        inv = Invoice.all_types.create(
            type="sales", number="0003/2026", sequential_number=3,
            date=date(2026, 1, 15), contact=eu_contact,
            sequence=sequence_sales, document_type="TD01",
        )
        InvoiceLine.objects.create(
            invoice=inv, description="Svc", quantity=1,
            unit_price=10000, vat_rate=vat_rate_22, total=10000,
        )
        xml = InvoiceXmlGenerator().generate(inv)
        assert "DE" in xml

    def test_amounts_two_decimals(self, invoice, invoice_line, company_settings):
        """All monetary amounts formatted with 2 decimal places."""
        from apps.sdi.services.xml_generator import InvoiceXmlGenerator

        xml = InvoiceXmlGenerator().generate(invoice)
        assert "100.00" in xml  # unit_price or total

    def test_cedente_company_data(self, invoice, invoice_line, company_settings):
        """Cedente/Prestatore section contains company data from Constance."""
        from apps.sdi.services.xml_generator import InvoiceXmlGenerator

        xml = InvoiceXmlGenerator().generate(invoice)
        assert "Test SRL" in xml
        assert "01234567890" in xml

    def test_riepilogo_per_aliquota(self, invoice, company_settings, vat_rate_22, vat_rate_10):
        """Riepilogo has one entry per VAT rate."""
        from apps.invoices.models import InvoiceLine
        from apps.sdi.services.xml_generator import InvoiceXmlGenerator

        InvoiceLine.objects.create(
            invoice=invoice, description="A", quantity=1,
            unit_price=10000, vat_rate=vat_rate_22, total=10000,
        )
        InvoiceLine.objects.create(
            invoice=invoice, description="B", quantity=1,
            unit_price=5000, vat_rate=vat_rate_10, total=5000,
        )
        xml = InvoiceXmlGenerator().generate(invoice)
        assert "22.00" in xml
        assert "10.00" in xml

    def test_validation_no_contact_raises(self, db):
        """Invoice without contact raises ValidationError."""
        from apps.common.exceptions import ValidationError
        from apps.sdi.services.xml_generator import InvoiceXmlGenerator

        class FakeInvoice:
            contact = None
            lines = type("M", (), {"exists": lambda self: False})()

        with pytest.raises(ValidationError):
            InvoiceXmlGenerator().generate(FakeInvoice())

    def test_validation_no_lines_raises(self, invoice, company_settings):
        """Invoice without lines raises ValidationError."""
        from apps.common.exceptions import ValidationError
        from apps.sdi.services.xml_generator import InvoiceXmlGenerator

        with pytest.raises(ValidationError):
            InvoiceXmlGenerator().generate(invoice)

    def test_document_type_in_xml(self, invoice, invoice_line, company_settings):
        """Document type (TD01) appears in XML."""
        from apps.sdi.services.xml_generator import InvoiceXmlGenerator

        xml = InvoiceXmlGenerator().generate(invoice)
        assert "TD01" in xml


@pytest.mark.django_db
class TestXmlDatiPagamento:
    """DatiPagamento section in FatturaPA XML."""

    def test_no_dues_no_payment_info_omits_section(
        self, invoice, invoice_line, company_settings,
    ):
        """No payment dues and no payment_terms → DatiPagamento absent."""
        from apps.sdi.services.xml_generator import InvoiceXmlGenerator

        xml = InvoiceXmlGenerator().generate(invoice)
        assert "DatiPagamento" not in xml
        assert "DettaglioPagamento" not in xml

    def test_single_due_produces_dati_pagamento(
        self, invoice, invoice_line, company_settings,
    ):
        """One PaymentDue → one DettaglioPagamento inside DatiPagamento."""
        from apps.sdi.services.xml_generator import InvoiceXmlGenerator

        PaymentDue.objects.create(
            invoice=invoice,
            due_date=date(2026, 2, 15),
            amount=12200,
            payment_method="MP05",
        )
        xml = InvoiceXmlGenerator().generate(invoice)
        assert "<DatiPagamento>" in xml
        assert "<DettaglioPagamento>" in xml
        assert "<ModalitaPagamento>MP05</ModalitaPagamento>" in xml
        assert "<DataScadenzaPagamento>2026-02-15</DataScadenzaPagamento>" in xml
        assert "<ImportoPagamento>122.00</ImportoPagamento>" in xml
        # Default condizioni = TP02 (rata unica)
        assert "<CondizioniPagamento>TP02</CondizioniPagamento>" in xml

    def test_multiple_dues_multiple_dettaglio(
        self, invoice, invoice_line, company_settings,
    ):
        """Two PaymentDue → two DettaglioPagamento blocks."""
        from apps.sdi.services.xml_generator import InvoiceXmlGenerator

        PaymentDue.objects.create(
            invoice=invoice, due_date=date(2026, 2, 15),
            amount=5000, payment_method="MP05",
        )
        PaymentDue.objects.create(
            invoice=invoice, due_date=date(2026, 3, 15),
            amount=7200, payment_method="MP08",
        )
        xml = InvoiceXmlGenerator().generate(invoice)
        assert xml.count("<DettaglioPagamento>") == 2
        assert "<ImportoPagamento>50.00</ImportoPagamento>" in xml
        assert "<ImportoPagamento>72.00</ImportoPagamento>" in xml
        assert "<ModalitaPagamento>MP05</ModalitaPagamento>" in xml
        assert "<ModalitaPagamento>MP08</ModalitaPagamento>" in xml

    def test_payment_terms_from_invoice(
        self, invoice, invoice_line, company_settings,
    ):
        """Invoice.payment_terms propagates to CondizioniPagamento."""
        from apps.sdi.services.xml_generator import InvoiceXmlGenerator

        invoice.payment_terms = "TP01"  # rate
        invoice.save(update_fields=["payment_terms"])
        PaymentDue.objects.create(
            invoice=invoice, due_date=date(2026, 2, 15),
            amount=12200, payment_method="MP05",
        )
        xml = InvoiceXmlGenerator().generate(invoice)
        assert "<CondizioniPagamento>TP01</CondizioniPagamento>" in xml

    def test_bank_info_in_dettaglio(
        self, invoice, invoice_line, company_settings,
    ):
        """bank_name and bank_iban appear in DettaglioPagamento."""
        from apps.sdi.services.xml_generator import InvoiceXmlGenerator

        invoice.bank_name = "Banca Test"
        invoice.bank_iban = "IT60X0542811101000000123456"
        invoice.save(update_fields=["bank_name", "bank_iban"])
        PaymentDue.objects.create(
            invoice=invoice, due_date=date(2026, 2, 15),
            amount=12200, payment_method="MP05",
        )
        xml = InvoiceXmlGenerator().generate(invoice)
        assert "<IstitutoFinanziario>Banca Test</IstitutoFinanziario>" in xml
        assert "<IBAN>IT60X0542811101000000123456</IBAN>" in xml

    def test_fallback_single_dettaglio_no_dues(
        self, invoice, invoice_line, company_settings,
    ):
        """Invoice with payment_method but no dues → single DettaglioPagamento with total_gross."""
        from apps.sdi.services.xml_generator import InvoiceXmlGenerator

        invoice.payment_method = "MP05"
        invoice.save(update_fields=["payment_method"])
        invoice.calculate_totals()
        xml = InvoiceXmlGenerator().generate(invoice)
        assert "<DatiPagamento>" in xml
        assert xml.count("<DettaglioPagamento>") == 1
        # total_gross = 10000 net + 2200 vat = 12200 → 122.00
        assert "<ImportoPagamento>122.00</ImportoPagamento>" in xml

    def test_due_inherits_invoice_payment_method(
        self, invoice, invoice_line, company_settings,
    ):
        """PaymentDue with empty payment_method falls back to invoice."""
        from apps.sdi.services.xml_generator import InvoiceXmlGenerator

        invoice.payment_method = "MP08"
        invoice.save(update_fields=["payment_method"])
        PaymentDue.objects.create(
            invoice=invoice, due_date=date(2026, 2, 15),
            amount=12200, payment_method="",
        )
        xml = InvoiceXmlGenerator().generate(invoice)
        assert "<ModalitaPagamento>MP08</ModalitaPagamento>" in xml
