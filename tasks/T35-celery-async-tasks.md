# T35 — Celery worker, task routing e periodic tasks

**Fase:** 5 — Integrazione SDI  
**Complessità:** Alta  
**Dipendenze:** T01, T19, T32  
**Blocca:** T28

---

## Obiettivo

Definire la configurazione completa di Celery: worker, broker Redis, task routing, periodic tasks (Celery Beat) e monitoraggio. Nelle fasi precedenti Celery è stato dichiarato come dipendenza ma mai configurato concretamente. Questo task colma il gap.

## Componenti

### 1. Configurazione Celery (`djafatt/celery.py`)

```python
import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "djafatt.settings.dev")

app = Celery("djafatt")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
```

### 2. Init (`djafatt/__init__.py`)

```python
from .celery import app as celery_app

__all__ = ("celery_app",)
```

### 3. Settings Celery (`djafatt/settings/base.py`)

```python
# Celery
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://redis:6379/0")
CELERY_RESULT_BACKEND = "django-db"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "Europe/Rome"

# Task routing
CELERY_TASK_ROUTES = {
    "apps.sdi.tasks.*": {"queue": "sdi"},
    "apps.notifications.tasks.*": {"queue": "email"},
    "apps.sdi.tasks.sync_supplier_invoices_task": {"queue": "sync"},
}

# Limiti
CELERY_TASK_SOFT_TIME_LIMIT = 300  # 5 min
CELERY_TASK_TIME_LIMIT = 600       # 10 min hard kill
CELERY_WORKER_MAX_TASKS_PER_CHILD = 100  # restart worker dopo 100 task (memory leak prevention)

# Rate limiting per coda
CELERY_TASK_ANNOTATIONS = {
    "apps.sdi.tasks.send_invoice_to_sdi_task": {"rate_limit": "10/m"},
    "apps.notifications.tasks.send_invoice_email_task": {"rate_limit": "30/m"},
}
```

## Task SDI (`apps/sdi/tasks.py`)

```python
from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=900,
)
def send_invoice_to_sdi_task(self, invoice_id: int):
    """Invia fattura XML al SDI in background."""
    from apps.invoices.models import Invoice
    from apps.sdi.services.openapi_client import OpenApiSdiClient
    from apps.sdi.services.xml_generator import InvoiceXmlGenerator

    invoice = Invoice.all_types.get(pk=invoice_id)
    xml = InvoiceXmlGenerator().generate(invoice)

    client = OpenApiSdiClient()
    result = client.send_invoice(xml)

    Invoice.all_types.filter(pk=invoice_id).update(
        sdi_uuid=result["uuid"],
        sdi_status="Sent",
        sdi_sent_at=timezone.now(),
    )
    logger.info("Fattura inviata a SDI", extra={
        "invoice_id": invoice_id,
        "sdi_uuid": result["uuid"],
    })
    return result


@shared_task(bind=True, max_retries=2)
def download_supplier_invoice_task(self, uuid: str):
    """Scarica XML fattura fornitore dal SDI."""
    from apps.sdi.services.openapi_client import OpenApiSdiClient
    from apps.sdi.services.xml_import import InvoiceXmlImportService

    client = OpenApiSdiClient()
    xml = client.download_invoice_xml(uuid)
    InvoiceXmlImportService().import_xml(xml, invoice_type="purchase")
    logger.info("Fattura fornitore importata", extra={"uuid": uuid})


@shared_task
def sync_supplier_invoices_task(page: int = 1, per_page: int = 50):
    """Sync periodico fatture fornitori — usato da Celery Beat."""
    from apps.sdi.services.openapi_client import OpenApiSdiClient
    from apps.sdi.models import SupplierInvoice

    client = OpenApiSdiClient()
    data = client.get_supplier_invoices(page=page, per_page=per_page)

    for item in data.get("data", []):
        SupplierInvoice.update_or_create_from_api(item)

    # Se ci sono altre pagine, accoda la prossima
    meta = data.get("meta", {})
    if meta.get("current_page", 0) < meta.get("last_page", 0):
        sync_supplier_invoices_task.delay(page=page + 1, per_page=per_page)
```

## Periodic Tasks (Celery Beat)

```python
# settings/base.py
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    "sync-supplier-invoices-daily": {
        "task": "apps.sdi.tasks.sync_supplier_invoices_task",
        "schedule": crontab(hour=6, minute=0),  # Ogni giorno alle 06:00
        "args": (1, 50),
    },
}
```

## Docker Compose (aggiungere)

```yaml
# docker-compose.yml (dev)
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  celery-worker:
    build: .
    command: celery -A djafatt worker -l INFO -Q default,sdi,email,sync --concurrency=2
    volumes:
      - .:/app
    depends_on:
      - db
      - redis
    env_file: .env

  celery-beat:
    build: .
    command: celery -A djafatt beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler
    volumes:
      - .:/app
    depends_on:
      - db
      - redis
    env_file: .env
```

```yaml
# docker-compose.prod.yml (aggiungere)
services:
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
    restart: unless-stopped

  celery-beat:
    build: .
    command: celery -A djafatt beat -l WARNING
    depends_on:
      - redis
    environment:
      - DJANGO_SETTINGS_MODULE=djafatt.settings.prod
      - CELERY_BROKER_URL=redis://redis:6379/0
    restart: unless-stopped

volumes:
  redisdata:
```

## Monitoraggio

### Health check worker

Aggiungere un endpoint o management command per verificare lo stato del worker:

```python
# apps/core/management/commands/check_celery.py
from django.core.management.base import BaseCommand
from djafatt.celery import app

class Command(BaseCommand):
    def handle(self, **options):
        inspect = app.control.inspect()
        active = inspect.active()
        if active:
            self.stdout.write(self.style.SUCCESS(f"Workers attivi: {list(active.keys())}"))
        else:
            self.stderr.write(self.style.ERROR("Nessun worker Celery attivo!"))
            raise SystemExit(1)
```

## Dipendenze aggiuntive

```toml
"django-celery-beat>=2.7",  # Scheduler per periodic tasks da DB
```

## `.env.example` (aggiungere)

```bash
CELERY_BROKER_URL=redis://redis:6379/0
```

## File da creare

- `djafatt/celery.py`
- `djafatt/__init__.py` — Aggiungere import celery
- `apps/sdi/tasks.py`
- `apps/core/management/commands/check_celery.py`
- Aggiornare `docker-compose.yml` e `docker-compose.prod.yml`

## Criteri di accettazione

- [ ] `celery -A djafatt worker` si avvia senza errori
- [ ] Task `send_invoice_to_sdi_task` invia fattura e aggiorna stato
- [ ] Task `send_invoice_email_task` invia email con PDF (T32)
- [ ] Task `sync_supplier_invoices_task` sincronizza fatture fornitori
- [ ] Celery Beat esegue sync giornaliero alle 06:00
- [ ] Retry con backoff esponenziale su fallimento
- [ ] Rate limiting: max 10 invii SDI/min, max 30 email/min
- [ ] Docker: servizi redis, celery-worker, celery-beat funzionanti
- [ ] Management command `check_celery` verifica stato worker
- [ ] Test: mock broker, verifica task accodato correttamente
