"""Report views: filtered invoice list with CSV and PDF export."""
import csv
from datetime import date, datetime

import weasyprint
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Sum
from django.http import HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string

from constance import config

from .models import Invoice


def _parse_filters(request):
    """Extract and validate filter params from GET query string."""
    today = date.today()
    fiscal_year = request.session.get("fiscal_year", today.year)

    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")
    invoice_type = request.GET.get("type", "")
    contact_id = request.GET.get("contact", "")
    payment_status = request.GET.get("payment_status", "")
    cash_basis = request.GET.get("cash_basis", "") == "1"

    try:
        date_from = datetime.strptime(date_from, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        date_from = date(fiscal_year, 1, 1)

    try:
        date_to = datetime.strptime(date_to, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        date_to = date(fiscal_year, 12, 31)

    return {
        "date_from": date_from,
        "date_to": date_to,
        "invoice_type": invoice_type,
        "contact_id": contact_id,
        "payment_status": payment_status,
        "cash_basis": cash_basis,
    }


def _get_filtered_invoices(filters):
    """Return filtered queryset based on parsed filters."""
    from django.db.models import BooleanField, Case, Q as _Q, Sum, Value, When

    qs = Invoice.all_types.select_related("contact", "sequence").annotate(
        _paid_total=Sum("payment_dues__amount", filter=_Q(payment_dues__paid=True)),
    )

    if filters.get("cash_basis"):
        date_in_range = _Q(date__gte=filters["date_from"], date__lte=filters["date_to"])
        paid_in_range = _Q(paid_at__gte=filters["date_from"], paid_at__lte=filters["date_to"])
        # Cash basis: invoices issued in the period OR paid in the period
        qs = qs.filter(date_in_range | paid_in_range)
        # Flag: paid in period but issued outside it
        qs = qs.annotate(
            paid_in_period_only=Case(
                When(paid_in_range & ~date_in_range, then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            ),
        )
    else:
        qs = qs.filter(
            date__gte=filters["date_from"],
            date__lte=filters["date_to"],
        )

    if filters["invoice_type"]:
        qs = qs.filter(type=filters["invoice_type"])
    if filters["contact_id"]:
        qs = qs.filter(contact_id=filters["contact_id"])
    if filters["payment_status"] == "paid":
        qs = qs.filter(paid_at__isnull=False)
    elif filters["payment_status"] == "unpaid":
        qs = qs.filter(paid_at__isnull=True, _paid_total__isnull=True)
    elif filters["payment_status"] == "partial":
        qs = qs.filter(paid_at__isnull=True, _paid_total__gt=0)
    return qs.order_by("date", "number")


TYPE_LABELS = {
    "sales": "Vendita",
    "purchase": "Acquisto",
    "self_invoice": "Autofattura",
}

PAYMENT_LABELS = {
    "MP01": "Contanti",
    "MP02": "Assegno",
    "MP05": "Bonifico",
    "MP08": "Carta",
    "MP12": "RIBA",
    "MP14": "Quietanza erario",
    "MP15": "Giroconto",
    "MP16": "Domiciliaz. bancaria",
    "MP17": "Domiciliaz. postale",
    "MP18": "Bollettino postale",
    "MP19": "SEPA DD",
    "MP20": "SEPA DD CORE",
    "MP21": "SEPA DD B2B",
    "MP22": "Trattenuta su somme",
    "MP23": "PagoPA",
}


def _payment_label(code):
    """MP code → readable label."""
    if not code:
        return ""
    desc = PAYMENT_LABELS.get(code)
    return f"{code} ({desc})" if desc else code


@login_required
@permission_required("invoices.view_invoice", raise_exception=True)
def report_index(request):
    """Report page with filters and summary table."""
    from apps.contacts.models import Contact

    filters = _parse_filters(request)
    invoices = _get_filtered_invoices(filters)

    agg = invoices.aggregate(
        total_net=Sum("total_net"),
        total_vat=Sum("total_vat"),
        total_gross=Sum("total_gross"),
    )
    summary = {
        "count": invoices.count(),
        "total_net": agg["total_net"] or 0,
        "total_vat": agg["total_vat"] or 0,
        "total_gross": agg["total_gross"] or 0,
    }

    if filters["cash_basis"]:
        d_from, d_to = filters["date_from"], filters["date_to"]
        paid_range = dict(paid_at__gte=d_from, paid_at__lte=d_to)
        date_range = dict(date__gte=d_from, date__lte=d_to)

        def _cash_agg(qs):
            a = qs.aggregate(t=Sum("total_gross"))
            return {"count": qs.count(), "total": a["t"] or 0}

        summary["sales_paid"] = _cash_agg(
            invoices.filter(type="sales", **paid_range))
        summary["sales_unpaid"] = _cash_agg(
            invoices.filter(type="sales", paid_at__isnull=True, **date_range))
        summary["purchase_paid"] = _cash_agg(
            invoices.filter(type="purchase", **paid_range))
        summary["purchase_unpaid"] = _cash_agg(
            invoices.filter(type="purchase", paid_at__isnull=True, **date_range))

    contacts = Contact.objects.order_by("name")

    return render(request, "reports/index.html", {
        "invoices": invoices,
        "filters": filters,
        "summary": summary,
        "contacts": contacts,
        "type_choices": [
            ("", "Tutti"),
            ("sales", "Vendita"),
            ("purchase", "Acquisto"),
            ("self_invoice", "Autofattura"),
        ],
        "payment_status_choices": [
            ("", "Tutti"),
            ("paid", "Pagata"),
            ("partial", "Parzialmente pagata"),
            ("unpaid", "Non pagata"),
        ],
        "type_labels": TYPE_LABELS,
    })


@login_required
@permission_required("invoices.view_invoice", raise_exception=True)
def report_csv(request):
    """Export filtered invoices as CSV."""
    filters = _parse_filters(request)
    invoices = _get_filtered_invoices(filters)

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    filename = f"report_{filters['date_from']}_{filters['date_to']}.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    # BOM for Excel UTF-8
    response.write("\ufeff")

    writer = csv.writer(response, delimiter=";")
    PAYMENT_STATUS_LABELS = {"paid": "Pagata", "partial": "Parziale", "unpaid": "Non pagata"}
    writer.writerow([
        "Numero", "Data", "Tipo", "Tipo Documento",
        "Contatto", "P.IVA Contatto", "C.F. Contatto",
        "Imponibile", "IVA", "Totale",
        "Metodo Pagamento", "Stato",
        "Data Invio SDI", "Incasso", "Data Incasso", "Metodo Incasso",
    ])
    for inv in invoices:
        writer.writerow([
            inv.number,
            inv.date.strftime("%d/%m/%Y"),
            TYPE_LABELS.get(inv.type, inv.type),
            inv.document_type,
            inv.contact.name,
            inv.contact.vat_number,
            inv.contact.tax_code,
            _cents_to_str(inv.total_net),
            _cents_to_str(inv.total_vat),
            _cents_to_str(inv.total_gross),
            _payment_label(inv.payment_method),
            inv.status,
            inv.sdi_sent_at.strftime("%d/%m/%Y") if inv.sdi_sent_at else "",
            PAYMENT_STATUS_LABELS.get(inv.payment_status, ""),
            inv.paid_at.strftime("%d/%m/%Y") if inv.paid_at else "",
            _payment_label(inv.paid_via),
        ])

    return response


@login_required
@permission_required("invoices.view_invoice", raise_exception=True)
def report_pdf(request):
    """Export filtered invoices as PDF summary report."""
    filters = _parse_filters(request)
    invoices = _get_filtered_invoices(filters)

    agg = invoices.aggregate(
        total_net=Sum("total_net"),
        total_vat=Sum("total_vat"),
        total_gross=Sum("total_gross"),
    )
    summary = {
        "count": invoices.count(),
        "total_net": agg["total_net"] or 0,
        "total_vat": agg["total_vat"] or 0,
        "total_gross": agg["total_gross"] or 0,
    }

    if filters["cash_basis"]:
        d_from, d_to = filters["date_from"], filters["date_to"]
        paid_range = dict(paid_at__gte=d_from, paid_at__lte=d_to)
        date_range = dict(date__gte=d_from, date__lte=d_to)

        def _cash_agg(qs):
            a = qs.aggregate(t=Sum("total_gross"))
            return {"count": qs.count(), "total": a["t"] or 0}

        summary["sales_paid"] = _cash_agg(
            invoices.filter(type="sales", **paid_range))
        summary["sales_unpaid"] = _cash_agg(
            invoices.filter(type="sales", paid_at__isnull=True, **date_range))
        summary["purchase_paid"] = _cash_agg(
            invoices.filter(type="purchase", **paid_range))
        summary["purchase_unpaid"] = _cash_agg(
            invoices.filter(type="purchase", paid_at__isnull=True, **date_range))

    company = {
        "name": config.COMPANY_NAME,
        "vat_number": config.COMPANY_VAT_NUMBER,
        "tax_code": config.COMPANY_TAX_CODE,
    }

    html = render_to_string("reports/pdf_report.html", {
        "invoices": invoices,
        "filters": filters,
        "summary": summary,
        "company": company,
        "type_labels": TYPE_LABELS,
        "generated_at": datetime.now(),
    })

    pdf = weasyprint.HTML(string=html).write_pdf()

    response = HttpResponse(pdf, content_type="application/pdf")
    filename = f"report_{filters['date_from']}_{filters['date_to']}.pdf"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def _cents_to_str(value):
    """Convert cents to decimal string for CSV: 10050 → '100,50'."""
    value = value or 0
    sign = "-" if value < 0 else ""
    euros = abs(value) // 100
    cents = abs(value) % 100
    return f"{sign}{euros},{cents:02d}"


@login_required
@permission_required("invoices.change_invoice", raise_exception=True)
def payment_form(request, pk):
    """HTMX GET: return inline payment form for an invoice row."""
    inv = get_object_or_404(Invoice.all_types, pk=pk)
    paid_dues = inv.payment_dues.filter(paid=True)
    paid_total = sum(d.amount for d in paid_dues)
    remaining = max(inv.total_gross - paid_total, 0)
    html = render_to_string("invoices/partials/_quick_payment_form.html", {
        "inv": inv,
        "remaining_cents": remaining,
        "remaining_display": f"{remaining / 100:.2f}",
        "payment_choices": PAYMENT_LABELS,
        "today": date.today().isoformat(),
    }, request=request)
    return HttpResponse(html)


@login_required
@permission_required("invoices.change_invoice", raise_exception=True)
def record_payment(request, pk):
    """HTMX POST: create a PaymentDue and sync invoice paid status."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    from decimal import Decimal, InvalidOperation

    from .models import PaymentDue

    inv = get_object_or_404(Invoice.all_types, pk=pk)
    try:
        amount_eur = Decimal(request.POST.get("amount", "0") or "0")
    except InvalidOperation:
        amount_eur = Decimal("0")
    amount_cents = int(amount_eur * 100)
    if amount_cents <= 0:
        messages.error(request, "Importo non valido.")
        return redirect(request.META.get("HTTP_REFERER", "/"))

    payment_date_str = request.POST.get("payment_date", "")
    try:
        from datetime import datetime as _dt
        payment_date = _dt.strptime(payment_date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        payment_date = date.today()

    payment_method = request.POST.get("payment_method", "").strip()
    if not payment_method and inv.payment_method:
        payment_method = inv.payment_method

    PaymentDue.objects.create(
        invoice=inv,
        due_date=payment_date,
        amount=amount_cents,
        payment_method=payment_method,
        paid=True,
        paid_at=payment_date,
    )
    inv.sync_paid_status()
    messages.success(request, f"Incasso €{amount_eur:.2f} registrato per {inv.number}.")
    return redirect(request.META.get("HTTP_REFERER", "/"))


@login_required
@permission_required("invoices.change_invoice", raise_exception=True)
def mark_paid(request, pk):
    """Legacy: mark invoice as fully paid in one shot (POST)."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    from .models import PaymentDue

    inv = get_object_or_404(Invoice.all_types, pk=pk)
    paid_total = sum(d.amount for d in inv.payment_dues.filter(paid=True))
    remaining = inv.total_gross - paid_total
    if remaining > 0:
        PaymentDue.objects.create(
            invoice=inv,
            due_date=date.today(),
            amount=remaining,
            payment_method=inv.payment_method or "",
            paid=True,
            paid_at=date.today(),
        )
    inv.sync_paid_status()
    messages.success(request, f"Fattura {inv.number} segnata come pagata.")
    return redirect(request.META.get("HTTP_REFERER", "/"))


@login_required
@permission_required("invoices.change_invoice", raise_exception=True)
def mark_unpaid(request, pk):
    """Remove all payment dues and clear paid status (POST)."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    inv = get_object_or_404(Invoice.all_types, pk=pk)
    inv.payment_dues.all().delete()
    inv.paid_at = None
    inv.paid_via = ""
    inv.save(update_fields=["paid_at", "paid_via"])
    messages.success(request, f"Fattura {inv.number}: incassi rimossi.")
    return redirect(request.META.get("HTTP_REFERER", "/"))
