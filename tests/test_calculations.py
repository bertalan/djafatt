"""TDD tests for TotalsCalculationService — RED phase.

All amounts in cents. No float/Decimal in DB fields.
"""
from datetime import date
from decimal import Decimal

import pytest


@pytest.mark.django_db
class TestTotalsCalculation:
    def test_simple_invoice_totals(self, invoice, vat_rate_22):
        """One line €100 + 22% VAT: net=10000, vat=2200, gross=12200."""
        from apps.invoices.models import InvoiceLine

        InvoiceLine.objects.create(
            invoice=invoice, description="Service", quantity=1,
            unit_price=10000, vat_rate=vat_rate_22, total=10000,
        )
        invoice.refresh_from_db()
        assert invoice.total_net == 10000
        assert invoice.total_vat == 2200
        assert invoice.total_gross == 12200

    def test_multiple_lines_same_rate(self, invoice, vat_rate_22):
        """Two lines €100 each: net=20000, vat=4400, gross=24400."""
        from apps.invoices.models import InvoiceLine

        for _ in range(2):
            InvoiceLine.objects.create(
                invoice=invoice, description="Service", quantity=1,
                unit_price=10000, vat_rate=vat_rate_22, total=10000,
            )
        invoice.refresh_from_db()
        assert invoice.total_net == 20000
        assert invoice.total_vat == 4400
        assert invoice.total_gross == 24400

    def test_different_vat_rates(self, invoice, vat_rate_22, vat_rate_10):
        """Line @22% + line @10%."""
        from apps.invoices.models import InvoiceLine

        InvoiceLine.objects.create(
            invoice=invoice, description="A", quantity=1,
            unit_price=10000, vat_rate=vat_rate_22, total=10000,
        )
        InvoiceLine.objects.create(
            invoice=invoice, description="B", quantity=1,
            unit_price=10000, vat_rate=vat_rate_10, total=10000,
        )
        invoice.refresh_from_db()
        assert invoice.total_net == 20000
        assert invoice.total_vat == 3200  # 2200 + 1000
        assert invoice.total_gross == 23200

    def test_withholding_tax(self, invoice, vat_rate_22):
        """Withholding 20% on net €100: ritenuta=2000, gross=10000+2200-2000=10200."""
        from apps.invoices.models import InvoiceLine

        invoice.withholding_tax_enabled = True
        invoice.withholding_tax_percent = Decimal("20.00")
        invoice.save()

        InvoiceLine.objects.create(
            invoice=invoice, description="Service", quantity=1,
            unit_price=10000, vat_rate=vat_rate_22, total=10000,
        )
        invoice.refresh_from_db()
        assert invoice.withholding_tax_amount == 2000
        assert invoice.total_gross == 10200

    def test_stamp_duty_user_enabled(self, invoice, vat_rate_22):
        """User checks stamp_duty_applied → €2.00 added to gross."""
        from apps.invoices.models import InvoiceLine

        invoice.stamp_duty_applied = True
        invoice.save(update_fields=["stamp_duty_applied"])
        InvoiceLine.objects.create(
            invoice=invoice, description="Service", quantity=1,
            unit_price=10000, vat_rate=vat_rate_22, total=10000,
        )
        invoice.refresh_from_db()
        assert invoice.stamp_duty_applied is True
        assert invoice.stamp_duty_amount == 200
        assert invoice.total_gross == 12400  # 10000 + 2200 + 200

    def test_stamp_duty_default_off(self, invoice, vat_rate_exempt):
        """Default: stamp_duty_applied=False → no stamp duty, even if exempt."""
        from apps.invoices.models import InvoiceLine

        InvoiceLine.objects.create(
            invoice=invoice, description="Exempt service", quantity=1,
            unit_price=10000, vat_rate=vat_rate_exempt, total=10000,
        )
        invoice.refresh_from_db()
        assert invoice.stamp_duty_applied is False
        assert invoice.stamp_duty_amount == 0

    def test_stamp_duty_persist_not_overwritten(self, invoice, vat_rate_22):
        """Recalculation does NOT overwrite user's stamp_duty_applied."""
        from apps.invoices.models import InvoiceLine

        invoice.stamp_duty_applied = True
        invoice.save(update_fields=["stamp_duty_applied"])
        InvoiceLine.objects.create(
            invoice=invoice, description="Service", quantity=1,
            unit_price=10000, vat_rate=vat_rate_22, total=10000,
        )
        invoice.refresh_from_db()
        # stamp_duty_applied must still be True (user-set)
        assert invoice.stamp_duty_applied is True

    def test_split_payment(self, invoice, vat_rate_22):
        """Split payment: VAT calculated but excluded from gross."""
        from apps.invoices.models import InvoiceLine

        invoice.split_payment = True
        invoice.vat_payability = "S"
        invoice.save()

        InvoiceLine.objects.create(
            invoice=invoice, description="Service", quantity=1,
            unit_price=10000, vat_rate=vat_rate_22, total=10000,
        )
        invoice.refresh_from_db()
        assert invoice.total_vat == 2200
        assert invoice.total_gross == 10000  # VAT excluded

    def test_signal_recalculation_on_save(self, invoice, vat_rate_22):
        """Saving a line triggers total recalculation via signal."""
        from apps.invoices.models import InvoiceLine

        line = InvoiceLine.objects.create(
            invoice=invoice, description="Service", quantity=1,
            unit_price=10000, vat_rate=vat_rate_22, total=10000,
        )
        invoice.refresh_from_db()
        assert invoice.total_net == 10000

        line.total = 20000
        line.save()
        invoice.refresh_from_db()
        assert invoice.total_net == 20000

    def test_signal_recalculation_on_delete(self, invoice, vat_rate_22):
        """Deleting a line triggers total recalculation via signal."""
        from apps.invoices.models import InvoiceLine

        line = InvoiceLine.objects.create(
            invoice=invoice, description="Service", quantity=1,
            unit_price=10000, vat_rate=vat_rate_22, total=10000,
        )
        invoice.refresh_from_db()
        assert invoice.total_net == 10000

        line.delete()
        invoice.refresh_from_db()
        assert invoice.total_net == 0
        assert invoice.total_gross == 0

    def test_vat_summary(self, invoice, vat_rate_22, vat_rate_10):
        """VAT summary groups by rate."""
        from apps.invoices.models import InvoiceLine

        InvoiceLine.objects.create(
            invoice=invoice, description="A", quantity=1,
            unit_price=10000, vat_rate=vat_rate_22, total=10000,
        )
        InvoiceLine.objects.create(
            invoice=invoice, description="B", quantity=1,
            unit_price=5000, vat_rate=vat_rate_10, total=5000,
        )
        summary = invoice.get_vat_summary()
        assert len(summary) == 2
        taxables = sorted([s["taxable"] for s in summary])
        assert taxables == [5000, 10000]

    def test_zero_lines_zero_totals(self, invoice):
        """Invoice with no lines has zero totals."""
        invoice.calculate_totals()
        invoice.refresh_from_db()
        assert invoice.total_net == 0
        assert invoice.total_vat == 0
        assert invoice.total_gross == 0
