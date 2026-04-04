# T07 — CRUD Aliquote IVA

**Fase:** 2 — CRUD Anagrafiche  
**Complessità:** Bassa  
**Dipendenze:** T02, T05  
**Blocca:** T10, T11

---

## Obiettivo

Gestione aliquote IVA con protezione delle aliquote di sistema.

---

## URL

| Metodo | URL | View | Nome |
|---|---|---|---|
| GET | `/vat-rates/` | `VatRateListView` | `invoices:vat-rates` |
| GET/POST | `/vat-rates/create/` | `VatRateCreateView` | `invoices:vat-rate-create` |
| GET/POST | `/vat-rates/<pk>/edit/` | `VatRateEditView` | `invoices:vat-rate-edit` |
| POST | `/vat-rates/<pk>/delete/` | `VatRateDeleteView` | `invoices:vat-rate-delete` |

---

## Campi form

- **name**: nome aliquota (es. "IVA 22%", "Esente Art. 10")
- **percent**: percentuale IVA (es. 22.00, 10.00, 4.00, 0.00)
- **description**: descrizione opzionale
- **nature**: codice natura per esenzioni IVA (N1-N7, vuoto se aliquota piena)
  - N1 = escluse ex art.15
  - N2 = non soggette
  - N3 = non imponibili
  - N4 = esenti
  - N5 = regime del margine
  - N6 = inversione contabile (reverse charge)
  - N7 = IVA assolta in altro stato UE
- **is_system**: read-only flag (non modificabile, non cancellabile)

---

## Protezioni

- Aliquote `is_system=True`: **non cancellabili**, nome e tipo non modificabili
- Aliquote in uso da `InvoiceLine`: **non cancellabili** → messaggio errore
- Le aliquote system vengono create dal seeder/setup (vedi T01)

### Seeder aliquote default

```python
VatRate.objects.get_or_create(name="IVA 22%", defaults={"percent": 22, "is_system": True})
VatRate.objects.get_or_create(name="IVA 10%", defaults={"percent": 10, "is_system": True})
VatRate.objects.get_or_create(name="IVA 4%", defaults={"percent": 4, "is_system": True})
VatRate.objects.get_or_create(name="Esente", defaults={"percent": 0, "nature": "N4", "is_system": True})
```

---

## Template

| File | Descrizione |
|---|---|
| `templates/invoices/vat_rates/index.html` | Lista con tabella |
| `templates/invoices/vat_rates/form.html` | Form create/edit |

---

## Criteri di accettazione

- [ ] Lista aliquote con nome, percentuale, natura, badge system
- [ ] Creazione nuova aliquota
- [ ] Modifica aliquota (non system)
- [ ] Cancellazione bloccata se system o in uso
- [ ] Campo `nature` visibile solo se `percent = 0`
- [ ] 4 aliquote system pre-create
