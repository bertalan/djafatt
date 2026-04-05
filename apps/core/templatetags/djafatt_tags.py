"""Template filters for formatting amounts and describing codes."""
from django import template

register = template.Library()


@register.filter
def format_cents(value):
    """Format cents integer to euro string: 1050 → '10,50'."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        return "0,00"
    sign = "-" if value < 0 else ""
    abs_value = abs(value)
    euros = abs_value // 100
    cents = abs_value % 100
    return f"{sign}{euros},{cents:02d}"


@register.filter
def format_cents_eur(value):
    """Format cents to '€ 10,50'."""
    return f"€ {format_cents(value)}"


# --- Code description filters ---

_DOC_TYPE_MAP = {
    "TD01": "Fattura",
    "TD02": "Acconto/Anticipo su fattura",
    "TD03": "Acconto/Anticipo su parcella",
    "TD04": "Nota di Credito",
    "TD05": "Nota di Debito",
    "TD06": "Parcella",
    "TD17": "Integrazione servizi estero",
    "TD18": "Integrazione beni intraUE",
    "TD19": "Integrazione beni art. 17 c.2",
    "TD24": "Fattura differita",
    "TD25": "Fattura differita DDT",
    "TD28": "Acquisti da San Marino",
}

_PAYMENT_METHOD_MAP = {
    "MP01": "Contanti",
    "MP02": "Assegno",
    "MP05": "Bonifico",
    "MP08": "Carta di pagamento",
    "MP12": "RIBA",
    "MP14": "Quietanza erario",
    "MP15": "Giroconto",
    "MP16": "Domiciliazione bancaria",
    "MP17": "Domiciliazione postale",
    "MP18": "Bollettino postale",
    "MP19": "SEPA DD",
    "MP20": "SEPA DD CORE",
    "MP21": "SEPA DD B2B",
    "MP22": "Trattenuta su somme",
    "MP23": "PagoPA",
}

_PAYMENT_TERMS_MAP = {
    "TP01": "Pagamento a rate",
    "TP02": "Pagamento completo",
    "TP03": "Anticipo",
}

_STATUS_MAP = {
    "draft": "Bozza",
    "sealed": "Sigillata",
    "outbox": "In uscita",
    "generated": "Generata",
    "sent": "Inviata",
    "received": "Ricevuta",
}

_VAT_PAYABILITY_MAP = {
    "I": "Immediata",
    "D": "Differita",
    "S": "Scissione pagamenti",
}


def _describe(value, mapping):
    """Return 'CODE (Descrizione)' or just the value if not found."""
    if not value:
        return ""
    desc = mapping.get(str(value))
    return f'{value} ({desc})' if desc else str(value)


@register.filter
def describe_doc_type(value):
    return _describe(value, _DOC_TYPE_MAP)


@register.filter
def describe_payment_method(value):
    return _describe(value, _PAYMENT_METHOD_MAP)


@register.filter
def describe_payment_terms(value):
    return _describe(value, _PAYMENT_TERMS_MAP)


@register.filter
def describe_status(value):
    """Status → Italian label (no code prefix)."""
    if not value:
        return ""
    return _STATUS_MAP.get(str(value), str(value))


@register.filter
def describe_vat_payability(value):
    return _describe(value, _VAT_PAYABILITY_MAP)


_INVOICE_TYPE_MAP = {
    "sales": "Vendita",
    "purchase": "Acquisto",
    "self_invoice": "Autofattura",
}


@register.filter
def describe_invoice_type(value):
    """Invoice type → Italian label."""
    if not value:
        return ""
    return _INVOICE_TYPE_MAP.get(str(value), str(value))
