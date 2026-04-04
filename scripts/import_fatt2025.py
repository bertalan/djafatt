"""Import all XML files from fatt2025 using the fixed importer."""
import glob
import os

from apps.sdi.services.xml_importer import InvoiceXmlImportService
from apps.invoices.models import Sequence

seq = Sequence.objects.filter(type="sales").first()
print(f"Sequence: {seq} (id={seq.pk})")

service = InvoiceXmlImportService()
for fpath in sorted(glob.glob("/app/fatt2025/*.xml")):
    with open(fpath, "rb") as f:
        content = f.read()
    try:
        inv = service.import_xml(content, sequence_id=seq.pk, category="electronic_invoice")
        if inv:
            print(
                f"  OK: {os.path.basename(fpath)} -> #{inv.number} "
                f"pm={inv.payment_method} pt={inv.payment_terms} "
                f"iban={inv.bank_iban} bank={inv.bank_name}"
            )
        else:
            print(f"  SKIP: {os.path.basename(fpath)} (duplicate)")
    except Exception as e:
        print(f"  ERR: {os.path.basename(fpath)}: {e}")

print(
    f"\nStats: {service.stats.invoices_imported} imported, "
    f"{service.stats.contacts_created} contacts, "
    f"{service.stats.errors} errors"
)
for msg in service.stats.error_messages:
    print(f"  Error: {msg}")
