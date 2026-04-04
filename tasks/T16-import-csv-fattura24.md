# T16 — Import CSV contatti Fattura24

**Fase:** 4 — Fatture Passive  
**Complessità:** Bassa  
**Dipendenze:** T02, T06  
**Blocca:** Nessuno

---

## Obiettivo

Parser CSV per importare contatti dal formato export di Fattura24. Delimitatore punto e virgola, mapping colonne specifico.

## Mapping colonne CSV → Contact

| Colonna CSV | Campo Contact |
|---|---|
| P.IVA | `vat_number` |
| Rag. Sociale | `name` |
| Cod. fiscale | `tax_code` |
| Email | `email` |
| Pec | `pec` |
| Telefono | `phone` |
| Cellulare | `mobile` |
| Indirizzo | `address` |
| Città | `city` |
| Provincia | `province` |
| CAP | `postal_code` |
| Cod. Destinatario | `sdi_code` |
| Tipo | flag `is_customer`/`is_supplier` |

## Logica (`apps/sdi/services/csv_import.py`)

```python
import csv

class Fattura24ContactImporter:
    def __init__(self):
        self.stats = {"created": 0, "updated": 0, "skipped": 0}
        self.errors = []
    
    def import_csv(self, file_path: str, update_existing: bool = False) -> dict:
        with open(file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, delimiter=";")
            for row in reader:
                vat = row.get("P.IVA", "").strip()
                if not vat:
                    self.stats["skipped"] += 1
                    continue
                
                contact_data = {
                    "name": row.get("Rag. Sociale", "").strip(),
                    "tax_code": row.get("Cod. fiscale", "").strip(),
                    "email": row.get("Email", "").strip(),
                    "pec": row.get("Pec", "").strip(),
                    "phone": row.get("Telefono", "").strip(),
                    "mobile": row.get("Cellulare", "").strip(),
                    "address": row.get("Indirizzo", "").strip(),
                    "city": row.get("Città", "").strip(),
                    "province": row.get("Provincia", "").strip(),
                    "postal_code": row.get("CAP", "").strip(),
                    "sdi_code": row.get("Cod. Destinatario", "").strip(),
                }
                
                # Flag cliente/fornitore dal campo Tipo
                tipo = row.get("Tipo", "").lower()
                contact_data["is_customer"] = "cliente" in tipo
                contact_data["is_supplier"] = "fornitore" in tipo
                
                existing = Contact.objects.filter(vat_number=vat).first()
                if existing:
                    if update_existing:
                        for k, v in contact_data.items():
                            setattr(existing, k, v)
                        existing.save()
                        self.stats["updated"] += 1
                    else:
                        self.stats["skipped"] += 1
                else:
                    Contact.objects.create(vat_number=vat, **contact_data)
                    self.stats["created"] += 1
        
        return {"stats": self.stats, "errors": self.errors}
```

## UI

- Card nella pagina `/imports/` : "Importa contatti Fattura24"
- Upload modal con file CSV + checkbox "Aggiorna esistenti"
- Risultati: creati, aggiornati, saltati, errori

## File da creare

- `apps/sdi/services/csv_import.py`
- Aggiornare `templates/imports/index.html` — card Fattura24
- `tests/test_csv_import.py`
- `tests/fixtures/sample_fattura24.csv`

## Criteri di accettazione

- [ ] Import CSV crea contatti correttamente
- [ ] Delimitatore `;` gestito
- [ ] Contatti con P.IVA duplicata saltati (default)
- [ ] Flag `update_existing` aggiorna contatti esistenti
- [ ] Statistiche import mostrate (creati/aggiornati/saltati)
- [ ] Encoding UTF-8 con BOM gestito
