"""Fiscal validators for Italian tax compliance."""
import re

from apps.common.exceptions import ValidationError

# EU member state codes (ISO 3166-1 alpha-2)
EU_COUNTRY_CODES = frozenset({
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
    "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
    "PL", "PT", "RO", "SK", "SI", "ES", "SE",
})


def validate_italian_vat_number(vat_number: str) -> str:
    """Validate Italian VAT number (P.IVA): exactly 11 digits."""
    cleaned = re.sub(r"\s+", "", vat_number)
    if cleaned.upper().startswith("IT"):
        cleaned = cleaned[2:]
    if not re.match(r"^\d{11}$", cleaned):
        raise ValidationError(f"Invalid Italian VAT number: {vat_number}")
    return cleaned


def validate_italian_tax_code(tax_code: str) -> str:
    """Validate Italian tax code (Codice Fiscale): 16 alphanumeric or 11 digits."""
    cleaned = re.sub(r"\s+", "", tax_code).upper()
    if not (re.match(r"^[A-Z0-9]{16}$", cleaned) or re.match(r"^\d{11}$", cleaned)):
        raise ValidationError(f"Invalid Italian tax code: {tax_code}")
    return cleaned


def is_eu_country(country_code: str) -> bool:
    """Check if a country code belongs to an EU member state."""
    return country_code.upper() in EU_COUNTRY_CODES
