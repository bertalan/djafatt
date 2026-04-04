# T15 — Import XML FatturaPA (singolo + ZIP)

**Fase:** 4 — Fatture Passive  
**Complessità:** Alta  
**Dipendenze:** T03, T02  
**Blocca:** T20

---

## Obiettivo

Parser XML FatturaPA che importa fatture (vendita, acquisto, autofattura) da file XML singoli o archivi ZIP. Replica `InvoiceXmlImportService.php`.

## Comportamento

1. Upload file (XML, P7M, ZIP) via pagina `/imports/`
2. Parser XML con namespace handling e rimozione firma digitale
3. Estrazione dati: header, fornitore/cliente, righe, IVA, pagamento
4. Auto-creazione Contact se non esiste (match su P.IVA)
5. Auto-creazione VatRate se non esiste (match su percentuale)
6. Creazione Invoice/PurchaseInvoice/SelfInvoice con stato `received`, SDI locked

## Logica parser (`apps/sdi/services/xml_import.py`)

```python
import defusedxml.ElementTree as ET

class InvoiceXmlImportService:
    def __init__(self):
        self.stats = {"invoices_imported": 0, "contacts_created": 0, "errors": 0}
        self.errors = []
    
    def import_xml(self, xml_content: str, sequence_id: int, category: str) -> None:
        """Importa una fattura da XML content."""
        # 1. Pre-process: rimuovi firma digitale, namespace
        xml_clean = self._clean_xml(xml_content)
        
        # 2. Parse con defusedxml (sicuro)
        root = ET.fromstring(xml_clean)
        
        # 3. Estrai header trasmissione
        header = root.find(".//FatturaElettronicaHeader")
        body = root.find(".//FatturaElettronicaBody")
        
        # 4. Estrai/crea contatto
        contact = self._get_or_create_contact(header, category)
        
        # 5. Estrai dati fattura
        invoice_data = self._extract_invoice_data(body)
        
        # 6. Estrai righe
        lines_data = self._extract_lines(body)
        
        # 7. Crea Invoice con tipo corretto
        invoice = self._create_invoice(
            category, sequence_id, contact, invoice_data, lines_data
        )
        
        self.stats["invoices_imported"] += 1
    
    def import_zip(self, zip_path: str, sequence_id: int, category: str) -> None:
        """Importa da archivio ZIP contenente più XML."""
        ...
    
    def _clean_xml(self, content: str) -> str:
        """Rimuovi namespace prefix e firma digitale."""
        # Rimuovi 'p:' namespace prefix
        content = re.sub(r'</?p:', lambda m: m.group().replace('p:', ''), content)
        # Rimuovi blocchi firma digitale
        content = re.sub(r'<ds:Signature.*?</ds:Signature>', '', content, flags=re.DOTALL)
        return content
    
    def _get_or_create_contact(self, header, category) -> Contact:
        """Trova contatto per P.IVA o creane uno nuovo."""
        if category == "purchase":
            # Fornitore = CedentePrestatore
            supplier_data = header.find(".//CedentePrestatore")
            vat = supplier_data.find(".//IdFiscaleIVA/IdCodice").text
            contact, created = Contact.objects.get_or_create(
                vat_number=vat,
                defaults={
                    "name": supplier_data.find(".//Denominazione").text,
                    "is_supplier": True,
                    # ... altri campi
                }
            )
        else:
            # Cliente = CessionarioCommittente
            ...
        return contact
    
    def _extract_invoice_data(self, body) -> dict:
        """Estrai header fattura."""
        general = body.find(".//DatiGeneraliDocumento")
        return {
            "number": general.find("Numero").text,
            "date": general.find("Data").text,
            "document_type": general.find("TipoDocumento").text,
            # ... ritenuta, bollo, pagamento
        }
    
    def _extract_lines(self, body) -> list[dict]:
        """Estrai righe dettaglio."""
        lines = []
        for det in body.findall(".//DettaglioLinee"):
            lines.append({
                "description": det.find("Descrizione").text,
                "quantity": Decimal(det.find("Quantita").text or "1"),
                "unit_price": int(Decimal(det.find("PrezzoUnitario").text) * 100),
                "vat_percent": Decimal(det.find("AliquotaIVA").text),
                # ... unit_of_measure, natura
            })
        return lines
```

## Categorie di import

| Categoria | Tipo fattura | Manager | Stato dopo import |
|---|---|---|---|
| `electronic_invoice` | Invoice (sales) | `Invoice.objects` | received, SDI Delivered |
| `purchase` | PurchaseInvoice | `PurchaseInvoice.objects` | received, SDI Delivered |
| `self_invoice` | SelfInvoice | `SelfInvoice.objects` | received, SDI Delivered |

## UI Import (`/imports/`)

- 3 card: "Fatture vendita XML", "Fatture acquisto XML", "Autofatture XML"
- Upload modal con file input (accept: .xml, .p7m, .zip)
- Risultati: fatture importate, contatti creati, errori
- Bottone "Importa" per ogni categoria

## Sicurezza

- `defusedxml` per prevenire XXE (CRITICO — era la vulnerabilità #1 dell'originale)
- Validazione estensione file (.xml, .p7m, .zip)
- Limite dimensione XML: 10MB per singolo file
- Limite archivio ZIP: 50MB compressi e 100MB espansi
- Rifiuto di archivi con troppi file o rapporto compressione sospetto (ZIP bomb)
- Validazione XSD FatturaPA prima della persistenza
- Import atomico: `transaction.atomic()` per evitare fatture parziali
- Idempotenza: hash del contenuto XML per evitare doppi import involontari
- Nessun `eval()` o `exec()` sul contenuto XML

## File da creare

- `apps/sdi/services/xml_import.py`
- `apps/sdi/views_import.py`
- `apps/sdi/forms.py` — ImportForm
- `apps/common/exceptions.py` — `XmlImportError`, `XmlSchemaError`
- `templates/imports/index.html`
- `templates/imports/partials/_modal.html`
- `templates/imports/partials/_results.html`
- `tests/test_xml_import.py`
- `tests/fixtures/sample_invoice.xml` — XML di esempio per test
- `tests/fixtures/fatturapa_schema.xsd`

## Criteri di accettazione

- [ ] Import XML singolo crea fattura con righe
- [ ] Import ZIP importa tutti gli XML contenuti
- [ ] Auto-creazione contatto se P.IVA non trovata
- [ ] Auto-creazione aliquota IVA se percentuale non trovata
- [ ] Fatture importate → status received, SDI Delivered (read-only)
- [ ] Gestione namespace XML e rimozione firma
- [ ] `defusedxml` per parsing sicuro (no XXE)
- [ ] Statistiche import visualizzate (conteggi + errori)
- [ ] File P7M gestiti (rimozione envelope firma)
- [ ] XML non conforme a XSD viene rifiutato con errore esplicito
- [ ] ZIP bomb o file fuori soglia vengono bloccati prima del parsing
