"""Check imported invoices for missing fields."""
import django, os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "djafatt.settings.dev")
django.setup()

from apps.invoices.models import Invoice

print(f"{'Type':15} {'Number':10} {'Date':10} {'Contact':30} {'Net':>8} {'VAT':>7} {'Gross':>8} {'PM':6} {'PT':6} {'IBAN':22} {'Status':10} {'SDI':10} {'DocType':7}")
print("-" * 180)
for inv in Invoice.all_types.order_by("date"):
    print(
        f"{inv.type:15} {inv.number:10} {str(inv.date):10} {inv.contact.name[:30]:30} "
        f"{inv.total_net:>8} {inv.total_vat:>7} {inv.total_gross:>8} "
        f"{inv.payment_method:6} {inv.payment_terms:6} {inv.bank_iban:22} "
        f"{inv.status:10} {inv.sdi_status:10} {inv.document_type:7}"
    )

print()
print("--- Payment Dues ---")
from apps.invoices.models import PaymentDue
for pd in PaymentDue.objects.select_related("invoice").all():
    print(f"  Invoice {pd.invoice.number}: due={pd.due_date} amount={pd.amount} method={pd.payment_method} paid={pd.paid}")
