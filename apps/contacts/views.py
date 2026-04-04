"""Views for contacts CRUD."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.common.helpers import annotate_invoice_urls
from apps.common.mixins import GroupPermissionMixin
from apps.invoices.models import Invoice

from .forms import ContactForm
from .models import Contact


class ContactListView(LoginRequiredMixin, GroupPermissionMixin, ListView):
    permission_required = "contacts.view_contact"
    model = Contact
    template_name = "contacts/index.html"
    context_object_name = "contacts"
    paginate_by = 15

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(name__icontains=q) | Q(vat_number__icontains=q) | Q(tax_code__icontains=q)
            )
        return qs

    def get_template_names(self):
        if self.request.htmx:
            return ["contacts/partials/_table.html"]
        return [self.template_name]


class ContactCreateView(LoginRequiredMixin, GroupPermissionMixin, CreateView):
    permission_required = "contacts.add_contact"
    model = Contact
    form_class = ContactForm
    template_name = "contacts/form.html"
    success_url = reverse_lazy("contacts-index")

    def form_valid(self, form):
        messages.success(self.request, "Contatto creato.")
        return super().form_valid(form)


class ContactEditView(LoginRequiredMixin, GroupPermissionMixin, UpdateView):
    permission_required = "contacts.change_contact"
    model = Contact
    form_class = ContactForm
    template_name = "contacts/form.html"
    success_url = reverse_lazy("contacts-index")

    def form_valid(self, form):
        messages.success(self.request, "Contatto aggiornato.")
        return super().form_valid(form)


class ContactDeleteView(LoginRequiredMixin, GroupPermissionMixin, DeleteView):
    permission_required = "contacts.delete_contact"
    model = Contact
    template_name = "common/confirm_delete.html"
    success_url = reverse_lazy("contacts-index")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        invoices = list(
            Invoice.all_types.filter(contact=self.object)
            .select_related("contact").order_by("-date")
        )
        ctx.update({
            "object_label": "Contatto",
            "cancel_url": reverse("contacts-index"),
            "related_objects": annotate_invoice_urls(invoices),
            "related_label": "Fatture",
            "delete_all_url": reverse("contacts-delete-related", args=[self.object.pk]),
        })
        return ctx

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return self.render_to_response(self.get_context_data())

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if Invoice.all_types.filter(contact=self.object).exists():
            messages.error(request, "Elimina prima le fatture collegate.")
            return self.render_to_response(self.get_context_data())
        messages.success(request, "Contatto eliminato.")
        return self.delete(request, *args, **kwargs)


class ContactDeleteRelatedView(LoginRequiredMixin, GroupPermissionMixin, View):
    """Delete all invoices linked to a contact, then redirect back to confirm page."""
    permission_required = "contacts.delete_contact"

    @transaction.atomic
    def post(self, request, pk):
        contact = get_object_or_404(Contact, pk=pk)
        qs = Invoice.all_types.filter(contact=contact)
        count = qs.count()
        qs.delete()
        messages.success(request, f"{count} fatture eliminate.")
        return redirect("contacts-delete", pk=pk)
