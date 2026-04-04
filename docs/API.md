# API & Integrazioni — djafatt

## Integrazione SDI (Sistema di Interscambio)

### Architettura

```
djafatt ──httpx──→ OpenAPI SDI REST API ──→ Agenzia delle Entrate SDI
                          ↓ webhook
djafatt ←──POST──── OpenAPI SDI callback
```

### Client: `OpenApiSdiClient`

Modulo: `apps/sdi/services/openapi_client.py`

| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| `send_invoice(xml)` | `POST /invoices` | Invia fattura XML al SDI |
| `get_invoice_status(uuid)` | `GET /invoices/{uuid}` | Stato fattura |
| `download_invoice_xml(uuid)` | `GET /invoices_download/{uuid}` | Scarica XML |
| `get_supplier_invoices(page, per_page)` | `GET /invoices` | Fatture passive |
| `register_business(vat_number)` | `POST /businesses` | Registra azienda |
| `configure_webhooks(url)` | `POST /webhooks` | Configura callback |

**Ambiente:**
- Sandbox: `https://test.sdi.openapi.it`
- Produzione: `https://sdi.openapi.it`

**Sicurezza:**
- Header `Authorization: Bearer <token>`
- Header `Idempotency-Key: SHA-256(xml_content)` su POST
- Timeout: 30 secondi
- Retry: delegato a Celery (con backoff esponenziale)

### Invio Fattura: Task Celery

L'invio SDI è **asincrono** tramite Celery per gestire retry e failure.

**Task:** `apps.sdi.tasks.send_invoice_to_sdi`

| Parametro | Valore |
|-----------|--------|
| Input | `invoice_id` (int) |
| Max retries | 3 |
| Retry backoff | Esponenziale (60s, 120s, 240s) |
| Auto-retry on | `SdiClientError` |

**Flusso:**
1. Carica fattura con relazioni (`contact`, `sequence`)
2. Verifica non già inviata (`sdi_uuid` + `is_sdi_editable()`)
3. Genera XML via `InvoiceXmlGenerator`
4. Invia via `OpenApiSdiClient.send_invoice(xml)`
5. Aggiorna: `sdi_uuid`, `sdi_status=SENT`, `sdi_sent_at=now()`

**View trigger:** `POST /sdi/invoices/<pk>/send-sdi/` (login required)
- Validazione: fattura editabile + almeno 1 riga
- Azione: `send_invoice_to_sdi.delay(pk)`
- Risposta: redirect a lista fatture con messaggio

### Webhook: `/webhooks/sdi/`

Endpoint POST riceve notifiche da OpenAPI SDI.

**Verifica firma:**
1. Legge header `X-Webhook-Signature`
2. Calcola `HMAC-SHA256(body, OPENAPI_SDI_WEBHOOK_SECRET)`
3. Confronto con `secrets.compare_digest` (timing-safe)
4. Se invalido → 403

**Payload:**
```json
{
  "event": "invoice.status_changed",
  "data": {
    "uuid": "abc-123",
    "status": "delivered",
    "timestamp": "2026-01-15T10:00:00Z"
  }
}
```

**Status possibili:** `queued`, `sent`, `delivered`, `accepted`, `rejected`, `error`

---

## XML FatturaPA

### Generazione: `InvoiceXmlGenerator`

Modulo: `apps/sdi/services/xml_generator.py`

Genera XML FatturaPA v1.2.2 conforme allo schema XSD dell'Agenzia delle Entrate.

**Nota IdTrasmittente.IdCodice:** Per persona fisica / forfettario, il campo `1.1.1.2 IdCodice` deve contenere il codice fiscale alfanumerico (16 caratteri), **non** la P.IVA numerica. Il generatore usa `company.tax_code or company.vat_number`.

**Sezioni XML:**
1. `FatturaElettronicaHeader`
   - `DatiTrasmissione` — ID trasmittente, progressivo, formato, codice destinatario
   - `CedentePrestatore` — Dati azienda (da Constance)
   - `CessionarioCommittente` — Dati cliente (da Contact)
2. `FatturaElettronicaBody`
   - `DatiGenerali` — Tipo documento, data, numero, importi, ritenuta, bollo
   - `DatiBeniServizi` — Righe (DettaglioLinee) e riepilogo IVA (DatiRiepilogo)

**Tipi documento:**
| Codice | Tipo |
|--------|------|
| TD01 | Fattura vendita |
| TD04 | Nota di credito |
| TD17 | Autofattura acquisto servizi UE |
| TD18 | Autofattura acquisto beni UE |
| TD19 | Autofattura acquisto beni art.17 |

### Import: `InvoiceXmlImportService`

Modulo: `apps/sdi/services/xml_importer.py`

Importa XML FatturaPA in modelli `PurchaseInvoice`.

**Funzionalità:**
- Parsing sicuro con `defusedxml`
- Auto-creazione Contact se fornitore non presente
- Auto-creazione VatRate se aliquota non presente
- Idempotency via `xml_content_hash` (SHA-256)
- Rifiuto XML > 10MB
- Supporto namespace prefix (`p:`)

---

## URL Endpoints

### Core (`/`)
| URL | View | Metodo |
|-----|------|--------|
| `/` | Dashboard | GET |
| `/login/` | Login | GET/POST |
| `/logout/` | Logout | POST |
| `/setup/` | Setup iniziale | GET/POST |
| `/set-fiscal-year/` | Set anno fiscale | POST |
| `/settings/` | Impostazioni azienda | GET/POST |
| `/users/` | Lista utenti | GET |
| `/users/create/` | Creazione utente | GET/POST |
| `/users/<pk>/edit/` | Modifica utente | GET/POST |

### Contatti (`/contacts/`)
| URL | View | Metodo |
|-----|------|--------|
| `/contacts/` | Lista (con search HTMX) | GET |
| `/contacts/create/` | Creazione | GET/POST |
| `/contacts/<pk>/edit/` | Modifica | GET/POST |
| `/contacts/<pk>/delete/` | Eliminazione | POST |
| `/contacts/<pk>/delete-related/` | Eliminazione con preview cascade | POST |

### Fatture Vendita (`/invoices/`)
| URL | View | Metodo | Note |
|-----|------|--------|------|
| `/invoices/` | Lista | GET | |
| `/invoices/create/` | Creazione | GET/POST | |
| `/invoices/<pk>/edit/` | Modifica | GET/POST | Payment-only se SDI-locked |
| `/invoices/<pk>/delete/` | Eliminazione | POST | |
| `/invoices/<pk>/duplicate/` | Duplica fattura | POST | |
| `/invoices/<pk>/preview/` | PDF preview | GET | WeasyPrint |
| `/invoices/<pk>/xml/` | Download XML | GET | `IT{CF}_{prog}.xml` |
| `/invoices/lines/add/` | Aggiungi riga | POST | HTMX |
| `/invoices/lines/<idx>/remove/` | Rimuovi riga | POST | HTMX |
| `/invoices/lines/totals/` | Ricalcola totali | POST | HTMX |
| `/invoices/lines/product-fill/<id>/` | Autofill prodotto | GET | JSON (fetch) |
| `/invoices/contact-defaults/<id>/` | Default pagamento contatto | GET | HTMX trigger |
| `/invoices/dues/add/` | Aggiungi rata | POST | HTMX |
| `/invoices/dues/<idx>/remove/` | Rimuovi rata | POST | HTMX |

### Fatture Acquisto (`/purchase-invoices/`)
Stesso pattern di fatture vendita (CRUD + preview).

### Autofatture (`/self-invoices/`)
Stesso pattern di fatture vendita (CRUD + preview).

### Prodotti (`/products/`)
| URL | View | Metodo |
|-----|------|--------|
| `/products/` | Lista | GET |
| `/products/create/` | Creazione | GET/POST |
| `/products/<pk>/edit/` | Modifica | GET/POST |
| `/products/<pk>/delete/` | Eliminazione | POST |

### Aliquote IVA (`/vat-rates/`)
| URL | View | Metodo |
|-----|------|--------|
| `/vat-rates/` | Lista | GET |
| `/vat-rates/create/` | Creazione | GET/POST |
| `/vat-rates/<pk>/edit/` | Modifica | GET/POST |
| `/vat-rates/<pk>/delete/` | Eliminazione | POST |
| `/vat-rates/<pk>/delete-related/` | Eliminazione con preview | POST |

### Sequenze (`/sequences/`)
| URL | View | Metodo |
|-----|------|--------|
| `/sequences/` | Lista | GET |
| `/sequences/create/` | Creazione | GET/POST |
| `/sequences/<pk>/edit/` | Modifica | GET/POST |
| `/sequences/<pk>/delete/` | Eliminazione | POST |
| `/sequences/<pk>/delete-related/` | Eliminazione con preview | POST |

### Report (`/reports/`)
| URL | View | Metodo | Note |
|-----|------|--------|------|
| `/reports/` | Report con filtri | GET | Supporta `cash_basis=1` |
| `/reports/csv/` | Export CSV | GET | BOM + semicolon |
| `/reports/pdf/` | Export PDF | GET | WeasyPrint |
| `/reports/payment-form/<pk>/` | Form pagamento inline | GET | HTMX partial |
| `/reports/record-payment/<pk>/` | Registra pagamento | POST | HTMX |
| `/reports/mark-paid/<pk>/` | Segna pagata | POST | HTMX |
| `/reports/mark-unpaid/<pk>/` | Segna non pagata | POST | HTMX |

### Import (`/imports/`)
| URL | View | Metodo |
|-----|------|--------|
| `/imports/` | Import XML/CSV | GET/POST |
| `/imports/sequences/` | Import sequenze | GET/POST |

### SDI (`/sdi/`)
| URL | View | Metodo | Note |
|-----|------|--------|------|
| `/sdi/invoices/<pk>/send-sdi/` | Invio SDI | POST | Login required, Celery async |

### Webhook (`/webhooks/`)
| URL | View | Metodo | Auth |
|-----|------|--------|------|
| `/webhooks/sdi/` | Callback SDI | POST | HMAC-SHA256 |
