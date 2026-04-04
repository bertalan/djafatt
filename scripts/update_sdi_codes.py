"""Update contacts with SDI codes from XML files."""
import glob
import re

from apps.contacts.models import Contact

sdi_data = {}
for fpath in glob.glob("/app/fatt2025/*.xml"):
    with open(fpath) as f:
        content = f.read()
    cod = re.search(r"<CodiceDestinatario>(.*?)</CodiceDestinatario>", content)
    pec = re.search(r"<PECDestinatario>(.*?)</PECDestinatario>", content)
    m = re.search(
        r"<CessionarioCommittente>.*?<IdCodice>(.*?)</IdCodice>",
        content, re.DOTALL,
    )
    if not m:
        m = re.search(
            r"<CessionarioCommittente>.*?<CodiceFiscale>(.*?)</CodiceFiscale>",
            content, re.DOTALL,
        )
    if m:
        vat = m.group(1)
        entry = sdi_data.setdefault(vat, {})
        if cod and cod.group(1) != "0000000":
            entry["sdi_code"] = cod.group(1)
        if pec:
            entry["pec"] = pec.group(1)

for vat, data in sdi_data.items():
    try:
        contact = Contact.objects.get(vat_number=vat)
    except Contact.DoesNotExist:
        try:
            contact = Contact.objects.get(tax_code=vat)
        except Contact.DoesNotExist:
            print(f"  NOT FOUND: {vat}")
            continue
    updated = []
    if data.get("sdi_code") and not contact.sdi_code:
        contact.sdi_code = data["sdi_code"]
        updated.append("sdi_code")
    if data.get("pec") and not contact.pec:
        contact.pec = data["pec"]
        updated.append("pec")
    if updated:
        contact.save(update_fields=updated)
        print(f"  UPDATED {contact.name}: {', '.join(f'{k}={getattr(contact, k)}' for k in updated)}")
    else:
        print(f"  OK {contact.name}: sdi={contact.sdi_code} pec={contact.pec}")

print("\n--- All contacts ---")
for c in Contact.objects.all():
    print(f"  {c.name}: sdi_code={c.sdi_code!r} pec={c.pec!r}")
