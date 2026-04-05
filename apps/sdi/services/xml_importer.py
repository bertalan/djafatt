"""FatturaPA XML import service.

Imports invoices from XML content using defusedxml for XXE protection.
All amounts converted to cents. Contacts and VatRates auto-created if missing.
"""
import hashlib
import re
import zipfile
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from io import BytesIO

import defusedxml.ElementTree as ET
from defusedxml.common import DTDForbidden, EntitiesForbidden, ExternalReferenceForbidden

from django.db import transaction

from apps.common.exceptions import XmlImportError, XmlSchemaError, XmlSecurityError
from apps.contacts.models import Contact
from apps.invoices.models import (
    Invoice,
    InvoiceLine,
    InvoiceType,
    PaymentDue,
    PurchaseInvoice,
    SdiStatus,
    SelfInvoice,
    Sequence,
    VatRate,
)


# Limits
MAX_XML_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_ZIP_SIZE = 50 * 1024 * 1024  # 50 MB compressed
MAX_ZIP_EXPANDED = 100 * 1024 * 1024  # 100 MB expanded
MAX_ZIP_FILES = 200
MAX_COMPRESSION_RATIO = 100

# Document type → invoice type mapping
DOC_TYPE_MAP = {
    "TD01": InvoiceType.SALES,
    "TD02": InvoiceType.SALES,
    "TD03": InvoiceType.SALES,
    "TD04": InvoiceType.SALES,
    "TD05": InvoiceType.SALES,
    "TD06": InvoiceType.SALES,
    "TD24": InvoiceType.SALES,
    "TD25": InvoiceType.SALES,
    "TD17": InvoiceType.SELF_INVOICE,
    "TD18": InvoiceType.SELF_INVOICE,
    "TD19": InvoiceType.SELF_INVOICE,
    "TD28": InvoiceType.SELF_INVOICE,
}


@dataclass
class ImportStats:
    invoices_imported: int = 0
    contacts_created: int = 0
    errors: int = 0
    error_messages: list[str] = field(default_factory=list)


class InvoiceXmlImportService:
    """Import FatturaPA XML invoices."""

    def __init__(self):
        self.stats = ImportStats()

    def import_xml(self, xml_content: bytes | str, sequence_id: int | None = None, category: str = "purchase") -> "Invoice | None":
        """Import a single invoice from XML content.

        Returns the created Invoice, or None if duplicate.
        """
        if isinstance(xml_content, str):
            xml_bytes = xml_content.encode("utf-8")
        else:
            xml_bytes = xml_content

        if len(xml_bytes) > MAX_XML_SIZE:
            raise XmlSecurityError(f"XML file exceeds {MAX_XML_SIZE // (1024 * 1024)}MB limit")

        # Parse XML first (catches security issues before hitting DB)
        xml_clean = self._clean_xml(xml_bytes.decode("utf-8", errors="replace"))

        try:
            root = ET.fromstring(xml_clean, forbid_dtd=True, forbid_entities=True, forbid_external=True)
        except (EntitiesForbidden, DTDForbidden, ExternalReferenceForbidden) as exc:
            raise XmlSecurityError(f"XML contiene elementi non sicuri: {exc}") from exc
        except ET.ParseError as exc:
            raise XmlSchemaError(f"XML non valido: {exc}") from exc

        # Idempotency check (DB access)
        content_hash = hashlib.sha256(xml_bytes).hexdigest()
        if Invoice.all_types.filter(xml_content_hash=content_hash).exists():
            self.stats.error_messages.append("Fattura già importata (duplicato).")
            self.stats.errors += 1
            return None

        header = root.find(".//{*}FatturaElettronicaHeader")
        if header is None:
            header = root.find(".//FatturaElettronicaHeader")
        if header is None:
            raise XmlSchemaError("Elemento FatturaElettronicaHeader non trovato")

        # Process each FatturaElettronicaBody (multi-body support)
        bodies = root.findall(".//{*}FatturaElettronicaBody")
        if not bodies:
            bodies = root.findall(".//FatturaElettronicaBody")
        if not bodies:
            raise XmlSchemaError("Nessun FatturaElettronicaBody trovato")

        sequence = Sequence.objects.get(pk=sequence_id) if sequence_id else None

        last_invoice = None
        for body in bodies:
            last_invoice = self._import_single_body(header, body, sequence, category, content_hash)

        return last_invoice

    def import_zip(self, zip_data: bytes, sequence_id: int, category: str) -> None:
        """Import from a ZIP archive containing multiple XML files."""
        if len(zip_data) > MAX_ZIP_SIZE:
            raise XmlSecurityError(f"ZIP exceeds {MAX_ZIP_SIZE // (1024 * 1024)}MB limit")

        try:
            zf = zipfile.ZipFile(BytesIO(zip_data))
        except zipfile.BadZipFile as exc:
            raise XmlImportError("File ZIP non valido") from exc

        # Security: check for ZIP bomb
        members = zf.infolist()
        if len(members) > MAX_ZIP_FILES:
            raise XmlSecurityError(f"ZIP contiene troppi file ({len(members)} > {MAX_ZIP_FILES})")

        total_expanded = sum(m.file_size for m in members)
        if total_expanded > MAX_ZIP_EXPANDED:
            raise XmlSecurityError("ZIP espanso supera il limite di dimensione")

        if len(zip_data) > 0 and total_expanded / len(zip_data) > MAX_COMPRESSION_RATIO:
            raise XmlSecurityError("Rapporto di compressione sospetto (possibile ZIP bomb)")

        for member in members:
            name_lower = member.filename.lower()
            if not (name_lower.endswith(".xml") or name_lower.endswith(".p7m")):
                continue
            xml_bytes = zf.read(member)
            try:
                self.import_xml(xml_bytes, sequence_id, category)
            except (XmlImportError, XmlSchemaError) as exc:
                self.stats.errors += 1
                self.stats.error_messages.append(f"{member.filename}: {exc}")

    def _clean_xml(self, content: str) -> str:
        """Remove namespace prefixes and digital signature blocks."""
        # Remove common namespace prefixes
        content = re.sub(r'</?p:', lambda m: m.group().replace('p:', ''), content)
        content = re.sub(r'</?ns\d+:', lambda m: re.sub(r'ns\d+:', '', m.group()), content)
        # Remove digital signature blocks
        content = re.sub(r'<ds:Signature.*?</ds:Signature>', '', content, flags=re.DOTALL)
        content = re.sub(r'<Signature.*?</Signature>', '', content, flags=re.DOTALL)
        return content

    @transaction.atomic
    def _import_single_body(self, header, body, sequence, category, content_hash):
        """Import one FatturaElettronicaBody into the database."""
        # Determine invoice type
        general = self._find(body, "DatiGenerali/DatiGeneraliDocumento")
        if general is None:
            raise XmlSchemaError("DatiGeneraliDocumento non trovato")

        doc_type = self._text(general, "TipoDocumento") or "TD01"
        invoice_data = self._extract_invoice_data(general)

        # Get or create contact
        contact = self._get_or_create_contact(header, category)

        # Determine model class
        if category == "purchase":
            model_class = PurchaseInvoice
            inv_type = InvoiceType.PURCHASE
        elif category == "self_invoice":
            model_class = SelfInvoice
            inv_type = InvoiceType.SELF_INVOICE
        else:
            # Auto-detect from doc_type
            inv_type = DOC_TYPE_MAP.get(doc_type, InvoiceType.SALES)
            if inv_type == InvoiceType.SELF_INVOICE:
                model_class = SelfInvoice
            elif inv_type == InvoiceType.PURCHASE:
                model_class = PurchaseInvoice
            else:
                model_class = Invoice

        year = invoice_data["date"].year
        seq_number = sequence.get_next_number(year) if sequence else 0

        # Extract payment data from DatiPagamento
        payment_data = self._extract_payment_data(body)

        invoice = model_class(
            type=inv_type,
            number=invoice_data["number"],
            sequential_number=seq_number,
            date=invoice_data["date"],
            document_type=doc_type,
            status="received",
            contact=contact,
            sequence=sequence,
            sdi_status=SdiStatus.DELIVERED,
            xml_content_hash=content_hash,
            notes=invoice_data.get("causale", ""),
            payment_method=payment_data.get("payment_method", ""),
            payment_terms=payment_data.get("payment_terms", ""),
            bank_name=payment_data.get("bank_name", ""),
            bank_iban=payment_data.get("bank_iban", ""),
        )

        # Withholding tax
        if invoice_data.get("withholding_percent"):
            invoice.withholding_tax_enabled = True
            invoice.withholding_tax_percent = invoice_data["withholding_percent"]

        # Stamp duty
        if invoice_data.get("stamp_duty"):
            invoice.stamp_duty_applied = True
            invoice.stamp_duty_amount = invoice_data["stamp_duty"]

        invoice.save()

        # Import lines
        lines_data = self._extract_lines(body)
        for ld in lines_data:
            vat_rate = self._get_or_create_vat_rate(ld["vat_percent"], ld.get("nature", ""))
            InvoiceLine.objects.create(
                invoice=invoice,
                description=ld["description"],
                quantity=ld["quantity"],
                unit_of_measure=ld.get("unit_of_measure", ""),
                unit_price=ld["unit_price"],
                vat_rate=vat_rate,
                total=int(ld["unit_price"] * ld["quantity"]),
            )

        # Create PaymentDue records from DettaglioPagamento
        for due in payment_data.get("dues", []):
            PaymentDue.objects.create(
                invoice=invoice,
                due_date=due["due_date"],
                amount=due["amount"],
                payment_method=due.get("payment_method", ""),
            )

        invoice.calculate_totals()
        self.stats.invoices_imported += 1
        return invoice

    def _get_or_create_contact(self, header, category):
        """Find or create contact from XML header."""
        if category == "purchase":
            party = self._find(header, "CedentePrestatore")
        else:
            party = self._find(header, "CessionarioCommittente")

        if party is None:
            raise XmlSchemaError("Dati cedente/cessionario non trovati")

        vat_id = self._find(party, "DatiAnagrafici/IdFiscaleIVA")
        vat_number = self._text(vat_id, "IdCodice") if vat_id is not None else ""
        tax_code = self._text(self._find(party, "DatiAnagrafici"), "CodiceFiscale") or ""

        name = self._text(self._find(party, "DatiAnagrafici/Anagrafica"), "Denominazione") or ""
        if not name:
            nome = self._text(self._find(party, "DatiAnagrafici/Anagrafica"), "Nome") or ""
            cognome = self._text(self._find(party, "DatiAnagrafici/Anagrafica"), "Cognome") or ""
            name = f"{nome} {cognome}".strip()

        if not name:
            name = vat_number or tax_code or "Contatto sconosciuto"

        lookup = {}
        if vat_number:
            lookup["vat_number"] = vat_number
        elif tax_code:
            lookup["tax_code"] = tax_code
        else:
            raise XmlSchemaError("Contatto senza P.IVA né Codice Fiscale")

        address_el = self._find(party, "Sede")
        defaults = {
            "name": name,
            "is_supplier": category == "purchase",
            "is_customer": category != "purchase",
        }
        if address_el is not None:
            address = self._text(address_el, "Indirizzo") or ""
            numero_civico = self._text(address_el, "NumeroCivico") or ""
            if numero_civico:
                address = f"{address} {numero_civico}"
            defaults["address"] = address
            defaults["city"] = self._text(address_el, "Comune") or ""
            defaults["postal_code"] = self._text(address_el, "CAP") or ""
            defaults["province"] = self._text(address_el, "Provincia") or ""
            defaults["country_code"] = self._text(address_el, "Nazione") or "IT"

        # SDI code and PEC from DatiTrasmissione (for emitted invoices,
        # CodiceDestinatario is the client's SDI code)
        if category != "purchase":
            sdi_code = self._text(
                self._find(header, "DatiTrasmissione"), "CodiceDestinatario",
            ) or ""
            if sdi_code and sdi_code != "0000000":
                defaults["sdi_code"] = sdi_code
            pec_dest = self._text(header, "PECDestinatario") or ""
            if pec_dest:
                defaults["pec"] = pec_dest

        contact, created = Contact.objects.get_or_create(**lookup, defaults=defaults)
        if created:
            self.stats.contacts_created += 1
        else:
            # Update SDI/PEC if contact already exists but fields are empty
            updated = False
            if category != "purchase":
                sdi_code = defaults.get("sdi_code", "")
                pec_dest = defaults.get("pec", "")
                if sdi_code and not contact.sdi_code:
                    contact.sdi_code = sdi_code
                    updated = True
                if pec_dest and not contact.pec:
                    contact.pec = pec_dest
                    updated = True
            if updated:
                contact.save(update_fields=["sdi_code", "pec"])
        return contact

    def _get_or_create_vat_rate(self, percent, nature=""):
        """Find or create VatRate by percent."""
        try:
            return VatRate.objects.get(percent=percent, nature=nature)
        except VatRate.DoesNotExist:
            pass
        try:
            return VatRate.objects.get(percent=percent)
        except VatRate.DoesNotExist:
            return VatRate.objects.create(
                name=f"IVA {percent}%",
                percent=percent,
                nature=nature,
            )

    def _extract_invoice_data(self, general) -> dict:
        """Extract invoice header data."""
        data = {
            "number": self._text(general, "Numero") or "",
            "date": self._parse_date(self._text(general, "Data")),
            "causale": "",
            "payment_method": "",
            "payment_terms": "",
            "withholding_percent": None,
            "stamp_duty": None,
        }

        causale = self._text(general, "Causale")
        if causale:
            data["causale"] = causale

        # Withholding tax
        ritenuta = self._find(general, "DatiRitenuta")
        if ritenuta is not None:
            try:
                data["withholding_percent"] = Decimal(self._text(ritenuta, "AliquotaRitenuta") or "0")
            except InvalidOperation:
                pass

        # Stamp duty
        bollo = self._find(general, "DatiBollo")
        if bollo is not None:
            try:
                amount = Decimal(self._text(bollo, "ImportoBollo") or "0")
                data["stamp_duty"] = int(amount * 100)
            except InvalidOperation:
                pass

        return data

    def _extract_payment_data(self, body) -> dict:
        """Extract DatiPagamento: payment terms, method, bank, and due dates."""
        result: dict = {"dues": []}
        pagamento = self._find(body, "DatiPagamento")
        if pagamento is None:
            return result

        result["payment_terms"] = self._text(pagamento, "CondizioniPagamento") or ""

        for det in pagamento.iter():
            if not det.tag.endswith("DettaglioPagamento"):
                continue

            method = self._text(det, "ModalitaPagamento") or ""
            if not result.get("payment_method"):
                result["payment_method"] = method

            bank = self._text(det, "IstitutoFinanziario") or ""
            if not result.get("bank_name"):
                result["bank_name"] = bank

            iban = self._text(det, "IBAN") or ""
            if not result.get("bank_iban"):
                result["bank_iban"] = iban

            # Build PaymentDue record
            due_date_str = self._text(det, "DataScadenzaPagamento")
            if not due_date_str:
                due_date_str = self._text(det, "DataRiferimentoTerminiPagamento")
            due_date = self._parse_date(due_date_str)

            try:
                amount = int(Decimal(self._text(det, "ImportoPagamento") or "0") * 100)
            except InvalidOperation:
                amount = 0

            if amount:
                result["dues"].append({
                    "due_date": due_date,
                    "amount": amount,
                    "payment_method": method,
                })

        return result

    def _extract_lines(self, body) -> list[dict]:
        """Extract line items from DettaglioLinee."""
        lines = []
        for det in body.iter():
            if not det.tag.endswith("DettaglioLinee"):
                continue
            desc = self._text(det, "Descrizione") or ""
            try:
                qty = Decimal(self._text(det, "Quantita") or "1")
            except InvalidOperation:
                qty = Decimal("1")
            try:
                price_eur = Decimal(self._text(det, "PrezzoUnitario") or "0")
            except InvalidOperation:
                price_eur = Decimal("0")
            try:
                vat_pct = Decimal(self._text(det, "AliquotaIVA") or "0")
            except InvalidOperation:
                vat_pct = Decimal("0")

            lines.append({
                "description": desc,
                "quantity": qty,
                "unit_price": int(price_eur * 100),
                "vat_percent": vat_pct,
                "unit_of_measure": self._text(det, "UnitaMisura") or "",
                "nature": self._text(det, "Natura") or "",
            })
        return lines

    def _parse_date(self, date_str: str | None) -> date:
        """Parse ISO date string (YYYY-MM-DD)."""
        if not date_str:
            return date.today()
        try:
            parts = date_str.strip()[:10].split("-")
            return date(int(parts[0]), int(parts[1]), int(parts[2]))
        except (ValueError, IndexError):
            return date.today()

    @staticmethod
    def _find(element, path: str):
        """Find child element, trying with and without namespace."""
        if element is None:
            return None
        result = element.find(f".//{path}")
        if result is None:
            result = element.find(f".//{{*}}{path.split('/')[-1]}")
        return result

    @staticmethod
    def _text(element, tag: str) -> str | None:
        """Get text of a child element."""
        if element is None:
            return None
        child = element.find(tag)
        if child is None:
            child = element.find(f"{{*}}{tag}")
        return child.text if child is not None else None


def import_supplier_invoices(client) -> int:
    """Fetch and import new supplier invoices from SDI.

    Returns count of newly imported invoices.
    Uses a single API call to get_supplier_invoices.
    """
    import logging

    from apps.invoices.models import Invoice

    logger = logging.getLogger("apps.sdi")
    importer = InvoiceXmlImportService()

    try:
        response = client.get_supplier_invoices(page=1, per_page=50)
    except Exception:
        logger.exception("Failed to fetch supplier invoices from SDI")
        return 0

    data = response.get("data", [])
    if not isinstance(data, list):
        logger.warning("Unexpected supplier invoices response format")
        return 0

    imported = 0
    for item in data:
        uuid = item.get("uuid", "")
        if not uuid:
            continue

        # Skip already imported
        if Invoice.all_types.filter(sdi_uuid=uuid).exists():
            continue

        try:
            xml_content = client.download_invoice_xml(uuid)
            result = importer.import_xml(xml_content)
            # Tag with SDI uuid
            if result and hasattr(result, "pk"):
                Invoice.all_types.filter(pk=result.pk).update(sdi_uuid=uuid)
            imported += 1
        except Exception:
            logger.exception("Failed to import supplier invoice uuid=%s", uuid)

    return imported
