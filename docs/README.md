# djafatt — Documentazione

Applicazione di fatturazione elettronica italiana (FatturaPA) costruita con Django 6.0.

## Indice Documentazione

| Documento | Descrizione |
|-----------|-------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Architettura software, pattern e struttura progetto |
| [MODELS.md](MODELS.md) | Schema modelli dati e relazioni |
| [SECURITY_REVIEW.md](SECURITY_REVIEW.md) | Analisi sicurezza OWASP Top 10 |
| [COMPATIBILITY.md](COMPATIBILITY.md) | Report compatibilità dipendenze |
| [DEVELOPMENT.md](DEVELOPMENT.md) | Guida sviluppo: setup, test, CI |
| [API.md](API.md) | Endpoint e integrazioni SDI |

## Stack Tecnologico

- **Backend:** Django 6.0, Python 3.12+, PostgreSQL 17
- **Frontend:** HTMX 2, Tailwind 4, DaisyUI 5, Vite 7
- **Async:** Celery 5.4 + Redis
- **FatturaPA:** a38 + defusedxml + lxml
- **SDI:** httpx → OpenAPI SDI REST
- **Test:** pytest + factory-boy + respx, 102 test CI + 4 sandbox, coverage ≥85%
