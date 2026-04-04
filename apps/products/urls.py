from django.urls import path

from .views import ProductCreateView, ProductDeleteView, ProductEditView, ProductListView

urlpatterns = [
    path("", ProductListView.as_view(), name="products-index"),
    path("create/", ProductCreateView.as_view(), name="products-create"),
    path("<int:pk>/edit/", ProductEditView.as_view(), name="products-edit"),
    path("<int:pk>/delete/", ProductDeleteView.as_view(), name="products-delete"),
]
