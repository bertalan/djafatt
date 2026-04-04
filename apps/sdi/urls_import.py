from django.urls import path

from .views_import import import_view, sequence_options_view

urlpatterns = [
    path("", import_view, name="imports-index"),
    path("sequences/", sequence_options_view, name="imports-sequences"),
]
