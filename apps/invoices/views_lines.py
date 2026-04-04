"""HTMX views for invoice line management (T12)."""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string

from apps.products.models import Product

from .models import VatRate
from .services.calculations import TotalsCalculationService


@login_required
@permission_required("invoices.add_invoiceline", raise_exception=True)
def add_invoice_line(request):
    """Return HTML partial for a new empty line row."""
    index = int(request.POST.get("next_index", 0))
    vat_rates = VatRate.objects.all()
    products = Product.objects.all()
    html = render_to_string("invoices/partials/_line_row.html", {
        "index": index,
        "vat_rates": vat_rates,
        "products": products,
    }, request=request)
    return HttpResponse(html)


@login_required
@permission_required("invoices.delete_invoiceline", raise_exception=True)
def remove_invoice_line(request, index):
    """Remove a line row — returns empty response to clear the DOM element."""
    return HttpResponse("")


@dataclass
class _PreviewLine:
    """Lightweight stand-in for InvoiceLine during preview calculations."""
    total: int = 0
    vat_rate: VatRate | None = None


@login_required
@permission_required("invoices.view_invoiceline", raise_exception=True)
def calculate_totals_partial(request):
    """Parse all line data from POST and return updated totals partial."""
    lines = []
    i = 0
    while True:
        desc_key = f"lines-{i}-description"
        if desc_key not in request.POST:
            break
        try:
            qty = Decimal(request.POST.get(f"lines-{i}-quantity", "0") or "0")
            price_eur = Decimal(request.POST.get(f"lines-{i}-unit_price_display", "0") or "0")
        except (InvalidOperation, ValueError):
            qty = Decimal("0")
            price_eur = Decimal("0")
        unit_price_cents = round(price_eur * 100)
        total = round(unit_price_cents * qty)
        vat_rate_id = request.POST.get(f"lines-{i}-vat_rate") or request.POST.get(f"lines-{i}-vat_rate_id")
        vat_rate = None
        if vat_rate_id:
            try:
                vat_rate = VatRate.objects.get(pk=int(vat_rate_id))
            except (VatRate.DoesNotExist, ValueError):
                pass
        lines.append(_PreviewLine(total=total, vat_rate=vat_rate))
        i += 1

    @dataclass
    class _FakeInvoice:
        withholding_tax_enabled: bool = False
        withholding_tax_percent: Decimal = Decimal("0")
        split_payment: bool = False
        stamp_duty_applied: bool = False
        type: str = "sales"

    fake_invoice = _FakeInvoice(
        withholding_tax_enabled=request.POST.get("withholding_tax_enabled") == "on",
        withholding_tax_percent=Decimal(request.POST.get("withholding_tax_percent", "0") or "0"),
        split_payment=request.POST.get("split_payment") == "on",
        stamp_duty_applied=request.POST.get("stamp_duty_applied") == "on",
        type=request.POST.get("invoice_type", "sales"),
    )
    result = TotalsCalculationService.compute_preview(lines, fake_invoice)

    html = render_to_string("invoices/partials/_totals.html", {
        "total_net": result.total_net,
        "total_vat": result.total_vat,
        "total_gross": result.total_gross,
        "withholding_amount": result.withholding_tax_amount,
        "stamp_duty_applied": result.stamp_duty_applied,
        "stamp_duty_amount": result.stamp_duty_amount,
    }, request=request)
    return HttpResponse(html)


@login_required
@permission_required("invoices.add_invoiceline", raise_exception=True)
def product_autofill(request, product_id):
    """Return JSON with product data to auto-fill line fields."""
    import json

    product = get_object_or_404(Product, pk=product_id)
    data = {
        "description": product.name,
        "unit_price_display": str(Decimal(product.price) / 100),
        "unit_of_measure": product.unit,
        "vat_rate_id": product.vat_rate_id or "",
    }
    return HttpResponse(json.dumps(data), content_type="application/json")


@login_required
@permission_required("invoices.view_invoice", raise_exception=True)
def contact_payment_defaults(request, contact_id):
    """Return contact payment defaults as HX-Trigger JSON."""
    import json

    from constance import config

    from apps.contacts.models import Contact

    contact = get_object_or_404(Contact, pk=contact_id)
    data = {
        "payment_method": contact.default_payment_method or config.DEFAULT_PAYMENT_METHOD,
        "payment_terms": contact.default_payment_terms or config.DEFAULT_PAYMENT_TERMS,
        "bank_name": contact.default_bank_name or config.COMPANY_BANK_NAME,
        "bank_iban": contact.default_bank_iban or config.COMPANY_BANK_IBAN,
    }
    response = HttpResponse("")
    response["HX-Trigger"] = json.dumps({"contactPaymentFill": data})
    return response


@login_required
@permission_required("invoices.add_invoice", raise_exception=True)
def add_payment_due(request):
    """Return HTML partial for a new payment due row, copying last row values."""
    index = int(request.POST.get("next_index", 0))
    html = render_to_string("invoices/partials/_payment_due_row.html", {
        "index": index,
        "last_due_date": request.POST.get("last_due_date", ""),
        "last_amount": request.POST.get("last_amount", ""),
        "last_method": request.POST.get("last_method", ""),
    }, request=request)
    return HttpResponse(html)


@login_required
@permission_required("invoices.change_invoice", raise_exception=True)
def remove_payment_due(request, index):
    """Remove a payment due row — returns empty response."""
    return HttpResponse("")
