"""Views for sales invoice CRUD."""
from datetime import date

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.common.mixins import GroupPermissionMixin

from .forms import InvoiceForm, InvoiceLineFormSet, PaymentDueFormSet
from .models import Invoice, SdiStatus


STATUS_BADGES = {
    "draft": "badge-warning",
    "generated": "badge-info",
    "sent": "badge-success",
    "received": "badge-accent",
}


class InvoiceListView(LoginRequiredMixin, GroupPermissionMixin, ListView):
    permission_required = "invoices.view_invoice"
    model = Invoice
    template_name = "invoices/index.html"
    context_object_name = "invoices"
    paginate_by = 20

    def get_queryset(self):
        from django.db.models import Q as _Q, Sum
        qs = super().get_queryset().select_related("contact", "sequence").annotate(
            _paid_total=Sum("payment_dues__amount", filter=_Q(payment_dues__paid=True)),
        )
        fiscal_year = self.request.session.get("fiscal_year", date.today().year)
        qs = qs.filter(date__year=fiscal_year)
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(number__icontains=q) | Q(contact__name__icontains=q))
        sort = self.request.GET.get("sort", "-date")
        if sort in ("date", "-date", "number", "-number", "total_gross", "-total_gross"):
            qs = qs.order_by(sort)
        return qs

    def get_template_names(self):
        if self.request.htmx:
            return ["invoices/partials/_table.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_badges"] = STATUS_BADGES
        return ctx


class InvoiceCreateView(LoginRequiredMixin, GroupPermissionMixin, CreateView):
    permission_required = "invoices.add_invoice"
    model = Invoice
    form_class = InvoiceForm
    template_name = "invoices/form.html"
    success_url = reverse_lazy("invoices-index")

    def dispatch(self, request, *args, **kwargs):
        fiscal_year = request.session.get("fiscal_year", date.today().year)
        if fiscal_year < date.today().year:
            messages.error(request, "Non puoi creare fatture in un anno fiscale passato.")
            return redirect("invoices-index")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx["formset"] = InvoiceLineFormSet(self.request.POST)
            ctx["dues_formset"] = PaymentDueFormSet(self.request.POST, prefix="dues")
        else:
            ctx["formset"] = InvoiceLineFormSet()
            ctx["dues_formset"] = PaymentDueFormSet(prefix="dues")
        return ctx

    @transaction.atomic
    def form_valid(self, form):
        ctx = self.get_context_data()
        formset = ctx["formset"]
        dues_formset = ctx["dues_formset"]
        if not formset.is_valid() or not dues_formset.is_valid():
            return self.form_invalid(form)
        invoice = form.save(commit=False)
        invoice.type = "sales"
        year = invoice.date.year
        invoice.sequential_number = invoice.sequence.get_next_number(year)
        invoice.number = invoice.sequence.pattern.replace(
            "{SEQ}", str(invoice.sequential_number).zfill(4)
        ).replace("{ANNO}", str(year))
        invoice.status = "draft"
        invoice.save()
        formset.instance = invoice
        formset.save()
        dues_formset.instance = invoice
        dues_formset.save()
        invoice.calculate_totals()
        messages.success(self.request, f"Fattura {invoice.number} creata.")
        return HttpResponseRedirect(self.success_url)


class InvoiceEditView(LoginRequiredMixin, GroupPermissionMixin, UpdateView):
    permission_required = "invoices.change_invoice"
    model = Invoice
    form_class = InvoiceForm
    template_name = "invoices/form.html"
    success_url = reverse_lazy("invoices-index")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["is_locked"] = not self.object.is_editable()
        inv = self.object
        ctx["total_net"] = inv.total_net
        ctx["total_vat"] = inv.total_vat
        ctx["total_gross"] = inv.total_gross
        ctx["withholding_amount"] = inv.withholding_tax_amount
        ctx["stamp_duty_applied"] = inv.stamp_duty_applied
        ctx["stamp_duty_amount"] = inv.stamp_duty_amount
        if self.request.POST:
            ctx["formset"] = InvoiceLineFormSet(self.request.POST, instance=self.object)
            ctx["dues_formset"] = PaymentDueFormSet(self.request.POST, instance=self.object, prefix="dues")
        else:
            ctx["formset"] = InvoiceLineFormSet(instance=self.object)
            ctx["dues_formset"] = PaymentDueFormSet(instance=self.object, prefix="dues")
        return ctx

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not self.object.is_editable():
            dues_formset = PaymentDueFormSet(
                request.POST, instance=self.object, prefix="dues",
            )
            if dues_formset.is_valid():
                dues_formset.save()
                self.object.sync_paid_status()
                messages.success(request, f"Pagamenti fattura {self.object.number} aggiornati.")
                return HttpResponseRedirect(self.get_success_url())
            ctx = self.get_context_data(form=self.get_form())
            return self.render_to_response(ctx)
        return super().post(request, *args, **kwargs)

    @transaction.atomic
    def form_valid(self, form):
        ctx = self.get_context_data()
        formset = ctx["formset"]
        dues_formset = ctx["dues_formset"]
        if not formset.is_valid() or not dues_formset.is_valid():
            return self.form_invalid(form)
        invoice = form.save()
        formset.save()
        dues_formset.save()
        invoice.calculate_totals()
        messages.success(self.request, f"Fattura {invoice.number} aggiornata.")
        return HttpResponseRedirect(self.success_url)


class InvoiceDeleteView(LoginRequiredMixin, GroupPermissionMixin, DeleteView):
    permission_required = "invoices.delete_invoice"
    model = Invoice
    success_url = reverse_lazy("invoices-index")
    http_method_names = ["post"]

    def form_valid(self, form):
        if not self.object.is_editable():
            messages.error(self.request, "Fattura bloccata, non eliminabile.")
            return redirect("invoices-index")
        messages.success(self.request, "Fattura eliminata.")
        return super().form_valid(form)


class InvoiceDuplicateView(LoginRequiredMixin, GroupPermissionMixin, View):
    permission_required = "invoices.add_invoice"
    """Duplicate a sales invoice: same content, new date + number."""

    @transaction.atomic
    def post(self, request, pk):
        source = get_object_or_404(Invoice, pk=pk, type="sales")
        new_invoice = Invoice(
            type="sales",
            date=date.today(),
            sequence=source.sequence,
            contact=source.contact,
            document_type=source.document_type,
            notes=source.notes,
            payment_method=source.payment_method,
            payment_terms=source.payment_terms,
            bank_name=source.bank_name,
            bank_iban=source.bank_iban,
            withholding_tax_enabled=source.withholding_tax_enabled,
            withholding_tax_percent=source.withholding_tax_percent,
            vat_payability=source.vat_payability,
            split_payment=source.split_payment,
            status="draft",
        )
        year = new_invoice.date.year
        new_invoice.sequential_number = source.sequence.get_next_number(year)
        new_invoice.number = source.sequence.pattern.replace(
            "{SEQ}", str(new_invoice.sequential_number).zfill(4)
        ).replace("{ANNO}", str(year))
        new_invoice.save()

        for line in source.lines.all():
            line.pk = None
            line.invoice = new_invoice
            line.save()

        for due in source.payment_dues.all():
            due.pk = None
            due.invoice = new_invoice
            due.paid = False
            due.paid_at = None
            due.save()

        new_invoice.calculate_totals()
        messages.success(request, f"Fattura duplicata: {new_invoice.number}")
        return HttpResponseRedirect(reverse("invoices-edit", args=[new_invoice.pk]))
