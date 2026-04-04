"""Shared pytest fixtures for djafatt test suite."""
from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.test import Client


@pytest.fixture
def auth_client(db):
    """Authenticated Django test client (superuser — bypasses all permissions)."""
    user = User.objects.create_superuser("test@test.com", password="testpass123")
    client = Client()
    client.login(username="test@test.com", password="testpass123")
    client.user = user
    return client


@pytest.fixture
def user(db):
    """Test user."""
    return User.objects.create_user("test@test.com", password="testpass123")


@pytest.fixture
def company_settings():
    """Setup Constance with test company data."""
    from constance import config

    config.COMPANY_NAME = "Test SRL"
    config.COMPANY_VAT_NUMBER = "01234567890"
    config.COMPANY_TAX_CODE = "01234567890"
    config.COMPANY_ADDRESS = "Via Test 1"
    config.COMPANY_CITY = "Roma"
    config.COMPANY_POSTAL_CODE = "00100"
    config.COMPANY_PROVINCE = "RM"
    config.COMPANY_FISCAL_REGIME = "RF01"
    config.COMPANY_PEC = "test@pec.it"
    config.SETUP_COMPLETED = True


@pytest.fixture
def italian_contact(db):
    """Italian customer contact."""
    from apps.contacts.models import Contact

    return Contact.objects.create(
        name="Cliente Italiano SRL",
        vat_number="IT12345678901",
        tax_code="12345678901",
        address="Via Roma 1",
        city="Milano",
        postal_code="20100",
        province="MI",
        country_code="IT",
        sdi_code="ABC1234",
        is_customer=True,
    )


@pytest.fixture
def foreign_contact(db):
    """Non-EU foreign contact."""
    from apps.contacts.models import Contact

    return Contact.objects.create(
        name="US Corp Inc",
        vat_number="US123456789",
        address="123 Main St",
        city="New York",
        postal_code="10001",
        province="NY",
        country_code="US",
        is_customer=True,
    )


@pytest.fixture
def eu_contact(db):
    """EU (non-Italian) contact."""
    from apps.contacts.models import Contact

    return Contact.objects.create(
        name="Deutsche GmbH",
        vat_number="DE123456789",
        address="Berliner Str. 1",
        city="Berlin",
        postal_code="10115",
        country_code="DE",
        is_customer=True,
    )


@pytest.fixture
def vat_rate_22(db):
    """Standard 22% VAT rate."""
    from apps.invoices.models import VatRate

    return VatRate.objects.create(name="IVA 22%", percent=Decimal("22.00"))


@pytest.fixture
def vat_rate_10(db):
    """Reduced 10% VAT rate."""
    from apps.invoices.models import VatRate

    return VatRate.objects.create(name="IVA 10%", percent=Decimal("10.00"))


@pytest.fixture
def vat_rate_exempt(db):
    """Exempt VAT rate with nature code."""
    from apps.invoices.models import VatRate

    return VatRate.objects.create(
        name="Esente art. 10", percent=Decimal("0.00"), nature="N1",
    )


@pytest.fixture
def vat_rate_system(db):
    """System VAT rate (not deletable)."""
    from apps.invoices.models import VatRate

    return VatRate.objects.create(
        name="IVA 22% (system)", percent=Decimal("22.00"), is_system=True,
    )


@pytest.fixture
def sequence_sales(db):
    """Sales invoice sequence."""
    from apps.invoices.models import Sequence

    return Sequence.objects.create(
        name="Fatture vendita", type="sales", pattern="{SEQ}/{ANNO}",
    )


@pytest.fixture
def sequence_purchase(db):
    """Purchase invoice sequence."""
    from apps.invoices.models import Sequence

    return Sequence.objects.create(
        name="Fatture acquisto", type="purchase", pattern="{SEQ}/{ANNO}",
    )


@pytest.fixture
def sequence_system(db):
    """System sequence (not deletable)."""
    from apps.invoices.models import Sequence

    return Sequence.objects.create(
        name="System seq", type="sales", pattern="{SEQ}/{ANNO}", is_system=True,
    )


@pytest.fixture
def invoice(db, italian_contact, sequence_sales):
    """Basic sales invoice."""
    from apps.invoices.models import Invoice

    return Invoice.all_types.create(
        type="sales",
        number="0001/2026",
        sequential_number=1,
        date=date(2026, 1, 15),
        contact=italian_contact,
        sequence=sequence_sales,
        document_type="TD01",
    )


@pytest.fixture
def purchase_invoice(db, italian_contact, sequence_purchase):
    """Purchase invoice."""
    from apps.invoices.models import PurchaseInvoice

    return PurchaseInvoice.objects.create(
        number="0001/2026",
        sequential_number=1,
        date=date(2026, 1, 15),
        contact=italian_contact,
        sequence=sequence_purchase,
    )


@pytest.fixture
def invoice_line(db, invoice, vat_rate_22):
    """Single invoice line: €100 + 22% VAT."""
    from apps.invoices.models import InvoiceLine

    return InvoiceLine.objects.create(
        invoice=invoice,
        description="Test service",
        quantity=Decimal("1.00"),
        unit_price=10000,  # €100.00
        vat_rate=vat_rate_22,
        total=10000,
    )


@pytest.fixture
def product(db, vat_rate_22):
    """Test product."""
    from apps.products.models import Product

    return Product.objects.create(
        name="Consulting service",
        description="Hourly consulting",
        price=10000,  # €100.00
        unit="ore",
        vat_rate=vat_rate_22,
    )
