"""Views for company settings and invoicing preferences."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import TemplateView

from constance import config

from apps.common.mixins import GroupPermissionMixin

from .forms import CompanySettingsForm, InvoicingSettingsForm

# Constance key → form field mapping
_COMPANY_MAP = {
    "company_name": "COMPANY_NAME",
    "vat_number": "COMPANY_VAT_NUMBER",
    "tax_code": "COMPANY_TAX_CODE",
    "address": "COMPANY_ADDRESS",
    "city": "COMPANY_CITY",
    "postal_code": "COMPANY_POSTAL_CODE",
    "province": "COMPANY_PROVINCE",
    "country_code": "COMPANY_COUNTRY_CODE",
    "fiscal_regime": "COMPANY_FISCAL_REGIME",
    "pec": "COMPANY_PEC",
    "sdi_code": "COMPANY_SDI_CODE",
    "phone": "COMPANY_PHONE",
    "email": "COMPANY_EMAIL",
    "bank_name": "COMPANY_BANK_NAME",
    "bank_iban": "COMPANY_BANK_IBAN",
}

_INVOICING_MAP = {
    "default_payment_method": "DEFAULT_PAYMENT_METHOD",
    "default_payment_terms": "DEFAULT_PAYMENT_TERMS",
    "default_withholding_tax_percent": "DEFAULT_WITHHOLDING_TAX_PERCENT",
}


class SettingsView(LoginRequiredMixin, GroupPermissionMixin, TemplateView):
    """Two-tab settings page: company + invoicing."""

    template_name = "settings/index.html"
    permission_required = "core.manage_settings"

    def _load_initial(self, field_map):
        return {field: getattr(config, key) for field, key in field_map.items()}

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        active_tab = self.request.GET.get("tab", "company")
        ctx["active_tab"] = active_tab
        ctx["company_form"] = CompanySettingsForm(
            initial=self._load_initial(_COMPANY_MAP),
            prefix="company",
        )
        ctx["invoicing_form"] = InvoicingSettingsForm(
            initial=self._load_initial(_INVOICING_MAP),
            prefix="invoicing",
        )
        return ctx

    def post(self, request, *args, **kwargs):
        tab = request.POST.get("_tab", "company")
        if tab == "company":
            form = CompanySettingsForm(request.POST, prefix="company")
            if form.is_valid():
                for field, key in _COMPANY_MAP.items():
                    setattr(config, key, form.cleaned_data[field])
                messages.success(request, "Dati azienda aggiornati.")
            else:
                ctx = self.get_context_data()
                ctx["company_form"] = form
                ctx["active_tab"] = "company"
                return self.render_to_response(ctx)
        elif tab == "invoicing":
            form = InvoicingSettingsForm(request.POST, prefix="invoicing")
            if form.is_valid():
                for field, key in _INVOICING_MAP.items():
                    val = form.cleaned_data[field]
                    setattr(config, key, val if val is not None else "")
                messages.success(request, "Impostazioni fatturazione aggiornate.")
            else:
                ctx = self.get_context_data()
                ctx["invoicing_form"] = form
                ctx["active_tab"] = "invoicing"
                return self.render_to_response(ctx)
        return redirect(f"/settings/?tab={tab}")
