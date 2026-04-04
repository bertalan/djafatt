# T03 — Modelli Invoice + InvoiceLine + Proxy Models

**Fase:** 1 — Fondamenta  
**Complessità:** Alta  
**Dipendenze:** T02  
**Blocca:** T10, T11, T13, T14, T15, T17

---

## Obiettivo

Creare il modello `Invoice` con Single Table Inheritance via Django Proxy Models per `PurchaseInvoice` e `SelfInvoice`. Creare `InvoiceLine` con signal per ricalcolo automatico totali.

## Design: Single Table Inheritance

L'originale usa un campo `type` discriminator su tabella `invoices`:
- `type='sales'` → Invoice (fattura vendita)
- `type='purchase'` → PurchaseInvoice (fattura acquisto)
- `type='self_invoice'` → SelfInvoice (autofattura)

In Django: **Proxy Models** con custom Manager che filtra su `type`.

```python
class InvoiceType(models.TextChoices):
    SALES = "sales", "Vendita"
    PURCHASE = "purchase", "Acquisto"
    SELF_INVOICE = "self_invoice", "Autofattura"

class SdiStatus(models.TextChoices):
    # ... enum stati SDI
    PENDING = "Pending", "In attesa"
    SENT = "Sent", "Inviato"
    DELIVERED = "Delivered", "Consegnato"
    REJECTED = "Rejected", "Rifiutato"
    # ... altri stati (NS, RC, MC, DT, NE, AT, EC)
```

## Modello Invoice (`apps/invoices/models.py`)

```python
class SalesManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(type=InvoiceType.SALES)

class Invoice(models.Model):
    # --- Identificazione ---
    type = models.CharField(max_length=20, choices=InvoiceType.choices, default=InvoiceType.SALES)
    number = models.CharField(max_length=50)
    sequential_number = models.IntegerField(null=True, blank=True)
    date = models.DateField()
    document_type = models.CharField(max_length=10, blank=True, default="")  # TD01, TD17, etc.
    status = models.CharField(max_length=20, default="draft")
    notes = models.TextField(blank=True, default="")

    # --- Relazioni ---
    contact = models.ForeignKey("contacts.Contact", on_delete=models.PROTECT)
    sequence = models.ForeignKey(Sequence, on_delete=models.PROTECT)

    # --- Totali (centesimi) ---
    total_net = models.IntegerField(default=0)
    total_vat = models.IntegerField(default=0)
    total_gross = models.IntegerField(default=0)

    # --- Ritenuta d'acconto ---
    withholding_tax_enabled = models.BooleanField(default=False)
    withholding_tax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    withholding_tax_amount = models.IntegerField(default=0)  # centesimi

    # --- Pagamento ---
    payment_method = models.CharField(max_length=10, blank=True, default="")
    payment_terms = models.CharField(max_length=10, blank=True, default="")
    bank_name = models.CharField(max_length=100, blank=True, default="")
    bank_iban = models.CharField(max_length=34, blank=True, default="")

    # --- IVA ---
    vat_payability = models.CharField(max_length=1, default="I")  # I=Immediata, D=Differita, S=Split
    split_payment = models.BooleanField(default=False)

    # --- Bollo ---
    stamp_duty_applied = models.BooleanField(default=False)
    stamp_duty_amount = models.IntegerField(default=0)  # centesimi

    # --- SDI ---
    sdi_status = models.CharField(max_length=30, blank=True, default="")
    sdi_uuid = models.CharField(max_length=100, blank=True, default="")
    sdi_id = models.CharField(max_length=100, blank=True, default="")
    sdi_message = models.TextField(blank=True, default="")
    sdi_sent_at = models.DateTimeField(null=True, blank=True)

    # --- Import idempotency ---
    xml_content_hash = models.CharField(
        max_length=64, blank=True, default="", db_index=True,
        help_text="SHA-256 dell'XML importato, per prevenire import duplicati",
    )

    # --- Email cortesia ---
    last_email_sent_at = models.DateTimeField(null=True, blank=True)
    email_delivery_status = models.CharField(
        max_length=10, blank=True, default="",
        choices=[("", "Non inviata"), ("sent", "Inviata"), ("failed", "Fallita")],
    )

    # --- Nota di credito ---
    related_invoice = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="credit_notes",
        help_text="Fattura originale (per note di credito TD04)",
    )

    # --- Self-invoice specifici ---
    related_invoice_number = models.CharField(max_length=50, blank=True, default="")
    related_invoice_date = models.DateField(null=True, blank=True)

    # --- Timestamps ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Manager: default filtra solo 'sales'
    objects = SalesManager()
    all_types = models.Manager()  # per query cross-type

    class Meta:
        ordering = ["-date", "-id"]
        indexes = [
            models.Index(fields=["type", "date"]),
            models.Index(fields=["contact_id"]),
            models.Index(fields=["sequence_id", "date"]),
        ]
```

**Metodi:**
- `is_sdi_editable() -> bool` — True se non locked da SDI
- `calculate_totals()` — Ricalcola da righe: netto, IVA per aliquota, ritenuta, bollo auto
- `save()` — Override: imposta `type` su creazione

## Proxy Models

```python
class PurchaseManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(type=InvoiceType.PURCHASE)

class PurchaseInvoice(Invoice):
    objects = PurchaseManager()

    class Meta:
        proxy = True

    def save(self, **kwargs):
        self.type = InvoiceType.PURCHASE
        super().save(**kwargs)

class SelfInvoiceManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(type=InvoiceType.SELF_INVOICE)

class SelfInvoice(Invoice):
    objects = SelfInvoiceManager()

    class Meta:
        proxy = True

    def save(self, **kwargs):
        self.type = InvoiceType.SELF_INVOICE
        super().save(**kwargs)
```

## Modello InvoiceLine

```python
class InvoiceLine(models.Model):
    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="lines"
    )
    product = models.ForeignKey(
        "products.Product", on_delete=models.SET_NULL, null=True, blank=True
    )
    description = models.CharField(max_length=500)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_of_measure = models.CharField(max_length=10, blank=True, default="")
    unit_price = models.IntegerField(default=0)  # centesimi
    vat_rate = models.ForeignKey(VatRate, on_delete=models.PROTECT)
    total = models.IntegerField(default=0)  # centesimi
```

**Signal `post_save` e `post_delete`:**
```python
@receiver([post_save, post_delete], sender=InvoiceLine)
def recalculate_invoice_totals(sender, instance, **kwargs):
    # Usa Invoice.all_types per bypassare il filtro type
    invoice = Invoice.all_types.get(pk=instance.invoice_id)
    invoice.calculate_totals()
```

## File da creare/modificare

- `apps/invoices/models.py` — Aggiungere Invoice, InvoiceLine, proxy models, managers
- `apps/invoices/signals.py` — Signal per ricalcolo totali
- `apps/invoices/apps.py` — `ready()` per caricare signals
- `apps/invoices/admin.py` — Admin base per debug
- Migrazione `apps/invoices/migrations/0002_invoice_invoiceline.py`

## Criteri di accettazione

- [ ] `Invoice.objects.all()` ritorna SOLO fatture con `type='sales'`
- [ ] `PurchaseInvoice.objects.all()` ritorna SOLO `type='purchase'`
- [ ] `SelfInvoice.objects.all()` ritorna SOLO `type='self_invoice'`
- [ ] `Invoice.all_types.all()` ritorna TUTTE le fatture
- [ ] Creare `PurchaseInvoice(...)` imposta automaticamente `type='purchase'`
- [ ] Salvare/cancellare `InvoiceLine` scatena `calculate_totals()` sulla fattura padre
- [ ] Importi tutti in centesimi (intero)
- [ ] `is_sdi_editable()` ritorna False se `sdi_status` in stati locked
