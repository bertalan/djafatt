from django.db import models


class Product(models.Model):
    """Product or service catalog item. Price stored in cents."""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    price = models.IntegerField(default=0)  # cents (100 = €1.00)
    unit = models.CharField(max_length=10, blank=True, default="")
    vat_rate = models.ForeignKey(
        "invoices.VatRate", on_delete=models.PROTECT, null=True, blank=True,
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
