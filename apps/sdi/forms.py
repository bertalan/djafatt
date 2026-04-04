"""Forms for SDI import."""
from django import forms

from apps.invoices.models import Sequence

ALLOWED_EXTENSIONS = (".xml", ".p7m", ".zip")

# Map import category → Sequence.SequenceType value(s)
# "electronic_invoice" auto-detects type from XML (sales or self_invoice)
CATEGORY_TO_SEQ_TYPES = {
    "purchase": [Sequence.SequenceType.PURCHASE],
    "electronic_invoice": [Sequence.SequenceType.SALES, Sequence.SequenceType.SELF_INVOICE],
    "self_invoice": [Sequence.SequenceType.SELF_INVOICE],
}


class ImportForm(forms.Form):
    category = forms.ChoiceField(
        choices=[
            ("purchase", "Fatture acquisto"),
            ("electronic_invoice", "Fatture vendita"),
            ("self_invoice", "Autofatture"),
        ],
        label="Categoria",
        widget=forms.Select(attrs={
            "class": "select select-bordered w-full",
            "hx-get": "/imports/sequences/",
            "hx-target": "#id_sequence_wrapper",
            "hx-trigger": "change",
        }),
    )
    sequence = forms.ModelChoiceField(
        queryset=Sequence.objects.none(),
        label="Sequenza",
        widget=forms.Select(attrs={"class": "select select-bordered w-full"}),
    )
    file = forms.FileField(
        label="File XML / P7M / ZIP",
        widget=forms.FileInput(attrs={"class": "file-input file-input-bordered w-full", "accept": ".xml,.p7m,.zip"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        category = self.data.get("category") if self.is_bound else None
        seq_types = CATEGORY_TO_SEQ_TYPES.get(category or "purchase", [])
        qs = Sequence.objects.filter(type__in=seq_types)
        self.fields["sequence"].queryset = qs
        if qs.count() == 1:
            self.initial.setdefault("sequence", qs.first().pk)

    def clean_file(self):
        f = self.cleaned_data["file"]
        name = f.name.lower()
        if not any(name.endswith(ext) for ext in ALLOWED_EXTENSIONS):
            raise forms.ValidationError("Formato non supportato. Usa .xml, .p7m o .zip")
        return f
