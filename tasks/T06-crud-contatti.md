# T06 — CRUD Contatti (Clienti/Fornitori)

**Fase:** 2 — CRUD Anagrafiche  
**Complessità:** Media  
**Dipendenze:** T02, T05  
**Blocca:** T10, T13

---

## Obiettivo

Lista contatti con ricerca e paginazione, creazione, modifica, cancellazione con protezione se in uso.

---

## URL (`apps/contacts/urls.py`)

| Metodo | URL | View | Nome |
|---|---|---|---|
| GET | `/contacts/` | `ContactListView` | `contacts:index` |
| GET | `/contacts/create/` | `ContactCreateView` | `contacts:create` |
| GET/POST | `/contacts/<pk>/edit/` | `ContactEditView` | `contacts:edit` |
| POST | `/contacts/<pk>/delete/` | `ContactDeleteView` | `contacts:delete` |

---

## Views

### Lista (`ContactListView`)

- Paginazione: 15 per pagina
- Ricerca live (HTMX): filtra per `name`, `vat_number`, `tax_code`
- Ordinamento: per nome (default), per data creazione
- Badge: `cliente` / `fornitore` / entrambi
- Logo avatar via Brandfetch (opzionale, T30)
- Bottone "Crea" nell'header

### Create / Edit (`ContactCreateView`, `ContactEditView`)

- Form con tutti i campi Contact
- Logica paese: se `country_code != IT`, disabilita/svuota `province`
- Selezione `country_code` da dropdown con paesi EU + extra-UE comuni
- `sdi_code` default: `0000000`
- Checkbox `is_customer`, `is_supplier`

### Delete (`ContactDeleteView`)

- Verifica: se il contatto ha fatture associate → errore "Impossibile eliminare"
- Altrimenti: elimina e toast "Contatto eliminato"
- Conferma via `hx-confirm`

---

## Template

| File | Descrizione |
|---|---|
| `templates/contacts/index.html` | Lista con tabella, search, pagination |
| `templates/contacts/form.html` | Form create/edit riusabile |
| `templates/contacts/partials/table.html` | Tabella HTMX (partial per ricerca live) |

### HTMX: ricerca live

```html
<input type="text" name="search"
       hx-get="{% url 'contacts:index' %}"
       hx-trigger="input changed delay:300ms"
       hx-target="#contacts-table"
       hx-push-url="true"
       placeholder="Cerca contatti..." />

<div id="contacts-table">
    {% include "contacts/partials/table.html" %}
</div>
```

---

## Form (`apps/contacts/forms.py`)

```python
class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = [
            "name", "vat_number", "tax_code",
            "address", "city", "postal_code", "province",
            "country", "country_code",
            "sdi_code", "pec", "email", "phone", "mobile",
            "notes", "is_customer", "is_supplier",
        ]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
            "country_code": forms.Select(choices=COUNTRY_CHOICES),
        }
```

---

## Criteri di accettazione

- [ ] Lista contatti con paginazione funzionante
- [ ] Ricerca live filtra senza reload pagina (HTMX)
- [ ] Creazione contatto con tutti i campi
- [ ] Modifica contatto preserva dati
- [ ] Cancellazione bloccata se contatto ha fatture
- [ ] Cancellazione con conferma modale/hx-confirm
- [ ] Badge cliente/fornitore visibili in lista
- [ ] Toast messages per successo/errore
