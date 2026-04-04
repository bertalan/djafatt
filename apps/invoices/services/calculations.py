"""Invoice totals calculation service.

Pure business logic — no request/form/template dependencies.
All amounts in cents (integer). No float/Decimal in intermediate calculations.
"""
from dataclasses import dataclass


@dataclass
class CalculationResult:
    """Result of invoice totals calculation."""

    total_net: int = 0
    total_vat: int = 0
    total_gross: int = 0
    withholding_tax_amount: int = 0
    stamp_duty_applied: bool = False
    stamp_duty_amount: int = 0


class TotalsCalculationService:
    """Calculate invoice totals from lines."""

    # Stamp duty threshold: €77.47 = 7747 cents
    STAMP_DUTY_THRESHOLD = 7747
    STAMP_DUTY_AMOUNT = 200  # €2.00

    @classmethod
    def calculate(cls, invoice) -> CalculationResult:
        """Recalculate all totals and persist to invoice."""
        lines = invoice.lines.select_related("vat_rate").all()
        result = cls._compute(lines, invoice)
        cls._persist(invoice, result)
        return result

    @classmethod
    def compute_preview(cls, lines, invoice) -> CalculationResult:
        """Compute totals without persisting (for live HTMX preview)."""
        return cls._compute(lines, invoice)

    @classmethod
    def _compute(cls, lines, invoice) -> CalculationResult:
        # 1. Net total = sum of line totals
        total_net = sum(line.total for line in lines)

        # 2. VAT total = sum per rate
        total_vat = 0
        exempt_total = 0
        for line in lines:
            if line.vat_rate and line.vat_rate.percent > 0:
                total_vat += round(line.total * line.vat_rate.percent / 100)
            if line.vat_rate and line.vat_rate.nature:
                exempt_total += line.total

        # 3. Withholding tax
        withholding_amount = 0
        if invoice.withholding_tax_enabled and invoice.withholding_tax_percent > 0:
            withholding_amount = round(total_net * invoice.withholding_tax_percent / 100)

        # 4. Stamp duty (user-controlled checkbox)
        stamp_duty_applied = getattr(invoice, 'stamp_duty_applied', False)
        stamp_duty_amount = cls.STAMP_DUTY_AMOUNT if stamp_duty_applied else 0

        # 5. Gross total
        if invoice.split_payment:
            # Split payment: VAT not charged to client
            total_gross = total_net - withholding_amount + stamp_duty_amount
        else:
            total_gross = total_net + total_vat - withholding_amount + stamp_duty_amount

        return CalculationResult(
            total_net=total_net,
            total_vat=total_vat,
            total_gross=total_gross,
            withholding_tax_amount=withholding_amount,
            stamp_duty_applied=stamp_duty_applied,
            stamp_duty_amount=stamp_duty_amount,
        )

    @classmethod
    def _persist(cls, invoice, result: CalculationResult):
        invoice.total_net = result.total_net
        invoice.total_vat = result.total_vat
        invoice.total_gross = result.total_gross
        invoice.withholding_tax_amount = result.withholding_tax_amount
        invoice.stamp_duty_amount = result.stamp_duty_amount
        invoice.save(update_fields=[
            "total_net", "total_vat", "total_gross",
            "withholding_tax_amount",
            "stamp_duty_amount",
        ])
