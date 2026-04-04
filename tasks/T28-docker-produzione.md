# T28 — Docker produzione + docker-compose

**Fase:** 6 — Dashboard, Settings, Deploy  
**Complessità:** Media  
**Dipendenze:** T01  
**Blocca:** Nessuno

---

## Obiettivo

Dockerfile multi-stage per produzione e docker-compose per deploy, con PostgreSQL, Gunicorn, health checks, utente non-root e strategia minima di backup.

## Dockerfile (multi-stage)

```dockerfile
# === Stage 1: Frontend build ===
FROM node:22-alpine AS frontend
WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci
COPY static/ static/
COPY vite.config.js ./
RUN npm run build

# === Stage 2: Python app ===
FROM python:3.12-slim AS app

# System deps including those for WeasyPrint
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc libcairo2 libpango-1.0-0 libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 libffi-dev shared-mime-info && \
    rm -rf /var/lib/apt/lists/*

# Python deps
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

# App code
COPY . .
COPY --from=frontend /build/static/dist /app/static/dist

# Collectstatic
RUN DJANGO_SETTINGS_MODULE=djafatt.settings.prod \
    SECRET_KEY=build-only \
    python manage.py collectstatic --noinput

# Translations
RUN python manage.py compilemessages || true

# Runtime
RUN useradd -r -u 1001 appuser
USER appuser
EXPOSE 8000
CMD ["gunicorn", "djafatt.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--timeout", "120"]
```

## docker-compose.prod.yml

```yaml
services:
  web:
    build: .
    ports:
      - "${APP_PORT:-8000}:8000"
    environment:
      - DJANGO_SETTINGS_MODULE=djafatt.settings.prod
      - DATABASE_URL=postgres://djafatt:${DB_PASSWORD}@db:5432/djafatt
      - SECRET_KEY=${SECRET_KEY}
      - ALLOWED_HOSTS=${ALLOWED_HOSTS:-localhost}
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/')"]
      interval: 30s
      timeout: 10s
      retries: 3

  db:
    image: postgres:17-alpine
    environment:
      POSTGRES_DB: djafatt
      POSTGRES_USER: djafatt
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U djafatt"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  backup:
    image: postgres:17-alpine
    depends_on:
      db:
        condition: service_healthy
    environment:
      PGPASSWORD: ${DB_PASSWORD}
    command: >-
      sh -c 'mkdir -p /backup && pg_dump -h db -U djafatt djafatt > /backup/djafatt.sql'
    volumes:
      - backups:/backup

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redisdata:/data

  celery-worker:
    build: .
    command: celery -A djafatt worker -l WARNING -Q default,sdi,email,sync --concurrency=4
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    environment:
      - DJANGO_SETTINGS_MODULE=djafatt.settings.prod
      - DATABASE_URL=postgres://djafatt:${DB_PASSWORD}@db:5432/djafatt
      - CELERY_BROKER_URL=redis://redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
    restart: unless-stopped

  celery-beat:
    build: .
    command: celery -A djafatt beat -l WARNING
    depends_on:
      - redis
    environment:
      - DJANGO_SETTINGS_MODULE=djafatt.settings.prod
      - CELERY_BROKER_URL=redis://redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
    restart: unless-stopped

volumes:
  pgdata:
  backups:
  redisdata:
```

## Settings produzione (`djafatt/settings/prod.py`)

```python
from .base import *

DEBUG = False
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# Static files — Django 6.0 usa STORAGES invece di STATICFILES_STORAGE
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Logging
LOGGING = {
    "version": 1,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {
        "django": {"handlers": ["console"], "level": "WARNING"},
        "apps": {"handlers": ["console"], "level": "INFO"},
    },
}
```

## Health check endpoint

```python
# apps/core/views.py
from django.http import JsonResponse
from django.db import connection

def health_check(request):
    try:
        connection.ensure_connection()
        return JsonResponse({"status": "ok"})
    except Exception as e:
        return JsonResponse({"status": "error", "detail": str(e)}, status=503)
```

## `.env.prod.example`

```bash
SECRET_KEY=genera-una-chiave-sicura-qui
DB_PASSWORD=password-sicura-qui
ALLOWED_HOSTS=tuodominio.it,localhost
APP_PORT=8000
OPENAPI_SDI_TOKEN=
OPENAPI_SDI_SANDBOX=false
BRANDFETCH_CLIENT_ID=
```

## File da creare

- `Dockerfile`
- `docker-compose.prod.yml`
- `djafatt/settings/prod.py`
- `.env.prod.example`
- Endpoint health check in `apps/core/views.py`

## Criteri di accettazione

- [ ] `docker compose -f docker-compose.prod.yml up --build` avvia senza errori
- [ ] Health check `/health/` risponde 200
- [ ] Static files serviti via WhiteNoise
- [ ] PostgreSQL con health check
- [ ] Gunicorn con 3 workers
- [ ] Variabili production sicure (no DEBUG, HTTPS settings)
- [ ] Container restart automatico
- [ ] Container applicativo gira come utente non-root
- [ ] Esiste una procedura minima di backup PostgreSQL
