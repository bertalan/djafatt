# T01 — Scaffold progetto djafatt

**Fase:** 1 — Fondamenta  
**Complessità:** Alta  
**Dipendenze:** Nessuna (primo task)  
**Blocca:** T02, T03, T04, T05

---

## Obiettivo

Creare la struttura base del progetto Django con Docker, PostgreSQL, configurazione iniziale e fondazioni solide per sicurezza, test e manutenibilita'.

## File da creare

```
djafatt/
├── pyproject.toml              # Poetry/uv con dipendenze
├── manage.py
├── Dockerfile
├── docker-compose.yml          # Django + PostgreSQL + Node (Vite)
├── .env.example
├── .gitignore
├── README.md
├── djafatt/
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py             # settings condivisi
│   │   ├── dev.py              # sviluppo locale
│   │   ├── prod.py             # produzione hardenizzata
│   │   └── test.py             # test isolati e veloci
│   ├── urls.py                 # Root URL configuration
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── __init__.py
│   ├── common/                 # validatori, eccezioni, helpers condivisi
│   │   ├── __init__.py
│   │   └── apps.py
│   ├── core/                   # Auth, layout, setup wizard, dashboard
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── templates/
│   ├── contacts/               # Contatti clienti/fornitori
│   │   ├── __init__.py
│   │   └── apps.py
│   ├── invoices/               # Fatture vendita, acquisto, autofatture, righe
│   │   ├── __init__.py
│   │   └── apps.py
│   ├── products/               # Prodotti/servizi
│   │   ├── __init__.py
│   │   └── apps.py
│   └── sdi/                    # Integrazione SDI, XML, webhook
│       ├── __init__.py
│       └── apps.py
├── static/
│   └── src/
│       ├── main.css            # Tailwind 4 + DaisyUI 5 entry
│       └── main.js             # HTMX 2 + CSRF handler (solo vanilla JS)
├── templates/
│   └── base.html               # Layout base (placeholder)
├── .github/
│   └── workflows/
│       └── ci.yml
├── vite.config.js
└── package.json                # Tailwind 4, DaisyUI 5, HTMX 2, Vite 7
```

## Dipendenze Python (`pyproject.toml`)

```toml
[project]
name = "djafatt"
version = "0.1.0"
requires-python = ">=3.12"

dependencies = [
    "django>=6.0,<6.1",
    "django-htmx>=1.27",
    "django-vite>=3.1",
    "dj-database-url>=3.1",
    "psycopg[binary]>=3.3",
    "a38>=0.1.8",
    "defusedxml>=0.7.1",
    "django-constance[database]>=4.3",
    "gunicorn>=25.0",
    "httpx>=0.28",
    "whitenoise>=6.12",
    "weasyprint>=68",
    "celery[redis]>=5.6",
    "django-celery-results>=2.6",
    "django-celery-beat>=2.7",
    "python-dateutil>=2.9",
]

[project.optional-dependencies]
dev = [
    "pytest>=9.0",
    "pytest-django>=4.12",
    "factory-boy>=3.3",
    "pytest-cov>=5.0",
    "respx>=0.22",
    "django-debug-toolbar>=6.2",
    "ruff>=0.15",
    "mypy>=1.19",
    "coverage>=7.13",
]
```

## Docker

```yaml
# docker-compose.yml
name: djafatt
services:
  db:
    image: postgres:17-alpine
    environment:
      POSTGRES_DB: djafatt
      POSTGRES_USER: djafatt
      POSTGRES_PASSWORD: djafatt
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  web:
    build: .
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - .:/app
    ports:
      - "${APP_PORT:-8000}:8000"
    depends_on:
      - db
    env_file: .env

  node:
    image: node:22-alpine
    working_dir: /app
    volumes:
      - .:/app
    command: npx vite --host
    ports:
      - "5173:5173"

volumes:
  pgdata:
```

## `.env.example`

```bash
DEBUG=True
SECRET_KEY=change-me-in-production
DATABASE_URL=postgres://djafatt:djafatt@db:5432/djafatt
APP_PORT=8000
ALLOWED_HOSTS=localhost,127.0.0.1
LANGUAGE_CODE=it
OPENAPI_SDI_TOKEN=
OPENAPI_SDI_SANDBOX=true
BRANDFETCH_CLIENT_ID=
```

## Settings package — Configurazione chiave

```python
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "django_htmx",
    "constance",
    "constance.backends.database",
    "django_celery_results",
    "django_celery_beat",
    # Project apps
    "apps.common",
    "apps.notifications",
    "apps.core",
    "apps.contacts",
    "apps.invoices",
    "apps.products",
    "apps.sdi",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

DATABASES = {
    "default": dj_database_url.config(default="postgres://djafatt:djafatt@db:5432/djafatt")
}

LANGUAGE_CODE = "it"
LANGUAGES = [("it", "Italiano"), ("en", "English")]
USE_I18N = True
USE_L10N = True
```

## Baseline architetturale obbligatoria

- Split settings: `base.py`, `dev.py`, `prod.py`, `test.py`
- `apps/common` per validatori fiscali, eccezioni, helper condivisi
- `DJANGO_SETTINGS_MODULE` esplicito per ogni ambiente
- Logging strutturato con redazione campi sensibili
- `python manage.py check --deploy` deve passare in produzione
- Quality gates minimi: `ruff`, `mypy`, `pytest --cov`

## Sicurezza minima

- `SECRET_KEY`, token SDI e segreti esterni solo via env o storage cifrato
- Nessun secret di produzione dentro `Constance`
- Cookie `HttpOnly`, `Secure`, `SameSite=Lax` in produzione
- `ALLOWED_HOSTS` e `CSRF_TRUSTED_ORIGINS` gestiti da env

## Criteri di accettazione

- [ ] `docker compose up` avvia i 3 container senza errori
- [ ] `http://localhost:8000/` risponde (anche solo 404 o pagina Django default)
- [ ] `docker compose exec web python manage.py check` → nessun errore
- [ ] `docker compose exec web python manage.py migrate` → crea tabelle auth base
- [ ] PostgreSQL raggiungibile da Django
- [ ] Vite serve CSS/JS in dev mode su porta 5173
- [ ] Struttura cartelle apps/ conforme allo schema sopra
- [ ] Esistono `djafatt/settings/base.py`, `dev.py`, `prod.py`, `test.py`
- [ ] `ruff`, `mypy` e `pytest --cov` sono eseguibili dal primo giorno
