"""Tests for PaymentDue (rate/scadenze) feature — T33."""
from datetime import date, timedelta
from decimal import Decimal

import pytest

from apps.invoices.models import Invoice, PaymentDue


@pytest.mark.django_db
class TestPaymentDueModel:
    """PaymentDue model behaviour."""

    def test_create_payment_due(self, invoice):
        due = PaymentDue.objects.create(
            invoice=invoice,
            due_date=date(2026, 2, 15),
            amount=10000,
            payment_method="MP05",
        )
        assert due.amount == 10000
        assert due.paid is False
        assert due.paid_at is None

    def test_is_overdue_true(self, invoice):
        due = PaymentDue.objects.create(
            invoice=invoice,
            due_date=date(2020, 1, 1),
            amount=5000,
        )
        assert due.is_overdue is True

    def test_is_overdue_false_when_paid(self, invoice):
        due = PaymentDue.objects.create(
            invoice=invoice,
            due_date=date(2020, 1, 1),
            amount=5000,
            paid=True,
            paid_at=date(2020, 1, 1),
        )
        assert due.is_overdue is False

    def test_is_overdue_false_future(self, invoice):
        due = PaymentDue.objects.create(
            invoice=invoice,
            due_date=date.today() + timedelta(days=30),
            amount=5000,
        )
        assert due.is_overdue is False

    def test_ordering_by_due_date(self, invoice):
        d1 = PaymentDue.objects.create(invoice=invoice, due_date=date(2026, 3, 1), amount=100)
        d2 = PaymentDue.objects.create(invoice=invoice, due_date=date(2026, 1, 1), amount=200)
        d3 = PaymentDue.objects.create(invoice=invoice, due_date=date(2026, 2, 1), amount=300)
        dues = list(invoice.payment_dues.all())
        assert dues == [d2, d3, d1]

    def test_cascade_delete(self, invoice):
        PaymentDue.objects.create(invoice=invoice, due_date=date(2026, 1, 1), amount=100)
        assert PaymentDue.objects.count() == 1
        invoice.delete()
        assert PaymentDue.objects.count() == 0

    def test_str_representation(self, invoice):
        due = PaymentDue.objects.create(
            invoice=invoice, due_date=date(2026, 2, 15), amount=12345,
        )
        assert "○" in str(due)
        assert "2026-02-15" in str(due)
        due.paid = True
        assert "✓" in str(due)


@pytest.mark.django_db
class TestPaymentDueFormSet:
    """PaymentDue inline formset on invoice create/edit."""

    def _base_post_data(self, invoice, invoice_line):
        return {
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
        }

    def test_save_invoice_with_dues(self, auth_client, invoice, invoice_line):
        """Editing an invoice can create payment dues."""
        data = self._base_post_data(invoice, invoice_line)
        data.update({
            "dues-TOTAL_FORMS": "2",
            "dues-INITIAL_FORMS": "0",
            "dues-MIN_NUM_FORMS": "0",
            "dues-MAX_NUM_FORMS": "1000",
            "dues-0-due_date": "2026-02-15",
            "dues-0-amount_display": "50.00",
            "dues-0-payment_method": "MP05",
            "dues-0-paid": "",
            "dues-0-paid_at": "",
            "dues-1-due_date": "2026-03-15",
            "dues-1-amount_display": "72.00",
            "dues-1-payment_method": "MP08",
            "dues-1-paid": "on",
            "dues-1-paid_at": "2026-03-15",
        })
        response = auth_client.post(f"/invoices/{invoice.pk}/edit/", data)
        assert response.status_code == 302
        dues = list(invoice.payment_dues.all())
        assert len(dues) == 2
        assert dues[0].amount == 5000
        assert dues[0].payment_method == "MP05"
        assert dues[0].paid is False
        assert dues[1].amount == 7200
        assert dues[1].paid is True
        assert dues[1].paid_at == date(2026, 3, 15)

    def test_edit_with_zero_dues(self, auth_client, invoice, invoice_line):
        """Editing with no dues still works."""
        data = self._base_post_data(invoice, invoice_line)
        data.update({
            "dues-TOTAL_FORMS": "0",
            "dues-INITIAL_FORMS": "0",
            "dues-MIN_NUM_FORMS": "0",
            "dues-MAX_NUM_FORMS": "1000",
        })
        response = auth_client.post(f"/invoices/{invoice.pk}/edit/", data)
        assert response.status_code == 302
        assert invoice.payment_dues.count() == 0

    def test_delete_existing_due(self, auth_client, invoice, invoice_line):
        """Can delete an existing payment due via formset DELETE."""
        due = PaymentDue.objects.create(
            invoice=invoice, due_date=date(2026, 2, 15), amount=5000,
        )
        data = self._base_post_data(invoice, invoice_line)
        data.update({
            "dues-TOTAL_FORMS": "1",
            "dues-INITIAL_FORMS": "1",
            "dues-MIN_NUM_FORMS": "0",
            "dues-MAX_NUM_FORMS": "1000",
            "dues-0-id": due.pk,
            "dues-0-due_date": "2026-02-15",
            "dues-0-amount_display": "50.00",
            "dues-0-payment_method": "",
            "dues-0-paid": "",
            "dues-0-paid_at": "",
            "dues-0-DELETE": "on",
        })
        response = auth_client.post(f"/invoices/{invoice.pk}/edit/", data)
        assert response.status_code == 302
        assert invoice.payment_dues.count() == 0

    def test_stamp_duty_checkbox_on(self, auth_client, invoice, invoice_line):
        """Submitting with stamp_duty_applied=on sets the field and adds €2."""
        data = self._base_post_data(invoice, invoice_line)
        data.update({
            "stamp_duty_applied": "on",
            "dues-TOTAL_FORMS": "0",
            "dues-INITIAL_FORMS": "0",
            "dues-MIN_NUM_FORMS": "0",
            "dues-MAX_NUM_FORMS": "1000",
        })
        response = auth_client.post(f"/invoices/{invoice.pk}/edit/", data)
        assert response.status_code == 302
        invoice.refresh_from_db()
        assert invoice.stamp_duty_applied is True
        assert invoice.stamp_duty_amount == 200
        assert invoice.total_gross == 12400  # 10000 net + 2200 vat + 200 stamp

    def test_stamp_duty_checkbox_off(self, auth_client, invoice, invoice_line):
        """Submitting without stamp_duty_applied keeps it off."""
        invoice.stamp_duty_applied = True
        invoice.save(update_fields=["stamp_duty_applied"])
        data = self._base_post_data(invoice, invoice_line)
        data.update({
            # stamp_duty_applied NOT in POST → checkbox unchecked
            "dues-TOTAL_FORMS": "0",
            "dues-INITIAL_FORMS": "0",
            "dues-MIN_NUM_FORMS": "0",
            "dues-MAX_NUM_FORMS": "1000",
        })
        response = auth_client.post(f"/invoices/{invoice.pk}/edit/", data)
        assert response.status_code == 302
        invoice.refresh_from_db()
        assert invoice.stamp_duty_applied is False
        assert invoice.stamp_duty_amount == 0


@pytest.mark.django_db
class TestPaymentDueHtmx:
    """HTMX add/remove endpoints for payment due rows."""

    def test_add_due_returns_html(self, auth_client):
        response = auth_client.post(
            "/invoices/dues/add/",
            {"next_index": "0"},
            HTTP_HX_REQUEST="true",
        )
        assert response.status_code == 200
        content = response.content.decode()
        assert "dues-0-due_date" in content
        assert "dues-0-amount_display" in content

    def test_add_due_uses_index(self, auth_client):
        response = auth_client.post(
            "/invoices/dues/add/",
            {"next_index": "3"},
            HTTP_HX_REQUEST="true",
        )
        content = response.content.decode()
        assert "dues-3-due_date" in content

    def test_remove_due_returns_empty(self, auth_client):
        response = auth_client.delete(
            "/invoices/dues/5/remove/",
            HTTP_HX_REQUEST="true",
        )
        assert response.status_code == 200
        assert response.content == b""

    def test_add_due_copies_last_values(self, auth_client):
        """Adding a new due row pre-fills from last row values."""
        response = auth_client.post(
            "/invoices/dues/add/",
            {
                "next_index": "1",
                "last_due_date": "2026-03-15",
                "last_amount": "100.00",
                "last_method": "MP05",
            },
            HTTP_HX_REQUEST="true",
        )
        assert response.status_code == 200
        content = response.content.decode()
        assert "dues-1-due_date" in content
        assert "2026-03-15" in content
        assert "100.00" in content

    def test_add_due_without_last_values(self, auth_client):
        """Without last values, fields are empty."""
        response = auth_client.post(
            "/invoices/dues/add/",
            {"next_index": "0"},
            HTTP_HX_REQUEST="true",
        )
        content = response.content.decode()
        assert "dues-0-due_date" in content
        # No prefilled date value
        assert 'value="2026' not in content


@pytest.mark.django_db
class TestPaymentDueOnCreate:
    """Payment dues on invoice creation."""

    def test_create_invoice_with_dues(self, auth_client, italian_contact, sequence_sales, vat_rate_22):
        data = {
            "sequence": sequence_sales.pk,
            "date": "2026-06-01",
            "contact": italian_contact.pk,
            "document_type": "TD01",
            "vat_payability": "I",
            "notes": "",
            "payment_method": "MP05",
            "payment_terms": "TP01",
            "bank_name": "",
            "bank_iban": "",
            "withholding_tax_percent": "0",
            "lines-TOTAL_FORMS": "1",
            "lines-INITIAL_FORMS": "0",
            "lines-MIN_NUM_FORMS": "0",
            "lines-MAX_NUM_FORMS": "1000",
            "lines-0-description": "Test Service",
            "lines-0-quantity": "1.00",
            "lines-0-unit_price_display": "200.00",
            "lines-0-vat_rate": vat_rate_22.pk,
            "lines-0-unit_of_measure": "",
            "dues-TOTAL_FORMS": "1",
            "dues-INITIAL_FORMS": "0",
            "dues-MIN_NUM_FORMS": "0",
            "dues-MAX_NUM_FORMS": "1000",
            "dues-0-due_date": "2026-07-01",
            "dues-0-amount_display": "244.00",
            "dues-0-payment_method": "MP05",
            "dues-0-paid": "",
            "dues-0-paid_at": "",
        }
        response = auth_client.post("/invoices/create/", data)
        assert response.status_code == 302
        inv = Invoice.all_types.last()
        assert inv.payment_dues.count() == 1
        due = inv.payment_dues.first()
        assert due.amount == 24400
        assert due.due_date == date(2026, 7, 1)
        assert due.payment_method == "MP05"


@pytest.mark.django_db
class TestPaymentDueDuplicate:
    """Payment dues are copied (as unpaid) when duplicating an invoice."""

    def test_duplicate_copies_dues_as_unpaid(self, auth_client, invoice, invoice_line):
        PaymentDue.objects.create(
            invoice=invoice,
            due_date=date(2026, 2, 15),
            amount=5000,
            payment_method="MP05",
            paid=True,
            paid_at=date(2026, 2, 15),
        )
        PaymentDue.objects.create(
            invoice=invoice,
            due_date=date(2026, 3, 15),
            amount=7200,
            payment_method="MP08",
        )
        response = auth_client.post(f"/invoices/{invoice.pk}/duplicate/")
        assert response.status_code == 302
        new_invoice = Invoice.all_types.exclude(pk=invoice.pk).last()
        new_dues = list(new_invoice.payment_dues.all())
        assert len(new_dues) == 2
        # All duplicated dues must be unpaid
        assert all(not d.paid for d in new_dues)
        assert all(d.paid_at is None for d in new_dues)
        # Amounts and methods preserved
        assert new_dues[0].amount == 5000
        assert new_dues[1].amount == 7200
