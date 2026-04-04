# T12 — Gestione righe fattura con HTMX

**Fase:** 3 — Fatture Attive  
**Complessità:** Media  
**Dipendenze:** T05, T03  
**Blocca:** T10, T13, T14

---

## Obiettivo

Implementare add/remove righe fattura via HTMX con ricalcolo totali live nel sidebar, selezione prodotto → auto-fill, datalist unità misura.

## Comportamento UI

### Aggiunta riga

1. Click "Aggiungi riga"
2. HTMX POST → view ritorna HTML partial con nuova riga vuota
3. Riga aggiunta al DOM senza reload

### Rimozione riga

1. Click icona 🗑️ sulla riga
2. HTMX DELETE → rimuove riga dal DOM
3. Totali sidebar aggiornati

### Ricalcolo totali live

1. Ogni modifica a quantità/prezzo/aliquota
2. HTMX POST (debounce 300ms) → ricalcolo server-side
3. Partial response aggiorna solo il div totali

### Selezione prodotto (opzionale)

1. Dropdown prodotto in riga
2. On change → HTMX GET → auto-popola: descrizione, prezzo, aliquota IVA, unità misura

## Endpoint HTMX

```python
urlpatterns = [
    path("invoices/lines/add/", add_invoice_line, name="invoices-add-line"),
    path("invoices/lines/<int:index>/remove/", remove_invoice_line, name="invoices-remove-line"),
    path("invoices/lines/totals/", calculate_totals_partial, name="invoices-totals"),
    path("invoices/lines/product-fill/<int:product_id>/", product_autofill, name="invoices-product-fill"),
]
```

## Template partial (`templates/invoices/partials/_line_row.html`)

```html
<div class="border-b pb-4 space-y-2" id="line-{{ index }}">
    <!-- Riga 1: Descrizione -->
    <input name="lines-{{ index }}-description" class="input input-bordered w-full" />
    
    <!-- Riga 2: Quantità, UdM, Prezzo, IVA, Delete -->
    <div class="grid grid-cols-12 gap-2 items-end">
        <div class="col-span-2">
            <input name="lines-{{ index }}-quantity" type="number" step="0.01" value="1"
                   hx-post="{% url 'invoices-totals' %}"
                   hx-trigger="input changed delay:300ms"
                   hx-target="#totals-sidebar" />
        </div>
        <div class="col-span-2">
            <input name="lines-{{ index }}-unit_of_measure" list="uom-options" placeholder="pz" />
        </div>
        <div class="col-span-3">
            <input name="lines-{{ index }}-unit_price" type="number" step="0.01" prefix="€"
                   hx-post="{% url 'invoices-totals' %}"
                   hx-trigger="input changed delay:300ms"
                   hx-target="#totals-sidebar" />
        </div>
        <div class="col-span-4">
            <select name="lines-{{ index }}-vat_rate"
                    hx-post="{% url 'invoices-totals' %}"
                    hx-trigger="change"
                    hx-target="#totals-sidebar">
                {% for rate in vat_rates %}
                    <option value="{{ rate.id }}">{{ rate.name }}</option>
                {% endfor %}
            </select>
        </div>
        <div class="col-span-1">
            <button hx-delete="{% url 'invoices-remove-line' index %}"
                    hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'
                    hx-target="#line-{{ index }}"
                    hx-swap="outerHTML">🗑️</button>
        </div>
    </div>
</div>
```

## Datalist unità misura

```html
<datalist id="uom-options">
    <option value="pz">Pezzi</option>
    <option value="hh">Ore</option>
    <option value="gg">Giorni</option>
    <option value="nr">Numero</option>
    <option value="m">Metri</option>
    <option value="kg">Kilogrammi</option>
    <option value="lt">Litri</option>
</datalist>
```

## Sidebar totali (`templates/invoices/partials/_totals.html`)

```html
<div id="totals-sidebar">
    <div class="flex justify-between mb-2">
        <span>Imponibile</span>
        <span>€ {{ total_net|format_cents }}</span>
    </div>
    <div class="flex justify-between mb-2">
        <span>IVA</span>
        <span>€ {{ total_vat|format_cents }}</span>
    </div>
    {% if withholding_amount > 0 %}
    <div class="flex justify-between mb-2 text-warning">
        <span>Ritenuta d'acconto</span>
        <span>- € {{ withholding_amount|format_cents }}</span>
    </div>
    {% endif %}
    {% if stamp_duty > 0 %}
    <div class="flex justify-between mb-2">
        <span>Bollo</span>
        <span>€ {{ stamp_duty|format_cents }}</span>
    </div>
    {% endif %}
    <hr class="my-3" />
    <div class="flex justify-between font-bold text-lg">
        <span>Totale</span>
        <span>€ {{ total_gross|format_cents }}</span>
    </div>
</div>
```

## Template filter `format_cents`

```python
@register.filter
def format_cents(value):
    """Formatta centesimi in euro con formato italiano."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        return "0,00"
    sign = "-" if value < 0 else ""
    abs_value = abs(value)
    euros = abs_value // 100
    cents = abs_value % 100
    return f"{sign}{euros},{cents:02d}"
```

## File da creare

- `apps/invoices/views_htmx.py` — View per add/remove/totali/product-fill
- `templates/invoices/partials/_line_row.html`
- `templates/invoices/partials/_totals.html`
- `apps/invoices/templatetags/invoice_tags.py` — `format_cents` filter

## Note di sicurezza

- Nessun endpoint HTMX mutante deve essere `csrf_exempt`
- Tutte le mutate linee devono validare server-side quantità, prezzo, IVA e ownership fattura
- Le route di rimozione devono verificare che la riga appartenga alla fattura corrente

## Vincoli implementativi

- **Zero JavaScript custom**: tutta l'interattività è in attributi HTMX nei template
- I partial (`_line_row.html`, `_totals.html`) devono avere un `id=` root element che corrisponde al `hx-target`
- Il CSRF è gestito globalmente dal listener in `main.js` (T05) — non duplicare
- `hx-headers` con CSRF esplicito è necessario SOLO per `hx-delete` su pulsanti (non form)
- Le classi CSS sono esclusivamente Tailwind utility + DaisyUI semantic (cfr. T05 regole frontend)
- `format_cents` è un template filter — mai formattare lato client

## Criteri di accettazione

- [ ] Aggiunta riga senza reload pagina
- [ ] Rimozione riga con aggiornamento DOM
- [ ] Totali sidebar aggiornati in tempo reale (dopo 300ms debounce)
- [ ] Selezione prodotto auto-popola campi
- [ ] Datalist unità di misura funzionante
- [ ] Formato euro italiano (1.234,56)
- [ ] POST/DELETE senza CSRF falliscono con 403
