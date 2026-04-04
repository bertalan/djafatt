# T18 — Generazione XML autofatture (TD17/18/19/28)

**Fase:** 5 — Integrazione SDI  
**Complessità:** Alta  
**Dipendenze:** T17, T14  
**Blocca:** T19

---

## Obiettivo

Estendere il generatore XML (T17) per supportare autofatture con le specifiche SDI per TD17, TD18, TD19, TD28.

## Differenze rispetto a fattura vendita

| Campo | Vendita (TD01) | Autofattura (TD17-28) |
|---|---|---|
| TipoDocumento | TD01 | TD17/TD18/TD19/TD28 |
| CedentePrestatore | Nostra azienda | **Fornitore estero** |
| CessionarioCommittente | Cliente | **Nostra azienda** |
| SoggettoEmittente | Non presente | **CC** (cessionario/committente) |
| TerzoIntermediarioOSoggettoEmittente | Non presente | **Dati nostra azienda** |
| DatiFattureCollegate | Non presente | **Riferimento fattura originale** |

## Implementazione (`apps/sdi/services/xml_self_invoice.py`)

```python
class SelfInvoiceXmlGenerator(InvoiceXmlGenerator):
    """Genera XML per autofatture TD17/18/19/28."""
    
    def _build_header(self, invoice):
        company = self._get_company_settings()
        supplier = invoice.contact  # Il fornitore (cedente)
        
        header = FatturaElettronicaHeader(
            DatiTrasmissione=DatiTrasmissione(
                IdTrasmittente={"IdPaese": "IT", "IdCodice": company.vat_number},
                ProgressivoInvio=str(invoice.sequential_number).zfill(5),
                FormatoTrasmissione="FPR12",
                CodiceDestinatario=company.sdi_code,  # A noi stessi
            ),
            # INVERTITO: cedente = fornitore estero
            CedentePrestatore=self._build_foreign_supplier(supplier),
            # INVERTITO: cessionario = nostra azienda
            CessionarioCommittente=self._build_our_company(company),
            # NUOVO: soggetto emittente = CC
            SoggettoEmittente="CC",
            # NUOVO: terzo intermediario = nostra azienda
            TerzoIntermediarioOSoggettoEmittente=self._build_intermediary(company),
        )
        return header
    
    def _build_body(self, invoice):
        body = super()._build_body(invoice)
        
        # NUOVO: DatiFattureCollegate (riferimento fattura originale)
        if invoice.related_invoice_number:
            body.DatiGenerali.DatiFattureCollegate = [{
                "IdDocumento": invoice.related_invoice_number,
                "Data": invoice.related_invoice_date.isoformat(),
            }]
        
        return body
    
    def _build_foreign_supplier(self, contact):
        """CedentePrestatore = fornitore estero."""
        dati = {
            "IdFiscaleIVA": {
                "IdPaese": contact.country_code,
                "IdCodice": contact.get_vat_number_clean(),
            },
            "Anagrafica": {"Denominazione": contact.name},
        }
        return CedentePrestatore(
            DatiAnagrafici=dati,
            Sede={
                "Indirizzo": contact.address or ".",
                "CAP": contact.get_postal_code_for_xml(),
                "Comune": contact.city or ".",
                "Provincia": contact.get_province_for_xml(),
                "Nazione": contact.country_code,
            },
        )
```

## File da creare

- `apps/sdi/services/xml_self_invoice.py`
- `tests/test_xml_self_invoice.py`

## Criteri di accettazione

- [ ] XML generato ha TipoDocumento corretto (TD17/18/19/28)
- [ ] CedentePrestatore = fornitore estero
- [ ] CessionarioCommittente = nostra azienda
- [ ] SoggettoEmittente = "CC"
- [ ] TerzoIntermediario con dati azienda
- [ ] DatiFattureCollegate con numero/data fattura originale
- [ ] XML validabile contro XSD FatturaPA
