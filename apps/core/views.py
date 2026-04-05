from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.db.models import Count, Sum
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme


def health_check(request):
    """Public health check — no auth required."""
    try:
        connection.ensure_connection()
        return JsonResponse({"status": "ok"})
    except Exception as exc:
        return JsonResponse({"status": "error", "detail": str(exc)}, status=503)


@login_required
def dashboard(request):
    """Main dashboard view with stats for current fiscal year."""
    from apps.contacts.models import Contact
    from apps.invoices.models import Invoice

    fiscal_year = request.session.get("fiscal_year", date.today().year)
    invoices = Invoice.all_types.filter(date__year=fiscal_year)

    def _agg(qs):
        r = qs.aggregate(c=Count("id"), t=Sum("total_gross"))
        return {"count": r["c"], "total": r["t"] or 0}

    sales = _agg(invoices.filter(type="sales"))
    purchase = _agg(invoices.filter(type="purchase"))
    self_inv = _agg(invoices.filter(type="self_invoice"))

    stats = {
        "sales_count": sales["count"],
        "sales_total": sales["total"],
        "purchase_count": purchase["count"],
        "purchase_total": purchase["total"],
        "self_count": self_inv["count"],
        "self_total": self_inv["total"],
        "contacts_count": Contact.objects.count(),
    }

    # Cash-basis stats: invoices paid in the fiscal year (regardless of issue date)
    paid_in_year = Invoice.all_types.filter(paid_at__year=fiscal_year)
    cash_sales = _agg(paid_in_year.filter(type="sales"))
    cash_purchase = _agg(paid_in_year.filter(type="purchase"))
    stats["cash_sales_count"] = cash_sales["count"]
    stats["cash_sales_total"] = cash_sales["total"]
    stats["cash_purchase_count"] = cash_purchase["count"]
    stats["cash_purchase_total"] = cash_purchase["total"]

    # Unpaid / partially paid invoices
    unpaid_sales_qs = invoices.filter(type="sales", paid_at__isnull=True).select_related("contact").order_by("date")
    unpaid_purchase_qs = invoices.filter(type="purchase", paid_at__isnull=True).select_related("contact").order_by("date")
    unpaid_sales = _agg(unpaid_sales_qs)
    unpaid_purchase = _agg(unpaid_purchase_qs)
    stats["unpaid_sales_count"] = unpaid_sales["count"]
    stats["unpaid_sales_total"] = unpaid_sales["total"]
    stats["unpaid_purchase_count"] = unpaid_purchase["count"]
    stats["unpaid_purchase_total"] = unpaid_purchase["total"]

    return render(request, "core/dashboard.html", {
        "stats": stats,
        "fiscal_year": fiscal_year,
        "unpaid_sales": unpaid_sales_qs,
        "unpaid_purchases": unpaid_purchase_qs,
    })


@login_required
def set_fiscal_year(request):
    """Set fiscal year in session (HTMX POST). Only Amministratore/Contabile."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    if not (request.user.is_superuser or request.user.has_perm("core.manage_fiscal_year")):
        messages.error(request, "Non hai i permessi per cambiare anno fiscale.")
        fallback = request.META.get("HTTP_REFERER", "/")
        if not url_has_allowed_host_and_scheme(fallback, allowed_hosts={request.get_host()}):
            fallback = "/"
        if request.headers.get("HX-Request"):
            response = HttpResponse(status=204)
            response["HX-Redirect"] = fallback
            return response
        return redirect(fallback)
    try:
        year = int(request.POST.get("year", 0))
    except (ValueError, TypeError):
        return HttpResponseBadRequest("Anno non valido")
    current_year = date.today().year
    if year < 2020 or year > current_year + 1:
        return HttpResponseBadRequest("Anno fuori range")
    request.session["fiscal_year"] = year
    redirect_url = request.META.get("HTTP_REFERER", "/")
    if not url_has_allowed_host_and_scheme(redirect_url, allowed_hosts={request.get_host()}):
        redirect_url = "/"
    if request.headers.get("HX-Request"):
        response = HttpResponse(status=204)
        response["HX-Redirect"] = redirect_url
        return response
    return redirect(redirect_url)
