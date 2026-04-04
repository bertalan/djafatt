from django.urls import path

from . import views_vat_rates as views

urlpatterns = [
    path("", views.VatRateListView.as_view(), name="vat-rates-index"),
    path("create/", views.VatRateCreateView.as_view(), name="vat-rates-create"),
    path("<int:pk>/edit/", views.VatRateEditView.as_view(), name="vat-rates-edit"),
    path("<int:pk>/delete/", views.VatRateDeleteView.as_view(), name="vat-rates-delete"),
    path("<int:pk>/delete-related/", views.VatRateDeleteRelatedView.as_view(), name="vat-rates-delete-related"),
]
