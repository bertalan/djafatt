# T34 — Note di credito (TD04)

**Fase:** 4 — Import/Export XML e tipi documento  
**Complessità:** Media  
**Dipendenze:** T03, T10, T11, T17  
**Blocca:** Nessuno

---

## Obiettivo

Implementare la gestione delle Note di Credito (tipo documento TD04) per correggere o annullare fatture già emesse. È un requisito fiscale obbligatorio: non è legalmente possibile cancellare una fattura inviata al SdI, si può solo emettere una nota di credito a storno totale o parziale.

## Tipo Documento SDI

- **TD04**: Nota di credito
- **TD05**: Nota di debito (meno comune, stessa logica ma con segno opposto)

## Design

Le note di credito usano lo stesso modello `Invoice` con:
- `type = 'sales'` (sono fatture attive, emesse dall'azienda)
- `document_type = 'TD04'`
- Una nuova sequenza dedicata o la stessa sequenza vendite
- Importi positivi nel modello, ma nel calcolo dei totali e nella dashboard vengono sottratti

### Proxy Model (opzionale)

Si può usare un Proxy Model `CreditNote` con manager che filtra su `document_type='TD04'`, oppure semplicemente filtrare nelle views.

Scelta consigliata: **NO proxy aggiuntivo**. Usare il model `Invoice` con filtro `document_type` nelle views. Meno complessità, stessa funzionalità.

## Relazione con fattura originale

```python
# Campi già esistenti in Invoice (T03)
related_invoice_number = models.CharField(max_length=50, blank=True, default="")
related_invoice_date = models.DateField(null=True, blank=True)

# Aggiungere FK opzionale
related_invoice = models.ForeignKey(
    "self", on_delete=models.SET_NULL, null=True, blank=True,
    related_name="credit_notes",
    help_text="Fattura originale a cui si riferisce la nota di credito",
)
```

## Generazione XML (T17)

La nota di credito è una fattura FatturaPA standard con:
- `TipoDocumento = "TD04"`
- `DatiFattureCollegate` con numero e data della fattura originale
- Importi positivi (per convenzione FatturaPA, non negativi)
- Tutti gli altri campi uguali a una fattura normale

```python
def _build_dati_generali(self, invoice):
    dati = {
        "TipoDocumento": invoice.document_type or "TD01",
        "Divisa": "EUR",
        "Data": invoice.date.isoformat(),
        "Numero": invoice.number,
    }
    # Se nota di credito, aggiungere fattura collegata
    if invoice.document_type == "TD04" and invoice.related_invoice_number:
        dati["DatiFattureCollegate"] = [{
            "IdDocumento": invoice.related_invoice_number,
            "Data": invoice.related_invoice_date.isoformat() if invoice.related_invoice_date else None,
        }]
    return dati
```

## UI

### Creazione nota di credito

Due modalità:
1. **Da fattura esistente:** Bottone "Emetti nota di credito" nella fattura → precompila:
   - `document_type = "TD04"`
   - `related_invoice` = fattura corrente
   - `contact` = stesso contatto
   - Righe copiate con stessi importi (storno totale) o modificabili (storno parziale)
2. **Manuale:** Da CRUD fatture vendita, selezionando `document_type = "TD04"`

### Lista fatture

- Le note di credito appaiono nella lista fatture vendita con badge "Nota di credito" (diverso colore).
- Filtro: tipo documento (TD01, TD04, TD05, tutti).

### Dashboard (T23)

- Le note di credito **sottraggono** dal fatturato.
- Metriche separate: "Note di credito emesse questo mese".

## Logica di calcolo (T11)

Nessuna modifica al motore di calcolo. Le note di credito hanno importi positivi come le fatture normali. La sottrazione avviene solo nelle aggregazioni (dashboard, report).

```python
# In ReportService (T23)
revenue = Invoice.objects.filter(
    type="sales", document_type="TD01", date__year=year
).aggregate(total=Sum("total_gross"))["total"] or 0

credit_notes = Invoice.objects.filter(
    type="sales", document_type="TD04", date__year=year
).aggregate(total=Sum("total_gross"))["total"] or 0

net_revenue = revenue - credit_notes
```

## File da creare/modificare

- `apps/invoices/models.py` — Aggiungere `related_invoice` FK
- `apps/invoices/views_invoice.py` — Aggiungere azione "Emetti nota di credito"
- `templates/invoices/create.html` — Supporto per TD04 (titolo, badge)
- `tests/test_credit_notes.py`

## Criteri di accettazione

- [ ] Creazione nota di credito TD04 con fattura collegata
- [ ] Precompilazione da fattura esistente (storno totale)
- [ ] Storno parziale (importi modificabili)
- [ ] XML generato con `TipoDocumento=TD04` e `DatiFattureCollegate`
- [ ] Badge "Nota di credito" nella lista fatture
- [ ] Dashboard: note di credito sottratte dal fatturato
- [ ] Campo `related_invoice` linkato alla fattura originale
- [ ] Invio al SDI funzionante (il flusso è identico a una fattura standard)
- [ ] Test: generazione XML TD04, round-trip import/export
