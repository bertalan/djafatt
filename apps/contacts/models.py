from django.db import models

from apps.common.validators import EU_COUNTRY_CODES


class Contact(models.Model):
    """Client or supplier contact."""

    name = models.CharField(max_length=255)
    vat_number = models.CharField(max_length=30, blank=True, default="")
    tax_code = models.CharField(max_length=30, blank=True, default="")
    address = models.CharField(max_length=255, blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    postal_code = models.CharField(max_length=10, blank=True, default="")
    province = models.CharField(max_length=5, blank=True, default="")
    country = models.CharField(max_length=100, blank=True, default="")
    country_code = models.CharField(max_length=2, default="IT")
    sdi_code = models.CharField(max_length=7, blank=True, default="")
    pec = models.CharField(max_length=255, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=30, blank=True, default="")
    mobile = models.CharField(max_length=30, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    is_customer = models.BooleanField(default=False)
    is_supplier = models.BooleanField(default=False)

    # --- Payment defaults ---
    default_payment_method = models.CharField(max_length=10, blank=True, default="")
    default_payment_terms = models.CharField(max_length=10, blank=True, default="")
    default_bank_name = models.CharField(max_length=100, blank=True, default="")
    default_bank_iban = models.CharField(max_length=34, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def is_pa(self) -> bool:
        """True if the contact is a Public Administration (codice IPA = 6 chars)."""
        return bool(self.sdi_code) and len(self.sdi_code) == 6

    def is_italian(self) -> bool:
        return self.country_code.upper() == "IT"

    def is_eu(self) -> bool:
        return self.country_code.upper() in EU_COUNTRY_CODES

    def get_sdi_code_for_xml(self) -> str:
        """Return SDI code for FatturaPA XML. 'XXXXXXX' for foreign clients."""
        if not self.is_italian():
            return "XXXXXXX"
        return self.sdi_code or "0000000"

    def get_postal_code_for_xml(self) -> str:
        """Return postal code for XML. '00000' for foreign contacts."""
        if not self.is_italian():
            return "00000"
        return self.postal_code

    def get_province_for_xml(self) -> str:
        """Return province for XML. 'EE' for foreign contacts."""
        if not self.is_italian():
            return "EE"
        return self.province

    def get_vat_number_clean(self) -> str:
        """Remove country prefix from VAT number (IT, DE, FR, etc.)."""
        vat = self.vat_number.strip().upper()
        if len(vat) > 2 and vat[:2].isalpha():
            return vat[2:]
        return vat

    def logo_url(self) -> str | None:
        """Brandfetch logo URL from email domain."""
        if not self.email:
            return None
        domain = self.email.split("@")[-1] if "@" in self.email else None
        if domain:
            return f"https://cdn.brandfetch.io/{domain}/w/128/h/128"
        return None
