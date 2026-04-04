# T00 — Convenzioni di progetto per produzione multiagente

**Tipo:** Meta-documento  
**Destinatari:** Qualsiasi agente AI o sviluppatore che implementi task di djafatt  
**Stato:** Vincolante — ogni task DEVE rispettare queste convenzioni
**Convenzioni:** Chat in italiano, commenti al codice e docs inglese

---

## Scopo

Questo documento definisce le regole architetturali, naming e stack vincolanti per l'intero progetto. Prima di implementare qualsiasi task, l'agente **DEVE** leggere questo file e il task specifico.

---

## 1. Stack tecnologico (immutabile)

| Layer | Tecnologia | Versione | Note |
|---|---|---|---|
| Backend | Django | >=6.0,<6.1 | Python >=3.12 obbligatorio |
| Database | PostgreSQL | 17 | Via Docker |
| Frontend interattivo | HTMX | ^2.0 | Unico framework JS ammesso |
| CSS framework | Tailwind CSS | ^4.0 | Utility-first, via Vite |
| Componenti UI | DaisyUI | ^5.0 | Classi semantiche (btn, badge, card, etc.) |
| Build tool | Vite | ^7.0 | Con `@tailwindcss/vite` |
| Django-Vite | django-vite | >=3.1 | Template tag `{% vite %}` |
| XML FatturaPA | a38 | >=0.1.8 | PyPI: `a38` (NON `python-a38`) |
| XML parser sicuro | defusedxml | >=0.7.1 | Mai usare `xml.etree` direttamente |
| HTTP client | httpx | >=0.28 | Per chiamate SDI |
| PDF | WeasyPrint | >=68 | Solo per PDF cortesia |
| Async tasks | Celery | >=5.6 | Redis broker |
| Reverse proxy | Nginx | 1.27 | Produzione (T36) |

### Divieti stack

- **NO Alpine.js** — non serve, eliminato dal progetto
- **NO React / Vue / Svelte / Angular** — architettura server-rendered
- **NO jQuery** — obsoleto
- **NO Hyperscript** — complessità inutile
- **NO librerie JS aggiuntive** senza task dedicato e approvazione
- **NO `python-a38`** — il pacchetto PyPI si chiama `a38`
- **NO `xml.etree.ElementTree`** per input esterno — usare `defusedxml`
- **NO `STATICFILES_STORAGE`** — Django 6.0 usa `STORAGES["staticfiles"]["BACKEND"]`

---

## 2. Struttura progetto

```
djafatt/
├── djafatt/
│   ├── settings/
│   │   ├── base.py         # Settings condivisi
│   │   ├── dev.py          # DEBUG=True, django-debug-toolbar
│   │   ├── prod.py         # Hardenizzato, Gunicorn, HTTPS
│   │   └── test.py         # DB in-memory, email backend test
│   ├── celery.py           # Celery app config
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── common/             # Validatori fiscali, eccezioni dominio, helpers
│   ├── core/               # Auth, layout, setup wizard, dashboard
│   ├── contacts/           # Contatti clienti/fornitori
│   ├── invoices/           # Fatture vendita/acquisto/autofatture/righe
│   ├── products/           # Prodotti/servizi
│   ├── notifications/      # Email/PEC Celery tasks
│   └── sdi/                # Client SDI, webhook, sync fornitori
├── templates/
│   ├── base.html
│   ├── partials/           # _sidebar.html, _messages.html, _header.html
│   └── {app}/
│       ├── index.html
│       ├── form.html
│       └── partials/       # _table.html, _line_row.html, etc.
├── static/src/
│   ├── main.css            # @import "tailwindcss"; @plugin "daisyui";
│   └── main.js             # import "htmx.org"; + CSRF listener (~10 righe)
├── tests/
│   ├── conftest.py         # Fixtures pytest condivise
│   ├── factories.py        # factory_boy factories
│   └── test_*.py           # Un file per modulo/funzionalità
└── docker-compose.yml
```

---

## 3. Convenzioni Python/Django

### Naming

| Elemento | Convenzione | Esempio |
|---|---|---|
| App Django | Singolare, lowercase | `contacts`, `invoices`, `sdi` |
| Model | PascalCase singolare | `Contact`, `Invoice`, `InvoiceLine` |
| View function | snake_case con verbo | `create_invoice`, `delete_contact` |
| View class | PascalCase + View | `InvoicePdfView`, `ContactListView` |
| Service | PascalCase + Service | `TotalsCalculationService`, `InvoicePdfService` |
| URL name | `{app}-{action}` | `invoices-create`, `contacts-list`, `invoices-add-line` |
| Template | `{app}/{nome}.html` | `invoices/form.html`, `contacts/index.html` |
| Partial template | `{app}/partials/_{nome}.html` | `invoices/partials/_totals.html` |
| Test file | `test_{modulo}.py` | `test_totals_engine.py`, `test_xml_generator.py` |
| Factory | `{Model}Factory` | `ContactFactory`, `InvoiceFactory` |

### Pattern architetturali

- **Business logic nei Service**, mai nei model `.save()` o nelle view
- **Model sottili**: solo field, Meta, `__str__`, property semplici
- **View sottili**: chiamano Service, restituiscono template/partial
- **Importi in centesimi**: `integer` per tutti gli importi monetari, mai `Decimal`/`float` nei campi DB
- **Formattazione euro**: template filter `format_cents` (es. `122350` → `"1.223,50"`)

### Sicurezza Django

- Mai `csrf_exempt` su endpoint HTMX mutanti
- Ownership check su OGNI view che accede a dati fattura/contatto
- `LoginRequiredMixin` o `@login_required` su OGNI view
- Segreti (token SDI, etc.) solo in env vars, mai in Constance
- `defusedxml` per qualsiasi XML in ingresso

---

## 4. Convenzioni frontend (template + HTMX + CSS)

### JavaScript: solo `main.js`

```js
// static/src/main.js — QUESTO È L'UNICO FILE JS DEL PROGETTO
import "htmx.org";

document.body.addEventListener("htmx:configRequest", (e) => {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    if (match && e.detail.verb !== "get") {
        e.detail.headers["X-CSRFToken"] = decodeURIComponent(match[1]);
    }
});
```

Non aggiungere altro codice JS. Se un'interazione non è possibile con HTMX + DaisyUI, documentare nel task e proporre soluzione.

### HTMX: pattern ammessi

| Pattern | Attributi | Dove |
|---|---|---|
| Ricerca live | `hx-get` + `hx-trigger="input changed delay:300ms"` + `hx-target` + `hx-push-url="true"` | T06, T22 |
| Add riga | `hx-post` + `hx-target` (append/outerHTML) | T12 |
| Remove riga | `hx-delete` + `hx-target` + `hx-swap="outerHTML"` | T12 |
| Ricalcolo live | `hx-post` + `hx-trigger="input changed delay:300ms"` + `hx-target="#totals-sidebar"` | T12 |
| Autofill prodotto | `hx-get` + `hx-trigger="change"` | T12 |
| Conferma delete | `hx-confirm="Sei sicuro?"` (browser native) | T06-T09 |
| Cambio anno | `hx-post` + `hx-trigger="change"` | T25 |

### CSS: solo Tailwind + DaisyUI

- Classi utility Tailwind per layout: `flex`, `grid`, `gap-*`, `p-*`, `m-*`, `text-*`, `w-*`
- Classi DaisyUI per componenti: `btn`, `badge`, `card`, `drawer`, `alert`, `table`, `input`, `select`, `modal`, `menu`, `stats`, `navbar`, `toast`
- Theme: `data-theme="business"` su `<html>`
- Responsive: `lg:` breakpoint per desktop. Mobile-first.
- **Mai** `style=""` inline. **Mai** CSS custom. **Mai** `<style>` tag nei template.
- **Eccezione**: template PDF (`invoices/pdf/invoice.html`) usa CSS `@page`/`@media print` standalone, senza Tailwind

### Template: partial come unità HTMX

Ogni partial HTMX deve:
1. Avere un **elemento root con `id=`** (es. `<div id="totals-sidebar">`)
2. L'`id` corrisponde esattamente al `hx-target` che lo referenzia
3. Essere **autosufficiente**: renderizzabile da solo con il suo contesto
4. Avere naming `_prefisso.html` (underscore)
5. Non includere `{% extends %}` — solo `{% load %}` e contenuto

---

## 5. Convenzioni test

- Framework: **pytest** + **pytest-django** + **factory-boy**
- Mock HTTP: **respx** (per httpx client SDI)
- Copertura: `pytest --cov` con `--cov-fail-under=80`
- Organizzazione: un file `test_*.py` per modulo/funzionalità, fixtures condivise in `conftest.py`
- **TDD**: per task critici (T11, T17, T19, T20), scrivere test RED prima dell'implementazione
- Test HTMX: verificare response con `django.test.Client` + header `HTTP_HX_REQUEST=True`
- **NO Playwright/Selenium/Cypress** salvo decisione futura esplicita

---

## 6. Convenzioni Docker

- Dev: `docker-compose.yml` con `db` (PostgreSQL 17), `web` (Django), `node` (Vite HMR)
- Prod: `docker-compose.prod.yml` con `db`, `web` (Gunicorn), `redis`, `celery-worker`, `celery-beat`, `nginx`
- Utente non-root in produzione
- `STORAGES` dict (Django 6.0), non `STATICFILES_STORAGE`

---

## 7. Ordine di implementazione

Ogni agente che inizia un task DEVE verificare che le dipendenze elencate nel task siano completate. La sequenza raccomandata:

```
T01 → T01e → T02 → T03 → T03b → T04 → T05 → T06 → T07 → T08 → T09
→ T10 → T11 → T12 → T33 → T34
→ T13 → T14 → T15 → T16 → T17 → T18
→ T35 → T19 → T20 → T20b
→ T31 → T32
→ T21 → T22 → T23 → T24 → T25 → T26 → T27 → T30
→ T36 → T28 → T29 → T29b
```

---

## 8. Checklist pre-commit per agente

Prima di considerare un task completato, l'agente DEVE verificare:

- [ ] `ruff check .` — zero errori
- [ ] `mypy .` — zero errori (o warnings documentati)
- [ ] `pytest` — tutti i test passano
- [ ] `python manage.py check` — zero errori
- [ ] Nessun `# TODO` senza task associato
- [ ] Nessun import `alpine`, `react`, `vue`, `jquery` in qualsiasi file
- [ ] Tutti i template usano `{% vite %}` per asset, mai `<script src="">` manuali
- [ ] Nessun `csrf_exempt` su endpoint mutanti
- [ ] Ownership check presente in ogni view che accede a dati specifici dell'utente
