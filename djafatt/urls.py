"""Root URL configuration for djafatt."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.core.urls")),
    path("contacts/", include("apps.contacts.urls")),
    path("invoices/", include("apps.invoices.urls")),
    path("purchase-invoices/", include("apps.invoices.urls_purchase")),
    path("self-invoices/", include("apps.invoices.urls_self")),
    path("products/", include("apps.products.urls")),
    path("vat-rates/", include("apps.invoices.urls_vat_rates")),
    path("sequences/", include("apps.invoices.urls_sequences")),
    path("imports/", include("apps.sdi.urls_import")),
    path("reports/", include("apps.invoices.urls_reports")),
    path("sdi/", include("apps.sdi.urls")),
    path("webhooks/", include("apps.sdi.urls_webhook")),
]
