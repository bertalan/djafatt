"""Views for user management (CRUD)."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView, TemplateView

from apps.common.mixins import GroupPermissionMixin

from .forms import UserCreateForm, UserEditForm


class UserListView(LoginRequiredMixin, GroupPermissionMixin, ListView):
    model = User
    template_name = "users/index.html"
    context_object_name = "users"
    permission_required = "core.manage_users"

    def get_queryset(self):
        return User.objects.prefetch_related("groups").order_by("-is_active", "username")


class UserCreateView(LoginRequiredMixin, GroupPermissionMixin, TemplateView):
    template_name = "users/form.html"
    permission_required = "core.manage_users"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form"] = UserCreateForm()
        ctx["is_new"] = True
        return ctx

    def post(self, request, *args, **kwargs):
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data["email"],
                email=form.cleaned_data["email"],
                password=form.cleaned_data["password"],
                first_name=form.cleaned_data.get("first_name", ""),
                last_name=form.cleaned_data.get("last_name", ""),
            )
            user.groups.set([form.cleaned_data["group"]])
            messages.success(request, f"Utente {user.email} creato.")
            return redirect("users-index")
        return self.render_to_response({"form": form, "is_new": True})


class UserEditView(LoginRequiredMixin, GroupPermissionMixin, TemplateView):
    template_name = "users/form.html"
    permission_required = "core.manage_users"

    def get_user_object(self):
        return get_object_or_404(User, pk=self.kwargs["pk"])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.get_user_object()
        ctx["form"] = UserEditForm(initial={
            "first_name": user.first_name,
            "last_name": user.last_name,
            "group": user.groups.first(),
            "is_active": user.is_active,
        })
        ctx["edit_user"] = user
        ctx["is_new"] = False
        return ctx

    def post(self, request, *args, **kwargs):
        user = self.get_user_object()
        form = UserEditForm(request.POST)
        if form.is_valid():
            user.first_name = form.cleaned_data.get("first_name", "")
            user.last_name = form.cleaned_data.get("last_name", "")
            user.is_active = form.cleaned_data["is_active"]
            if form.cleaned_data.get("new_password"):
                user.set_password(form.cleaned_data["new_password"])
            user.save()
            user.groups.set([form.cleaned_data["group"]])
            messages.success(request, f"Utente {user.email} aggiornato.")
            return redirect("users-index")
        return self.render_to_response({
            "form": form,
            "edit_user": user,
            "is_new": False,
        })
