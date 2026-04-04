# T17 — Generazione XML FatturaPA (python-a38)

**Fase:** 5 — Integrazione SDI  
**Complessità:** CRITICA  
**Dipendenze:** T03, T11  
**Blocca:** T18, T19

---

## Obiettivo

Generare XML FatturaPA v1.2.2 valido per l'invio al Sistema di Interscambio, usando la libreria `a38`. Questo è il **task più critico** dell'intero progetto.

## Libreria a38

Repository: https://github.com/Truelite/python-a38  
Pacchetto PyPI: `a38` (attenzione: il nome del pacchetto è `a38`, non `python-a38`)  
Approccio: modello dati dichiarativo Python → serializzazione XML automatica.

```python
from a38.fattura import FatturaElettronica, FatturaElettronicaHeader, FatturaElettronicaBody
from a38.fattura import DatiTrasmissione, CedentePrestatore, CessionarioCommittente
from a38.fattura import DatiGeneraliDocumento, DettaglioLinee, DatiRiepilogo
```

## Servizio generazione (`apps/sdi/services/xml_generator.py`)

```python
class InvoiceXmlGenerator:
    """Genera XML FatturaPA da un'Invoice Django."""
    
    def generate(self, invoice: Invoice) -> str:
        """Genera XML completo per una fattura."""
        fattura = FatturaElettronica(
            FatturaElettronicaHeader=self._build_header(invoice),
            FatturaElettronicaBody=[self._build_body(invoice)],
        )
        # Serializza a XML string
        return fattura.to_xml()
    
    def _build_header(self, invoice):
        """Header: trasmissione + cedente + cessionario."""
        company = self._get_company_settings()
        contact = invoice.contact
        
        return FatturaElettronicaHeader(
            DatiTrasmissione=DatiTrasmissione(
                IdTrasmittente={"IdPaese": "IT", "IdCodice": company.vat_number},
                ProgressivoInvio=str(invoice.sequential_number).zfill(5),
                FormatoTrasmissione="FPR12",  # Privati
                CodiceDestinatario=contact.get_sdi_code_for_xml(),
                # PECDestinatario se CodiceDestinatario == "0000000"
            ),
            CedentePrestatore=self._build_cedente(company),
            CessionarioCommittente=self._build_cessionario(contact),
        )
    
    def _build_cedente(self, company):
        """Cedente/Prestatore = la nostra azienda."""
        return CedentePrestatore(
            DatiAnagrafici={
                "IdFiscaleIVA": {"IdPaese": "IT", "IdCodice": company.vat_number},
                "CodiceFiscale": company.tax_code,
                "Anagrafica": {"Denominazione": company.name},
                "RegimeFiscale": company.fiscal_regime,
            },
            Sede={
                "Indirizzo": company.address,
                "CAP": company.postal_code,
                "Comune": company.city,
                "Provincia": company.province,
                "Nazione": "IT",
            },
        )
    
    def _build_cessionario(self, contact):
        """Cessionario/Committente = il cliente."""
        dati = {
            "Anagrafica": {"Denominazione": contact.name},
        }
        if contact.is_italian():
            dati["IdFiscaleIVA"] = {"IdPaese": "IT", "IdCodice": contact.get_vat_number_clean()}
            if contact.tax_code:
                dati["CodiceFiscale"] = contact.tax_code
        else:
            dati["IdFiscaleIVA"] = {"IdPaese": contact.country_code, "IdCodice": contact.get_vat_number_clean()}
        
        return CessionarioCommittente(
            DatiAnagrafici=dati,
            Sede={
                "Indirizzo": contact.address or ".",
                "CAP": contact.get_postal_code_for_xml(),
                "Comune": contact.city or ".",
                "Provincia": contact.get_province_for_xml(),
                "Nazione": contact.country_code,
            },
        )
    
    def _build_body(self, invoice):
        """Body: dati generali + righe + riepilogo + pagamento."""
        body = FatturaElettronicaBody(
            DatiGenerali=self._build_dati_generali(invoice),
            DatiBeniServizi={
                "DettaglioLinee": self._build_lines(invoice),
                "DatiRiepilogo": self._build_riepilogo(invoice),
            },
        )
        
        # Pagamento
        if invoice.payment_method:
            body.DatiPagamento = self._build_pagamento(invoice)
        
        return body
    
    def _build_lines(self, invoice) -> list:
        """Righe dettaglio."""
        lines = []
        for i, line in enumerate(invoice.lines.select_related("vat_rate").all(), 1):
            lines.append(DettaglioLinee(
                NumeroLinea=i,
                Descrizione=line.description,
                Quantita=f"{line.quantity:.2f}",
                UnitaMisura=line.unit_of_measure or None,
                PrezzoUnitario=f"{line.unit_price / 100:.2f}",
                PrezzoTotale=f"{line.total / 100:.2f}",
                AliquotaIVA=f"{line.vat_rate.percent:.2f}",
                Natura=line.vat_rate.nature or None,
            ))
        return lines
    
    def _build_riepilogo(self, invoice) -> list:
        """Riepilogo per aliquota IVA."""
        riepilogo = []
        for summary in invoice.get_vat_summary():
            riepilogo.append(DatiRiepilogo(
                AliquotaIVA=f"{summary['vat_rate'].percent:.2f}",
                ImponibileImporto=f"{summary['taxable'] / 100:.2f}",
                Imposta=f"{summary['vat'] / 100:.2f}",
                EsigibilitaIVA=invoice.vat_payability,
                Natura=summary['vat_rate'].nature or None,
            ))
        return riepilogo
```

## Validazione pre-rischio

Prima dell'invio, validare l'XML generato:
1. Struttura completa (campi obbligatori presenti)
2. Formattazione importi (2 decimali)
3. Codice SDI valido
4. P.IVA/CF presenti

## ⚠️ Rischio critico

**python-a38 potrebbe non supportare tutti i campi.** Verificare:
- [ ] Ritenuta d'acconto (`DatiRitenuta`)
- [ ] Bollo virtuale (`DatiBollo`)
- [ ] Split payment esigibilità "S"
- [ ] Sconto/maggiorazione sulle righe

Se python-a38 non supporta un campo, generare XML raw con `lxml` come fallback.

## File da creare

- `apps/sdi/services/xml_generator.py`
- `tests/test_xml_generator.py`
- `tests/fixtures/expected_invoice.xml` — XML atteso per confronto

## Criteri di accettazione

- [ ] XML generato è FatturaPA v1.2.2 valido
- [ ] Header trasmissione corretto (IdTrasmittente, CodiceDestinatario)
- [ ] Cedente = dati azienda da Constance
- [ ] Cessionario = dati contatto con logica Italia/estero
- [ ] Righe con importi a 2 decimali (centesimi → euro)
- [ ] Riepilogo IVA raggruppato per aliquota
- [ ] Bollo virtuale presente se applicato
- [ ] Ritenuta d'acconto presente se abilitata
- [ ] Clienti esteri: SDI "XXXXXXX", CAP "00000", Provincia "EE"
- [ ] XML validabile contro XSD FatturaPA
