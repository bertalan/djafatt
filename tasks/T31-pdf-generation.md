# T31 — Generazione PDF cortesia + invio email automatico

**Fase:** 6 — Dashboard, Settings, Deploy  
**Complessità:** Media  
**Dipendenze:** T10, T11, T27  
**Blocca:** T32

---

## Obiettivo

Implementare la generazione del PDF di cortesia per le fatture (vendita e acquisto) e il suo invio automatico a tutti i clienti con email (ordinaria o PEC), non solo come fallback per mancata consegna SDI.

## Razionale

In Italia la fattura elettronica viene recapitata dal SdI, ma la maggior parte dei clienti (specialmente privati, professionisti e piccole aziende) preferisce ricevere una copia leggibile via email subito dopo l'emissione. Questo è lo standard de-facto per qualsiasi gestionale serio.

## Stack tecnologico

- **Libreria:** `weasyprint` (già nel `pyproject.toml`)
- **Template:** Django templates standard con CSS specifico per stampa (media print)
- **Storage:** PDF generati on-the-fly. Per fatture in stato finale (Delivered/Accepted) implementare cache opzionale per evitare rigenerazioni.

## Requisiti funzionali

1. **Layout Professionale:** Header con logo aziendale, dati emittente, dati destinatario, tabella righe con colonne (Desc, Qty, UdM, Prezzo, IVA, Totale), riepilogo totali/IVA per aliquota, ritenuta d'acconto se presente, bollo se presente, condizioni pagamento, dati bancari (IBAN).
2. **Watermark:** Aggiungere dicitura "COPIA DI CORTESIA" nel footer.
3. **Multilingua:** Etichette in inglese se `contact.country_code != 'IT'` (usa Django i18n da T27).
4. **Performance:** Generazione rapida. Se > 500ms, considerare Celery task per bulk.
5. **Download:** Endpoint dedicato per preview/scaricamento manuale.
6. **Invio automatico:** Dopo invio SDI riuscito (stato `Sent`), inviare PDF via email al contatto **se ha un indirizzo email o PEC configurato**.

## Scenari di spedizione email cortesia

| Scenario | Trigger | Destinatario | Note |
|---|---|---|---|
| **Invio automatico post-SDI** | Webhook `customer-invoice` (conferma invio) | `contact.email` o `contact.pec` | Configurabile: on/off in Settings (T24) |
| **Invio manuale** | Bottone "Invia copia cortesia" in fattura | Email scelta dall'utente | Sempre disponibile per fatture in stato ≥ draft |
| **Fallback MC** | Webhook stato `MC` (mancata consegna) | `contact.email` o `contact.pec` | Testo speciale: "fattura disponibile nel cassetto fiscale" |
| **Invio a email alternativa** | Bottone + campo email custom | Qualsiasi email inserita | Per commercialisti, segretarie, etc. |

## Implementazione (`apps/invoices/services/pdf_generator.py`)

```python
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.translation import activate, get_language
from weasyprint import HTML

class InvoicePdfService:
    WATERMARK_TEXT = "COPIA DI CORTESIA"

    @staticmethod
    def generate_pdf(invoice, language=None) -> bytes:
        if language is None:
            language = 'en' if invoice.contact.country_code != 'IT' else 'it'

        prev_lang = get_language()
        try:
            activate(language)
            context = {
                'invoice': invoice,
                'company': invoice.company_data,
                'client': invoice.contact,
                'lines': invoice.lines.select_related('vat_rate').all(),
                'totals': invoice.totals,
                'vat_summary': invoice.get_vat_summary(),
                'bank': invoice.bank_data,
                'watermark': InvoicePdfService.WATERMARK_TEXT,
            }
            html_string = render_to_string(
                'invoices/pdf/invoice.html', context
            )
            return HTML(
                string=html_string,
                base_url=str(settings.STATIC_ROOT),
            ).write_pdf()
        finally:
            activate(prev_lang)

    @staticmethod
    def get_recipient_email(invoice) -> str | None:
        """Ritorna l'email migliore per il contatto: PEC > email > None."""
        contact = invoice.contact
        return contact.pec or contact.email or None
```

## Template (`apps/invoices/templates/invoices/pdf/invoice.html`)

Struttura:
- `@page { size: A4; margin: 15mm 20mm; }`
- `@page { @bottom-center { content: "COPIA DI CORTESIA — Pagina " counter(page) " di " counter(pages); } }`
- `table thead` ripetuto su ogni pagina break (`thead { display: table-header-group; }`)
- Logo azienda da `STATIC_ROOT` o `CONSTANCE_CONFIG['COMPANY_LOGO_URL']`
- Tutte le stringhe wrappate in `{% trans %}` per multilingua

## Endpoint

```python
# apps/invoices/urls.py
path("<int:pk>/pdf/", InvoicePdfView.as_view(), name="invoice-pdf"),
```

- `GET /invoices/<pk>/pdf/`: Preview/download PDF.
- Permessi: `LoginRequiredMixin` + ownership check (stessa azienda).
- `Content-Type: application/pdf`
- `Content-Disposition: inline; filename="Fattura_{number}.pdf"` (inline = preview browser, il download è via `?download=1`)

## Configurazione (T24 - Settings)

Aggiungere in `CONSTANCE_CONFIG`:
```python
'AUTO_SEND_COURTESY_PDF': (True, 'Invia PDF cortesia via email dopo invio SDI', bool),
```

## Cache

- Fatture con `sdi_status in ('Delivered', 'Accepted')` sono immutabili → cache il PDF generato in `MEDIA_ROOT/pdf_cache/{invoice_pk}.pdf`.
- Invalidare se la fattura cambia status (non dovrebbe succedere per stati finali).

## File da creare

- `apps/invoices/services/pdf_generator.py`
- `apps/invoices/templates/invoices/pdf/invoice.html`
- `apps/invoices/templates/invoices/pdf/styles.css` (incluso inline nel template)
- `apps/invoices/views_pdf.py` — View per endpoint download
- `tests/test_pdf_generator.py`

## Vincoli implementativi

- Il template PDF (`invoices/pdf/invoice.html`) è **standalone**: include il proprio CSS inline, non usa `base.html` né Tailwind/DaisyUI
- Il CSS è `@page`/`@media print` puro, non Tailwind utility classes — WeasyPrint non supporta Tailwind
- I bottoni "Invia copia cortesia" e "Scarica PDF" nel template fattura web sono normali link/form DaisyUI (cfr. T05 regole frontend)
- Nessun JavaScript nel flusso PDF: la preview nel browser è un `Content-Type: application/pdf` diretto
- I task Celery per invio email sono definiti in T32 — questo task produce solo il `bytes` PDF

## Criteri di accettazione

- [ ] PDF generato corretto per fattura con righe, IVA, ritenuta, bollo
- [ ] Layout A4 professionale con logo e dati bancari
- [ ] Watermark "COPIA DI CORTESIA" nel footer
- [ ] Multilingua: etichette in inglese per clienti esteri
- [ ] Endpoint restituisce PDF con content-type corretto
- [ ] Solo utenti autenticati (owner) possono accedere al PDF
- [ ] Servizio `get_recipient_email()` restituisce PEC > email > None
- [ ] Test: fattura con 0 righe → PDF valido (vuoto ma generato)
- [ ] Test: fattura con 50 righe → PDF multi-pagina con header ripetuto
