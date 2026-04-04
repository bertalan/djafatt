# T19 — Client OpenAPI SDI

**Fase:** 5 — Integrazione SDI  
**Complessità:** Alta  
**Dipendenze:** T17  
**Blocca:** T20, T21

---

## Obiettivo

Client HTTP per l'API OpenAPI SDI: invio fatture, verifica stato, download XML, registrazione azienda, configurazione webhook.

## API OpenAPI SDI

**Base URL:**
- Sandbox: `https://test.sdi.openapi.it`
- Production: `https://sdi.openapi.it`

**Auth:** Bearer token nell'header `Authorization`

## Endpoint da implementare

| Metodo | Endpoint | Funzione |
|---|---|---|
| POST | `/invoices` | Invia XML fattura al SDI |
| GET | `/invoices?type=1&page=1&per_page=50` | Lista fatture fornitori |
| GET | `/invoices/{uuid}` | Dettaglio fattura per UUID |
| GET | `/invoices_download/{uuid}` | Download XML fattura |
| POST | `/business_registry_configurations` | Registra azienda |
| GET | `/business_registry_configurations/{fiscal_id}` | Verifica attivazione |
| POST | `/api_configurations` | Configura webhook |

## Performance e Async

Le chiamate a SdI possono richiedere setup SSL e tempo di risposta (timeout 30s).
**NON eseguire queste chiamate nel thread principale della web request.**
Utilizzare **Celery** (configurato in T01/T19) per:
1. `send_invoice`: Eseguire in background worker.
2. `download_invoice_xml`: Scaricare XML di ricezione (T20 attiva T21).

L'interfaccia utente deve mostrare uno stato "Invio in corso..." e aggiornarsi via polling o HTMX non appena il task asincrono completa il lavoro e salva l'UUID o l'errore.

## Implementazione (`apps/sdi/services/openapi_client.py`)

```python
import httpx
from django.conf import settings

class OpenApiSdiClient:
    """Client per API OpenAPI SDI."""
    
    def __init__(self):
        self.token = settings.OPENAPI_SDI_TOKEN
        sandbox = settings.OPENAPI_SDI_SANDBOX
        self.base_url = (
            "https://test.sdi.openapi.it" if sandbox 
            else "https://sdi.openapi.it"
        )
        self.client = httpx.Client(
            timeout=httpx.Timeout(30.0, connect=5.0),
            headers=self._headers,
        )
    
    @property
    def _headers(self):
        return {"Authorization": f"Bearer {self.token}"}
    
    def send_invoice(self, xml_content: str) -> dict:
        """Invia fattura XML al SDI. Ritorna {uuid, status}."""
        response = self.client.post(
            f"{self.base_url}/invoices",
            content=xml_content,
            headers={
                "Content-Type": "application/xml",
                "Idempotency-Key": self._build_idempotency_key(xml_content),
            },
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("success"):
            raise SdiError(data.get("message", "Unknown error"))
        return data["data"]
    
    def get_invoice_status(self, uuid: str) -> dict:
        """Verifica stato fattura per UUID."""
        response = httpx.get(
            f"{self.base_url}/invoices/{uuid}",
            headers=self._headers,
        )
        response.raise_for_status()
        return response.json()["data"]
    
    def download_invoice_xml(self, uuid: str) -> str:
        """Scarica XML fattura per UUID."""
        response = httpx.get(
            f"{self.base_url}/invoices_download/{uuid}",
            headers=self._headers,
        )
        response.raise_for_status()
        return response.text
    
    def get_supplier_invoices(self, page=1, per_page=50) -> dict:
        """Lista fatture ricevute (fornitori)."""
        response = httpx.get(
            f"{self.base_url}/invoices",
            params={"type": 1, "page": page, "per_page": per_page},
            headers=self._headers,
        )
        response.raise_for_status()
        return response.json()
    
    def register_business(self, vat_number: str, pec: str) -> dict:
        """Registra azienda per e-invoicing."""
        ...
    
    def configure_webhooks(self, webhook_url: str) -> dict:
        """Configura URL webhook per notifiche."""
        ...

class SdiError(Exception):
    pass
```

## Requisiti di robustezza

- Token letto da env o secret provider cifrato, non da Constance in chiaro
- Timeout e retry con backoff per errori transienti `5xx` e timeout
- `Idempotency-Key` per evitare doppi invii accidentali
- Logging redatto: mai serializzare il bearer token
- Traduzione errori `httpx` in `SdiClientError`

## Logica invio fattura

```python
def send_invoice_to_sdi(invoice: Invoice) -> None:
    """Genera XML, invia al SDI, aggiorna stato."""
    # 1. Genera XML
    generator = InvoiceXmlGenerator()
    xml = generator.generate(invoice)
    
    # 2. Valida XML localmente
    if not validate_xml(xml):
        raise SdiError("XML non valido")
    
    # 3. Invia al SDI
    client = OpenApiSdiClient()
    result = client.send_invoice(xml)
    
    # 4. Aggiorna fattura
    invoice.sdi_uuid = result["uuid"]
    invoice.sdi_status = SdiStatus.SENT
    invoice.sdi_sent_at = timezone.now()
    invoice.status = "sent"
    invoice.save()
    
    # 5. Log
    SdiLog.objects.create(
        invoice=invoice,
        event_type="send",
        status=SdiStatus.SENT,
        message=f"Inviata al SDI: {result['uuid']}",
    )
```

## File da creare

- `apps/sdi/services/openapi_client.py`
- `apps/sdi/services/invoice_sender.py` — orchestrazione invio
- `tests/test_openapi_client.py` (con mock httpx)

## Settings/secret aggiunti

```python
OPENAPI_SDI_TOKEN = env("OPENAPI_SDI_TOKEN", default="")
OPENAPI_SDI_SANDBOX = env.bool("OPENAPI_SDI_SANDBOX", default=True)
```

## Criteri di accettazione

- [ ] `send_invoice()` invia XML e ritorna UUID
- [ ] `get_invoice_status()` verifica stato per UUID
- [ ] `download_invoice_xml()` scarica XML
- [ ] `get_supplier_invoices()` con paginazione
- [ ] Errori API gestiti con `SdiError`
- [ ] Sandbox/production switch da settings
- [ ] Headers auth corretti
- [ ] Timeout configurato (30s)
- [ ] Test con mock httpx (no chiamate reali)
- [ ] Token non compare in log o traceback applicativi
- [ ] Retry/idempotency coperti da test dedicati
