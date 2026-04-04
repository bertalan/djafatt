# djafatt — Piano di refactoring

Riscrittura completa di **Fatturino** (Laravel) in **Django 6.0 + HTMX + a38**.

**Stack target:** Django 6.0.x · Python 3.12+ · PostgreSQL 17 · HTMX 2 · Tailwind 4 · DaisyUI 5 · Vite 7 · a38 · Celery + Redis

> **Produzione multiagente:** Prima di implementare qualsiasi task, leggere [T00-convenzioni-agenti.md](T00-convenzioni-agenti.md) — contiene stack vincolante, divieti, naming, pattern HTMX e checklist.

---

## Decisione frontend

**HTMX 2 + Tailwind 4 + DaisyUI 5 + Vite 7 — zero framework JS.**

Motivazione: djafatt è un'applicazione CRUD pura (form, tabelle, ricerche, PDF). Tutte le interazioni mappate (ricerca live, righe fattura dinamiche, totali live, autofill, conferme) sono pattern HTMX standard. Non servono state management client-side, SPA routing, né componenti React/Vue. L'unico file JavaScript è `main.js` (~10 righe: import HTMX + CSRF injection). Dettagli e regole vincolanti in [T05-layout-navigazione.md](T05-layout-navigazione.md) sezione "Regole frontend vincolanti".

---

## Fasi e task

### Meta-documento

| # | Task | File | Note |
|---|---|---|---|
| T00 | [Convenzioni per agenti](T00-convenzioni-agenti.md) | Stack, divieti, naming, pattern, checklist | **Leggere prima di ogni task** |

### Fase 1 — Fondamenta (T01-T05)

| # | Task | File | Complessità |
|---|---|---|---|
| T01 | [Scaffold progetto + Docker](T01-scaffold.md) | Django project, docker-compose, PostgreSQL | Alta |
| T02 | [Modelli anagrafiche](T02-models-anagrafiche.md) | Contact, VatRate, Sequence, Product | Media |
| T03 | [Modelli fattura](T03-models-fattura.md) | Invoice, InvoiceLine, proxy models | Alta |
| T04 | [Auth + Setup Wizard](T04-auth-setup.md) | Login, setup flow, Constance | Media |
| T05 | [Layout + navigazione](T05-layout-navigazione.md) | Base template, sidebar, HTMX, Tailwind | Media |

### Fase 2 — CRUD principali (T06-T10)

| # | Task | File | Complessità |
|---|---|---|---|
| T06 | [CRUD Contatti](T06-crud-contatti.md) | Contact views, search HTMX | Media |
| T07 | [CRUD Aliquote IVA](T07-crud-aliquote-iva.md) | VatRate CRUD, system protection | Bassa |
| T08 | [CRUD Sequenze](T08-crud-sequenze.md) | Sequence CRUD, pattern formatting | Bassa |
| T09 | [CRUD Prodotti](T09-crud-prodotti.md) | Product CRUD, cents conversion | Bassa |
| T10 | [CRUD Fatture vendita](T10-crud-fatture-vendita.md) | Full invoice CRUD + inline lines | Alta |

### Fase 3 — Motore calcolo, righe e pagamenti (T11-T12, T33)

| # | Task | File | Complessità |
|---|---|---|---|
| T11 | [Engine calcolo totali](T11-engine-calcolo-totali.md) | Net/VAT/withholding/stamp/split | Alta |
| T12 | [Righe fattura HTMX](T12-righe-fattura-htmx.md) | Add/remove lines, live totals | Alta |
| T33 | [Scadenze e pagamenti](T33-scadenze-pagamenti.md) | PaymentDue, PaymentRecord, scadenzario | Alta |

### Fase 4 — Import/Export XML e tipi documento (T13-T18, T34)

| # | Task | File | Complessità |
|---|---|---|---|
| T13 | [CRUD Fatture acquisto](T13-crud-fatture-acquisto.md) | PurchaseInvoice proxy, supplier filter | Media |
| T14 | [CRUD Autofatture](T14-crud-autofatture.md) | SelfInvoice TD17/TD18/TD19/TD28 | Media |
| T15 | [Import XML FatturaPA](T15-import-xml.md) | defusedxml, namespace, signature | Alta |
| T16 | [Import CSV Fattura24](T16-import-csv-fattura24.md) | Semicolon CSV contact import | Bassa |
| T17 | [XML generator vendite](T17-xml-generator-vendite.md) | a38 FatturaPA generation | **Critica** |
| T18 | [XML generator autofatture](T18-xml-generator-autofatture.md) | Self-invoice XML, inverted parties | Alta |
| T34 | [Note di credito TD04](T34-note-di-credito.md) | Storno totale/parziale, DatiFattureCollegate | Media |

### Fase 5 — Integrazione SDI (T19-T22, T35)

| # | Task | File | Complessità |
|---|---|---|---|
| T19 | [Client OpenAPI SDI](T19-client-openapi-sdi.md) | httpx client, send/status/download | Alta |
| T20 | [Webhook SDI](T20-webhook-sdi.md) | Webhook handler, 3 event types | Media |
| T21 | [Sync fatture fornitori](T21-sync-fornitori-command.md) | Management command, pagination | Media |
| T22 | [SupplierInvoice model + UI](T22-supplier-invoice-model-ui.md) | Model 21 fields, list, detail | Media |
| T35 | [Celery async tasks](T35-celery-async-tasks.md) | Worker, routing, Beat periodic, monitoring | Alta |

### Fase 6 — Dashboard, Settings, Deploy (T23-T32, T36)

| # | Task | File | Complessità |
|---|---|---|---|
| T23 | [Dashboard metriche](T23-dashboard-metriche.md) | ReportService, stats cards | Media |
| T24 | [Pagine Settings](T24-pagine-settings.md) | 3 tab: Azienda, Fatturazione, SDI | Media |
| T25 | [Anno fiscale](T25-anno-fiscale.md) | Selector, filtro globale, read-only | Bassa |
| T26 | [SDI Log audit](T26-sdi-log-audit.md) | SdiLog model, invoice detail | Bassa |
| T27 | [Traduzioni it/en](T27-traduzioni.md) | Django .po files, ~200 stringhe | Bassa |
| T28 | [Docker produzione](T28-docker-produzione.md) | Multi-stage, Gunicorn, backup, health | Media |
| T29 | [Test suite](T29-test-suite.md) | pytest + factory_boy, 50+ test | Alta |
| T30 | [Brandfetch logo](T30-brandfetch-logo.md) | CDN logo da email domain | Bassa |
| T31 | [PDF cortesia + invio auto](T31-pdf-generation.md) | Weasyprint, watermark, multilingua, email auto | Media |
| T32 | [Notifiche Email/PEC](T32-notifiche-email-pec.md) | Celery tasks, dual SMTP, MC fallback, retry | Alta |
| T36 | [Nginx + SSL](T36-nginx-ssl-reverse-proxy.md) | Reverse proxy, Let's Encrypt, rate limiting | Media |

### Task supplementari — Hardening e qualità

| # | Task | File | Complessità |
|---|---|---|---|
| T01e | [CI + quality gates](T01e-ci-quality-gates.md) | pytest, ruff, mypy, coverage, build | Media |
| T03b | [Error handling + osservabilità](T03b-error-handling-osservabilita.md) | eccezioni dominio, logging strutturato, audit | Media |
| T20b | [Hardening webhook SDI](T20b-hardening-webhook-sdi.md) | firma HMAC, idempotenza, rate limiting | Alta |
| T29b | [Test integrazione + sicurezza](T29b-test-integrazione-sicurezza.md) | round-trip XML, webhook signing, XXE, CSRF | Alta |

---

## Riepilogo

- **T00**: Convenzioni vincolanti per produzione multiagente (leggere per primo)
- **36 task** in **6 fasi** + **4 task supplementari**
- **Complessità critica:** T17 (XML generator)
- **Complessità alta:** T01, T03, T10, T11, T12, T15, T18, T19, T29, T32, T33, T35
- **Dipendenza principale**: T01 (scaffold) → tutto il resto
- **Stack**: Django 6.0.3 + HTMX 2 + a38 + PostgreSQL 17 + Tailwind 4 / DaisyUI 5 + Celery/Redis
- **Frontend**: puro HTMX 2. Zero Alpine/React/Vue. Regole in T05, convenzioni in T00
- **Python**: >= 3.12 (requisito Django 6.0)

## Debolezze corrette nel piano

- Segreti SDI: non vanno salvati in chiaro nelle impostazioni dinamiche; usare env o storage cifrato con UI write-only.
- Webhook: non basta renderlo pubblico; servono verifica firma, idempotenza, rate limiting e test negativi.
- XML: `defusedxml` da solo non basta; servono limiti di dimensione, difese ZIP bomb, validazione schema e rollback atomico.
- TDD: la suite deve includere test di integrazione e sicurezza, non solo unit test funzionali.
- Pagamenti: senza scadenzario e tracciamento incassi il gestionale è incompleto (T33).
- Note di credito: obbligatorie per legge, impossibile cancellare fatture inviate al SdI (T34).
- Async: tutte le operazioni SDI e email devono essere asincrone via Celery (T35).
- Reverse proxy: Gunicorn non deve essere esposto direttamente su Internet (T36).
- Email cortesia: invio automatico a tutti i clienti con email, non solo come fallback MC (T31/T32).
