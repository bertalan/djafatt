# T32 — Notifiche Email, PEC e Invio Cortesia

**Fase:** 6 — Dashboard, Settings, Deploy  
**Complessità:** Alta  
**Dipendenze:** T31, T20, T19, T03b  
**Blocca:** Nessuno

---

## Obiettivo

Implementare il motore di invio email/PEC per tutte le notifiche fattura: invio cortesia automatico dopo SDI, invio manuale, fallback su mancata consegna (MC), e notifica ad email alternative (commercialista, segreteria). Questo è un componente critico e non opzionale per un gestionale di fatturazione.

## Requisiti Architetturali

- **Async obbligatorio:** Ogni invio email DEVE passare per un task Celery. I server SMTP PEC sono lenti (3-10s). Mai bloccare la request HTTP.
- **Dual backend SMTP:** Un backend per email transazionale (Mailgun, SES, etc.) e uno dedicato per PEC (Aruba, Legalmail, etc.).
- **Template HTML:** Email responsive con allegati (PDF + XML opzionale).
- **Retry:** Celery retry con backoff esponenziale (max 3 tentativi, delay 60/300/900s).
- **Audit:** Ogni invio/fallimento loggato nel SdiLog e nel log strutturato (T03b).

## Scenari completi di invio

### 1. Invio cortesia automatico (post-SDI)

**Trigger:** Webhook `customer-invoice` (conferma invio SDI) **E** `AUTO_SEND_COURTESY_PDF=True` in Settings.
**Destinatario:** `contact.email` o `contact.pec` (logica in `InvoicePdfService.get_recipient_email()`).
**Azione:**
1. Genera PDF di cortesia (T31).
2. Accoda task Celery `send_invoice_email_task`.
3. Allega PDF. Se l'XML è disponibile, allegarlo come secondo file.
4. Subject: "Fattura n. {number} del {date} — {company_name}".
5. Body HTML: template con riepilogo importi e CTA per visualizzare il PDF.

### 2. Invio cortesia manuale

**Trigger:** Bottone "Invia copia cortesia" nella pagina dettaglio fattura.
**Destinatario:** Campo email precompilato con `contact.email` ma modificabile (per inviare a commercialista, segreteria, etc.).
**Azione:** Accoda task Celery. Registra invio.

### 3. Invio a tutti i clienti con email (bulk, opzionale)

**Trigger:** Bottone nella lista fatture "Invia cortesia alle fatture selezionate".
**Guardia:** Solo fatture in stato ≥ "Sent". Max 50 fatture per batch per evitare abuse.
**Azione:** Accoda un task per ciascuna fattura.

### 4. Fallback Mancata Consegna (MC)

**Trigger:** Webhook SDI con stato `MC`.
**Destinatario:** `contact.pec` (priorità) > `contact.email`.
**Azione:**
1. Genera PDF di cortesia.
2. Invia con template specifico: "La fattura è stata emessa regolarmente ma il SdI non è riuscito a recapitarla al destinatario. È comunque disponibile nel cassetto fiscale. In allegato copia di cortesia."
3. Allegati: PDF + XML originale.
4. Registra invio nel SdiLog con `event_type='mc_fallback'`.

### 5. Invio PEC dedicata

**Trigger:** Bottone "Invia via PEC" (visibile solo se PEC configurata in Settings).
**Destinatario:** `contact.pec` obbligatorio.
**Backend:** Usa il backend SMTP PEC dedicato.
**Azione:** Come invio manuale ma con backend diverso.

## Implementazione

### Task Celery (`apps/notifications/tasks.py`)

```python
from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
from django.core.mail import EmailMessage, get_connection
from django.template.loader import render_to_string

from apps.invoices.models import Invoice
from apps.invoices.services.pdf_generator import InvoicePdfService

logger = get_task_logger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=900,
)
def send_invoice_email_task(
    self,
    invoice_id: int,
    recipient_email: str,
    use_pec_backend: bool = False,
    template_name: str = "emails/invoice_courtesy.html",
    extra_context: dict | None = None,
):
    invoice = Invoice.all_types.select_related("contact", "sequence").get(
        pk=invoice_id
    )
    pdf_bytes = InvoicePdfService.generate_pdf(invoice)

    context = {
        "invoice": invoice,
        "company_name": settings.CONSTANCE_CONFIG.get("COMPANY_NAME", ""),
        **(extra_context or {}),
    }
    subject = f"Fattura n. {invoice.number} del {invoice.date:%d/%m/%Y}"
    body_html = render_to_string(template_name, context)

    # Scegli backend SMTP
    if use_pec_backend and hasattr(settings, "PEC_EMAIL_BACKEND"):
        connection = get_connection(backend=settings.PEC_EMAIL_BACKEND)
        from_email = settings.PEC_FROM_EMAIL
    else:
        connection = get_connection()
        from_email = settings.DEFAULT_FROM_EMAIL

    email = EmailMessage(
        subject=subject,
        body=body_html,
        from_email=from_email,
        to=[recipient_email],
        connection=connection,
    )
    email.content_subtype = "html"
    email.attach(
        f"Fattura_{invoice.number}.pdf",
        pdf_bytes,
        "application/pdf",
    )

    # Allega XML se disponibile
    xml_content = getattr(invoice, "xml_content", None)
    if xml_content:
        email.attach(
            f"Fattura_{invoice.number}.xml",
            xml_content.encode() if isinstance(xml_content, str) else xml_content,
            "application/xml",
        )

    email.send(fail_silently=False)

    # Aggiorna tracking
    from django.utils import timezone
    Invoice.all_types.filter(pk=invoice_id).update(
        last_email_sent_at=timezone.now(),
        email_delivery_status="sent",
    )
    logger.info("Email cortesia inviata", extra={
        "invoice_id": invoice_id,
        "recipient": recipient_email,
        "pec": use_pec_backend,
    })
```

### Servizio orchestratore (`apps/notifications/services.py`)

```python
class InvoiceNotificationService:
    @staticmethod
    def send_courtesy_email(invoice, recipient_email=None, use_pec=False):
        """Accoda invio email cortesia. Ritorna task_id."""
        if not recipient_email:
            recipient_email = InvoicePdfService.get_recipient_email(invoice)
        if not recipient_email:
            raise ValueError("Nessun indirizzo email disponibile per il contatto")

        return send_invoice_email_task.delay(
            invoice_id=invoice.pk,
            recipient_email=recipient_email,
            use_pec_backend=use_pec,
        )

    @staticmethod
    def send_mc_fallback(invoice):
        """Invio automatico su Mancata Consegna."""
        recipient = invoice.contact.pec or invoice.contact.email
        if not recipient:
            logger.warning("MC fallback: nessun email per contatto %s", invoice.contact_id)
            return None

        return send_invoice_email_task.delay(
            invoice_id=invoice.pk,
            recipient_email=recipient,
            use_pec_backend=bool(invoice.contact.pec),
            template_name="emails/invoice_mc_fallback.html",
            extra_context={"is_mc_fallback": True},
        )
```

## Configurazione SMTP

### Settings (`djafatt/settings/base.py`)

```python
# Email transazionale standard
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@example.com")

# PEC dedicata (backend separato)
PEC_EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
PEC_HOST = env("PEC_HOST", default="")
PEC_PORT = env.int("PEC_PORT", default=465)
PEC_USER = env("PEC_USER", default="")
PEC_PASSWORD = env("PEC_PASSWORD", default="")
PEC_USE_SSL = True
PEC_FROM_EMAIL = env("PEC_FROM_EMAIL", default="")
```

### `.env.example` (aggiungere)

```bash
# Email transazionale
EMAIL_HOST=smtp.mailgun.org
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=noreply@tuaazienda.it

# PEC
PEC_HOST=smtps.pec.aruba.it
PEC_PORT=465
PEC_USER=tuaazienda@pec.it
PEC_PASSWORD=
PEC_FROM_EMAIL=tuaazienda@pec.it
```

## Template email

### `templates/emails/invoice_courtesy.html`

Email HTML responsive con:
- Logo aziendale
- "Gentile {contact.name}, in allegato la copia di cortesia della fattura n. {number} del {date}."
- Tabella riepilogo: Imponibile, IVA, Totale
- Footer con dati azienda e disclaimer "Questo documento ha valore puramente informativo."

### `templates/emails/invoice_mc_fallback.html`

Come sopra ma con testo dedicato:
- "La fattura è stata regolarmente emessa al SdI ma non è stato possibile recapitarla. È disponibile nel suo cassetto fiscale (fatture e corrispettivi). In allegato copia di cortesia e XML originale."

## Campi tracking su Invoice (T03)

Aggiungere al modello `Invoice`:
```python
last_email_sent_at = models.DateTimeField(null=True, blank=True)
email_delivery_status = models.CharField(
    max_length=10, blank=True, default="",
    choices=[("", "Non inviata"), ("sent", "Inviata"), ("failed", "Fallita")],
)
```

## UI

### Pagina dettaglio fattura

Aggiungere sezione "Invio cortesia":
- Badge stato invio: "Non inviata", "Inviata il {date}", "Fallita".
- Bottone "Invia copia cortesia via Email" → modale con campo email precompilato.
- Bottone "Invia via PEC" (visibile solo se PEC configurata).
- Il bottone è disabilitato se la fattura è in stato `draft` (non ha senso inviare un draft).

## File da creare

- `apps/notifications/__init__.py`
- `apps/notifications/apps.py`
- `apps/notifications/tasks.py` — Task Celery
- `apps/notifications/services.py` — Servizio orchestratore
- `templates/emails/invoice_courtesy.html`
- `templates/emails/invoice_mc_fallback.html`
- `tests/test_notifications.py`

## Criteri di accettazione

- [ ] Email cortesia inviata automaticamente dopo conferma SDI (se `AUTO_SEND_COURTESY_PDF=True`)
- [ ] Email cortesia inviabile manualmente da dettaglio fattura
- [ ] Supporto invio a email alternativa (campo editabile)
- [ ] Fallback MC: email automatica con template dedicato
- [ ] PEC: backend SMTP separato funzionante
- [ ] Retry con backoff esponenziale (3 tentativi)
- [ ] Allegati: PDF + XML (se disponibile)
- [ ] Tracking: `last_email_sent_at` e `email_delivery_status` aggiornati
- [ ] Nessun blocco della request HTTP (tutto via Celery)
- [ ] Test: mock SMTP, verifica allegati, verifica retry su timeout
