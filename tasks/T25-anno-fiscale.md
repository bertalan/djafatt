# T25 — Anno fiscale (selezione + filtro + read-only)

**Fase:** 6 — Dashboard, Settings, Deploy  
**Complessità:** Bassa  
**Dipendenze:** T05  
**Blocca:** T10, T13, T23

---

## Obiettivo

Implementare selezione anno fiscale in sessione con filtro globale sulle query e protezione read-only per anni passati.

## Comportamento (replica dell'originale)

1. **Selezione anno** nella sidebar (dropdown o selector)
2. **Anno in sessione**: `request.session["fiscal_year"]`, default anno corrente
3. **Filtro globale**: tutte le view fatture filtrano per `date__year=fiscal_year`
4. **Read-only per anni passati**: se anno < anno corrente:
   - Banner "Anno XXXX — solo lettura"
   - Nascondere bottoni "Crea", "Elimina"
   - Form in edit mode → campi disabilitati
5. **Redirect se crea in anno passato**: redirect a /invoices/ con messaggio

## Implementazione

### Selector anno (sidebar)

```html
<select hx-post="{% url 'set-fiscal-year' %}" 
        hx-trigger="change"
        hx-target="body"
        hx-swap="outerHTML"
        name="year">
    {% for y in available_years %}
        <option value="{{ y }}" {% if y == fiscal_year %}selected{% endif %}>
            {{ y }}
        </option>
    {% endfor %}
</select>
```

### View cambio anno

```python
def set_fiscal_year(request):
    year = int(request.POST.get("year", datetime.now().year))
    if year not in range(datetime.now().year, 2024, -1):
        return HttpResponseBadRequest("Invalid fiscal year")
    request.session["fiscal_year"] = year
    return redirect(request.META.get("HTTP_REFERER", "/dashboard/"))
```

### Context processor

```python
def fiscal_year_context(request):
    year = request.session.get("fiscal_year", datetime.now().year)
    return {
        "fiscal_year": year,
        "is_read_only": year < datetime.now().year,
        "available_years": range(datetime.now().year, 2024, -1),
    }
```

### Mixin per view

```python
class FiscalYearMixin:
    def get_fiscal_year(self):
        return self.request.session.get("fiscal_year", datetime.now().year)
    
    def is_read_only(self):
        return self.get_fiscal_year() < datetime.now().year
    
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(date__year=self.get_fiscal_year())
```

## File da creare/modificare

- `apps/core/context_processors.py` — fiscal_year_context
- `apps/core/views.py` — set_fiscal_year view
- `apps/core/mixins.py` — FiscalYearMixin
- `templates/partials/_sidebar.html` — Aggiungere selector
- `templates/components/_alert.html` — Banner read-only
- `djafatt/settings/base.py` — Registrare context processor

## Criteri di accettazione

- [x] Selector anno visibile in sidebar
- [x] Cambio anno aggiorna sessione
- [x] Fatture filtrate per anno selezionato
- [x] Banner read-only per anni passati
- [ ] Bottoni "Crea" nascosti in anno passato
- [ ] Edit disabilitato in anno passato
- [x] Redirect se tenta create in anno passato
- [x] Cambio anno usa POST con CSRF, non GET mutante
- [x] Anno fuori range → 400
- [x] Solo Amministratore/Contabile possono cambiare anno (Operatore vede solo l'anno corrente)
- [x] Sidebar mostra dropdown solo a utenti con permesso `invoices.view_invoice`
