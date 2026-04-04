# Security Review — djafatt

## Sommario

Analisi di sicurezza basata su OWASP Top 10 (2021) per l'applicazione djafatt di fatturazione elettronica italiana.

**Postura complessiva: MEDIO-ALTA** — L'architettura è solida ma richiede attenzione su aree specifiche.

---

## OWASP Top 10 Analysis

### A01 — Broken Access Control ⚠️ MEDIO

| Area | Stato | Dettaglio |
|------|-------|-----------|
| `@login_required` su tutte le view | ✅ | Configurato in `urls.py` e middleware |
| Protezione record SDI-locked | ✅ | Service + view layer check. Fatture locked: solo pagamenti editabili |
| System VatRate/Sequence protezione | ✅ | `is_system` flag con protezione `delete()` |
| IDOR (Insecure Direct Object Reference) | ⚠️ | Single-tenant per design, ma verificare `get_object_or_404` |

**Raccomandazioni:**
- In ogni view di edit/delete, verificare `is_sdi_editable()` prima di procedere (già implementato).
- Le fatture SDI-locked permettono solo la modifica delle rate di pagamento (`PaymentDueFormSet`).
- I campi non-payment sono disabilitati tramite `<fieldset disabled>` nel template.

### A02 — Cryptographic Failures ✅ BASSO

| Area | Stato | Dettaglio |
|------|-------|-----------|
| Password hashing | ✅ | Django default (PBKDF2/Argon2) |
| HMAC webhook verification | ✅ | SHA-256 + `secrets.compare_digest` |
| Token SDI in env var | ✅ | `OPENAPI_SDI_TOKEN` da `.env`, non in codice |
| Idempotency key | ✅ | SHA-256 hash del contenuto XML || XML IdCodice | ✅ | Per persona fisica usa `tax_code` (CF 16 chars), non P.IVA numerica |
### A03 — Injection ✅ BASSO

| Area | Stato | Dettaglio |
|------|-------|-----------|
| SQL Injection | ✅ | Django ORM esclude SQL raw |
| XML Injection (XXE) | ✅ | `defusedxml` per tutti i parsing |
| XSS | ✅ | Django template auto-escaping + HTMX |
| Command Injection | ✅ | Nessun `os.system()` o `subprocess` |
| SSTI | ✅ | Django templates (non Jinja2 user-input) |

### A04 — Insecure Design ⚠️ MEDIO

| Area | Stato | Dettaglio |
|------|-------|-----------|
| Rate limiting | ⚠️ | Non implementato su login/webhook |
| Session timeout | ⚠️ | Django default (2 settimane) — troppo lungo per app finanziaria |
| Audit trail | ⚠️ | Logging strutturato presente, audit DB non implementato |

**Raccomandazioni:**
- `SESSION_COOKIE_AGE = 3600` (1 ora) per app finanziaria.
- Aggiungere `django-axes` per rate limiting login.
- Implementare IP whitelist per webhook SDI (se OpenAPI fornisce range IP).

### A05 — Security Misconfiguration ✅ BASSO

| Area | Stato | Dettaglio |
|------|-------|-----------|
| DEBUG = False in prod | ✅ | `settings/prod.py` |
| HTTPS enforced | ✅ | `SECURE_SSL_REDIRECT`, `HSTS` |
| Secret key da env | ✅ | `SECRET_KEY = os.environ["SECRET_KEY"]` |
| ALLOWED_HOSTS | ✅ | Configurato da env var |
| Security middleware | ✅ | `SecurityMiddleware`, `X-Frame-Options`, `CSP` |

### A06 — Vulnerable Components ⚠️ MEDIO

| Area | Stato | Dettaglio |
|------|-------|-----------|
| Dependency scanning | ⚠️ | `pip-audit` non in CI |
| Known CVEs | ✅ | Nessun CVE noto nelle versioni pinnate |
| a38 library audit | ⚠️ | Libreria piccola, pochi auditor |

**Raccomandazioni:**
- Aggiungere `pip-audit` allo step CI.
- GitHub Dependabot alerts attivati.
- Monitorare `a38` per aggiornamenti sicurezza.

### A07 — Authentication Failures ✅ BASSO

| Area | Stato | Dettaglio |
|------|-------|-----------|
| Django auth system | ✅ | `django.contrib.auth` standard |
| Password validation | ✅ | `AUTH_PASSWORD_VALIDATORS` configurati |
| CSRF protection | ✅ | `CsrfViewMiddleware` + HTMX header injection |

### A08 — Software Integrity Failures ⚠️ MEDIO

| Area | Stato | Dettaglio |
|------|-------|-----------|
| Celery serializer | ✅ | `CELERY_ACCEPT_CONTENT = ["json"]` — no pickle |
| SRI per JS/CSS esterni | ⚠️ | CDN non usati (Vite bundle locale) — OK |
| XML content hash | ✅ | SHA-256 per idempotency import |
| Docker image pinning | ⚠️ | Usare digest specifici in Dockerfile prod |

### A09 — Logging & Monitoring ⚠️ MEDIO

| Area | Stato | Dettaglio |
|------|-------|-----------|
| Structured logging | ✅ | `structlog`/JSON logging configurato |
| Request ID | ✅ | `RequestIdMiddleware` propaga UUID |
| Sensitive data redaction | ✅ | `RedactingFilter` per token/password in log |
| SDI event logging | ⚠️ | Da implementare (T26 — SdiLog model) |
| Alert on security events | ⚠️ | Non configurato |

**Raccomandazioni:**
- Implementare `SdiLog` model (T26) per audit trail completo.
- Alert su: webhook signature failure, login failure burst, SDI error rate.

### A10 — Server-Side Request Forgery (SSRF) ✅ BASSO

| Area | Stato | Dettaglio |
|------|-------|-----------|
| Outbound HTTP | ✅ | Solo verso endpoint SDI fissi (`openapi.it`) |
| XML external entities | ✅ | `defusedxml` blocca URI esterni |
| Redirect following | ✅ | `httpx` con `follow_redirects=False` default |

---

## Riepilogo Rischi e Priorità

| # | Rischio | Severità | Priorità | Azione |
|---|---------|----------|----------|--------|
| 1 | Session timeout troppo lungo | MEDIA | P1 | `SESSION_COOKIE_AGE = 3600` |
| 2 | Rate limiting assente | MEDIA | P2 | `django-axes` o middleware custom |
| 3 | pip-audit in CI | MEDIA | P2 | Aggiungere step in `ci.yml` |
| 4 | Audit trail SDI (T26) | MEDIA | P2 | Implementare `SdiLog` model |
| 5 | Docker image digest pinning | BASSA | P3 | Usare `python:3.12-slim@sha256:...` |
| 6 | Webhook IP whitelist | BASSA | P3 | Se disponibile da OpenAPI |
| 7 | Alert security events | BASSA | P3 | Sentry/PagerDuty integration |

---

## Checklist Sicurezza Pre-Produzione

- [ ] `SECRET_KEY` generato con `django.core.management.utils.get_random_secret_key()`
- [ ] `DEBUG = False` verificato
- [ ] `ALLOWED_HOSTS` restrittivo
- [ ] `SECURE_SSL_REDIRECT = True`
- [ ] `SECURE_HSTS_SECONDS >= 31536000`
- [ ] `SESSION_COOKIE_SECURE = True`
- [ ] `CSRF_COOKIE_SECURE = True`
- [ ] `SECURE_BROWSER_XSS_FILTER = True`
- [ ] PostgreSQL utente con permessi minimi
- [ ] Backup database criptato
- [ ] pip-audit clean
- [ ] `manage.py check --deploy` senza warning
