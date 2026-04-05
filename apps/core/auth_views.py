"""Authentication views: login, logout, setup wizard."""
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from constance import config

from apps.core.forms import SetupForm


def login_view(request):
    """Login page — redirects to setup if no users exist."""
    if User.objects.count() == 0:
        return redirect("core-setup")
    if request.user.is_authenticated:
        return redirect("core-dashboard")
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        next_url = request.GET.get("next", "/")
        if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            next_url = "/"
        return redirect(next_url)
    return render(request, "auth/login.html", {"form": form})


def setup_view(request):
    """Setup wizard — only accessible when no users exist."""
    if User.objects.count() > 0:
        return redirect("core-dashboard")
    form = SetupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            user = User.objects.create_superuser(
                username=form.cleaned_data["email"],
                email=form.cleaned_data["email"],
                password=form.cleaned_data["password"],
            )
            config.COMPANY_NAME = form.cleaned_data["company_name"]
            config.COMPANY_VAT_NUMBER = form.cleaned_data["vat_number"]
            config.COMPANY_TAX_CODE = form.cleaned_data["tax_code"]
            config.COMPANY_ADDRESS = form.cleaned_data["address"]
            config.COMPANY_CITY = form.cleaned_data["city"]
            config.COMPANY_POSTAL_CODE = form.cleaned_data["postal_code"]
            config.COMPANY_PROVINCE = form.cleaned_data["province"]
            config.COMPANY_COUNTRY_CODE = form.cleaned_data.get("country_code", "IT")
            config.COMPANY_FISCAL_REGIME = form.cleaned_data["fiscal_regime"]
            config.COMPANY_PEC = form.cleaned_data.get("pec", "")
            config.COMPANY_SDI_CODE = form.cleaned_data.get("sdi_code", "")
            config.SETUP_COMPLETED = True
            _seed_system_data()
            _assign_admin_group(user)
            login(request, user)
        return redirect("core-dashboard")
    return render(request, "core/setup.html", {"form": form})


def _seed_system_data():
    """Create system VatRates and Sequences on first setup."""
    from apps.invoices.models import Sequence, VatRate

    vat_defaults = [
        {"name": "IVA 22%", "percent": 22, "is_system": True},
        {"name": "IVA 10%", "percent": 10, "is_system": True},
        {"name": "IVA 4%", "percent": 4, "is_system": True},
        {"name": "Esente", "percent": 0, "nature": "N1", "is_system": True},
    ]
    for d in vat_defaults:
        VatRate.objects.get_or_create(name=d["name"], defaults=d)

    seq_defaults = [
        {"name": "Fatture Vendita", "type": "sales", "pattern": "{SEQ}/{ANNO}", "is_system": True},
        {"name": "Fatture Acquisto", "type": "purchase", "pattern": "{SEQ}/{ANNO}", "is_system": True},
        {"name": "Autofatture", "type": "self_invoice", "pattern": "{SEQ}/{ANNO}", "is_system": True},
    ]
    for d in seq_defaults:
        Sequence.objects.get_or_create(name=d["name"], defaults=d)


def _assign_admin_group(user):
    """Seed permission groups and assign Amministratore to the first user."""
    from django.core.management import call_command

    call_command("seed_groups", verbosity=0)
    from django.contrib.auth.models import Group

    admin_group = Group.objects.filter(name="Amministratore").first()
    if admin_group:
        user.groups.add(admin_group)
