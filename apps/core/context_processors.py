"""Context processors for core app."""
from datetime import date


def fiscal_year_context(request):
    """Add fiscal year info to every template."""
    current_year = date.today().year
    fiscal_year = request.session.get("fiscal_year", current_year)
    available_years = list(range(current_year, 2019, -1))
    return {
        "fiscal_year": fiscal_year,
        "is_read_only": fiscal_year < current_year,
        "available_years": available_years,
    }
