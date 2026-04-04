# T05 — Layout base + Navigazione + HTMX + Tailwind

**Fase:** 1 — Fondamenta  
**Complessità:** Media  
**Dipendenze:** T01, T04  
**Blocca:** T06-T30 (tutti i task con UI)

---

## Obiettivo

Template base con sidebar di navigazione, integrazione HTMX per reattività, Tailwind CSS 4 + DaisyUI 5 via Vite.

Il task deve definire convenzioni stabili per partial, CSRF e componenti riusabili, cosi' la UI non degeneri in template duplicati.

---

## Layout (`templates/base.html`)

```html
<!DOCTYPE html>
<html lang="{{ LANGUAGE_CODE }}" data-theme="business">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}djafatt{% endblock %}</title>
    {% vite 'static/src/main.css' %}
    {% vite 'static/src/main.js' %}
</head>
<body class="min-h-screen bg-base-200">
    <div class="drawer lg:drawer-open">
        <input id="drawer" type="checkbox" class="drawer-toggle" />

        <!-- Contenuto principale -->
        <div class="drawer-content">
            <!-- Top bar mobile -->
            <div class="navbar lg:hidden bg-base-100">
                <label for="drawer" class="btn btn-ghost drawer-button">
                    <svg><!-- hamburger --></svg>
                </label>
                <span class="text-xl font-bold">djafatt</span>
            </div>

            <main class="p-6">
                <!-- Toast messages -->
                {% include "partials/_messages.html" %}
                {% block content %}{% endblock %}
            </main>
        </div>

        <!-- Sidebar -->
        <div class="drawer-side">
            <label for="drawer" class="drawer-overlay"></label>
            {% include "partials/_sidebar.html" %}
        </div>
    </div>
</body>
</html>
```

---

## Sidebar (`templates/partials/sidebar.html`)

```
djafatt (logo)
─────────────
📊 Dashboard                    → /dashboard
─────────────
📄 Fatturazione (submenu)
  ├─ Fatture vendita            → /invoices/
  ├─ Fatture acquisto           → /purchase-invoices/
  └─ Autofatture                → /self-invoices/
─────────────
⚙️ Configurazione (submenu)
  ├─ Contatti                   → /contacts/
  ├─ Prodotti                   → /products/
  ├─ Aliquote IVA               → /vat-rates/
  ├─ Sequenze                   → /sequences/
  ├─ Importazioni               → /imports/
  └─ Impostazioni               → /settings/
─────────────
📥 Fatture fornitori (SDI)      → /supplier-invoices/
─────────────
🔒 Logout                       → POST /logout
```

**Menu attivo:** Evidenziare voce corrente con `menu-active` DaisyUI, basato su `request.path`.

---

## Partials HTMX

### Toast messages (`templates/partials/_messages.html`)

```html
{% for message in messages %}
<div class="toast toast-bottom toast-end">
    <div class="alert alert-{{ message.tags }}">
        <span>{{ message }}</span>
    </div>
</div>
{% endfor %}
```

### Progress indicator — da valutare: `htmx-indicator` globale

---

## Frontend build

### `package.json`

```json
{
  "devDependencies": {
    "tailwindcss": "^4.0",
    "daisyui": "^5.0",
    "vite": "^7.0",
    "@tailwindcss/vite": "^4.0"
  },
  "dependencies": {
    "htmx.org": "^2.0"
  }
}
```

### `static/src/main.js`

```js
import "htmx.org";
// Configurazione HTMX globale
document.body.addEventListener("htmx:configRequest", (e) => {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    if (match && e.detail.verb !== "get") {
        e.detail.headers["X-CSRFToken"] = decodeURIComponent(match[1]);
    }
});
```

### `static/src/main.css`

```css
@import "tailwindcss";
@plugin "daisyui";
```

---

## Integrazione Vite + Django

Opzione: **django-vite** o **django-vite-plugin** per `{% vite %}` template tag.

Aggiungere a `settings.py`:
```python
DJANGO_VITE = {
    "default": {
        "dev_mode": DEBUG,
        "dev_server_host": "localhost",
        "dev_server_port": 5173,
    }
}
```

---

## File da creare

| File | Descrizione |
|---|---|
| `templates/base.html` | Layout principale |
| `templates/partials/_sidebar.html` | Menu laterale |
| `templates/partials/_messages.html` | Toast notifications |
| `templates/partials/_header.html` | Header riusabile per pagine |
| `static/src/main.css` | Entry point Tailwind |
| `static/src/main.js` | HTMX + CSRF setup |
| `package.json` | Dipendenze frontend |
| `vite.config.js` | Configurazione Vite |

---

## Criteri di accettazione

- [ ] Layout responsive: sidebar fissa su desktop, drawer su mobile
- [ ] Tutte le voci di menu presenti e con link corretti
- [ ] Voce menu attiva evidenziata basandosi su URL corrente
- [ ] HTMX caricato e funzionante (testare con un GET partiale)
- [ ] CSRF token inviato automaticamente con richieste HTMX
- [ ] Toast messages visualizzati correttamente (success, warning, error)
- [ ] Tailwind + DaisyUI funzionanti (card, button, badge, table, form)
- [ ] Hot reload funzionante in dev (Vite)
- [ ] Convenzione partial con underscore coerente in tutto il progetto
- [ ] **Nessun** framework JS diverso da HTMX nel bundle (no Alpine, React, Vue)
- [ ] `main.js` contiene solo import HTMX + event listener CSRF (< 15 righe)

---

## Regole frontend vincolanti (per tutti i task con UI)

Queste regole sono **obbligatorie** in ogni task che produce template, CSS o JS.

### Stack ammesso

| Tecnologia | Ruolo | Versione |
|---|---|---|
| **HTMX 2** | Reattività: hx-get, hx-post, hx-delete, hx-trigger, hx-target, hx-swap | ^2.0 |
| **Tailwind CSS 4** | Utility classes | ^4.0 |
| **DaisyUI 5** | Componenti semantici (btn, badge, card, drawer, alert, table, stats) | ^5.0 |
| **Vite 7** | Build, HMR dev, bundle prod | ^7.0 |
| **Vanilla JS** | Solo per CSRF injection in `main.js` | — |

### Divieti espliciti

- **NO Alpine.js** — non serve, HTMX + DaisyUI coprono tutto
- **NO React / Vue / Svelte / Angular** — il progetto è server-rendered
- **NO jQuery** — obsoleto
- **NO Hyperscript** — complessità inutile per questo scope
- **NO librerie JS di terze parti** (chart.js, sortable, etc.) salvo valutazione esplicita con task dedicato
- **NO CSS custom** fuori da Tailwind utility — usare solo classi DaisyUI e utility Tailwind
- **NO `style=""` inline** — mai. Usare classi Tailwind
- **NO `<script>` inline** nei template — tutto via `main.js` importato da Vite

### Pattern HTMX standard

```
Ricerca live:  hx-get + hx-trigger="input changed delay:300ms" + hx-target="#results"
Mutazione:     hx-post / hx-delete + CSRF via cookie (auto-inject in main.js)
Conferma:      hx-confirm="Sei sicuro?" (browser native)
Totali live:   hx-post + hx-trigger="input changed delay:300ms" + hx-target="#totals"
Swap:          hx-swap="outerHTML" per sostituzione riga, "innerHTML" per contenuto
Selezione:     hx-get + hx-trigger="change" per autofill prodotto
Anno fiscale:  hx-post + hx-trigger="change" (mai GET mutante)
```

### Naming template/partials

```
templates/
├── base.html                          # Layout globale (drawer + sidebar + main)
├── partials/
│   ├── _sidebar.html                  # Menu laterale
│   ├── _messages.html                 # Toast DaisyUI
│   └── _header.html                   # Header riusabile
├── {app}/
│   ├── index.html                     # Lista (extends base.html)
│   ├── form.html                      # Create/Edit (extends base.html)
│   ├── detail.html                    # Dettaglio read-only (opzionale)
│   └── partials/
│       └── _table.html                # Partial per HTMX swap (ricerca, filtri)
```

- Prefix `_` per partials (mai serviti come full page)
- Un partial = un target HTMX (il suo `id` corrisponde all'`hx-target`)
- Ogni partial è autosufficiente: contiene il suo `id=` root element

### DaisyUI componenti obbligatori

| Componente | Uso | Esempio |
|---|---|---|
| `drawer` | Layout sidebar responsive | `base.html` |
| `btn` | Tutti i pulsanti | `btn btn-primary`, `btn btn-ghost` |
| `badge` | Status fattura | `badge badge-warning` |
| `alert` | Toast messages | `alert alert-success` |
| `table` | Liste CRUD | `table table-zebra` |
| `input` | Campi form | `input input-bordered` |
| `select` | Dropdown | `select select-bordered` |
| `card` | Stats dashboard | `card bg-base-100 shadow-xl` |
| `stats` | KPI dashboard | `stats shadow` |
| `modal` | Conferme complesse, email | `<dialog class="modal">` |
| `menu` | Voci sidebar | `menu`, `menu-active` per voce corrente |

### Test frontend

- **Backend-only**: tutti i test sono `pytest` + `django.test.Client`
- Verificare con `response.content` che i partial HTMX contengano gli ID attesi
- Verificare risposte 200 per endpoint HTMX con header `HX-Request: true`
- **NO Playwright/Selenium/Cypress** salvo decisione futura esplicita
