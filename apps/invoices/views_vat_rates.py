"""Views for VatRate CRUD."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.common.helpers import annotate_invoice_urls
from apps.common.mixins import GroupPermissionMixin

from .forms import VatRateForm
from .models import Invoice, VatRate


class VatRateListView(LoginRequiredMixin, GroupPermissionMixin, ListView):
    permission_required = "invoices.view_vatrate"
    model = VatRate
    template_name = "invoices/vat_rates/index.html"
    context_object_name = "vat_rates"


class VatRateCreateView(LoginRequiredMixin, GroupPermissionMixin, CreateView):
    permission_required = "invoices.add_vatrate"
    model = VatRate
    form_class = VatRateForm
    template_name = "invoices/vat_rates/form.html"
    success_url = reverse_lazy("vat-rates-index")

    def form_valid(self, form):
        messages.success(self.request, "Aliquota IVA creata.")
        return super().form_valid(form)


class VatRateEditView(LoginRequiredMixin, GroupPermissionMixin, UpdateView):
    permission_required = "invoices.change_vatrate"
    model = VatRate
    form_class = VatRateForm
    template_name = "invoices/vat_rates/form.html"
    success_url = reverse_lazy("vat-rates-index")

    def get_queryset(self):
        return VatRate.objects.filter(is_system=False)

    def form_valid(self, form):
        messages.success(self.request, "Aliquota IVA aggiornata.")
        return super().form_valid(form)


class VatRateDeleteView(LoginRequiredMixin, GroupPermissionMixin, DeleteView):
    permission_required = "invoices.delete_vatrate"
    model = VatRate
    template_name = "common/confirm_delete.html"
    success_url = reverse_lazy("vat-rates-index")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        invoices = list(
            Invoice.all_types
            .filter(lines__vat_rate=self.object)
            .distinct()
            .select_related("contact")
            .order_by("-date")
        )
        ctx.update({
            "object_label": "Aliquota IVA",
            "cancel_url": reverse("vat-rates-index"),
            "related_objects": annotate_invoice_urls(invoices),
            "related_label": "Fatture",
            "delete_all_url": reverse("vat-rates-delete-related", args=[self.object.pk]),
        })
        return ctx

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.is_system:
            messages.error(request, "Aliquota di sistema — non eliminabile.")
            return redirect("vat-rates-index")
        return self.render_to_response(self.get_context_data())

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.is_system:
            messages.error(request, "Aliquota di sistema — non eliminabile.")
            return redirect("vat-rates-index")
        if self.object.invoiceline_set.exists():
            messages.error(request, "Elimina prima le fatture collegate.")
            return self.render_to_response(self.get_context_data())
        self.object.delete()
        messages.success(request, "Aliquota IVA eliminata.")
        return redirect(self.success_url)


class VatRateDeleteRelatedView(LoginRequiredMixin, GroupPermissionMixin, View):
    """Delete all invoices that use this VatRate, then redirect back."""
    permission_required = "invoices.delete_vatrate"

    @transaction.atomic
    def post(self, request, pk):
        vat_rate = get_object_or_404(VatRate, pk=pk)
        invoices = Invoice.all_types.filter(lines__vat_rate=vat_rate).distinct()
        count = invoices.count()
        invoices.delete()
        messages.success(request, f"{count} fatture eliminate.")
        return redirect("vat-rates-delete", pk=pk)
