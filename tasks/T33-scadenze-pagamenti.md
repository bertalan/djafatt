# T33 — Scadenze e tracciamento pagamenti

**Fase:** 3 — Motore calcolo e righe  
**Complessità:** Alta  
**Dipendenze:** T03, T10, T11  
**Blocca:** T23  
**Stato:** ✅ Implementato

---

## Obiettivo

Modello `PaymentDue` per tracciare rate/scadenze e registrare incassi per ogni fattura.
`Invoice.paid_at` / `Invoice.paid_via` sono campi **derivati** da `sync_paid_status()`:
la fattura è considerata pagata quando la somma delle rate pagate copre il totale lordo.

## Implementazione effettiva

### `PaymentDue` (`apps/invoices/models.py`)

```python
class PaymentDue(models.Model):
    invoice = models.ForeignKey(
        "Invoice", on_delete=models.CASCADE, related_name="payment_dues"
    )
    due_date = models.DateField()
    amount = models.IntegerField()  # centesimi
    payment_method = models.CharField(max_length=4, blank=True, default="")
    paid = models.BooleanField(default=False)
    paid_at = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["due_date"]

    @property
    def is_overdue(self) -> bool:
        from datetime import date
        return not self.paid and self.due_date < date.today()
```

> **Nota:** il modello `PaymentRecord` previsto in origine non è stato implementato.
> La registrazione dell'incasso avviene settando `paid=True` e `paid_at` direttamente
> sulla rata `PaymentDue`. Questo semplifica il flusso senza perdere funzionalità.

### `Invoice.sync_paid_status()`

```python
def sync_paid_status(self):
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
```

## UI implementata

### Form fattura — sezione "Rate di pagamento"

- `PaymentDueForm` + `PaymentDueFormSet` (prefix `"dues"`, extra=0, can_delete=True)
- Campo `amount_display` (DecimalField €) ↔ `amount` (centesimi) con conversione in `save()`
- HTMX add/remove singola rata
- Presente in tutti e 3 i template form (vendite, acquisti, autofatture)

### Lista fatture — pulsante 💰

- Click su 💰 → HTMX GET a `payment-form/<pk>/` → form inline sotto la riga
- Form chiede: importo (pre-compilato con residuo), data, metodo pagamento
- Submit → `record_payment` crea `PaymentDue(paid=True)` + `sync_paid_status()`
- La fattura diventa "pagata" solo quando somma rate ≥ totale lordo
- Pulsante ↩️ per rimuovere tutti gli incassi (con conferma)

### Duplicazione fattura

Le 3 `DuplicateView` copiano le rate della fattura originale come non pagate.

## Sezione "Incasso" rimossa

I campi `paid_at` / `paid_via` sono stati rimossi da `InvoiceForm` e dai 3 template form.
Restano sul modello `Invoice` come campi derivati (scritti solo da `sync_paid_status()`).

## File modificati

- `apps/invoices/models.py` — `PaymentDue`, `sync_paid_status()`
- `apps/invoices/forms.py` — `PaymentDueForm`, `PaymentDueFormSet`, rimossi `paid_at`/`paid_via` da `InvoiceForm`
- `apps/invoices/views_lines.py` — `add_payment_due`, `remove_payment_due`
- `apps/invoices/views_reports.py` — `payment_form`, `record_payment`, `mark_paid`, `mark_unpaid`
- `apps/invoices/urls.py` — `dues/add/`, `dues/<int:index>/remove/`
- `apps/invoices/urls_reports.py` — `payment-form/<pk>/`, `record-payment/<pk>/`
- `templates/invoices/partials/_quick_payment_form.html` — form inline HTMX
- `templates/invoices/partials/_payment_due_row.html` — riga singola rata
- 3 template form — sezione "Rate di pagamento", rimossa sezione "Incasso"
- 3 template lista `_table.html` — 💰 diventa HTMX GET, ↩️ con conferma
- `tests/test_payment_dues.py` — 16 test (model, formset, htmx, create, duplicate)
- `tests/test_reports.py` — test `record_payment`, `payment_form`, `mark_paid`/`mark_unpaid`
- Migration `0005_add_payment_due`

## Criteri di accettazione

- [x] Modello PaymentDue con rate individuali
- [x] FormSet rate nel form fattura (add/remove HTMX)
- [x] Pulsante 💰 chiede importo prima di registrare
- [x] Fattura marcata pagata solo quando somma rate ≥ totale lordo
- [x] Duplicazione fattura copia rate come non pagate
- [x] Invoice.paid_at/paid_via derivati da sync_paid_status()
- [x] Sezione "Incasso" ridondante rimossa dai form
- [x] 191 test passano
