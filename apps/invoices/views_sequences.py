"""Views for Sequence CRUD."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.common.helpers import annotate_invoice_urls
from apps.common.mixins import GroupPermissionMixin

from .forms import SequenceForm
from .models import Invoice, Sequence


class SequenceListView(LoginRequiredMixin, GroupPermissionMixin, ListView):
    permission_required = "invoices.view_sequence"
    model = Sequence
    template_name = "sequences/index.html"
    context_object_name = "sequences"


class SequenceCreateView(LoginRequiredMixin, GroupPermissionMixin, CreateView):
    permission_required = "invoices.add_sequence"
    model = Sequence
    form_class = SequenceForm
    template_name = "sequences/form.html"
    success_url = reverse_lazy("sequences-index")

    def form_valid(self, form):
        messages.success(self.request, "Sequenza creata.")
        return super().form_valid(form)


class SequenceEditView(LoginRequiredMixin, GroupPermissionMixin, UpdateView):
    permission_required = "invoices.change_sequence"
    model = Sequence
    form_class = SequenceForm
    template_name = "sequences/form.html"
    success_url = reverse_lazy("sequences-index")

    def get_queryset(self):
        return Sequence.objects.filter(is_system=False)

    def form_valid(self, form):
        messages.success(self.request, "Sequenza aggiornata.")
        return super().form_valid(form)


class SequenceDeleteView(LoginRequiredMixin, GroupPermissionMixin, DeleteView):
    permission_required = "invoices.delete_sequence"
    model = Sequence
    template_name = "common/confirm_delete.html"
    success_url = reverse_lazy("sequences-index")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        invoices = list(
            Invoice.all_types
            .filter(sequence=self.object)
            .select_related("contact")
            .order_by("-date")
        )
        ctx.update({
            "object_label": "Sequenza",
            "cancel_url": reverse("sequences-index"),
            "related_objects": annotate_invoice_urls(invoices),
            "related_label": "Fatture",
            "delete_all_url": reverse("sequences-delete-related", args=[self.object.pk]),
        })
        return ctx

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.is_system:
            messages.error(request, "Sequenza di sistema — non eliminabile.")
            return redirect("sequences-index")
        return self.render_to_response(self.get_context_data())

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.is_system:
            messages.error(request, "Sequenza di sistema — non eliminabile.")
            return redirect("sequences-index")
        if self.object.invoice_set.exists():
            messages.error(request, "Elimina prima le fatture collegate.")
            return self.render_to_response(self.get_context_data())
        self.object.delete()
        messages.success(request, "Sequenza eliminata.")
        return redirect(self.success_url)


class SequenceDeleteRelatedView(LoginRequiredMixin, GroupPermissionMixin, View):
    """Delete all invoices in this sequence, then redirect back."""
    permission_required = "invoices.delete_sequence"

    @transaction.atomic
    def post(self, request, pk):
        sequence = get_object_or_404(Sequence, pk=pk)
        invoices = Invoice.all_types.filter(sequence=sequence)
        count = invoices.count()
        invoices.delete()
        messages.success(request, f"{count} fatture eliminate.")
        return redirect("sequences-delete", pk=pk)
