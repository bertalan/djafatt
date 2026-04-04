"""TDD tests for models — RED phase.

These tests define expected model behavior. Implementation must make them pass.
"""
import pytest
from decimal import Decimal

from apps.common.exceptions import SystemRecordError


@pytest.mark.django_db
class TestContact:
    def test_is_italian_true(self, italian_contact):
        assert italian_contact.is_italian() is True

    def test_is_italian_false(self, foreign_contact):
        assert foreign_contact.is_italian() is False

    def test_is_eu_true(self, eu_contact):
        assert eu_contact.is_eu() is True

    def test_is_eu_false_for_us(self, foreign_contact):
        assert foreign_contact.is_eu() is False

    def test_is_eu_true_for_italy(self, italian_contact):
        assert italian_contact.is_eu() is True

    def test_sdi_code_italian(self, italian_contact):
        assert italian_contact.get_sdi_code_for_xml() == "ABC1234"

    def test_sdi_code_italian_no_sdi(self, db):
        from apps.contacts.models import Contact

        c = Contact.objects.create(name="No SDI", country_code="IT", is_customer=True)
        assert c.get_sdi_code_for_xml() == "0000000"

    def test_sdi_code_foreign(self, foreign_contact):
        assert foreign_contact.get_sdi_code_for_xml() == "XXXXXXX"

    def test_postal_code_foreign(self, foreign_contact):
        assert foreign_contact.get_postal_code_for_xml() == "00000"

    def test_province_foreign(self, foreign_contact):
        assert foreign_contact.get_province_for_xml() == "EE"

    def test_vat_number_clean_with_prefix(self, italian_contact):
        assert italian_contact.get_vat_number_clean() == "12345678901"

    def test_vat_number_clean_without_prefix(self, db):
        from apps.contacts.models import Contact

        c = Contact.objects.create(name="No Prefix", vat_number="12345678901", country_code="IT")
        assert c.get_vat_number_clean() == "12345678901"


@pytest.mark.django_db
class TestVatRate:
    def test_system_not_deletable(self, vat_rate_system):
        with pytest.raises(SystemRecordError):
            vat_rate_system.delete()

    def test_regular_deletable(self, vat_rate_22):
        vat_rate_22.delete()

    def test_in_use_not_deletable(self, invoice_line):
        with pytest.raises(SystemRecordError):
            invoice_line.vat_rate.delete()


@pytest.mark.django_db
class TestSequence:
    def test_next_number_first(self, sequence_sales):
        assert sequence_sales.get_next_number(2026) == 1

    def test_next_number_increments(self, invoice, sequence_sales):
        assert sequence_sales.get_next_number(2026) == 2

    def test_formatted_number(self, sequence_sales):
        result = sequence_sales.get_formatted_number(2026)
        assert result == "0001/2026"

    def test_system_not_deletable(self, sequence_system):
        with pytest.raises(SystemRecordError):
            sequence_system.delete()


@pytest.mark.django_db
class TestInvoiceProxyModels:
    def test_sales_manager_filters(self, invoice, purchase_invoice):
        from apps.invoices.models import Invoice

        sales = Invoice.objects.all()
        assert invoice in sales
        assert purchase_invoice not in sales

    def test_purchase_manager_filters(self, invoice, purchase_invoice):
        from apps.invoices.models import PurchaseInvoice

        purchases = PurchaseInvoice.objects.all()
        assert purchase_invoice in purchases
        assert invoice not in purchases

    def test_all_types_returns_all(self, invoice, purchase_invoice):
        from apps.invoices.models import Invoice

        all_invoices = Invoice.all_types.all()
        assert invoice in all_invoices
        assert purchase_invoice in all_invoices

    def test_purchase_sets_type_on_save(self, purchase_invoice):
        assert purchase_invoice.type == "purchase"


@pytest.mark.django_db
class TestProduct:
    def test_price_in_cents(self, product):
        assert product.price == 10000  # €100.00
        assert isinstance(product.price, int)


@pytest.mark.django_db
class TestPaymentStatus:
    """Invoice.payment_status property returns 'paid', 'partial', or 'unpaid'."""

    def test_unpaid_by_default(self, invoice):
        assert invoice.payment_status == "unpaid"

    def test_fully_paid(self, invoice):
        from apps.invoices.models import PaymentDue
        from datetime import date

        invoice.total_gross = 10000
        invoice.save(update_fields=["total_gross"])
        PaymentDue.objects.create(
            invoice=invoice, due_date=date(2026, 2, 1), amount=10000,
            paid=True, paid_at=date(2026, 2, 1),
        )
        assert invoice.payment_status == "paid"

    def test_partially_paid(self, invoice):
        from apps.invoices.models import PaymentDue
        from datetime import date

        invoice.total_gross = 10000
        invoice.save(update_fields=["total_gross"])
        PaymentDue.objects.create(
            invoice=invoice, due_date=date(2026, 2, 1), amount=5000,
            paid=True, paid_at=date(2026, 2, 1),
        )
        assert invoice.payment_status == "partial"

    def test_uses_annotation_when_available(self, invoice):
        invoice.total_gross = 10000
        invoice._paid_total = 5000
        assert invoice.payment_status == "partial"
        invoice._paid_total = 10000
        assert invoice.payment_status == "paid"
        invoice._paid_total = 0
        assert invoice.payment_status == "unpaid"
