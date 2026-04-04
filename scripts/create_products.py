"""Create 3 products from invoice data."""
from apps.products.models import Product
from apps.invoices.models import VatRate

iva0 = VatRate.objects.filter(percent=0, nature="N2.2").first()
if not iva0:
    iva0 = VatRate.objects.filter(percent=0).first()
print(f"IVA rate: {iva0} (id={iva0.pk})")

products = [
    {
        "name": "Manutenzione server Sinelec",
        "defaults": {
            "description": "Project 3629: Manutenzione server presso Sinelec datacenters",
            "price": 20000,
            "unit": "ore",
            "vat_rate": iva0,
        },
    },
    {
        "name": "Manutenzione hosting",
        "defaults": {
            "description": "Manutenzione hosting annuale",
            "price": 0,
            "unit": "",
            "vat_rate": iva0,
        },
    },
    {
        "name": "Assistenza e manutenzione applicativo",
        "defaults": {
            "description": "Assistenza e manutenzione applicativo e server",
            "price": 8000,
            "unit": "ore",
            "vat_rate": iva0,
        },
    },
]

for data in products:
    p, created = Product.objects.get_or_create(name=data["name"], defaults=data["defaults"])
    status = "CREATED" if created else "EXISTS"
    print(f"  {status}: {p.name} - {p.price} cents, unit={p.unit!r}")
