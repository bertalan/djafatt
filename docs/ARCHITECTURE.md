# Architettura — djafatt

## Principi

1. **Service Layer Pattern** — Logica business nei service, modelli e view sottili.
2. **Importi in centesimi** — Tutti gli importi monetari sono `IntegerField` in centesimi (€1.00 = 100).
3. **Proxy Models** — Fatture vendita, acquisto e autofatture sono proxy dello stesso modello `Invoice`.
4. **Sicurezza XML** — Tutto il parsing XML tramite `defusedxml`. Mai `xml.etree.ElementTree` diretto.
5. **Single-tenant** — Un'installazione per azienda. Dati azienda in `django-constance`.

## Struttura Progetto

```
djafatt/                    # Progetto Django
├── settings/
│   ├── base.py             # Settings condivisi
│   ├── dev.py              # Sviluppo (DEBUG, debug_toolbar)
│   ├── prod.py             # Produzione (SSL, HSTS, WhiteNoise)
│   └── test.py             # Test (MD5 hasher, eager Celery)
├── celery.py               # Configurazione Celery
├── urls.py                 # URL root
└── wsgi.py / asgi.py

apps/
├── common/                 # Utilities condivise
│   ├── exceptions.py       # Gerarchia eccezioni custom
│   ├── validators.py       # Validatori P.IVA, CF, paesi EU
│   └── logging.py          # RedactingFilter per dati sensibili
├── core/                   # Views principali, middleware
│   ├── views.py            # Dashboard, fiscal year
│   ├── middleware/
│   │   └── request_id.py   # RequestIdMiddleware (UUID per request)
│   └── urls.py
├── contacts/               # Anagrafica clienti/fornitori
│   ├── models.py           # Contact (con helper SDI)
│   └── admin.py
├── invoices/               # Fatture (core business)
│   ├── models.py           # Invoice, InvoiceLine, VatRate, Sequence, PaymentDue, Proxy models
│   ├── signals.py          # Auto-ricalcolo totali
│   ├── views_invoice.py    # CRUD fatture vendita
│   ├── views_purchase.py   # CRUD fatture acquisto
│   ├── views_self_invoice.py # CRUD autofatture
│   ├── views_lines.py      # HTMX: add/remove riga, totali, product autofill
│   ├── views_reports.py    # Report, export CSV/PDF, payment tracking
│   ├── views_pdf.py        # PDF preview, XML download
│   ├── forms.py            # InvoiceForm, InvoiceLineFormSet, PaymentDueFormSet
│   ├── services/
│   │   └── calculations.py # TotalsCalculationService
│   └── admin.py
├── products/               # Anagrafica prodotti/servizi
│   └── models.py           # Product (prezzo in centesimi)
├── sdi/                    # Integrazione Sistema di Interscambio
│   ├── services/
│   │   ├── openapi_client.py  # Client REST OpenAPI SDI
│   │   ├── xml_generator.py   # FatturaPA XML generator
│   │   └── xml_importer.py    # Import XML fatture passive
│   ├── tasks.py            # Celery task: send_invoice_to_sdi (retry 3×, backoff)
│   ├── views_send.py       # View POST invio SDI (login_required)
│   ├── urls.py             # URL sdi-send
│   └── security.py         # HMAC webhook verification
└── notifications/          # Email/PEC (stub)

tests/
├── conftest.py             # Fixtures condivise
├── factories.py            # factory-boy factories
├── test_models.py          # Test modelli
├── test_calculations.py    # Test motore calcolo
├── test_xml_generator.py   # Test generazione XML
├── test_xml_import.py      # Test import XML
├── test_views.py           # Test views e HTMX
├── test_openapi_client.py  # Test client SDI
├── test_webhook.py         # Test webhook security
├── test_error_handling.py  # Test gerarchia eccezioni
├── test_sdi_send.py        # Test invio SDI: task + view (mock)
├── test_sdi_sandbox.py     # Test accettazione sandbox SDI (@sandbox)
├── test_sdi_connection.py  # Test connessione SDI
├── test_multiuser.py       # Test multi-utente e permessi
├── test_invoice_features.py # Test funzionalità fattura (duplicate, locked, ecc.)
├── test_payment_dues.py    # Test scadenze e pagamenti
├── test_reports.py         # Test report e principio di cassa
└── security/
    ├── test_xml_security.py       # XXE, billion laughs, SSRF
    └── test_csrf_and_permissions.py # CSRF, permessi, headers
```

## Flusso Fattura Vendita

```
Utente → HTMX form → View → InvoiceLine.save()
                                    ↓ signal
                              calculate_totals()
                              TotalsCalculationService
                                    ↓
                        Invoice (totali aggiornati)
                                    ↓
              Utente → POST /sdi/invoices/<pk>/send-sdi/
                                    ↓
                  send_to_sdi_view → validazione
                    (is_sdi_editable, has lines)
                                    ↓
                  send_invoice_to_sdi.delay(pk)   ← Celery async
                                    ↓
                    InvoiceXmlGenerator.generate()
                                    ↓
                    OpenApiSdiClient.send_invoice()
                    (retry: 3×, backoff esponenziale)
                                    ↓
                  Invoice: sdi_uuid, sdi_status=SENT
                                    ↓
                            SDI webhook callback
                                    ↓
                        Invoice.sdi_status aggiornato
```

## Flusso Fattura Acquisto

```
SDI webhook / sync_fornitori command
            ↓
OpenApiSdiClient.get_supplier_invoices()
            ↓
InvoiceXmlImportService.import_xml()
  ├── defusedxml parsing
  ├── Contact auto-create
  ├── VatRate auto-create
  └── PurchaseInvoice created
```

## Frontend Build Pipeline

```
static/src/main.js          ─┐
  import "./main.css"        │    Vite 7 (build --watch)
  import "htmx.org"          ├──────────────────────────→ static/dist/
static/src/main.css          │                              ├── .vite/manifest.json
  @import "tailwindcss"      │                              └── assets/
  @plugin "daisyui"         ─┘                                  ├── main-*.js (61 kB)
                                                                └── style-*.css (10 kB)
```

- **Entry point unico**: `main.js` importa CSS (Tailwind 4 + DaisyUI 5) e JS (HTMX 2)
- **Build mode**: `vite build --watch` nel container `node` — Django serve i file compilati
- **django-vite**: `dev_mode=False`, legge `manifest.json` per generare `<link>` + `<script>` tag
- **CSRF auto-injection**: HTMX configRequest inietta `X-CSRFToken` su POST/PUT/DELETE
- **Product autofill**: JS `fetch()` → JSON → popola campi riga (non HTMX, per evitare swap indesiderati)
- **Contact defaults**: HTMX ajax → evento `contactPaymentFill` → JS popola campi pagamento
- **Totali riga**: HTMX `hx-post` con `hx-include="closest form"` per ricalcolo server-side

## Flusso Report e Pagamenti

```
Utente → /reports/ (filtri: periodo, tipo, contatto, stato pagamento, cassa)
                ↓
        _parse_filters() → _get_filtered_invoices()
                ↓
        Aggregazioni: vendite/acquisti × pagato/da pagare
                ↓
        Tabella con sorting client-side (JS data-sort)
                ↓
        Azioni inline HTMX:
          ├── "Registra pagamento" → payment_form → record_payment
          ├── "Segna pagata" → mark_paid (crea PaymentDue totale)
          └── "Segna non pagata" → mark_unpaid (elimina PaymentDue)
                ↓
        Invoice.sync_paid_status() aggiorna paid_at/paid_via
```

## Convenzioni

- **Branch**: `feat/TXXX-description`, `fix/TXXX-description`
- **Commit**: `feat(TXXX): description`, `fix(TXXX): description`
- **Test naming**: `test_<what>_<condition>` — es. `test_stamp_duty_below_threshold`
- **Service methods**: verbo all'infinito — `calculate()`, `generate()`, `import_xml()`
