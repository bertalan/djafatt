from django.db import models

from apps.common.exceptions import SystemRecordError


class InvoiceType(models.TextChoices):
    SALES = "sales", "Vendita"
    PURCHASE = "purchase", "Acquisto"
    SELF_INVOICE = "self_invoice", "Autofattura"


class SdiStatus(models.TextChoices):
    PENDING = "Pending", "In attesa"
    SENT = "Sent", "Inviato"
    DELIVERED = "Delivered", "Consegnato"
    REJECTED = "Rejected", "Rifiutato"
    NOT_SENT = "NS", "Non consegnata (NS)"
    RECEIVED = "RC", "Ricevuta di consegna (RC)"
    UNABLE_TO_DELIVER = "MC", "Mancata consegna (MC)"
    DEADLINE = "DT", "Decorrenza termini (DT)"
    OUTCOME_NEGATIVE = "NE", "Esito negativo (NE)"
    ACCEPTED = "AT", "Accettata (AT)"
    OUTCOME_POSITIVE = "EC", "Esito cedente (EC)"


# SDI statuses that lock the invoice from editing
SDI_LOCKED_STATUSES = frozenset({
    SdiStatus.SENT, SdiStatus.DELIVERED, SdiStatus.RECEIVED,
    SdiStatus.UNABLE_TO_DELIVER, SdiStatus.DEADLINE,
    SdiStatus.ACCEPTED, SdiStatus.OUTCOME_POSITIVE,
})


class VatRate(models.Model):
    """IVA rate (aliquota IVA)."""

    name = models.CharField(max_length=100)
    percent = models.DecimalField(max_digits=5, decimal_places=2)
    description = models.CharField(max_length=255, blank=True, default="")
    nature = models.CharField(max_length=10, blank=True, default="")  # N1-N7
    is_system = models.BooleanField(default=False)

    class Meta:
        ordering = ["-percent", "name"]

    def __str__(self):
        return f"{self.name} ({self.percent}%)"

    def delete(self, *args, **kwargs):
        if self.is_system:
            raise SystemRecordError("Cannot delete system VAT rate")
        if self.invoiceline_set.exists():
            raise SystemRecordError("Cannot delete VAT rate with linked invoice lines")
        return super().delete(*args, **kwargs)


class Sequence(models.Model):
    """Invoice numbering sequence."""

    class SequenceType(models.TextChoices):
        SALES = "sales", "Vendita"
        PURCHASE = "purchase", "Acquisto"
        SELF_INVOICE = "self_invoice", "Autofattura"

    name = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=SequenceType.choices)
    pattern = models.CharField(max_length=100, default="{SEQ}")
    is_system = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def delete(self, *args, **kwargs):
        if self.is_system:
            raise SystemRecordError("Cannot delete system sequence")
        if self.invoice_set.exists():
            raise SystemRecordError("Cannot delete sequence with linked invoices")
        return super().delete(*args, **kwargs)

    def get_next_number(self, year: int | None = None) -> int:
        """Next sequential number for the given year. Uses SELECT FOR UPDATE."""
        from datetime import date

        from django.db import transaction

        if year is None:
            year = date.today().year

        with transaction.atomic():
            last = (
                Invoice.all_types
                .select_for_update()
                .filter(sequence=self, date__year=year)
                .order_by("-sequential_number")
                .values_list("sequential_number", flat=True)
                .first()
            )
        return (last or 0) + 1

    def get_formatted_number(self, year: int | None = None) -> str:
        """Format the next number using the sequence pattern."""
        from datetime import date

        if year is None:
            year = date.today().year
        seq = self.get_next_number(year)
        result = self.pattern.replace("{SEQ}", str(seq).zfill(4))
        result = result.replace("{ANNO}", str(year))
        return result


# --- Invoice model ---

class SalesManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(type=InvoiceType.SALES)


class PurchaseManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(type=InvoiceType.PURCHASE)


class SelfInvoiceManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(type=InvoiceType.SELF_INVOICE)


class Invoice(models.Model):
    """Core invoice model — Single Table Inheritance via proxy models."""

    # --- Identification ---
    type = models.CharField(max_length=20, choices=InvoiceType.choices, default=InvoiceType.SALES)
    number = models.CharField(max_length=50)
    sequential_number = models.IntegerField(null=True, blank=True)
    date = models.DateField()
    document_type = models.CharField(max_length=10, blank=True, default="")  # TD01, TD04, TD17, etc.
    status = models.CharField(max_length=20, default="draft")
    notes = models.TextField(blank=True, default="")

    # --- Relations ---
    contact = models.ForeignKey("contacts.Contact", on_delete=models.PROTECT)
    sequence = models.ForeignKey(Sequence, on_delete=models.PROTECT, null=True, blank=True)

    # --- Totals (cents) ---
    total_net = models.IntegerField(default=0)
    total_vat = models.IntegerField(default=0)
    total_gross = models.IntegerField(default=0)

    # --- Withholding tax (ritenuta d'acconto) ---
    withholding_tax_enabled = models.BooleanField(default=False)
    withholding_tax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    withholding_tax_amount = models.IntegerField(default=0)  # cents

    # --- Payment ---
    payment_method = models.CharField(max_length=10, blank=True, default="")
    payment_terms = models.CharField(max_length=10, blank=True, default="")
    bank_name = models.CharField(max_length=100, blank=True, default="")
    bank_iban = models.CharField(max_length=34, blank=True, default="")

    # --- VAT payability ---
    vat_payability = models.CharField(max_length=1, default="I")  # I=Immediata, D=Differita, S=Split
    split_payment = models.BooleanField(default=False)

    # --- Stamp duty (bollo) ---
    stamp_duty_applied = models.BooleanField(default=False)
    stamp_duty_amount = models.IntegerField(default=0)  # cents

    # --- SDI ---
    sdi_status = models.CharField(max_length=30, blank=True, default="")
    sdi_uuid = models.CharField(max_length=100, blank=True, default="")
    sdi_id = models.CharField(max_length=100, blank=True, default="")
    sdi_message = models.TextField(blank=True, default="")
    sdi_sent_at = models.DateTimeField(null=True, blank=True)

    # --- Import idempotency ---
    xml_content_hash = models.CharField(
        max_length=64, blank=True, default="", db_index=True,
        help_text="SHA-256 of imported XML to prevent duplicate imports",
    )

    # --- Courtesy email ---
    last_email_sent_at = models.DateTimeField(null=True, blank=True)
    email_delivery_status = models.CharField(
        max_length=10, blank=True, default="",
        choices=[("", "Non inviata"), ("sent", "Inviata"), ("failed", "Fallita")],
    )

    # --- Credit note link ---
    related_invoice = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="credit_notes",
        help_text="Original invoice (for credit notes TD04)",
    )

    # --- Self-invoice specific ---
    related_invoice_number = models.CharField(max_length=50, blank=True, default="")
    related_invoice_date = models.DateField(null=True, blank=True)

    # --- Payment tracking ---
    paid_at = models.DateField(null=True, blank=True, help_text="Data incasso effettivo")
    paid_via = models.CharField(
        max_length=10, blank=True, default="",
        help_text="Metodo di incasso effettivo (codice MP)",
    )

    # --- Timestamps ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Managers
    objects = SalesManager()
    all_types = models.Manager()

    class Meta:
        ordering = ["-date", "-id"]
        indexes = [
            models.Index(fields=["type", "date"]),
            models.Index(fields=["contact_id"]),
            models.Index(fields=["sequence_id", "date"]),
        ]

    def __str__(self):
        return f"{self.number} — {self.contact}"

    def is_sdi_editable(self) -> bool:
        """True if invoice is not locked by SDI status."""
        return self.sdi_status not in SDI_LOCKED_STATUSES

    def calculate_totals(self):
        """Recalculate all totals from invoice lines. Delegates to service."""
        from apps.invoices.services.calculations import TotalsCalculationService

        TotalsCalculationService.calculate(self)

    def get_vat_summary(self) -> list[dict]:
        """Group line totals by VAT rate for XML riepilogo."""
        summary: dict[int, dict] = {}
        for line in self.lines.select_related("vat_rate").all():
            rate_id = line.vat_rate_id
            if rate_id not in summary:
                summary[rate_id] = {
                    "vat_rate": line.vat_rate,
                    "taxable": 0,
                    "vat": 0,
                }
            summary[rate_id]["taxable"] += line.total
            summary[rate_id]["vat"] += round(line.total * line.vat_rate.percent / 100)
        return list(summary.values())

    @property
    def payment_status(self):
        """Return 'paid', 'partial', or 'unpaid'.

        Uses annotated `_paid_total` if available (from queryset),
        otherwise queries PaymentDue.
        """
        paid_total = getattr(self, "_paid_total", None)
        if paid_total is None:
            paid_total = sum(
                d.amount for d in self.payment_dues.filter(paid=True)
            )
        if self.total_gross and paid_total >= self.total_gross:
            return "paid"
        if paid_total > 0:
            return "partial"
        return "unpaid"

    def sync_paid_status(self):
        """Derive paid_at / paid_via from PaymentDue records.

        When the sum of paid dues covers total_gross the invoice is
        considered fully paid; paid_at is set to the latest paid_at
        among the dues, paid_via to the method of the latest due.
        If no dues or not fully covered, paid_at/paid_via are cleared.
        """
        dues = self.payment_dues.all()
        paid_dues = [d for d in dues if d.paid]
        paid_total = sum(d.amount for d in paid_dues)
        if paid_dues and paid_total >= self.total_gross:
            latest = max(paid_dues, key=lambda d: d.paid_at or d.due_date)
            self.paid_at = latest.paid_at or latest.due_date
            self.paid_via = latest.payment_method
        else:
            self.paid_at = None
            self.paid_via = ""
        self.save(update_fields=["paid_at", "paid_via"])


class PurchaseInvoice(Invoice):
    """Purchase invoice proxy model."""

    objects = PurchaseManager()

    class Meta:
        proxy = True

    def save(self, **kwargs):
        self.type = InvoiceType.PURCHASE
        super().save(**kwargs)


class SelfInvoice(Invoice):
    """Self-invoice (autofattura) proxy model."""

    objects = SelfInvoiceManager()

    class Meta:
        proxy = True

    def save(self, **kwargs):
        self.type = InvoiceType.SELF_INVOICE
        super().save(**kwargs)


class InvoiceLine(models.Model):
    """Single line item within an invoice."""

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey(
        "products.Product", on_delete=models.SET_NULL, null=True, blank=True
    )
    description = models.CharField(max_length=500)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_of_measure = models.CharField(max_length=10, blank=True, default="")
    unit_price = models.IntegerField(default=0)  # cents
    vat_rate = models.ForeignKey(VatRate, on_delete=models.PROTECT)
    total = models.IntegerField(default=0)  # cents

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.description} (€{self.total / 100:.2f})"


class PaymentDue(models.Model):
    """Singola rata/scadenza di pagamento di una fattura."""

    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="payment_dues",
    )
    due_date = models.DateField()
    amount = models.IntegerField(default=0, help_text="Importo in centesimi")
    payment_method = models.CharField(max_length=10, blank=True, default="")
    paid = models.BooleanField(default=False, db_index=True)
    paid_at = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["due_date"]

    def __str__(self):
        status = "✓" if self.paid else "○"
        return f"{status} {self.due_date} — €{self.amount / 100:.2f}"

    @property
    def is_overdue(self) -> bool:
        from datetime import date as _date
        return not self.paid and self.due_date < _date.today()
