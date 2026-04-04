"""Views for products CRUD."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.common.mixins import GroupPermissionMixin

from .forms import ProductForm
from .models import Product


class ProductListView(LoginRequiredMixin, GroupPermissionMixin, ListView):
    permission_required = "products.view_product"
    model = Product
    template_name = "products/index.html"
    context_object_name = "products"
    paginate_by = 15

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
        return qs

    def get_template_names(self):
        if self.request.htmx:
            return ["products/partials/_table.html"]
        return [self.template_name]


class ProductCreateView(LoginRequiredMixin, GroupPermissionMixin, CreateView):
    permission_required = "products.add_product"
    model = Product
    form_class = ProductForm
    template_name = "products/form.html"
    success_url = reverse_lazy("products-index")

    def form_valid(self, form):
        messages.success(self.request, "Prodotto creato.")
        return super().form_valid(form)


class ProductEditView(LoginRequiredMixin, GroupPermissionMixin, UpdateView):
    permission_required = "products.change_product"
    model = Product
    form_class = ProductForm
    template_name = "products/form.html"
    success_url = reverse_lazy("products-index")

    def form_valid(self, form):
        messages.success(self.request, "Prodotto aggiornato.")
        return super().form_valid(form)


class ProductDeleteView(LoginRequiredMixin, GroupPermissionMixin, DeleteView):
    permission_required = "products.delete_product"
    model = Product
    success_url = reverse_lazy("products-index")
    http_method_names = ["post"]

    def form_valid(self, form):
        messages.success(self.request, "Prodotto eliminato.")
        return super().form_valid(form)
