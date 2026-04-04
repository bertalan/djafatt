"""Shared view mixins."""
from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import redirect


class GroupPermissionMixin(PermissionRequiredMixin):
    """PermissionRequiredMixin that redirects to dashboard with error on denial."""

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        messages.error(self.request, "Non hai i permessi per questa operazione.")
        return redirect("core-dashboard")
