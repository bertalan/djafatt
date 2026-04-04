"""TDD tests for XML import — RED phase.

Tests for importing FatturaPA XML files into Invoice models.
"""
import hashlib
from datetime import date

import pytest


SAMPLE_FATTURAPA_XML = """<?xml version="1.0" encoding="UTF-8"?>
<p:FatturaElettronica xmlns:p="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2.2"
    versione="FPR12">
  <FatturaElettronicaHeader>
    <DatiTrasmissione>
      <IdTrasmittente><IdPaese>IT</IdPaese><IdCodice>01234567890</IdCodice></IdTrasmittente>
      <ProgressivoInvio>00001</ProgressivoInvio>
      <FormatoTrasmissione>FPR12</FormatoTrasmissione>
      <CodiceDestinatario>ABC1234</CodiceDestinatario>
    </DatiTrasmissione>
    <CedentePrestatore>
      <DatiAnagrafici>
        <IdFiscaleIVA><IdPaese>IT</IdPaese><IdCodice>09876543210</IdCodice></IdFiscaleIVA>
        <Anagrafica><Denominazione>Fornitore SRL</Denominazione></Anagrafica>
        <RegimeFiscale>RF01</RegimeFiscale>
      </DatiAnagrafici>
      <Sede>
        <Indirizzo>Via Fornitore 1</Indirizzo><CAP>00100</CAP>
        <Comune>Roma</Comune><Provincia>RM</Provincia><Nazione>IT</Nazione>
      </Sede>
    </CedentePrestatore>
    <CessionarioCommittente>
      <DatiAnagrafici>
        <IdFiscaleIVA><IdPaese>IT</IdPaese><IdCodice>01234567890</IdCodice></IdFiscaleIVA>
        <Anagrafica><Denominazione>Test SRL</Denominazione></Anagrafica>
      </DatiAnagrafici>
      <Sede>
        <Indirizzo>Via Test 1</Indirizzo><CAP>00100</CAP>
        <Comune>Roma</Comune><Provincia>RM</Provincia><Nazione>IT</Nazione>
      </Sede>
    </CessionarioCommittente>
  </FatturaElettronicaHeader>
  <FatturaElettronicaBody>
    <DatiGenerali>
      <DatiGeneraliDocumento>
        <TipoDocumento>TD01</TipoDocumento><Divisa>EUR</Divisa>
        <Data>2026-01-15</Data><Numero>0001/2026</Numero>
      </DatiGeneraliDocumento>
    </DatiGenerali>
    <DatiBeniServizi>
      <DettaglioLinee>
        <NumeroLinea>1</NumeroLinea><Descrizione>Test service</Descrizione>
        <Quantita>1.00</Quantita><PrezzoUnitario>100.00</PrezzoUnitario>
        <PrezzoTotale>100.00</PrezzoTotale><AliquotaIVA>22.00</AliquotaIVA>
      </DettaglioLinee>
      <DatiRiepilogo>
        <AliquotaIVA>22.00</AliquotaIVA><ImponibileImporto>100.00</ImponibileImporto>
        <Imposta>22.00</Imposta><EsigibilitaIVA>I</EsigibilitaIVA>
      </DatiRiepilogo>
    </DatiBeniServizi>
  </FatturaElettronicaBody>
</p:FatturaElettronica>"""


@pytest.mark.django_db
class TestXmlImport:
    def test_import_creates_invoice(self):
        """Importing valid XML creates an Invoice record."""
        # Import service to be implemented in T15
        from apps.sdi.services.xml_importer import InvoiceXmlImportService

        result = InvoiceXmlImportService().import_xml(SAMPLE_FATTURAPA_XML)
        assert result is not None
        assert result.number == "0001/2026"

    def test_import_creates_contact_if_missing(self):
        """Import creates a Contact for the cedente if not existing."""
        from apps.contacts.models import Contact
        from apps.sdi.services.xml_importer import InvoiceXmlImportService

        InvoiceXmlImportService().import_xml(SAMPLE_FATTURAPA_XML)
        assert Contact.objects.filter(vat_number__contains="09876543210").exists()

    def test_import_creates_vat_rate_if_missing(self):
        """Import creates a VatRate if the aliquota doesn't exist."""
        from apps.invoices.models import VatRate
        from apps.sdi.services.xml_importer import InvoiceXmlImportService

        InvoiceXmlImportService().import_xml(SAMPLE_FATTURAPA_XML)
        assert VatRate.objects.filter(percent=22).exists()

    def test_import_sets_content_hash(self):
        """Import sets xml_content_hash for idempotency."""
        from apps.sdi.services.xml_importer import InvoiceXmlImportService

        result = InvoiceXmlImportService().import_xml(SAMPLE_FATTURAPA_XML)
        expected_hash = hashlib.sha256(SAMPLE_FATTURAPA_XML.encode()).hexdigest()
        assert result.xml_content_hash == expected_hash

    def test_import_duplicate_rejected(self):
        """Second import of same XML is rejected (idempotency)."""
        from apps.sdi.services.xml_importer import InvoiceXmlImportService

        service = InvoiceXmlImportService()
        service.import_xml(SAMPLE_FATTURAPA_XML)
        result = service.import_xml(SAMPLE_FATTURAPA_XML)
        assert result is None  # Duplicate, no new invoice

    def test_import_uses_defusedxml(self):
        """XXE payload in XML is safely rejected."""
        xxe_xml = """<?xml version="1.0"?>
        <!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
        <root>&xxe;</root>"""
        from apps.common.exceptions import XmlSecurityError
        from apps.sdi.services.xml_importer import InvoiceXmlImportService

        with pytest.raises(XmlSecurityError):
            InvoiceXmlImportService().import_xml(xxe_xml)

    def test_import_with_namespace_prefix(self):
        """XML with namespace prefix (p:) is parsed correctly."""
        from apps.sdi.services.xml_importer import InvoiceXmlImportService

        result = InvoiceXmlImportService().import_xml(SAMPLE_FATTURAPA_XML)
        assert result is not None

    def test_import_oversized_xml_rejected(self):
        """XML exceeding size limit is rejected."""
        from apps.common.exceptions import XmlSecurityError
        from apps.sdi.services.xml_importer import InvoiceXmlImportService

        huge_xml = "<?xml version='1.0'?><root>" + ("x" * 11_000_000) + "</root>"
        with pytest.raises(XmlSecurityError):
            InvoiceXmlImportService().import_xml(huge_xml)
