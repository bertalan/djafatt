"""Forms for products CRUD."""
from decimal import Decimal

from django import forms

from .models import Product


class ProductForm(forms.ModelForm):
    price_display = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        label="Prezzo (€)",
        min_value=Decimal("0"),
        widget=forms.NumberInput(attrs={"class": "input input-bordered w-full", "step": "0.01", "placeholder": "0,00"}),
    )

    class Meta:
        model = Product
        fields = ["name", "description", "unit", "vat_rate"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "input input-bordered w-full"}),
            "description": forms.Textarea(attrs={"class": "textarea textarea-bordered w-full", "rows": 3}),
            "unit": forms.TextInput(attrs={"class": "input input-bordered w-full", "placeholder": "PZ, NR, ore…"}),
            "vat_rate": forms.Select(attrs={"class": "select select-bordered w-full"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["price_display"].initial = Decimal(self.instance.price) / 100

    def save(self, commit=True):
        self.instance.price = int(self.cleaned_data["price_display"] * 100)
        return super().save(commit=commit)
