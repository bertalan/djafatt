# T09 — CRUD Prodotti/Servizi

**Fase:** 2 — CRUD Anagrafiche  
**Complessità:** Bassa  
**Dipendenze:** T02, T05, T07  
**Blocca:** T10, T12

---

## Obiettivo

Gestione catalogo prodotti/servizi con prezzo in centesimi e aliquota IVA default.

## Viste

### Lista (`/products/`)

- Tabella: Nome, Prezzo (€), Unità, Aliquota IVA, Azioni
- Ricerca per nome
- Paginazione

### Create (`/products/create/`)

- Form: nome, descrizione, prezzo (input €, salva in centesimi), unità di misura, aliquota IVA (select)

### Edit (`/products/<id>/edit/`)

- Stesso form pre-popolato
- Delete con conferma

## Conversione prezzo

- UI: utente inserisce €10.50
- Backend: salva 1050 (centesimi)
- Display: formatta come "€ 10,50" (formato italiano)

```python
class ProductForm(forms.ModelForm):
    price_display = forms.DecimalField(
        max_digits=10, decimal_places=2, label="Prezzo (€)"
    )
    
    def clean_price_display(self):
        return int(self.cleaned_data["price_display"] * 100)
    
    def save(self, commit=True):
        self.instance.price = self.cleaned_data["price_display"]
        return super().save(commit=commit)
```

## File da creare

- `apps/products/views.py`
- `apps/products/forms.py`
- `apps/products/urls.py`
- `templates/products/index.html`
- `templates/products/create.html`
- `templates/products/edit.html`
- `tests/test_products.py`

## Criteri di accettazione

- [ ] Lista prodotti con prezzo formattato in euro
- [ ] Create salva prezzo in centesimi
- [ ] Edit mostra prezzo in euro, salva in centesimi
- [ ] Select aliquota IVA funzionante
- [ ] Delete con conferma
- [ ] Ricerca per nome
