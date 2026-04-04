# T29b — Test integrazione + sicurezza

**Fase:** Trasversale — TDD  
**Complessità:** Alta  
**Dipendenze:** T15, T17, T19, T20, T20b, T29  
**Blocca:** T28

---

## Obiettivo

Integrare alla suite principale un pacchetto di test che verifichi i flussi reali end-to-end e i casi ostili piu' probabili.

## Scope test

### Round-trip XML

- Genera XML da fattura vendita
- Reimporta lo stesso XML
- Verifica campi business invarianti: numero, imponibile, IVA, cliente, righe, tipo documento

### Sicurezza XML

- XXE payload malevolo
- XML troppo grande
- ZIP bomb / archivio con dimensione espansa oltre soglia
- XML non conforme a XSD

### Sicurezza webhook

- Firma corretta
- Firma errata
- replay dello stesso evento
- content-type errato
- payload JSON malformato

### Sicurezza UI/HTMX

- POST/DELETE senza CSRF -> 403
- set fiscal year con anno fuori range -> 400

### Contratti OpenAPI SDI

- Mock con `respx` per timeout, retry, 4xx, 5xx
- Verifica redazione token nei log

## File da creare

- `tests/integration/test_xml_roundtrip.py`
- `tests/security/test_xml_security.py`
- `tests/security/test_webhook_security.py`
- `tests/security/test_csrf_and_permissions.py`
- `tests/contracts/test_openapi_client_contract.py`

## Criteri di accettazione

- [ ] Tutti i test round-trip XML verdi
- [ ] XXE e ZIP bomb rigettati
- [ ] Replay webhook non duplica effetti applicativi
- [ ] Nessuna mutazione HTMX senza CSRF
- [ ] Timeout e retry SDI coperti da test di contratto