# T08 — CRUD Sequenze numerazione

**Fase:** 2 — CRUD Anagrafiche  
**Complessità:** Media  
**Dipendenze:** T02, T05  
**Blocca:** T10, T13, T14

---

## Obiettivo

Gestione sequenze di numerazione fatture con pattern personalizzabili e protezione system.

## Viste

### Lista (`/sequences/`)

- Tabella: Nome, Tipo, Pattern, System, Prossimo numero, Azioni
- Badge tipo (Vendita/Acquisto/Autofattura)
- Preview "Prossimo numero" calcolato in tempo reale

### Create (`/sequences/create/`)

- Form: nome, tipo (select), pattern
- Help text pattern: `{SEQ}` = numero sequenziale (0001), `{ANNO}` = anno (2026)
- Preview live del pattern (es. "0001/2026")

### Edit (`/sequences/<id>/edit/`)

- Tipo non modificabile se `is_system=True`
- Delete bloccato se ha fatture collegate o `is_system=True`

## Logica Pattern

```python
def get_formatted_number(self, year=None):
    year = year or datetime.now().year
    next_num = self.get_next_number(year)
    result = self.pattern
    result = result.replace("{SEQ}", str(next_num).zfill(4))
    result = result.replace("{ANNO}", str(year))
    return result

def get_next_number(self, year=None):
    year = year or datetime.now().year
    # SELECT FOR UPDATE per evitare race condition su creazioni concorrenti
    with transaction.atomic():
        max_num = (
            Invoice.all_types
            .select_for_update()
            .filter(sequence=self, date__year=year)
            .aggregate(max_num=Max("sequential_number"))["max_num"]
        )
        return (max_num or 0) + 1
```

## File da creare

- `apps/invoices/views_sequence.py`
- `apps/invoices/forms.py` — SequenceForm (aggiungere)
- `templates/sequences/index.html`
- `templates/sequences/create.html`
- `templates/sequences/edit.html`
- `tests/test_sequences.py`

## Criteri di accettazione

- [ ] Lista sequenze con preview prossimo numero
- [ ] Pattern `{SEQ}/{ANNO}` formatta correttamente (es. "0001/2026")
- [ ] Numerazione resetta a 1 ogni anno
- [ ] Delete bloccato per sequenze system
- [ ] Delete bloccato per sequenze con fatture
- [ ] Tipo non modificabile se system
