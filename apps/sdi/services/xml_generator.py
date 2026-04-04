"""FatturaPA XML generator using a38 library.

Generates FatturaPA v1.2.2 XML from Invoice model data.
Company data read from Constance config.
"""
import io
import logging

from constance import config
from xml.etree import ElementTree as ET

from a38 import builder as a38_builder
from a38.fattura import (
    Anagrafica,
    CedentePrestatore,
    CessionarioCommittente,
    DatiAnagraficiCedentePrestatore,
    DatiAnagraficiCessionarioCommittente,
    DatiBeniServizi,
    DatiGenerali,
    DatiGeneraliDocumento,
    DatiPagamento,
    DatiRiepilogo,
    DatiTrasmissione,
    DettaglioLinee,
    DettaglioPagamento,
    FatturaElettronicaBody,
    FatturaElettronicaHeader,
    FatturaPrivati12,
    IdFiscaleIVA,
    IdTrasmittente,
    Sede,
)

from apps.common.exceptions import ValidationError

logger = logging.getLogger(__name__)


class CompanySettings:
    """Read-only wrapper around Constance company config."""

    @property
    def name(self):
        return config.COMPANY_NAME

    @property
    def vat_number(self):
        return config.COMPANY_VAT_NUMBER

    @property
    def tax_code(self):
        return config.COMPANY_TAX_CODE

    @property
    def address(self):
        return config.COMPANY_ADDRESS

    @property
    def city(self):
        return config.COMPANY_CITY

    @property
    def postal_code(self):
        return config.COMPANY_POSTAL_CODE

    @property
    def province(self):
        return config.COMPANY_PROVINCE

    @property
    def fiscal_regime(self):
        return config.COMPANY_FISCAL_REGIME

    @property
    def pec(self):
        return config.COMPANY_PEC


class InvoiceXmlGenerator:
    """Generate FatturaPA XML from an Invoice instance."""

    def generate(self, invoice) -> str:
        """Generate complete FatturaPA XML string."""
        self._validate_prerequisites(invoice)
        company = CompanySettings()

        header = FatturaElettronicaHeader()
        header.dati_trasmissione = self._build_trasmissione(invoice, company)
        header.cedente_prestatore = self._build_cedente(company)
        header.cessionario_committente = self._build_cessionario(invoice.contact)

        body = FatturaElettronicaBody()
        body.dati_generali = self._build_dati_generali(invoice)
        body.dati_beni_servizi = self._build_dati_beni_servizi(invoice)
        dati_pagamento = self._build_dati_pagamento(invoice)
        if dati_pagamento:
            body.dati_pagamento = [dati_pagamento]

        fattura = FatturaPrivati12()
        fattura.fattura_elettronica_header = header
        fattura.fattura_elettronica_body = [body]

        b = a38_builder.Builder()
        fattura.to_xml(b)
        tree = b.get_tree()
        buf = io.BytesIO()
        tree.write(buf, encoding="utf-8", xml_declaration=True)
        return buf.getvalue().decode("utf-8")

    def _validate_prerequisites(self, invoice):
        if not invoice.contact:
            raise ValidationError("Invoice must have a contact")
        if not invoice.lines.exists():
            raise ValidationError("Invoice must have at least one line")

    def _build_trasmissione(self, invoice, company):
        contact = invoice.contact
        trasm = DatiTrasmissione()
        trasm.id_trasmittente = IdTrasmittente()
        trasm.id_trasmittente.id_paese = "IT"
        trasm.id_trasmittente.id_codice = company.tax_code or company.vat_number
        trasm.progressivo_invio = str(invoice.sequential_number or 0).zfill(5)
        trasm.formato_trasmissione = "FPR12"
        trasm.codice_destinatario = contact.get_sdi_code_for_xml()
        return trasm

    def _build_cedente(self, company):
        cedente = CedentePrestatore()
        dati = DatiAnagraficiCedentePrestatore()
        dati.id_fiscale_iva = IdFiscaleIVA()
        dati.id_fiscale_iva.id_paese = "IT"
        dati.id_fiscale_iva.id_codice = company.vat_number
        dati.codice_fiscale = company.tax_code
        dati.anagrafica = Anagrafica()
        dati.anagrafica.denominazione = company.name
        dati.regime_fiscale = company.fiscal_regime
        cedente.dati_anagrafici = dati

        sede = Sede()
        sede.indirizzo = company.address
        sede.cap = company.postal_code
        sede.comune = company.city
        sede.provincia = company.province
        sede.nazione = "IT"
        cedente.sede = sede
        return cedente

    def _build_cessionario(self, contact):
        cess = CessionarioCommittente()
        dati = DatiAnagraficiCessionarioCommittente()
        dati.anagrafica = Anagrafica()
        dati.anagrafica.denominazione = contact.name

        dati.id_fiscale_iva = IdFiscaleIVA()
        if contact.is_italian():
            dati.id_fiscale_iva.id_paese = "IT"
            dati.id_fiscale_iva.id_codice = contact.get_vat_number_clean()
            if contact.tax_code:
                dati.codice_fiscale = contact.tax_code
        else:
            dati.id_fiscale_iva.id_paese = contact.country_code
            dati.id_fiscale_iva.id_codice = contact.get_vat_number_clean()

        cess.dati_anagrafici = dati

        sede = Sede()
        sede.indirizzo = contact.address or "."
        sede.cap = contact.get_postal_code_for_xml()
        sede.comune = contact.city or "."
        sede.provincia = contact.get_province_for_xml()
        sede.nazione = contact.country_code
        cess.sede = sede
        return cess

    def _build_dati_generali(self, invoice):
        dg = DatiGenerali()
        doc = DatiGeneraliDocumento()
        doc.tipo_documento = invoice.document_type or "TD01"
        doc.divisa = "EUR"
        doc.data = invoice.date.isoformat()
        doc.numero = invoice.number
        dg.dati_generali_documento = doc
        return dg

    def _build_dati_beni_servizi(self, invoice):
        dbs = DatiBeniServizi()
        dbs.dettaglio_linee = self._build_lines(invoice)
        dbs.dati_riepilogo = self._build_riepilogo(invoice)
        return dbs

    def _build_lines(self, invoice) -> list:
        lines = []
        for i, line in enumerate(invoice.lines.select_related("vat_rate").all(), 1):
            dl = DettaglioLinee()
            dl.numero_linea = i
            dl.descrizione = line.description
            dl.quantita = f"{line.quantity:.2f}"
            if line.unit_of_measure:
                dl.unita_misura = line.unit_of_measure
            dl.prezzo_unitario = f"{line.unit_price / 100:.2f}"
            dl.prezzo_totale = f"{line.total / 100:.2f}"
            dl.aliquota_iva = f"{line.vat_rate.percent:.2f}"
            if line.vat_rate.nature:
                dl.natura = line.vat_rate.nature
            lines.append(dl)
        return lines

    def _build_riepilogo(self, invoice) -> list:
        riepilogo = []
        for summary in invoice.get_vat_summary():
            dr = DatiRiepilogo()
            dr.aliquota_iva = f"{summary['vat_rate'].percent:.2f}"
            dr.imponibile_importo = f"{summary['taxable'] / 100:.2f}"
            dr.imposta = f"{summary['vat'] / 100:.2f}"
            dr.esigibilita_iva = invoice.vat_payability
            if summary["vat_rate"].nature:
                dr.natura = summary["vat_rate"].nature
            riepilogo.append(dr)
        return riepilogo

    def _build_dati_pagamento(self, invoice):
        """Build DatiPagamento from PaymentDue records.

        Returns None when the invoice has no payment dues and no
        payment_terms / payment_method set.
        """
        dues = list(invoice.payment_dues.all())

        # Fallback: no dues but invoice has payment info → single entry
        if not dues and not invoice.payment_terms and not invoice.payment_method:
            return None

        dp = DatiPagamento()
        dp.condizioni_pagamento = invoice.payment_terms or "TP02"

        if dues:
            details = []
            for due in dues:
                det = DettaglioPagamento()
                det.modalita_pagamento = due.payment_method or invoice.payment_method or "MP05"
                det.data_scadenza_pagamento = due.due_date.isoformat()
                det.importo_pagamento = f"{due.amount / 100:.2f}"
                if invoice.bank_name:
                    det.istituto_finanziario = invoice.bank_name
                if invoice.bank_iban:
                    det.iban = invoice.bank_iban
                details.append(det)
            dp.dettaglio_pagamento = details
        else:
            # No dues: emit a single DettaglioPagamento with totale lordo
            det = DettaglioPagamento()
            det.modalita_pagamento = invoice.payment_method or "MP05"
            det.importo_pagamento = f"{invoice.total_gross / 100:.2f}"
            if invoice.bank_name:
                det.istituto_finanziario = invoice.bank_name
            if invoice.bank_iban:
                det.iban = invoice.bank_iban
            dp.dettaglio_pagamento = [det]

        return dp
