"""Forms for core app: setup wizard, settings, user management."""
from django import forms
from django.contrib.auth.models import Group, User

from apps.common.validators import validate_italian_tax_code, validate_italian_vat_number

FISCAL_REGIME_CHOICES = [
    ("RF01", "RF01 — Ordinario"),
    ("RF02", "RF02 — Contribuenti minimi"),
    ("RF04", "RF04 — Agricoltura"),
    ("RF05", "RF05 — Pesca"),
    ("RF06", "RF06 — Commercio ambulante"),
    ("RF07", "RF07 — Asta giudiziaria"),
    ("RF08", "RF08 — Vendita domicilio"),
    ("RF09", "RF09 — Rivendita beni usati"),
    ("RF10", "RF10 — Agenzie viaggi"),
    ("RF11", "RF11 — Agriturismo"),
    ("RF12", "RF12 — Vendite a domicilio"),
    ("RF13", "RF13 — Trasporto e deposito"),
    ("RF14", "RF14 — Entrate da restauro"),
    ("RF15", "RF15 — Editoria"),
    ("RF16", "RF16 — Intrattenimenti/giochi"),
    ("RF17", "RF17 — Agenzie di viaggio"),
    ("RF18", "RF18 — Manifatture"),
    ("RF19", "RF19 — Forfettario"),
]


class SetupForm(forms.Form):
    """Setup wizard form — company data + admin user."""

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": "input input-bordered w-full", "placeholder": "admin@example.com"}),
    )
    password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={"class": "input input-bordered w-full", "placeholder": "••••••••"}),
    )
    password_confirm = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={"class": "input input-bordered w-full", "placeholder": "••••••••"}),
    )
    company_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={"class": "input input-bordered w-full", "placeholder": "Ragione sociale"}),
    )
    vat_number = forms.CharField(
        max_length=16,
        widget=forms.TextInput(attrs={"class": "input input-bordered w-full", "placeholder": "01234567890"}),
    )
    tax_code = forms.CharField(
        max_length=16,
        widget=forms.TextInput(attrs={"class": "input input-bordered w-full", "placeholder": "Codice Fiscale"}),
    )
    address = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={"class": "input input-bordered w-full", "placeholder": "Via Roma 1"}),
    )
    city = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={"class": "input input-bordered w-full", "placeholder": "Roma"}),
    )
    postal_code = forms.CharField(
        max_length=10,
        widget=forms.TextInput(attrs={"class": "input input-bordered w-full", "placeholder": "00100"}),
    )
    province = forms.CharField(
        max_length=2,
        widget=forms.TextInput(attrs={"class": "input input-bordered w-full", "placeholder": "RM"}),
    )
    country_code = forms.CharField(
        max_length=2, initial="IT", required=False,
        widget=forms.TextInput(attrs={"class": "input input-bordered w-full"}),
    )
    fiscal_regime = forms.ChoiceField(
        choices=FISCAL_REGIME_CHOICES,
        widget=forms.Select(attrs={"class": "select select-bordered w-full"}),
    )
    pec = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={"class": "input input-bordered w-full", "placeholder": "azienda@pec.it"}),
    )
    sdi_code = forms.CharField(
        max_length=7, required=False,
        widget=forms.TextInput(attrs={"class": "input input-bordered w-full", "placeholder": "ABC1234"}),
    )

    def clean_vat_number(self):
        return validate_italian_vat_number(self.cleaned_data["vat_number"])

    def clean_tax_code(self):
        return validate_italian_tax_code(self.cleaned_data["tax_code"])

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password") != cleaned.get("password_confirm"):
            raise forms.ValidationError("Le password non corrispondono.")
        return cleaned


# ---------------------------------------------------------------------------
# Company Settings Form (Constance-backed)
# ---------------------------------------------------------------------------

from apps.invoices.forms import PAYMENT_METHOD_CHOICES, PAYMENT_TERMS_CHOICES

_W = "input input-bordered w-full"
_S = "select select-bordered w-full"


class CompanySettingsForm(forms.Form):
    """Company data settings — maps to Constance keys."""

    company_name = forms.CharField(
        label="Ragione sociale", max_length=200,
        widget=forms.TextInput(attrs={"class": _W}),
    )
    vat_number = forms.CharField(
        label="Partita IVA", max_length=16,
        widget=forms.TextInput(attrs={"class": _W}),
    )
    tax_code = forms.CharField(
        label="Codice Fiscale", max_length=16,
        widget=forms.TextInput(attrs={"class": _W}),
    )
    address = forms.CharField(
        label="Indirizzo", max_length=200,
        widget=forms.TextInput(attrs={"class": _W}),
    )
    city = forms.CharField(
        label="Città", max_length=100,
        widget=forms.TextInput(attrs={"class": _W}),
    )
    postal_code = forms.CharField(
        label="CAP", max_length=10,
        widget=forms.TextInput(attrs={"class": _W}),
    )
    province = forms.CharField(
        label="Provincia", max_length=2,
        widget=forms.TextInput(attrs={"class": _W, "maxlength": 2}),
    )
    country_code = forms.CharField(
        label="Paese (ISO)", max_length=2, initial="IT",
        widget=forms.TextInput(attrs={"class": _W, "maxlength": 2}),
    )
    fiscal_regime = forms.ChoiceField(
        label="Regime fiscale", choices=FISCAL_REGIME_CHOICES,
        widget=forms.Select(attrs={"class": _S}),
    )
    pec = forms.EmailField(
        label="PEC", required=False,
        widget=forms.EmailInput(attrs={"class": _W}),
    )
    sdi_code = forms.CharField(
        label="Codice SDI", max_length=7, required=False,
        widget=forms.TextInput(attrs={"class": _W, "maxlength": 7}),
    )
    phone = forms.CharField(
        label="Telefono", max_length=30, required=False,
        widget=forms.TextInput(attrs={"class": _W}),
    )
    email = forms.EmailField(
        label="Email", required=False,
        widget=forms.EmailInput(attrs={"class": _W}),
    )
    bank_name = forms.CharField(
        label="Banca", max_length=100, required=False,
        widget=forms.TextInput(attrs={"class": _W}),
    )
    bank_iban = forms.CharField(
        label="IBAN", max_length=34, required=False,
        widget=forms.TextInput(attrs={"class": _W, "maxlength": 34}),
    )

    def clean_vat_number(self):
        return validate_italian_vat_number(self.cleaned_data["vat_number"])

    def clean_tax_code(self):
        return validate_italian_tax_code(self.cleaned_data["tax_code"])


class InvoicingSettingsForm(forms.Form):
    """Invoicing defaults — maps to Constance keys."""

    default_payment_method = forms.ChoiceField(
        label="Metodo pagamento default", choices=PAYMENT_METHOD_CHOICES, required=False,
        widget=forms.Select(attrs={"class": _S}),
    )
    default_payment_terms = forms.ChoiceField(
        label="Condizioni pagamento default", choices=PAYMENT_TERMS_CHOICES, required=False,
        widget=forms.Select(attrs={"class": _S}),
    )
    default_withholding_tax_percent = forms.DecimalField(
        label="% Ritenuta d'acconto default", required=False, min_value=0, max_value=100,
        widget=forms.NumberInput(attrs={"class": _W, "step": "0.01"}),
    )


# ---------------------------------------------------------------------------
# User Management Forms
# ---------------------------------------------------------------------------

class UserCreateForm(forms.Form):
    """Create a new user with group assignment."""

    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"class": _W}),
    )
    first_name = forms.CharField(
        label="Nome", max_length=150, required=False,
        widget=forms.TextInput(attrs={"class": _W}),
    )
    last_name = forms.CharField(
        label="Cognome", max_length=150, required=False,
        widget=forms.TextInput(attrs={"class": _W}),
    )
    group = forms.ModelChoiceField(
        label="Gruppo",
        queryset=Group.objects.all(),
        widget=forms.Select(attrs={"class": _S}),
    )
    password = forms.CharField(
        label="Password", min_length=8,
        widget=forms.PasswordInput(attrs={"class": _W}),
    )
    password_confirm = forms.CharField(
        label="Conferma password", min_length=8,
        widget=forms.PasswordInput(attrs={"class": _W}),
    )

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(username=email).exists():
            raise forms.ValidationError("Esiste già un utente con questa email.")
        return email

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password") != cleaned.get("password_confirm"):
            raise forms.ValidationError("Le password non corrispondono.")
        return cleaned


class UserEditForm(forms.Form):
    """Edit existing user — group + active status."""

    first_name = forms.CharField(
        label="Nome", max_length=150, required=False,
        widget=forms.TextInput(attrs={"class": _W}),
    )
    last_name = forms.CharField(
        label="Cognome", max_length=150, required=False,
        widget=forms.TextInput(attrs={"class": _W}),
    )
    group = forms.ModelChoiceField(
        label="Gruppo",
        queryset=Group.objects.all(),
        widget=forms.Select(attrs={"class": _S}),
    )
    is_active = forms.BooleanField(
        label="Attivo", required=False,
        widget=forms.CheckboxInput(attrs={"class": "checkbox"}),
    )
    new_password = forms.CharField(
        label="Nuova password (lascia vuoto per non cambiare)",
        min_length=8, required=False,
        widget=forms.PasswordInput(attrs={"class": _W, "placeholder": "••••••••"}),
    )
