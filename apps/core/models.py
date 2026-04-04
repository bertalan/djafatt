"""Core models — custom permissions for settings and user management."""
from django.db import models


class CorePermissions(models.Model):
    """Phantom model for custom permissions (no DB table)."""

    class Meta:
        managed = False
        default_permissions = ()
        permissions = [
            ("manage_settings", "Può modificare impostazioni azienda"),
            ("manage_users", "Può gestire utenti e gruppi"),
            ("manage_fiscal_year", "Può cambiare anno fiscale"),
        ]
