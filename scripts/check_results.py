from apps.invoices.models import PaymentDue
print("--- PaymentDue records ---")
for pd in PaymentDue.objects.select_related("invoice").order_by("invoice__number"):
    print(f"  Invoice #{pd.invoice.number}: due={pd.due_date} amount={pd.amount} method={pd.payment_method}")
print(f"Total: {PaymentDue.objects.count()} records")
print()
from apps.contacts.models import Contact
print("--- Contacts addresses ---")
for c in Contact.objects.all():
    print(f"  {c.name}: address={c.address!r}")
