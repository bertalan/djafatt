"""Views for XML import (T15)."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse
from django.shortcuts import redirect, render

from apps.common.exceptions import XmlImportError
from apps.invoices.models import Sequence

from .forms import CATEGORY_TO_SEQ_TYPES, ImportForm
from .services.xml_importer import InvoiceXmlImportService


@login_required
@permission_required("invoices.add_invoice", raise_exception=True)
def import_view(request):
    """Import page with upload form."""
    form = ImportForm()
    stats = None

    if request.method == "POST":
        form = ImportForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded = form.cleaned_data["file"]
            sequence_id = form.cleaned_data["sequence"].pk
            category = form.cleaned_data["category"]

            service = InvoiceXmlImportService()
            try:
                content = uploaded.read()
                if uploaded.name.lower().endswith(".zip"):
                    service.import_zip(content, sequence_id, category)
                else:
                    service.import_xml(content, sequence_id, category)

                stats = service.stats
                if stats.invoices_imported > 0:
                    messages.success(
                        request,
                        f"Importate {stats.invoices_imported} fatture"
                        + (f", {stats.contacts_created} contatti creati" if stats.contacts_created else "")
                        + ".",
                    )
                if stats.errors > 0:
                    messages.warning(request, f"{stats.errors} errori durante l'import.")

            except XmlImportError as exc:
                messages.error(request, f"Errore import: {exc}")
            except Exception:
                messages.error(request, "Errore imprevisto durante l'import.")

    return render(request, "imports/index.html", {"form": form, "stats": stats})


@login_required
@permission_required("invoices.add_invoice", raise_exception=True)
def sequence_options_view(request):
    """HTMX endpoint: return <select> options filtered by category."""
    category = request.GET.get("category", "purchase")
    seq_types = CATEGORY_TO_SEQ_TYPES.get(category, [])
    sequences = Sequence.objects.filter(type__in=seq_types) if seq_types else Sequence.objects.none()

    options = ['<option value="">---------</option>']
    for seq in sequences:
        options.append(f'<option value="{seq.pk}">{seq.name}</option>')

    html = (
        f'<select name="sequence" id="id_sequence" class="select select-bordered w-full">'
        f'{"".join(options)}</select>'
    )
    return HttpResponse(html)
