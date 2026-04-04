# T20b — Hardening webhook SDI

**Fase:** Trasversale — Sicurezza integrazione  
**Complessità:** Alta  
**Dipendenze:** T19, T20, T03b  
**Blocca:** T21, T28

---

## Obiettivo

Rendere il webhook SDI sicuro e idempotente. Un endpoint pubblico senza firma, rate limit e deduplica non e' accettabile per produzione.

## Hardening richiesto

### 1. Verifica firma

- Header previsto: `X-Openapi-Signature` o equivalente definito dal provider
- Algoritmo: HMAC SHA-256 su raw body
- Secret: da env o secret store cifrato, mai mostrato in chiaro nella UI

```python
expected = hmac.new(secret.encode(), request.body, hashlib.sha256).hexdigest()
if not secrets.compare_digest(expected, signature_header):
    raise SdiWebhookSecurityError("invalid_signature")
```

### 2. Idempotenza

- Salvare `event_id` o fingerprint del payload
- Se il medesimo evento arriva due volte: rispondere `200` senza rieseguire il side effect

### 3. Rate limiting

- Limite per IP e per finestra temporale
- Risposta `429` su abuso

### 4. Size limit e JSON validation

- `Content-Length` massimo documentato
- Accettare solo `application/json`
- Validare struttura minima: `event`, `data`, identificatori richiesti

### 5. Elaborazione robusta

- Ack rapido e delega a job asincrono se l'elaborazione richiede download/import XML
- Log di sicurezza separati dagli errori business

## File da creare

- `apps/sdi/security.py`
- `apps/sdi/models_webhook.py` o estensione modello audit per idempotenza eventi
- `tests/test_webhook_security.py`

## Criteri di accettazione

- [ ] Firma invalida -> 401 o 403
- [ ] Content-Type errato -> 415
- [ ] Payload duplicato -> nessun side effect duplicato
- [ ] Rate limit -> 429
- [ ] Eventi validi continuano a funzionare
- [ ] Log security distinti dai log applicativi