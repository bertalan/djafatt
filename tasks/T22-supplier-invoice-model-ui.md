# T22 — Modello SupplierInvoice + UI lista

**Fase:** 5 — Integrazione SDI  
**Complessità:** Media  
**Dipendenze:** T02, T05, T19  
**Blocca:** T21

---

## Obiettivo

Creare il modello `SupplierInvoice` per fatture ricevute via API SDI e la UI per visualizzarle. Nell'originale questa era una pagina WIP — la completiamo.

## Modello `SupplierInvoice` (`apps/sdi/models.py`)

```python
class SupplierInvoice(models.Model):
    """Fatture fornitori sincronizzate da OpenAPI SDI."""
    
    # Identificazione
    uuid = models.CharField(max_length=100, unique=True)
    filename = models.CharField(max_length=255, blank=True, default="")
    file_id = models.CharField(max_length=100, blank=True, default="")
    
    # Dati fornitore
    supplier_vat_number = models.CharField(max_length=30, db_index=True)
    supplier_tax_code = models.CharField(max_length=30, blank=True, default="")
    supplier_name = models.CharField(max_length=255)
    supplier_address = models.CharField(max_length=500, blank=True, default="")
    
    # Dati fattura
    invoice_number = models.CharField(max_length=50)
    invoice_date = models.DateField(db_index=True)
    document_type = models.CharField(max_length=10, blank=True, default="")
    currency = models.CharField(max_length=3, default="EUR")
    
    # Importi (centesimi)
    taxable_amount = models.IntegerField(default=0)
    vat_amount = models.IntegerField(default=0)
    total_amount = models.IntegerField(default=0)
    
    # Stato
    sdi_status = models.CharField(max_length=30, blank=True, default="")
    received_at = models.DateTimeField(null=True, blank=True, db_index=True)
    
    # Dati raw
    payload = models.JSONField(default=dict)
    xml_content = models.TextField(blank=True, default="")
    
    # Sync
    synced_at = models.DateTimeField(auto_now=True)
    processed = models.BooleanField(default=False, db_index=True)
    
    class Meta:
        ordering = ["-invoice_date", "-id"]
    
    @classmethod
    def update_or_create_from_api(cls, api_data: dict) -> "SupplierInvoice":
        """Crea o aggiorna da dati API OpenAPI."""
        return cls.objects.update_or_create(
            uuid=api_data["uuid"],
            defaults={
                "filename": api_data.get("filename", ""),
                "supplier_vat_number": api_data.get("sender", {}).get("vat_number", ""),
                "supplier_name": api_data.get("sender", {}).get("name", ""),
                "invoice_number": api_data.get("number", ""),
                "invoice_date": api_data.get("date"),
                "total_amount": int(float(api_data.get("amount", 0)) * 100),
                "sdi_status": api_data.get("status", ""),
                "payload": api_data,
            },
        )[0]
    
    def mark_as_processed(self):
        self.processed = True
        self.save(update_fields=["processed"])
    
    @property
    def formatted_total(self) -> str:
        return f"€ {self.total_amount / 100:,.2f}"
```

## UI

### Lista (`/supplier-invoices/`)

- Tabella: Fornitore, P.IVA, Numero, Data, Totale, Stato, Processata
- Filtri: data, fornitore, processata/non processata
- Ricerca per nome fornitore o numero fattura
- Badge "Processata" / "Da processare"
- Bottone "Sincronizza" → trigger command sync (o HTMX call)

### Dettaglio (opzionale)

- Vista dettaglio con tutti i campi
- Visualizzazione XML originale
- Bottone "Importa come fattura acquisto" → crea PurchaseInvoice

## URL

```python
urlpatterns = [
    path("supplier-invoices/", SupplierInvoiceListView.as_view(), name="supplier-invoices-index"),
    path("supplier-invoices/<int:pk>/", SupplierInvoiceDetailView.as_view(), name="supplier-invoices-detail"),
    path("supplier-invoices/sync/", trigger_sync, name="supplier-invoices-sync"),
]
```

## File da creare

- `apps/sdi/models.py` — SupplierInvoice
- `apps/sdi/views_supplier.py`
- `apps/sdi/urls.py` — Aggiungere route
- `templates/supplier-invoices/index.html`
- `templates/supplier-invoices/detail.html`
- Migrazione `apps/sdi/migrations/0001_supplier_invoice.py`
- `tests/test_supplier_invoice.py`

## Criteri di accettazione

- [ ] Modello SupplierInvoice con tutti i campi
- [ ] `update_or_create_from_api()` non duplica
- [ ] Lista con paginazione e ricerca
- [ ] Filtro per stato processata
- [ ] Importi in centesimi, formattati in euro in UI
- [ ] Bottone sync triggera sincronizzazione
- [ ] Dettaglio con visualizzazione XML
