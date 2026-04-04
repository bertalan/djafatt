# T13 — CRUD Fatture acquisto

**Fase:** 4 — Fatture Passive  
**Complessità:** Media  
**Dipendenze:** T03, T10, T11, T12  
**Blocca:** T15, T23

---

## Obiettivo

Implementare gestione fatture acquisto (passive/spese) utilizzando il proxy model `PurchaseInvoice`. Stessa UI delle fatture vendita ma con sequenza tipo `purchase` e stato `received` per importate.

## Differenze rispetto a fatture vendita (T10)

| Aspetto | Vendita | Acquisto |
|---|---|---|
| Modello | `Invoice` (type=sales) | `PurchaseInvoice` (proxy, type=purchase) |
| Sequenza | tipo `sales` | tipo `purchase` |
| Contatto | Cliente (`is_customer`) | Fornitore (`is_supplier`) |
| Bollo auto | Sì | No |
| Invio SDI | Sì (T17) | No |
| Import XML | Sì | Sì (con stato `received`, read-only) |
| Label colonna | "Cliente" | "Fornitore" |
| URL base | `/invoices/` | `/purchase-invoices/` |

## URL

```python
urlpatterns = [
    path("purchase-invoices/", PurchaseInvoiceListView.as_view(), name="purchase-invoices-index"),
    path("purchase-invoices/create/", PurchaseInvoiceCreateView.as_view(), name="purchase-invoices-create"),
    path("purchase-invoices/<int:pk>/edit/", PurchaseInvoiceUpdateView.as_view(), name="purchase-invoices-edit"),
    path("purchase-invoices/<int:pk>/delete/", PurchaseInvoiceDeleteView.as_view(), name="purchase-invoices-delete"),
]
```

## Viste

### Lista (`/purchase-invoices/`)

- Tabella: #, Numero, Data, Fornitore, Totale, Stato, Azioni
- Filtro anno fiscale
- Ricerca per numero/nome fornitore
- Badge stato: draft (modif.), received (importata, read-only)
- Delete: bloccato se `status == "received"` (importata da XML, SDI locked)

### Create (`/purchase-invoices/create/`)

- Sequenza tipo `purchase`
- Contatti filtrati: solo `is_supplier=True`
- Righe inline (riusa T12)
- Nessun bollo automatico

### Edit (`/purchase-invoices/<id>/edit/`)

- Read-only se importata (status=received, SDI locked)
- Read-only se anno fiscale passato
- Alert specifico: "Fattura importata — non modificabile"

## Logica `calculate_totals` per acquisto

- Stessa logica di T11 ma **senza bollo automatico**
- La ritenuta d'acconto si applica (fornitore può avere ritenuta)

## File da creare/modificare

- `apps/invoices/views_purchase.py`
- `templates/purchase-invoices/index.html`
- `templates/purchase-invoices/create.html`
- `templates/purchase-invoices/edit.html`
- `templates/purchase-invoices/partials/_table.html`
- `tests/test_purchase_invoices.py`

## Criteri di accettazione

- [ ] Lista fatture acquisto separata da vendita
- [ ] `PurchaseInvoice.objects.all()` ritorna solo type=purchase
- [ ] Create con sequenza tipo purchase
- [ ] Contatti filtrati: solo fornitori
- [ ] Edit read-only per fatture importate (status=received)
- [ ] Delete bloccato per fatture SDI locked
- [ ] Nessun bollo automatico
- [ ] Totali calcolati correttamente
