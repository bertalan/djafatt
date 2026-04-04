"""Forms for invoices app: VatRate, Sequence, Invoice, InvoiceLine."""
from decimal import Decimal

from django import forms

from .models import Invoice, InvoiceLine, PaymentDue, Sequence, VatRate

NATURE_CHOICES = [
    ("", "— Nessuna (imponibile) —"),
    ("N1", "N1 — Escluse ex art. 15"),
    ("N2", "N2 — Non soggette"),
    ("N2.1", "N2.1 — Non soggette art. 7"),
    ("N2.2", "N2.2 — Non soggette altri"),
    ("N3", "N3 — Non imponibili"),
    ("N3.1", "N3.1 — Non imponibili esportazioni"),
    ("N3.2", "N3.2 — Non imponibili cessioni intraUE"),
    ("N3.3", "N3.3 — Non imponibili verso San Marino"),
    ("N3.4", "N3.4 — Non imponibili operazioni assimilate"),
    ("N3.5", "N3.5 — Non imponibili dichiarazione d'intento"),
    ("N3.6", "N3.6 — Non imponibili altre operazioni"),
    ("N4", "N4 — Esenti"),
    ("N5", "N5 — Regime del margine / IVA non esposta"),
    ("N6", "N6 — Inversione contabile (reverse charge)"),
    ("N6.1", "N6.1 — Reverse charge cessione rottami"),
    ("N6.2", "N6.2 — Reverse charge cessione oro/argento"),
    ("N6.3", "N6.3 — Reverse charge subappalto edilizia"),
    ("N6.4", "N6.4 — Reverse charge cessione fabbricati"),
    ("N6.5", "N6.5 — Reverse charge cessione telefoni"),
    ("N6.6", "N6.6 — Reverse charge cessione prodotti elettronici"),
    ("N6.7", "N6.7 — Reverse charge prestazioni comparto edile"),
    ("N6.8", "N6.8 — Reverse charge operazioni settore energetico"),
    ("N6.9", "N6.9 — Reverse charge altri casi"),
    ("N7", "N7 — IVA assolta in altro stato UE"),
]


class VatRateForm(forms.ModelForm):
    nature = forms.ChoiceField(
        choices=NATURE_CHOICES, required=False,
        widget=forms.Select(attrs={"class": "select select-bordered w-full"}),
    )

    class Meta:
        model = VatRate
        fields = ["name", "percent", "description", "nature"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "input input-bordered w-full"}),
            "percent": forms.NumberInput(attrs={"class": "input input-bordered w-full", "min": 0, "max": 100, "step": "0.01"}),
            "description": forms.TextInput(attrs={"class": "input input-bordered w-full"}),
        }


class SequenceForm(forms.ModelForm):
    class Meta:
        model = Sequence
        fields = ["name", "type", "pattern"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "input input-bordered w-full"}),
            "type": forms.Select(attrs={"class": "select select-bordered w-full"}),
            "pattern": forms.TextInput(attrs={"class": "input input-bordered w-full", "placeholder": "{SEQ}/{ANNO}"}),
        }


DOCUMENT_TYPE_CHOICES = [
    ("TD01", "TD01 — Fattura"),
    ("TD02", "TD02 — Acconto/Anticipo su fattura"),
    ("TD03", "TD03 — Acconto/Anticipo su parcella"),
    ("TD04", "TD04 — Nota di Credito"),
    ("TD05", "TD05 — Nota di Debito"),
    ("TD06", "TD06 — Parcella"),
    ("TD24", "TD24 — Fattura differita"),
    ("TD25", "TD25 — Fattura differita DDT"),
]

PAYMENT_METHOD_CHOICES = [
    ("", "—"),
    ("MP01", "MP01 — Contanti"),
    ("MP02", "MP02 — Assegno"),
    ("MP05", "MP05 — Bonifico"),
    ("MP08", "MP08 — Carta di pagamento"),
    ("MP12", "MP12 — RIBA"),
    ("MP14", "MP14 — Quietanza erario"),
    ("MP15", "MP15 — Giroconto"),
    ("MP16", "MP16 — Domiciliazione bancaria"),
    ("MP17", "MP17 — Domiciliazione postale"),
    ("MP18", "MP18 — Bollettino postale"),
    ("MP19", "MP19 — SEPA DD"),
    ("MP20", "MP20 — SEPA DD CORE"),
    ("MP21", "MP21 — SEPA DD B2B"),
    ("MP22", "MP22 — Trattenuta su somme"),
    ("MP23", "MP23 — PagoPA"),
]

PAYMENT_TERMS_CHOICES = [
    ("", "—"),
    ("TP01", "TP01 — Pagamento a rate"),
    ("TP02", "TP02 — Pagamento completo"),
    ("TP03", "TP03 — Anticipo"),
]

VAT_PAYABILITY_CHOICES = [
    ("I", "I — Immediata"),
    ("D", "D — Differita"),
    ("S", "S — Scissione pagamenti"),
]


class InvoiceForm(forms.ModelForm):
    document_type = forms.ChoiceField(
        choices=DOCUMENT_TYPE_CHOICES,
        widget=forms.Select(attrs={"class": "select select-bordered w-full"}),
    )
    payment_method = forms.ChoiceField(
        choices=PAYMENT_METHOD_CHOICES, required=False,
        widget=forms.Select(attrs={"class": "select select-bordered w-full"}),
    )
    payment_terms = forms.ChoiceField(
        choices=PAYMENT_TERMS_CHOICES, required=False,
        widget=forms.Select(attrs={"class": "select select-bordered w-full"}),
    )
    vat_payability = forms.ChoiceField(
        choices=VAT_PAYABILITY_CHOICES,
        widget=forms.Select(attrs={"class": "select select-bordered w-full"}),
    )

    class Meta:
        model = Invoice
        fields = [
            "number", "sequence", "date", "contact", "document_type",
            "notes", "payment_method", "payment_terms",
            "bank_name", "bank_iban",
            "withholding_tax_enabled", "withholding_tax_percent",
            "vat_payability", "split_payment",
            "stamp_duty_applied",
        ]
        widgets = {
            "number": forms.TextInput(attrs={"class": "input input-bordered w-full"}),
            "sequence": forms.Select(attrs={"class": "select select-bordered w-full"}),
            "date": forms.DateInput(format="%Y-%m-%d", attrs={"class": "input input-bordered w-full", "type": "date"}),
            "contact": forms.Select(attrs={
                "class": "select select-bordered w-full",
                "data-contact-defaults-url": "/invoices/contact-defaults/{id}/",
            }),
            "notes": forms.Textarea(attrs={"class": "textarea textarea-bordered w-full", "rows": 3}),
            "bank_name": forms.TextInput(attrs={"class": "input input-bordered w-full"}),
            "bank_iban": forms.TextInput(attrs={"class": "input input-bordered w-full", "maxlength": 34}),
            "withholding_tax_enabled": forms.CheckboxInput(attrs={"class": "checkbox"}),
            "withholding_tax_percent": forms.NumberInput(attrs={"class": "input input-bordered w-full", "min": 0, "max": 100, "step": "0.01"}),
            "split_payment": forms.CheckboxInput(attrs={"class": "checkbox"}),
            "stamp_duty_applied": forms.CheckboxInput(attrs={
                "class": "checkbox",
                "hx-post": "/invoices/lines/totals/",
                "hx-trigger": "change",
                "hx-target": "#totals-sidebar",
                "hx-include": "closest form",
            }),
        }

    def __init__(self, *args, invoice_type="sales", **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Sequence
        seq_qs = Sequence.objects.filter(type=invoice_type)
        self.fields["sequence"].queryset = seq_qs
        # Auto-select if only one sequence exists for this type
        if not self.instance.pk and seq_qs.count() == 1:
            self.initial.setdefault("sequence", seq_qs.first().pk)
        self.fields["number"].required = False

        # Pre-fill payment defaults for new invoices (no pk yet)
        if not self.instance.pk:
            from constance import config
            defaults = {
                "payment_method": config.DEFAULT_PAYMENT_METHOD,
                "payment_terms": config.DEFAULT_PAYMENT_TERMS,
                "bank_name": config.COMPANY_BANK_NAME,
                "bank_iban": config.COMPANY_BANK_IBAN,
            }
            for field, value in defaults.items():
                if value and not self.initial.get(field):
                    self.initial[field] = value


class SelfInvoiceForm(InvoiceForm):
    SELF_INVOICE_DOC_TYPES = [
        ("TD17", "TD17 — Integrazione/autofattura acquisto servizi estero"),
        ("TD18", "TD18 — Integrazione acquisto beni intraUE"),
        ("TD19", "TD19 — Integrazione/autofattura acquisto beni ex art. 17 c.2"),
        ("TD28", "TD28 — Acquisti da San Marino con IVA"),
    ]

    document_type = forms.ChoiceField(
        choices=SELF_INVOICE_DOC_TYPES,
        widget=forms.Select(attrs={"class": "select select-bordered w-full"}),
    )

    class Meta(InvoiceForm.Meta):
        fields = InvoiceForm.Meta.fields + [
            "related_invoice_number", "related_invoice_date",
        ]
        widgets = {
            **InvoiceForm.Meta.widgets,
            "related_invoice_number": forms.TextInput(attrs={"class": "input input-bordered w-full"}),
            "related_invoice_date": forms.DateInput(format="%Y-%m-%d", attrs={"class": "input input-bordered w-full", "type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        kwargs["invoice_type"] = "self_invoice"
        super().__init__(*args, **kwargs)


class InvoiceLineForm(forms.ModelForm):
    unit_price_display = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        label="Prezzo unit. (€)",
        min_value=Decimal("0"),
        widget=forms.NumberInput(attrs={
            "class": "input input-bordered w-full input-sm",
            "step": "0.01",
            "placeholder": "0,00",
            "hx-post": "/invoices/lines/totals/",
            "hx-trigger": "input changed delay:300ms",
            "hx-target": "#totals-sidebar",
            "hx-include": "closest form",
        }),
    )

    class Meta:
        model = InvoiceLine
        fields = ["product", "description", "quantity", "unit_of_measure", "vat_rate"]
        widgets = {
            "product": forms.Select(attrs={
                "class": "select select-bordered w-full select-sm product-select",
                "data-product-fill-url": "/invoices/lines/product-fill/{id}/",
            }),
            "description": forms.TextInput(attrs={"class": "input input-bordered w-full input-sm"}),
            "quantity": forms.NumberInput(attrs={
                "class": "input input-bordered w-full input-sm",
                "step": "0.01",
                "min": "0",
                "hx-post": "/invoices/lines/totals/",
                "hx-trigger": "input changed delay:300ms",
                "hx-target": "#totals-sidebar",
                "hx-include": "closest form",
            }),
            "unit_of_measure": forms.TextInput(attrs={
                "class": "input input-bordered w-full input-sm",
                "list": "uom-options",
                "placeholder": "pz",
            }),
            "vat_rate": forms.Select(attrs={
                "class": "select select-bordered w-full select-sm",
                "hx-post": "/invoices/lines/totals/",
                "hx-trigger": "change",
                "hx-target": "#totals-sidebar",
                "hx-include": "closest form",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["unit_price_display"].initial = Decimal(self.instance.unit_price) / 100

    def clean(self):
        """Skip validation for new empty rows (no description, no product)."""
        cleaned = super().clean()
        # Only skip NEW rows (no pk) that are essentially empty
        if not self.instance.pk and not cleaned.get("description") and not cleaned.get("product"):
            self._errors.clear()
            cleaned["DELETE"] = True
        return cleaned

    def save(self, commit=True):
        self.instance.unit_price = round(self.cleaned_data["unit_price_display"] * 100)
        qty = self.cleaned_data["quantity"]
        self.instance.total = round(self.instance.unit_price * qty)
        return super().save(commit=commit)


InvoiceLineFormSet = forms.inlineformset_factory(
    Invoice,
    InvoiceLine,
    form=InvoiceLineForm,
    extra=1,
    can_delete=True,
)


class PaymentDueForm(forms.ModelForm):
    amount_display = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        label="Importo (€)",
        min_value=Decimal("0"),
        widget=forms.NumberInput(attrs={
            "class": "input input-bordered w-full input-sm",
            "step": "0.01",
            "placeholder": "0,00",
        }),
    )
    payment_method = forms.ChoiceField(
        choices=PAYMENT_METHOD_CHOICES, required=False,
        widget=forms.Select(attrs={"class": "select select-bordered w-full select-sm"}),
    )

    class Meta:
        model = PaymentDue
        fields = ["due_date", "payment_method", "paid", "paid_at"]
        widgets = {
            "due_date": forms.DateInput(format="%Y-%m-%d", attrs={
                "class": "input input-bordered w-full input-sm",
                "type": "date",
            }),
            "paid": forms.CheckboxInput(attrs={"class": "checkbox checkbox-sm"}),
            "paid_at": forms.DateInput(format="%Y-%m-%d", attrs={
                "class": "input input-bordered w-full input-sm",
                "type": "date",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["amount_display"].initial = Decimal(self.instance.amount) / 100

    def save(self, commit=True):
        self.instance.amount = int(self.cleaned_data["amount_display"] * 100)
        return super().save(commit=commit)


PaymentDueFormSet = forms.inlineformset_factory(
    Invoice,
    PaymentDue,
    form=PaymentDueForm,
    extra=0,
    can_delete=True,
)

SELF_INVOICE_DOC_CHOICES = [
    ("TD17", "TD17 — Integrazione/autofattura acquisto servizi dall'estero"),
    ("TD18", "TD18 — Integrazione acquisto beni intracomunitari"),
    ("TD19", "TD19 — Integrazione/autofattura acquisto beni art.17 c.2"),
    ("TD28", "TD28 — Acquisti da San Marino con IVA"),
]


class SelfInvoiceForm(InvoiceForm):
    document_type = forms.ChoiceField(
        choices=SELF_INVOICE_DOC_CHOICES,
        widget=forms.Select(attrs={"class": "select select-bordered w-full"}),
    )
    related_invoice_number = forms.CharField(
        max_length=50, required=False,
        widget=forms.TextInput(attrs={"class": "input input-bordered w-full", "placeholder": "Num. fattura fornitore"}),
    )
    related_invoice_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "input input-bordered w-full", "type": "date"}),
    )

    class Meta(InvoiceForm.Meta):
        fields = InvoiceForm.Meta.fields + ["related_invoice_number", "related_invoice_date"]

    def __init__(self, *args, **kwargs):
        kwargs["invoice_type"] = "self_invoice"
        super().__init__(*args, **kwargs)
