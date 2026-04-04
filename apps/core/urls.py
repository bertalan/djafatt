from django.contrib.auth.views import LogoutView
from django.urls import path

from . import auth_views, views
from .views_settings import SettingsView
from .views_users import UserCreateView, UserEditView, UserListView

urlpatterns = [
    path("health/", views.health_check, name="health-check"),
    path("", views.dashboard, name="core-dashboard"),
    path("login/", auth_views.login_view, name="core-login"),
    path("logout/", LogoutView.as_view(), name="core-logout"),
    path("setup/", auth_views.setup_view, name="core-setup"),
    path("set-fiscal-year/", views.set_fiscal_year, name="core-set-fiscal-year"),
    # Settings
    path("settings/", SettingsView.as_view(), name="settings-index"),
    # User management
    path("users/", UserListView.as_view(), name="users-index"),
    path("users/create/", UserCreateView.as_view(), name="users-create"),
    path("users/<int:pk>/edit/", UserEditView.as_view(), name="users-edit"),
]
