from django.urls import path

from . import views_sequences as views

urlpatterns = [
    path("", views.SequenceListView.as_view(), name="sequences-index"),
    path("create/", views.SequenceCreateView.as_view(), name="sequences-create"),
    path("<int:pk>/edit/", views.SequenceEditView.as_view(), name="sequences-edit"),
    path("<int:pk>/delete/", views.SequenceDeleteView.as_view(), name="sequences-delete"),
    path("<int:pk>/delete-related/", views.SequenceDeleteRelatedView.as_view(), name="sequences-delete-related"),
]
