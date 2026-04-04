# Guida Sviluppo — djafatt

## Prerequisiti

- Docker e Docker Compose
- Python 3.12+
- Node.js 22+ (per Vite/Tailwind)

## Quick Start

```bash
# Clone
git clone <repo-url> djafatt && cd djafatt

# Configurazione
cp .env.example .env
# Editare .env con i propri valori

# Avvio rapido (con script)
./restart.sh              # avvio standard
./restart.sh --build      # ricostruisce immagini Docker

# Oppure manualmente:
docker compose up -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

L'app è disponibile su `http://localhost:8000`.

## Struttura Settings

| File | Uso | `DJANGO_SETTINGS_MODULE` |
|------|-----|--------------------------|
| `settings/base.py` | Settings condivisi | — |
| `settings/dev.py` | Sviluppo locale | `djafatt.settings.dev` |
| `settings/prod.py` | Produzione | `djafatt.settings.prod` |
| `settings/test.py` | Test (veloce) | `djafatt.settings.test` |

## Test

```bash
# Tutti i test (204 test, esclude sandbox)
docker compose exec web pytest tests/ -v -m "not sandbox"

# Con coverage
docker compose exec web pytest tests/ --cov=apps --cov-report=html

# Solo test security
docker compose exec web pytest tests/security/ -v

# Solo test SDI send (task + view)
docker compose exec web pytest tests/test_sdi_send.py -v

# Test sandbox SDI (richiede OPENAPI_SDI_TOKEN in .env)
docker compose exec web pytest -m sandbox -v

# Solo un test
docker compose exec web pytest tests/test_calculations.py::TestTotalsCalculation::test_stamp_duty_applied -v
```

**Test totali:** 204 (CI) + 4 sandbox (accettazione).
**Coverage minimo: 85%** — Enforced in CI.

### Marker pytest

| Marker | Descrizione | Default |
|--------|-------------|--------|
| `slow` | Test lenti | inclusi |
| `security` | Test sicurezza | inclusi |
| `integration` | Test integrazione | inclusi |
| `sandbox` | Test su SDI sandbox reale | **esclusi** (`-m "not sandbox"`) |

## Linting

```bash
# Ruff (lint + format)
docker compose exec web ruff check apps/ tests/
docker compose exec web ruff format apps/ tests/

# Type checking
docker compose exec web mypy apps/
```

## CI

GitHub Actions (`.github/workflows/ci.yml`):
1. Matrice Python 3.12 + 3.13
2. PostgreSQL 17 service
3. `ruff check` + `ruff format --check`
4. `mypy apps/`
5. `pytest --cov-fail-under=85`

## Convenzioni Codice

### Commit Messages

```
tipo(TXXX): descrizione breve

Corpo opzionale con dettagli.
```

Tipi: `feat`, `fix`, `test`, `docs`, `refactor`, `ci`, `chore`

### Branch Naming

```
feat/T11-engine-calcolo
fix/T03-invoice-signal
test/T29-security-suite
```

### Importi

**Tutti gli importi in centesimi** (IntegerField):
- €100.00 → `10000`
- €2.00 (bollo) → `200`
- €77.47 (soglia bollo) → `7747`

Mai usare `float` o `Decimal` per importi in DB.

### Test Naming

```python
def test_<cosa>_<condizione>(self):
    """Descrizione leggibile."""
```

Esempio: `test_stamp_duty_below_threshold`, `test_xxe_attack_blocked`

## Docker

```yaml
# docker-compose.yml services:
web:         # Django runserver (porta 8000)
db:          # PostgreSQL 17
redis:       # Cache + Celery broker
node:        # Vite build --watch (frontend)
# celery:   # Worker async (abilitare in produzione)
# celery-beat: # Scheduler periodico (abilitare in produzione)
```

### Frontend (Vite build --watch)

Il container `node` esegue `npx vite build --watch` che:
- Compila `static/src/main.js` + `static/src/main.css` → `static/dist/`
- Genera `static/dist/.vite/manifest.json` letto da django-vite
- Ricostruisce automaticamente ad ogni modifica dei sorgenti (~130ms)

Django serve i file compilati direttamente (`dev_mode=False`). Non è necessario un dev server Vite separato.

```bash
# Verificare stato build
docker compose logs node --tail 5

# Forzare rebuild
docker compose restart node

# Script NPM disponibili
npm run dev     # equivalente a: vite build --watch
npm run build   # build una tantum per produzione
npm run serve   # dev server HMR (debugging avanzato)
```

### Comandi Utili

```bash
# Riavvio completo
./restart.sh
./restart.sh --build   # con rebuild immagini

# Logs
docker compose logs -f web
docker compose logs -f node    # watcher frontend

# Shell Django
docker compose exec web python manage.py shell_plus

# Migrazioni
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate

# Sync fornitori SDI
docker compose exec web python manage.py sync_supplier_invoices
```

## Variabili d'Ambiente

Vedi [../.env.example](../.env.example) per la lista completa. Variabili critiche:

| Variabile | Descrizione | Esempio |
|-----------|-------------|---------|
| `SECRET_KEY` | Django secret key | (generare) |
| `DATABASE_URL` | PostgreSQL connection | `postgres://user:pass@db:5432/djafatt` |
| `OPENAPI_SDI_TOKEN` | Token API OpenAPI SDI | (dal provider) |
| `OPENAPI_SDI_WEBHOOK_SECRET` | Secret HMAC webhook | (generare) |
| `OPENAPI_SDI_SANDBOX` | Modalità sandbox | `true` |
