# T10 — CRUD Fatture vendita

**Fase:** 3 — Fatture Attive  
**Complessità:** Alta  
**Dipendenze:** T03, T05, T06, T07, T08, T11  
**Blocca:** T13, T14, T17

---

## Obiettivo

Implementare gestione completa fatture di vendita: lista con filtri, creazione con righe inline, modifica con protezione SDI/anno fiscale.

## Viste

### Lista (`/invoices/`)

- Tabella paginata: #, Numero, Data, Cliente, Totale (€), Stato, Azioni
- Ricerca: per numero fattura o nome cliente
- Sort: data, numero, totale
- Filtro anno fiscale (da session)
- Badge stato colorato: draft (warning), generated (info), sent (success), received (accent)
- Bottone "Nuova fattura" (nascosto se anno read-only)
- Delete con conferma (bloccato se SDI locked)
- Banner read-only per anni fiscali chiusi

### Create (`/invoices/create/`)

- **Header**: Sequenza (select), Numero (auto-generato), Data, Cliente (select con ricerca)
- **Righe**: Inline formset con add/remove via HTMX (vedi T12)
- **Sidebar**: Totali live (Netto, IVA, Lordo)
- Redirect se anno fiscale passato
- Sequenza default da settings

### Edit (`/invoices/<id>/edit/`)

- Stesso form di Create, pre-popolato
- Read-only completo se:
  - Anno fiscale passato
  - SDI locked (`is_sdi_editable() == False`)
- Alert banner se read-only
- Dettagli SDI visibili (stato, UUID, messaggio)

## URL

```python
urlpatterns = [
    path("invoices/", InvoiceListView.as_view(), name="invoices-index"),
    path("invoices/create/", InvoiceCreateView.as_view(), name="invoices-create"),
    path("invoices/<int:pk>/edit/", InvoiceUpdateView.as_view(), name="invoices-edit"),
    path("invoices/<int:pk>/delete/", InvoiceDeleteView.as_view(), name="invoices-delete"),
]
```

## Form

```python
class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = [
            "sequence", "number", "date", "contact",
            "notes", "payment_method", "payment_terms",
            "bank_name", "bank_iban",
            "withholding_tax_enabled", "withholding_tax_percent",
            "vat_payability", "split_payment",
        ]

InvoiceLineFormSet = inlineformset_factory(
    Invoice, InvoiceLine,
    form=InvoiceLineForm,
    extra=1, can_delete=True,
)
```

## Logica

- Al save: `sequence.get_next_number(year)` → `sequential_number`
- Al save: `invoice.calculate_totals()` (T11)
- Stato iniziale: `"draft"`
- `number` auto-generato da `sequence.get_formatted_number()`

## File da creare

- `apps/invoices/views_invoice.py`
- `apps/invoices/forms.py` — InvoiceForm, InvoiceLineForm, InvoiceLineFormSet
- `apps/invoices/urls.py`
- `templates/invoices/index.html`
- `templates/invoices/create.html`
- `templates/invoices/edit.html`
- `templates/invoices/partials/_table.html`
- `templates/invoices/partials/_lines.html`
- `templates/invoices/partials/_totals.html`
- `tests/test_invoices.py`

## Criteri di accettazione

- [ ] Lista fatture con paginazione, ricerca, sort, filtro anno
- [ ] Create con righe inline, totali calcolati live
- [ ] Numero auto-generato da sequenza
- [ ] Edit con protezione read-only (anno + SDI)
- [ ] Delete bloccato se SDI locked
- [ ] Badge stato colorato
- [ ] Banner read-only per anni passati
