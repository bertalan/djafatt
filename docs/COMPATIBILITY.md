# Report di Compatibilità — djafatt

## Sommario Esecutivo

Stack verificato: Django 6.0 + Python 3.12+ + PostgreSQL 17 + HTMX 2 + Tailwind 4 + DaisyUI 5 + Vite 7.

- **21 dipendenze** analizzate
- **3 a rischio MEDIO** (no classifiers Django 6.0, serve test reale)
- **1 a rischio MEDIO** (a38 — copertura features FatturaPA incerta)
- **17 a rischio BASSO** (compatibili o agnostiche)

---

## Dipendenze Core

| Pacchetto               | Versione richiesta | Django 6.0 | Rischio  | Note                                                                 |
|-------------------------|--------------------|------------|----------|----------------------------------------------------------------------|
| Django                  | >=6.0,<6.1         | ✅         | BASSO    | Versione target                                                     |
| psycopg[binary]         | >=3.3              | ✅         | BASSO    | Adattatore nativo consigliato da Django                             |
| dj-database-url         | >=2.3              | ✅         | BASSO    | Parser URL, agnostico dal framework                                 |
| django-constance[database] | >=4.0           | ⚠️         | MEDIO    | Classifiers solo Django 5.2; serve test reale                       |
| whitenoise              | >=6.8              | ✅         | BASSO    | Funziona con STORAGES dict (Django 5.1+)                            |
| django-htmx             | >=1.21             | ✅         | BASSO    | Middleware leggero, rilascio Django 6.0 atteso                      |

## Dipendenze FatturaPA / XML

| Pacchetto     | Versione | Django 6.0 | Rischio | Note                                                                    |
|---------------|----------|------------|---------|-------------------------------------------------------------------------|
| a38           | latest   | N/A        | MEDIO   | Supporto DatiRitenuta, DatiBollo, split payment non verificato          |
| defusedxml    | >=0.7    | N/A        | BASSO   | Libreria sicurezza XML, nessuna dipendenza Django                       |
| lxml          | >=5.3    | N/A        | BASSO   | Fallback per a38 se incompleta                                          |

## Async / Task Queue

| Pacchetto               | Versione | Django 6.0 | Rischio | Note                                                    |
|-------------------------|----------|------------|---------|----------------------------------------------------------|
| celery                  | >=5.4    | N/A        | BASSO   | Non dipende da Django direttamente                       |
| django-celery-results   | >=2.6    | ⚠️         | MEDIO   | Classifiers solo Django 5.2; modelli/migrazioni da testare|
| django-celery-beat      | >=2.7    | ⚠️         | MEDIO   | Stessa situazione di results                             |
| redis                   | >=5.2    | N/A        | BASSO   | Client puro, agnostico                                   |

## HTTP / API

| Pacchetto | Versione | Rischio | Note                                     |
|-----------|----------|---------|------------------------------------------|
| httpx     | >=0.28   | BASSO   | Client HTTP async, nessuna dipendenza Django |
| respx     | >=0.22   | BASSO   | Mock httpx per test                      |

## Frontend / Build

| Pacchetto            | Versione | Rischio | Note                                                |
|----------------------|----------|---------|-----------------------------------------------------|
| django-vite          | >=3.1    | BASSO   | Template tags per Vite manifest                     |
| tailwindcss          | 4.x      | BASSO   | CSS puro, nessuna dipendenza server                 |
| daisyui              | 5.x      | BASSO   | Plugin Tailwind, nessuna dipendenza server          |
| htmx.org             | 2.x      | BASSO   | JS client-side, zero framework dependency           |
| vite                 | 7.x      | BASSO   | Build tool, nessuna dipendenza Django               |

## Test

| Pacchetto     | Versione | Rischio | Note                                          |
|---------------|----------|---------|-----------------------------------------------|
| pytest-django | >=4.10   | BASSO   | Supporto Django 6.0 atteso/disponibile        |
| factory-boy   | >=3.3    | BASSO   | Non usa direttamente API Django deprecate     |

---

## Azioni Raccomandate

### Priorità ALTA
1. **Test django-constance 4.3 con Django 6.0** — Creare virtualenv di test, eseguire `manage.py migrate` e verificare admin/API constance funzionanti.
2. **Test django-celery-results/beat** — Verificare migrazioni e beat scheduler con Django 6.0.

### Priorità MEDIA
3. **Spike a38** — Testare generazione XML con DatiRitenuta, DatiBollo, scissione pagamenti. Se mancanti, implementare fallback lxml.
4. **STORAGES dict** — Verificare che `whitenoise` e `django-vite` funzionino con la nuova API `STORAGES` (introdotta Django 5.1, obbligatoria 6.0).

### Priorità BASSA
5. **Pin versions** — Pinnare tutte le dipendenze nel pyproject.toml con upper bounds.
6. **pip-audit** — Aggiungere `pip-audit` alla CI per vulnerabilità supply-chain.

---

## Matrice Compatibilità Python

| Python | Django 6.0 | Note                    |
|--------|------------|-------------------------|
| 3.12   | ✅         | Versione minima target  |
| 3.13   | ✅         | Supportato              |
| 3.11   | ❌         | Non supportato da Django 6.0 |
