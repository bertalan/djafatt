"""Views for purchase invoice CRUD (T13)."""
from datetime import date

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.common.mixins import GroupPermissionMixin

from .forms import InvoiceForm, InvoiceLineFormSet, PaymentDueFormSet
from .models import PurchaseInvoice


class PurchaseInvoiceListView(LoginRequiredMixin, GroupPermissionMixin, ListView):
    permission_required = "invoices.view_invoice"
    model = PurchaseInvoice
    template_name = "purchase_invoices/index.html"
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
        return qs

    def get_template_names(self):
        if self.request.htmx:
            return ["purchase_invoices/partials/_table.html"]
        return [self.template_name]


class PurchaseInvoiceCreateView(LoginRequiredMixin, GroupPermissionMixin, CreateView):
    permission_required = "invoices.add_invoice"
    model = PurchaseInvoice
    form_class = InvoiceForm
    template_name = "purchase_invoices/form.html"
    success_url = reverse_lazy("purchase-invoices-index")

    def dispatch(self, request, *args, **kwargs):
        fiscal_year = request.session.get("fiscal_year", date.today().year)
        if fiscal_year < date.today().year:
            messages.error(request, "Non puoi creare fatture in un anno fiscale passato.")
            return redirect("purchase-invoices-index")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["invoice_type"] = "purchase"
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["invoice_type_label"] = "Acquisto"
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
        invoice.type = "purchase"
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
        messages.success(self.request, f"Fattura acquisto {invoice.number} creata.")
        return HttpResponseRedirect(self.success_url)


class PurchaseInvoiceEditView(LoginRequiredMixin, GroupPermissionMixin, UpdateView):
    permission_required = "invoices.change_invoice"
    model = PurchaseInvoice
    form_class = InvoiceForm
    template_name = "purchase_invoices/form.html"
    success_url = reverse_lazy("purchase-invoices-index")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["invoice_type"] = "purchase"
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["invoice_type_label"] = "Acquisto"
        ctx["is_locked"] = not self.object.is_sdi_editable() or self.object.status == "received"
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
        is_locked = not self.object.is_sdi_editable() or self.object.status == "received"
        if is_locked:
            dues_formset = PaymentDueFormSet(
                request.POST, instance=self.object, prefix="dues",
            )
            if dues_formset.is_valid():
                dues_formset.save()
                self.object.sync_paid_status()
                messages.success(request, f"Pagamenti fattura acquisto {self.object.number} aggiornati.")
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
        messages.success(self.request, f"Fattura acquisto {invoice.number} aggiornata.")
        return HttpResponseRedirect(self.success_url)


class PurchaseInvoiceDeleteView(LoginRequiredMixin, GroupPermissionMixin, DeleteView):
    permission_required = "invoices.delete_invoice"
    model = PurchaseInvoice
    success_url = reverse_lazy("purchase-invoices-index")
    http_method_names = ["post"]

    def form_valid(self, form):
        messages.success(self.request, "Fattura acquisto eliminata.")
        return super().form_valid(form)


class PurchaseInvoiceDuplicateView(LoginRequiredMixin, GroupPermissionMixin, View):
    permission_required = "invoices.add_invoice"
    """Duplicate a purchase invoice: same content, new date + number."""

    @transaction.atomic
    def post(self, request, pk):
        source = get_object_or_404(PurchaseInvoice, pk=pk)
        new_invoice = PurchaseInvoice(
            type="purchase",
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
        messages.success(request, f"Fattura acquisto duplicata: {new_invoice.number}")
        return HttpResponseRedirect(reverse("purchase-invoices-edit", args=[new_invoice.pk]))
