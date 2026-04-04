# T21 — Command sync fatture fornitori

**Fase:** 5 — Integrazione SDI  
**Complessità:** Media  
**Dipendenze:** T19, T22  
**Blocca:** Nessuno

---

## Obiettivo

Management command Django per sincronizzare fatture ricevute dai fornitori via API OpenAPI SDI. Replica `SyncSupplierInvoices.php`.

## Command

```bash
python manage.py sync_supplier_invoices [--page N] [--per-page N] [--all] [--sender VAT]
```

### Opzioni

| Flag | Default | Descrizione |
|---|---|---|
| `--page` | 1 | Pagina da recuperare |
| `--per-page` | 50 | Fatture per pagina |
| `--all` | False | Recupera tutte le pagine |
| `--sender` | None | Filtra per P.IVA fornitore |

## Implementazione (`apps/sdi/management/commands/sync_supplier_invoices.py`)

```python
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Sincronizza fatture fornitori da OpenAPI SDI"
    
    def add_arguments(self, parser):
        parser.add_argument("--page", type=int, default=1)
        parser.add_argument("--per-page", type=int, default=50)
        parser.add_argument("--all", action="store_true")
        parser.add_argument("--sender", type=str, default=None)
    
    def handle(self, *args, **options):
        client = OpenApiSdiClient()
        page = options["page"]
        per_page = options["per_page"]
        total_synced = 0
        
        while True:
            self.stdout.write(f"Fetching page {page}...")
            result = client.get_supplier_invoices(page=page, per_page=per_page)
            
            invoices = result.get("data", [])
            if not invoices:
                break
            
            for inv_data in invoices:
                # Filtra per fornitore se specificato
                if options["sender"]:
                    sender_vat = inv_data.get("sender", {}).get("vat_number", "")
                    if sender_vat != options["sender"]:
                        continue
                
                # Upsert SupplierInvoice
                SupplierInvoice.update_or_create_from_api(inv_data)
                total_synced += 1
            
            if not options["all"]:
                break
            
            # Prossima pagina
            if len(invoices) < per_page:
                break
            page += 1
        
        self.stdout.write(self.style.SUCCESS(
            f"Sincronizzate {total_synced} fatture fornitori"
        ))
```

## File da creare

- `apps/sdi/management/__init__.py`
- `apps/sdi/management/commands/__init__.py`
- `apps/sdi/management/commands/sync_supplier_invoices.py`
- `tests/test_sync_command.py`

## Criteri di accettazione

- [ ] Command esegue senza errori con mock API
- [ ] Paginazione funzionante con `--all`
- [ ] Filtro `--sender` filtra per P.IVA
- [ ] Upsert: non duplica fatture già sincronizzate
- [ ] Output informativo (conteggio sincronizzate)
- [ ] Errore API gestito gracefully (non crash)
