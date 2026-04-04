# Analisi architetturale, sicurezza e TDD di djafatt

## Sintesi

Il piano è stato revisionato in tre passaggi successivi. Il primo hardening ha coperto sicurezza webhook, XML e quality gates. La seconda revisione ha portato il progetto a **Django 6.0.3** (ultima stabile, richiede Python ≥ 3.12), aggiunto funzionalità obbligatorie mancanti (scadenzario, note di credito, email cortesia automatica, async Celery, reverse proxy), e allineato tutte le dipendenze alle versioni verificate su PyPI. La terza revisione ha formalizzato la decisione frontend, rimosso Alpine.js (mai usato), e creato il documento di convenzioni per produzione multiagente (T00).

## Produzione multiagente

Questo progetto è progettato per essere implementato da agenti AI o sviluppatori che lavorano in parallelo su task indipendenti. Il documento [T00-convenzioni-agenti.md](T00-convenzioni-agenti.md) definisce le regole vincolanti: stack ammesso, divieti, naming, pattern HTMX, checklist pre-commit. Ogni agente **DEVE** leggere T00 prima di iniziare qualsiasi task.

## Stack aggiornato

| Componente | Versione | Note |
|---|---|---|
| Django | 6.0.3 (>=6.0,<6.1) | Ultima stabile, richiede Python >=3.12 |
| Python | >=3.12 | Requisito Django 6.0 |
| PostgreSQL | 17 | Stabile |
| HTMX | 2 | Stabile |
| Tailwind | 4 | Stabile |
| DaisyUI | 5 | Stabile |
| Vite | 7 | Stabile |
| a38 | 0.1.8 | Pacchetto PyPI `a38` (NON `python-a38`) |
| Celery | 5.6+ | Con Redis broker |
| WeasyPrint | 68+ | Per PDF cortesia |
| httpx | 0.28+ | Client SDI |
| Nginx | 1.27 | Reverse proxy + SSL |

### Compatibilità Django 6.0.3 verificata

| Pacchetto | Versione | Django 6.0 |
|---|---|---|
| django-htmx | 1.27.0 | ✅ Classifier 6.0 |
| django-debug-toolbar | 6.2.0 | ✅ Classifier 6.0 |
| pytest-django | 4.12.0 | ✅ Classifier 6.0 |
| whitenoise | 6.12.0 | ✅ Classifier 6.0 |
| django-constance | 4.3.5 | ⚠️ Solo classifier 5.2, ma funziona (testare) |
| django-celery-results | 2.6.0 | ⚠️ Solo classifier 5.2, ma funziona (testare) |
| django-vite | 3.1.0 | ✅ Nessun legame Django-specifico |

### Breaking changes Django 6.0 da gestire

- `STATICFILES_STORAGE` → `STORAGES["staticfiles"]["BACKEND"]` (corretto in T28)
- Python 3.10/3.11 non più supportati → CI matrix aggiornata a 3.12/3.13 (T01e)
- Pacchetto FatturaPA: si chiama `a38` su PyPI, NON `python-a38` (corretto in T01, T17)

## Decisione frontend: HTMX 2 (senza Alpine.js)

Analisi condotta valutando HTMX 2, Alpine.js, React/Next.js, Vue/Nuxt, Inertia.js e varie librerie CSS.

**Verdetto: HTMX 2 + Tailwind 4 + DaisyUI 5 + Vite 7 — zero framework JS aggiuntivi.**

| Criterio | HTMX 2 | React/Vue SPA |
|---|---|---|
| Complessità per CRUD pura | ✅ Minima | ❌ Overkill (API REST + frontend separato) |
| Dipendenze JS | 9 | 250+ |
| Build time | ~5s | ~40s |
| First load time | 1-2s | 2-6s |
| Team full-stack | ✅ Un linguaggio (Python) | ❌ Split backend/frontend |
| Interazioni richieste | ✅ Tutte coperte (search, add/remove righe, live totals, autofill) | ✅ Ovviamente coperte, ma inutile |
| Testabilità backend | ✅ pytest + django.test.Client | ⚠️ Richiede test suite JS separata |

**Alpine.js**: rimosso. Era menzionato in T01 per errore (copia dal progetto Laravel). Nessun task lo utilizza. DaisyUI gestisce toggle modali e drawer via CSS puro (`:checked`, `<dialog>`). Eventuali micro-interazioni client-only possono essere gestite con 3 righe di vanilla JS nel listener HTMX esistente.

**Regole vincolanti**: documentate in [T05-layout-navigazione.md](T05-layout-navigazione.md) sezione "Regole frontend vincolanti" e [T00-convenzioni-agenti.md](T00-convenzioni-agenti.md) sezione 4.

## Punti deboli identificati e corretti

### 1. Sicurezza (corretto nel primo hardening)

- Webhook pubblico senza firma forte, idempotenza e rate limiting → T20b
- `defusedxml` presente nel piano, ma senza limiti anti ZIP bomb, schema validation e import atomico → T15
- Token SDI previsto in configurazione dinamica in chiaro → T19, T24
- Mutazioni HTMX non esplicitamente protette da CSRF e ownership checks → T12
- Cambio anno fiscale via GET mutante → T25 (ora POST)

### 2. Funzionalità mancanti (corretto nella seconda revisione)

- **Scadenzario e pagamenti:** Impossibile sapere chi deve pagare e quando. Aggiunto T33 con PaymentDue, PaymentRecord, scadenzario e integrazione DatiPagamento XML.
- **Note di credito (TD04):** Obbligatorie per legge. Non è possibile cancellare una fattura inviata al SdI. Aggiunto T34.
- **Email cortesia automatica:** Il piano originale prevedeva email solo come fallback MC. In realtà tutti i gestionali inviano il PDF cortesia a qualsiasi cliente con email. Riscritti T31 e T32.
- **Async/Celery:** Dichiarato come dipendenza ma mai configurato concretamente. Aggiunto T35 con worker, routing, Beat, monitoring.
- **Reverse proxy:** Gunicorn non deve essere esposto direttamente. Aggiunto T36 con Nginx, SSL Let's Encrypt, rate limiting infrastrutturale.

### 3. TDD e quality (corretto nel primo hardening)

- La suite test originaria copriva bene gli happy path, ma non round-trip XML, casi malevoli, replay webhook, timeouts SDI o contract tests → T29b
- Mancavano quality gates minimi come coverage fail-under, type checking e `manage.py check --deploy` → T01e
- Nessuna strategia esplicita per separare unit, integration, security e contract tests → T29

### 4. Manutenibilità (corretto nel primo hardening)

- Settings non separati in `base/dev/prod/test` → T01
- Logica di calcolo troppo vicina al model, poco isolata per test e refactoring → T11
- Nessuna gerarchia di eccezioni di dominio → T03b
- Logging e audit trail non definiti in modo coerente → T03b, T26

### 5. Race condition numerazione (corretto nella seconda revisione)

- `get_next_number()` usava `MAX()` senza `SELECT FOR UPDATE` → race condition su creazioni concorrenti → T08 corretto

### 6. Idempotenza import XML (corretto nella seconda revisione)

- Nessun campo per prevenire import duplicati → aggiunto `xml_content_hash` (SHA-256) nel modello Invoice (T03)

## Correzioni introdotte

### Task corretti

- [T01-scaffold.md](T01-scaffold.md): split settings, dipendenze corrette, `apps/common`, baseline di sicurezza e quality gates.
- [T04-auth-setup.md](T04-auth-setup.md): setup atomico, rate limiting login, validatori fiscali obbligatori.
- [T05-layout-navigazione.md](T05-layout-navigazione.md): convenzioni partial coerenti e CSRF HTMX via cookie.
- [T11-engine-calcolo-totali.md](T11-engine-calcolo-totali.md): estrazione della logica in un servizio puro.
- [T12-righe-fattura-htmx.md](T12-righe-fattura-htmx.md): note di sicurezza e requisito CSRF esplicito.
- [T15-import-xml.md](T15-import-xml.md): limiti dimensionali, XSD, idempotenza e transazioni.
- [T19-client-openapi-sdi.md](T19-client-openapi-sdi.md): token da env, retry, idempotency key, redazione log.
- [T20-webhook-sdi.md](T20-webhook-sdi.md): firma e request validation richiamate esplicitamente.
- [T24-pagine-settings.md](T24-pagine-settings.md): separazione segreti/config, token write-only, audit log.
- [T25-anno-fiscale.md](T25-anno-fiscale.md): cambio anno via POST e validazione range.
- [T28-docker-produzione.md](T28-docker-produzione.md): utente non-root e backup minimo.
- [T29-test-suite.md](T29-test-suite.md): strategia TDD a livelli e coverage piu' alta.

### Nuovi task supplementari

- [T01e-ci-quality-gates.md](T01e-ci-quality-gates.md) — CI pipeline, Python 3.12/3.13 matrix
- [T03b-error-handling-osservabilita.md](T03b-error-handling-osservabilita.md) — Eccezioni dominio, logging
- [T20b-hardening-webhook-sdi.md](T20b-hardening-webhook-sdi.md) — HMAC, idempotenza, rate limit
- [T29b-test-integrazione-sicurezza.md](T29b-test-integrazione-sicurezza.md) — Test XXE, round-trip, webhook

### Nuovi task funzionali (seconda revisione)

- [T33-scadenze-pagamenti.md](T33-scadenze-pagamenti.md) — PaymentDue/PaymentRecord, scadenzario, DatiPagamento XML
- [T34-note-di-credito.md](T34-note-di-credito.md) — TD04, storno totale/parziale, DatiFattureCollegate
- [T35-celery-async-tasks.md](T35-celery-async-tasks.md) — Worker, routing, Beat, task SDI/email
- [T36-nginx-ssl-reverse-proxy.md](T36-nginx-ssl-reverse-proxy.md) — Nginx, Let's Encrypt, rate limiting infrastrutturale

## Priorità consigliata

1. **T01 + T01e**: Scaffold e CI. Senza questo niente funziona.
2. **T02 + T03 + T03b**: Modelli, eccezioni dominio. Fondamenta di tutto il resto.
3. **T04 + T05**: Auth e layout. Prerequisito per tutte le UI.
4. **T06-T09**: CRUD anagrafiche (veloci, bassa complessità).
5. **T10-T12 + T33**: Fatture vendita + motore calcolo + scadenzario. Il cuore del gestionale.
6. **T34**: Note di credito (prima dell'integrazione SDI, perché vanno inviate).
7. **T15 + T17 + T18**: Import/export XML. Blocco critico.
8. **T35**: Celery worker e task. Prerequisito per invio SDI e email.
9. **T19 + T20 + T20b**: Client SDI + webhook + hardening.
10. **T31 + T32**: PDF cortesia + email/PEC. Necessari per MC fallback e cortesia automatica.
11. **T21-T22**: Sync fornitori.
12. **T23-T30**: Dashboard, settings, traduzioni, branding.
13. **T36**: Nginx + SSL (prima del deploy in produzione).
14. **T28 + T29 + T29b**: Docker prod + suite test completa.

## Conclusione

Con queste correzioni il piano copre un gestionale fiscale completo: fatturazione attiva e passiva, note di credito, scadenzario, integrazione SdI asincrona, email cortesia automatica, fallback PEC su mancata consegna, reverse proxy con SSL, e suite di test che copre sicurezza e integrazione. Lo stack è aggiornato a Django 6.0.3 con tutte le dipendenze verificate. La decisione frontend (HTMX 2, zero SPA) è formalizzata e documentata. Il documento T00 garantisce che qualsiasi agente AI o sviluppatore che implementi un task operi con le stesse convenzioni.