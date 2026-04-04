# T03b — Error handling + osservabilità

**Fase:** Trasversale — Architettura  
**Complessità:** Media  
**Dipendenze:** T01, T03  
**Blocca:** T15, T19, T20, T21

---

## Obiettivo

Definire una gerarchia coerente di eccezioni, logging strutturato e audit trail per rendere import XML, SDI e workflow di fatturazione debuggabili e manutenibili.

## Problema che risolve

- Errori tecnici e business oggi rischiano di essere mescolati
- I task critici parlano di `raise Exception` o `logger.exception` generici
- Senza correlation ID e payload redaction il debug in produzione diventa fragile

## Gerarchia eccezioni

```python
class DjafattError(Exception):
    code = "application_error"

class ValidationError(DjafattError):
    code = "validation_error"

class XmlImportError(DjafattError):
    code = "xml_import_error"

class XmlSchemaError(XmlImportError):
    code = "xml_schema_error"

class SdiClientError(DjafattError):
    code = "sdi_client_error"

class SdiWebhookSecurityError(DjafattError):
    code = "sdi_webhook_security_error"

class BusinessRuleViolation(DjafattError):
    code = "business_rule_violation"
```

## Logging strutturato

- Formato JSON in produzione
- Campi minimi: `timestamp`, `level`, `logger`, `event`, `invoice_id`, `sdi_uuid`, `request_id`, `user_id`
- Redazione automatica di token, IBAN, secret e payload sensibili
- `request_id` middleware per correlare UI, import, API client e webhook

## Audit trail

- Login falliti
- Setup iniziale completato
- Cambio impostazioni sensibili
- Invio fattura al SDI
- Ricezione webhook e relativo esito sicurezza

## File da creare

- `apps/common/exceptions.py`
- `apps/common/logging.py`
- `apps/core/middleware/request_id.py`
- `tests/test_error_handling.py`

## Criteri di accettazione

- [ ] I servizi XML e SDI sollevano eccezioni dominio specifiche
- [ ] Nessun `except Exception` silenzioso nei task critici
- [ ] Log strutturati con request ID e campi dominio
- [ ] Segreti e payload sensibili redatti nei log
- [ ] Errori business traducibili in messaggi utente chiari