from django.urls import path

from . import views

urlpatterns = [
    path("", views.ContactListView.as_view(), name="contacts-index"),
    path("create/", views.ContactCreateView.as_view(), name="contacts-create"),
    path("<int:pk>/edit/", views.ContactEditView.as_view(), name="contacts-edit"),
    path("<int:pk>/delete/", views.ContactDeleteView.as_view(), name="contacts-delete"),
    path("<int:pk>/delete-related/", views.ContactDeleteRelatedView.as_view(), name="contacts-delete-related"),
]
