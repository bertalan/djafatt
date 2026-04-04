# T20 — Webhook handler SDI

**Fase:** 5 — Integrazione SDI  
**Complessità:** Alta  
**Dipendenze:** T15, T19  
**Blocca:** T21

---

## Obiettivo

Endpoint Django per ricevere notifiche webhook da OpenAPI SDI. Gestisce 3 tipi di evento: ricezione fattura fornitore, notifica stato fattura cliente, conferma invio.

Questo task definisce il flusso base. L'hardening obbligatorio del webhook viene dettagliato nel task supplementare `T20b`.

## Endpoint

```python
# POST /api/openapi/webhook (senza autenticazione — accesso pubblico)
path("api/openapi/webhook", WebhookView.as_view(), name="sdi-webhook"),
```

**SICUREZZA:** L'endpoint è pubblico (nessun login required). Validare payload, firma, content type, idempotenza e rate limit.

## Tipi di evento

### 1. `supplier-invoice` — Fattura fornitore ricevuta

```json
{
    "event": "supplier-invoice",
    "data": {
        "uuid": "abc-123",
        "filename": "IT01234567890_AB123.xml"
    }
}
```

**Azione:**
1. Download XML via `OpenApiSdiClient.download_invoice_xml(uuid)`
2. Import via `InvoiceXmlImportService.import_xml(xml, sequence_id, "purchase")`
3. Log in `SdiLog`

### 2. `customer-notification` — Notifica stato fattura

```json
{
    "event": "customer-notification",
    "data": {
        "uuid": "abc-123",
        "notification_type": "RC",
        "notification_description": "Ricevuta di consegna"
    }
}
```

**Mapping stati SDI:**

| Codice | Stato | Significato | Azione Richiesta |
|---|---|---|---|
| NS | Rejected | Notifica di scarto | Correggere XML e rinviare |
| RC | Delivered | Ricevuta di consegna | Nessuna (tutto OK) |
| MC | Warning | Mancata consegna | **Fallback:** Inviare copia cortesia via Email/PEC (T32) |
| DT | Accepted | Decorrenza termini | Nessuna (accettata per silenzio-assenso) |
| NE | Error | Notifica esito negativo | Gestire errore tecnico |
| AT | Accepted | Attestazione | Nessuna |
| EC | Accepted | Esito committente positivo | Nessuna |

**Azione:**
1. Trova fattura per `sdi_uuid`
2. Aggiorna `sdi_status` con mapping
3. Aggiorna `sdi_message` con descrizione
4. Se stato == `MC`, accoda task invio email di cortesia (vedi T32)
5. Log in `SdiLog` con raw payload

### 3. `customer-invoice` — Conferma invio fattura

```json
{
    "event": "customer-invoice",
    "data": {
        "uuid": "abc-123",
        "sdi_id": "12345678"
    }
}
```

**Azione:**
1. Trova fattura per `sdi_uuid`
2. Aggiorna `sdi_id`
3. Log in `SdiLog`

## Implementazione (`apps/sdi/views_webhook.py`)

```python
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

@csrf_exempt
@require_POST
def webhook_handler(request):
    """Gestisce webhook SDI."""
    verify_webhook_request(request)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    
    event = payload.get("event")
    data = payload.get("data", {})
    
    handlers = {
        "supplier-invoice": handle_supplier_invoice,
        "customer-notification": handle_customer_notification,
        "customer-invoice": handle_customer_invoice,
    }
    
    handler = handlers.get(event)
    if not handler:
        return JsonResponse({"error": f"Unknown event: {event}"}, status=400)
    
    try:
        handler(data)
        return JsonResponse({"status": "ok"})
    except Exception as e:
        logger.exception(f"Webhook error: {e}")
        return JsonResponse({"error": str(e)}, status=500)
```

## File da creare

- `apps/sdi/views_webhook.py`
- `apps/sdi/urls.py` — Route webhook
- `apps/sdi/security.py` — verifica firma e request validation
- `tests/test_webhook.py`

## Criteri di accettazione

- [ ] POST `/api/openapi/webhook` accessibile senza auth
- [ ] `supplier-invoice` scarica XML e importa come PurchaseInvoice
- [ ] `customer-notification` aggiorna sdi_status con mapping corretto
- [ ] `customer-invoice` aggiorna sdi_id
- [ ] CSRF exempt (endpoint API)
- [ ] Payload non valido → 400
- [ ] Evento sconosciuto → 400
- [ ] Errore interno → 500 con log
- [ ] SdiLog creato per ogni evento
- [ ] Firma webhook verificata prima di processare il payload
