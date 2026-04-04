# T14 — CRUD Autofatture (TD17/TD18/TD19/TD28)

**Fase:** 4 — Fatture Passive  
**Complessità:** Media  
**Dipendenze:** T03, T10, T11  
**Blocca:** T18

---

## Obiettivo

Implementare gestione autofatture (self-invoices) per reverse charge e acquisti intra-UE/esteri. Usa il proxy model `SelfInvoice` con campi specifici per tipo documento e fattura originale.

## Tipi documento autofattura

| Codice | Descrizione | Quando si usa |
|---|---|---|
| TD17 | Integrazione/autofattura per acquisto servizi dall'estero | Servizi da fornitore UE/extra-UE |
| TD18 | Integrazione per acquisto beni intracomunitari | Beni da fornitore UE |
| TD19 | Integrazione/autofattura per acquisto beni ex art. 17 c.2 | Beni da fornitore extra-UE |
| TD28 | Acquisti da San Marino con IVA | Beni/servizi da San Marino |

## URL

```python
urlpatterns = [
    path("self-invoices/", SelfInvoiceListView.as_view(), name="self-invoices-index"),
    path("self-invoices/create/", SelfInvoiceCreateView.as_view(), name="self-invoices-create"),
    path("self-invoices/<int:pk>/edit/", SelfInvoiceUpdateView.as_view(), name="self-invoices-edit"),
    path("self-invoices/<int:pk>/delete/", SelfInvoiceDeleteView.as_view(), name="self-invoices-delete"),
]
```

## Differenze rispetto a fattura vendita

| Aspetto | Vendita | Autofattura |
|---|---|---|
| Modello | Invoice (type=sales) | SelfInvoice (proxy, type=self_invoice) |
| Campo `document_type` | TD01 (default) | TD17/TD18/TD19/TD28 (obbligatorio) |
| Campi extra | — | `related_invoice_number`, `related_invoice_date` |
| Bollo | Sì | No |
| SoggettoEmittente | — | CC (cessionario/committente emette) |
| TerzoIntermediario | — | Sì (dati azienda come intermediario) |

## Form extra

```python
class SelfInvoiceForm(InvoiceForm):
    document_type = forms.ChoiceField(choices=[
        ("TD17", "TD17 – Servizi dall'estero"),
        ("TD18", "TD18 – Beni intracomunitari"),
        ("TD19", "TD19 – Beni ex art.17 c.2"),
        ("TD28", "TD28 – Acquisti da San Marino"),
    ])
    related_invoice_number = forms.CharField(
        max_length=50, label="Numero fattura originale"
    )
    related_invoice_date = forms.DateField(
        label="Data fattura originale"
    )
```

## Logica UI

1. Select `document_type` obbligatorio
2. Sezione "Fattura originale" con numero e data della fattura del fornitore
3. Contatto = fornitore estero (non italiano o UE)
4. Nessun bollo automatico
5. IVA calcolata normalmente (reverse charge: l'azienda integra l'IVA)

## File da creare

- `apps/invoices/views_self_invoice.py`
- `templates/self-invoices/index.html`
- `templates/self-invoices/create.html`
- `templates/self-invoices/edit.html`
- `tests/test_self_invoices.py`

## Criteri di accettazione

- [ ] Lista autofatture separata
- [ ] `SelfInvoice.objects.all()` ritorna solo type=self_invoice
- [ ] Campo document_type obbligatorio (TD17/18/19/28)
- [ ] Campi fattura originale (related_invoice_number/date) presenti
- [ ] Nessun bollo automatico
- [ ] Totali calcolati correttamente
- [ ] Edit read-only se SDI locked o anno passato
