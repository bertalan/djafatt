"""Template filters for formatting."""
from django import template

register = template.Library()


@register.filter
def format_cents(value):
    """Format cents integer to euro string: 1050 → '10,50'."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        return "0,00"
    euros = value // 100
    cents = abs(value) % 100
    sign = "-" if value < 0 else ""
    return f"{sign}{euros},{cents:02d}"


@register.filter
def format_cents_eur(value):
    """Format cents to '€ 10,50'."""
    return f"€ {format_cents(value)}"
