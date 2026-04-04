"""Factory-boy factories for djafatt models.

TDD: These factories define the test data contract. Implementation must match.
"""
from datetime import date
from decimal import Decimal

import factory


class ContactFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "contacts.Contact"

    name = factory.Sequence(lambda n: f"Cliente {n}")
    vat_number = factory.Sequence(lambda n: f"IT{n:011d}")
    tax_code = factory.Sequence(lambda n: f"{n:011d}")
    address = "Via Test 1"
    city = "Roma"
    postal_code = "00100"
    province = "RM"
    country_code = "IT"
    is_customer = True


class VatRateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "invoices.VatRate"

    name = "IVA 22%"
    percent = Decimal("22.00")


class SequenceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "invoices.Sequence"

    name = "Test"
    type = "sales"
    pattern = "{SEQ}/{ANNO}"


class ProductFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "products.Product"

    name = factory.Sequence(lambda n: f"Product {n}")
    price = 10000  # €100.00
    unit = "nr"
    vat_rate = factory.SubFactory(VatRateFactory)


class InvoiceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "invoices.Invoice"

    contact = factory.SubFactory(ContactFactory)
    sequence = factory.SubFactory(SequenceFactory)
    date = factory.LazyFunction(date.today)
    number = factory.Sequence(lambda n: f"{n:04d}/2026")
    sequential_number = factory.Sequence(lambda n: n + 1)
    type = "sales"
    document_type = "TD01"

    class Params:
        with_withholding = factory.Trait(
            withholding_tax_enabled=True,
            withholding_tax_percent=Decimal("20.00"),
        )
        with_split_payment = factory.Trait(
            split_payment=True,
            vat_payability="S",
        )


class InvoiceLineFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "invoices.InvoiceLine"

    invoice = factory.SubFactory(InvoiceFactory)
    vat_rate = factory.SubFactory(VatRateFactory)
    description = "Test service"
    quantity = Decimal("1.00")
    unit_price = 10000  # €100.00
    total = 10000


class PurchaseInvoiceFactory(InvoiceFactory):
    class Meta:
        model = "invoices.PurchaseInvoice"

    type = "purchase"


class SelfInvoiceFactory(InvoiceFactory):
    class Meta:
        model = "invoices.SelfInvoice"

    type = "self_invoice"
    document_type = "TD17"
