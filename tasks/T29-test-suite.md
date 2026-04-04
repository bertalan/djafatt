# T29 — Test suite completa

**Fase:** 6 — Dashboard, Settings, Deploy  
**Complessità:** Alta  
**Dipendenze:** T01-T28 (tutti)  
**Blocca:** Nessuno

---

## Obiettivo

Test suite con pytest + factory_boy. Target: 50+ test methods che coprono modelli, calcoli, XML, import, API, views.

La suite va organizzata per livelli: unit, integration, security, contract. Questo task copre la base; i casi round-trip e hardening sono estesi in `T29b`.

## Strategia TDD

- Ogni task di dominio critico nasce con test failing prima dell'implementazione
- Unit test per servizi puri e validatori
- Integration test per view, DB, import XML e workflow SDI
- Security test per XXE, CSRF, webhook signing, permission boundary
- Contract test per client OpenAPI SDI con mock `respx`

## Setup (`tests/conftest.py`)

```python
import pytest
from django.test import Client

@pytest.fixture
def auth_client(db):
    """Client autenticato."""
    from django.contrib.auth.models import User
    user = User.objects.create_user("test@test.com", password="testpass")
    client = Client()
    client.login(username="test@test.com", password="testpass")
    return client

@pytest.fixture
def company_settings():
    """Setup constance con dati azienda test."""
    from constance import config
    config.COMPANY_NAME = "Test SRL"
    config.COMPANY_VAT_NUMBER = "01234567890"
    config.COMPANY_TAX_CODE = "01234567890"
    config.COMPANY_ADDRESS = "Via Test 1"
    config.COMPANY_CITY = "Roma"
    config.COMPANY_POSTAL_CODE = "00100"
    config.COMPANY_PROVINCE = "RM"
    config.COMPANY_FISCAL_REGIME = "RF01"
```

## Factories (`tests/factories.py`)

```python
import factory
from apps.contacts.models import Contact
from apps.invoices.models import Invoice, InvoiceLine, VatRate, Sequence

class ContactFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Contact
    name = factory.Sequence(lambda n: f"Cliente {n}")
    vat_number = factory.Sequence(lambda n: f"{n:011d}")
    country_code = "IT"
    is_customer = True

class VatRateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = VatRate
    name = "IVA 22%"
    percent = 22

class SequenceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Sequence
    name = "Test"
    type = "sales"
    pattern = "{SEQ}/{ANNO}"

class InvoiceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Invoice
    contact = factory.SubFactory(ContactFactory)
    sequence = factory.SubFactory(SequenceFactory)
    date = factory.LazyFunction(lambda: date.today())
    number = "0001/2026"

class InvoiceLineFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = InvoiceLine
    invoice = factory.SubFactory(InvoiceFactory)
    vat_rate = factory.SubFactory(VatRateFactory)
    description = "Servizio test"
    quantity = 1
    unit_price = 10000  # €100
    total = 10000
```

## Categorie test

### 1. Modelli base (~10 test)

```python
# tests/test_models.py
def test_contact_is_italian()
def test_contact_is_eu()
def test_contact_sdi_code_foreign()
def test_vat_rate_system_not_deletable()
def test_vat_rate_in_use_not_deletable()
def test_sequence_next_number()
def test_sequence_formatted_number()
def test_sequence_system_not_deletable()
def test_product_price_in_cents()
def test_invoice_proxy_type_filter()
```

### 2. Calcoli fattura (~10 test)

```python
# tests/test_calculations.py
def test_simple_totals()
def test_multiple_lines()
def test_different_vat_rates()
def test_withholding_tax()
def test_stamp_duty_applied()
def test_stamp_duty_below_threshold()
def test_stamp_duty_not_on_purchase()
def test_split_payment()
def test_signal_recalculation()
def test_vat_summary()
```

### 3. XML generation (~8 test)

```python
# tests/test_xml.py
def test_generate_sales_invoice_xml()
def test_xml_italian_client()
def test_xml_foreign_client()
def test_xml_eu_client()
def test_xml_with_stamp_duty()
def test_xml_with_withholding()
def test_self_invoice_xml_td17()
def test_self_invoice_xml_td18()
```

### 4. XML import (~8 test)

```python
# tests/test_import.py
def test_import_sales_xml()
def test_import_purchase_xml()
def test_import_creates_contact()
def test_import_creates_vat_rate()
def test_import_zip()
def test_import_with_namespace()
def test_import_with_signature_removal()
def test_import_sets_received_status()
```

### 5. Views (~10 test)

```python
# tests/test_views.py
def test_dashboard_loads()
def test_invoice_list()
def test_invoice_create()
def test_invoice_edit()
def test_invoice_delete_blocked_if_sdi()
def test_contact_list_search()
def test_settings_save()
def test_setup_wizard()
def test_login_required()
def test_fiscal_year_filter()
```

### 6. API/Webhook (~5 test)

```python
# tests/test_webhook.py
def test_webhook_supplier_invoice()
def test_webhook_customer_notification()
def test_webhook_unknown_event()
def test_webhook_invalid_json()
def test_openapi_client_send_mock()
```

### 7. CSV import (~3 test)

```python
# tests/test_csv_import.py
def test_import_fattura24_csv()
def test_import_csv_skip_existing()
def test_import_csv_update_existing()
```

### 8. Report (~5 test)

```python
# tests/test_report.py
def test_revenue_this_month()
def test_revenue_ytd()
def test_active_clients_count()
def test_top_clients()
def test_month_change_percent()
```

## File da creare

- `tests/conftest.py`
- `tests/factories.py`
- `tests/test_models.py`
- `tests/test_calculations.py`
- `tests/test_xml.py`
- `tests/test_import.py`
- `tests/test_views.py`
- `tests/test_webhook.py`
- `tests/test_csv_import.py`
- `tests/test_report.py`
- `tests/fixtures/sample_invoice.xml`
- `tests/fixtures/sample_purchase.xml`
- `tests/fixtures/sample_fattura24.csv`
- `pytest.ini` o sezione in `pyproject.toml`

## Configurazione pytest in pyproject.toml

```toml
[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "djafatt.settings.dev"
python_files = ["tests/test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short"
```

## Criteri di accettazione

- [ ] `pytest` esegue 50+ test
- [ ] 0 failures
- [ ] Factories creano oggetti validi
- [ ] Test XML confrontano output con fixture
- [ ] Test views verificano status code e contenuto
- [ ] Test webhook con mock HTTP
- [ ] Coverage > 85% sulle app djafatt
- [ ] Suite separata per unit, integration e security con marker pytest
