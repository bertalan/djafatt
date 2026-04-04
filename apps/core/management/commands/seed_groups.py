"""Seed default groups with permissions (idempotent)."""
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

# Permission codenames per group.
# "*" means all perms for the app_label.model combo.
GROUPS = {
    "Amministratore": {
        "contacts.contact": "*",
        "invoices.invoice": "*",
        "invoices.invoiceline": "*",
        "invoices.vatrate": "*",
        "invoices.sequence": "*",
        "products.product": "*",
        "core.corepermissions": ["manage_settings", "manage_users", "manage_fiscal_year"],
    },
    "Contabile": {
        "contacts.contact": "*",
        "invoices.invoice": "*",
        "invoices.invoiceline": "*",
        "invoices.vatrate": ["view_vatrate"],
        "invoices.sequence": ["view_sequence"],
        "products.product": "*",
        "core.corepermissions": ["manage_fiscal_year"],
    },
    "Operatore": {
        "contacts.contact": ["view_contact"],
        "invoices.invoice": ["add_invoice", "change_invoice", "view_invoice"],
        "invoices.invoiceline": ["add_invoiceline", "change_invoiceline", "view_invoiceline"],
        "invoices.vatrate": ["view_vatrate"],
        "invoices.sequence": ["view_sequence"],
        "products.product": ["view_product"],
    },
}


class Command(BaseCommand):
    help = "Create default groups (Amministratore, Contabile, Operatore) with permissions."

    def handle(self, *args, **options):
        for group_name, model_perms in GROUPS.items():
            group, created = Group.objects.get_or_create(name=group_name)
            perms = []
            for model_key, codes in model_perms.items():
                app_label, model = model_key.split(".")
                if codes == "*":
                    perms.extend(
                        Permission.objects.filter(
                            content_type__app_label=app_label,
                            content_type__model=model,
                        )
                    )
                else:
                    perms.extend(
                        Permission.objects.filter(
                            content_type__app_label=app_label,
                            content_type__model=model,
                            codename__in=codes,
                        )
                    )
            group.permissions.set(perms)
            verb = "Created" if created else "Updated"
            self.stdout.write(f"  {verb} group '{group_name}' with {len(perms)} permissions")
        self.stdout.write(self.style.SUCCESS("Groups seeded successfully."))
