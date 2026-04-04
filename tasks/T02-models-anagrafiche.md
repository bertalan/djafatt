# T02 — Modelli anagrafiche (Contact, VatRate, Sequence, Product)

**Fase:** 1 — Fondamenta  
**Complessità:** Media  
**Dipendenze:** T01  
**Blocca:** T06, T07, T08, T09, T03

---

## Obiettivo

Creare i modelli Django per le entità anagrafiche di base, traducendo fedelmente i modelli Laravel.

## Modelli

### Contact (`apps/contacts/models.py`)

```python
class Contact(models.Model):
    name = models.CharField(max_length=255)
    vat_number = models.CharField(max_length=30, blank=True, default="")
    tax_code = models.CharField(max_length=30, blank=True, default="")
    address = models.CharField(max_length=255, blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    postal_code = models.CharField(max_length=10, blank=True, default="")
    province = models.CharField(max_length=5, blank=True, default="")
    country = models.CharField(max_length=100, blank=True, default="")
    country_code = models.CharField(max_length=2, default="IT")
    sdi_code = models.CharField(max_length=7, blank=True, default="")
    pec = models.CharField(max_length=255, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=30, blank=True, default="")
    mobile = models.CharField(max_length=30, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    is_customer = models.BooleanField(default=False)
    is_supplier = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

**Metodi business:**
- `is_italian() -> bool` — `self.country_code == "IT"`
- `is_eu() -> bool` — country_code in lista paesi UE
- `get_sdi_code_for_xml() -> str` — SDI code o `"XXXXXXX"` per esteri
- `get_postal_code_for_xml() -> str` — postal_code o `"00000"` per esteri
- `get_province_for_xml() -> str` — province o `"EE"` per esteri
- `get_vat_number_clean() -> str` — rimuove prefisso paese (IT, DE, FR…)
- `logo_url() -> str|None` — URL Brandfetch da dominio email

### VatRate (`apps/invoices/models.py`)

```python
class VatRate(models.Model):
    name = models.CharField(max_length=100)
    percent = models.DecimalField(max_digits=5, decimal_places=2)
    description = models.CharField(max_length=255, blank=True, default="")
    nature = models.CharField(max_length=10, blank=True, default="")  # N1-N7
    is_system = models.BooleanField(default=False)
```

**Vincoli:** Non eliminabile se `is_system=True` o se ha righe fattura collegate.

### Sequence (`apps/invoices/models.py`)

```python
class Sequence(models.Model):
    class SequenceType(models.TextChoices):
        SALES = "sales", "Vendita"
        PURCHASE = "purchase", "Acquisto"
        SELF_INVOICE = "self_invoice", "Autofattura"

    name = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=SequenceType.choices)
    pattern = models.CharField(max_length=100, default="{SEQ}")
    is_system = models.BooleanField(default=False)
```

**Metodi business:**
- `get_next_number(year: int = None) -> int` — Prossimo numero sequenziale per anno (MAX + 1 dalla tabella invoices)
- `get_formatted_number(year: int = None) -> str` — Applica pattern: `{SEQ}` → zero-padded 4 cifre, `{ANNO}` → anno 4 cifre

**Vincoli:**
- Non eliminabile se `is_system=True` o se ha fatture collegate
- Non può cambiare `type` se `is_system=True`

### Product (`apps/products/models.py`)

```python
class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    price = models.IntegerField(default=0)  # centesimi
    unit = models.CharField(max_length=10, blank=True, default="")
    vat_rate = models.ForeignKey(VatRate, on_delete=models.PROTECT, null=True, blank=True)
```

## Migrazioni

- `apps/contacts/migrations/0001_initial.py`
- `apps/invoices/migrations/0001_initial.py` (VatRate + Sequence)
- `apps/products/migrations/0001_initial.py`

## Seeder iniziale

Creare management command `seed_defaults`:
- Aliquote IVA system: 22% Ordinaria, 10% Ridotta, 4% Minima, 0% Esente (N1), 0% Non imponibile (N3.1)
- Sequenze system: "Fatture vendita" (sales, `{SEQ}/{ANNO}`), "Fatture acquisto" (purchase, `{SEQ}/{ANNO}`)

## File da creare/modificare

- `apps/contacts/models.py`
- `apps/contacts/admin.py` (registrazione base)
- `apps/invoices/models.py` (VatRate, Sequence)
- `apps/invoices/admin.py`
- `apps/products/models.py`
- `apps/products/admin.py`
- `apps/core/management/commands/seed_defaults.py`
- `tests/test_models_base.py`

## Criteri di accettazione

- [ ] `migrate` crea tabelle contacts, vat_rates, sequences, products
- [ ] `seed_defaults` popola aliquote e sequenze system
- [ ] `Contact.is_italian()` ritorna True/False correttamente
- [ ] `Contact.get_sdi_code_for_xml()` ritorna "XXXXXXX" per esteri
- [ ] `Sequence.get_formatted_number()` formatta correttamente con pattern
- [ ] `VatRate` system non eliminabile (override `delete()`)
- [ ] `Sequence` con fatture non eliminabile
- [ ] Importi Product in centesimi (100 = €1.00)
