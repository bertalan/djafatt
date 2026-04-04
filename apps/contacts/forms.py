"""Forms for contacts app."""
from django import forms

from apps.invoices.forms import PAYMENT_METHOD_CHOICES, PAYMENT_TERMS_CHOICES

from .models import Contact


class ContactForm(forms.ModelForm):
    default_payment_method = forms.ChoiceField(
        choices=PAYMENT_METHOD_CHOICES, required=False,
        widget=forms.Select(attrs={"class": "select select-bordered w-full"}),
    )
    default_payment_terms = forms.ChoiceField(
        choices=PAYMENT_TERMS_CHOICES, required=False,
        widget=forms.Select(attrs={"class": "select select-bordered w-full"}),
    )

    class Meta:
        model = Contact
        fields = [
            "name", "vat_number", "tax_code",
            "address", "city", "postal_code", "province", "country_code",
            "sdi_code", "pec", "email", "phone", "mobile",
            "is_customer", "is_supplier",
            "default_payment_method", "default_payment_terms",
            "default_bank_name", "default_bank_iban",
            "notes",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "input input-bordered w-full"}),
            "vat_number": forms.TextInput(attrs={"class": "input input-bordered w-full", "placeholder": "IT01234567890"}),
            "tax_code": forms.TextInput(attrs={"class": "input input-bordered w-full"}),
            "address": forms.TextInput(attrs={"class": "input input-bordered w-full"}),
            "city": forms.TextInput(attrs={"class": "input input-bordered w-full"}),
            "postal_code": forms.TextInput(attrs={"class": "input input-bordered w-full"}),
            "province": forms.TextInput(attrs={"class": "input input-bordered w-full", "maxlength": 2}),
            "country_code": forms.TextInput(attrs={"class": "input input-bordered w-full", "maxlength": 2}),
            "sdi_code": forms.TextInput(attrs={"class": "input input-bordered w-full", "maxlength": 7, "placeholder": "0000000"}),
            "pec": forms.EmailInput(attrs={"class": "input input-bordered w-full"}),
            "email": forms.EmailInput(attrs={"class": "input input-bordered w-full"}),
            "phone": forms.TextInput(attrs={"class": "input input-bordered w-full"}),
            "mobile": forms.TextInput(attrs={"class": "input input-bordered w-full"}),
            "notes": forms.Textarea(attrs={"class": "textarea textarea-bordered w-full", "rows": 3}),
            "is_customer": forms.CheckboxInput(attrs={"class": "checkbox"}),
            "is_supplier": forms.CheckboxInput(attrs={"class": "checkbox"}),
            "default_bank_name": forms.TextInput(attrs={"class": "input input-bordered w-full"}),
            "default_bank_iban": forms.TextInput(attrs={"class": "input input-bordered w-full", "maxlength": 34}),
        }
