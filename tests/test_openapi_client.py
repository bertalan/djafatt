"""TDD tests for OpenAPI SDI client — RED phase.

Uses respx to mock httpx requests. No real API calls.
"""
import pytest
import respx
from httpx import Response


@pytest.mark.django_db
class TestOpenApiSdiClient:
    @respx.mock
    def test_send_invoice_success(self, settings):
        """send_invoice returns UUID on success."""
        settings.OPENAPI_SDI_TOKEN = "test-token"
        settings.OPENAPI_SDI_SANDBOX = True

        respx.post("https://test.sdi.openapi.it/invoices").mock(
            return_value=Response(200, json={
                "success": True,
                "data": {"uuid": "abc-123", "status": "queued"},
            })
        )

        from apps.sdi.services.openapi_client import OpenApiSdiClient

        client = OpenApiSdiClient()
        result = client.send_invoice("<xml>test</xml>")
        assert result["uuid"] == "abc-123"

    @respx.mock
    def test_send_invoice_includes_idempotency_key(self, settings):
        """send_invoice includes Idempotency-Key header."""
        settings.OPENAPI_SDI_TOKEN = "test-token"
        settings.OPENAPI_SDI_SANDBOX = True

        route = respx.post("https://test.sdi.openapi.it/invoices").mock(
            return_value=Response(200, json={"success": True, "data": {"uuid": "x"}})
        )

        from apps.sdi.services.openapi_client import OpenApiSdiClient

        client = OpenApiSdiClient()
        client.send_invoice("<xml>test</xml>")
        assert "Idempotency-Key" in route.calls[0].request.headers

    @respx.mock
    def test_get_invoice_status(self, settings):
        """get_invoice_status returns status data."""
        settings.OPENAPI_SDI_TOKEN = "test-token"
        settings.OPENAPI_SDI_SANDBOX = True

        respx.get("https://test.sdi.openapi.it/invoices/abc-123").mock(
            return_value=Response(200, json={
                "data": {"uuid": "abc-123", "status": "delivered"},
            })
        )

        from apps.sdi.services.openapi_client import OpenApiSdiClient

        client = OpenApiSdiClient()
        result = client.get_invoice_status("abc-123")
        assert result["status"] == "delivered"

    @respx.mock
    def test_download_invoice_xml(self, settings):
        """download_invoice_xml returns XML string."""
        settings.OPENAPI_SDI_TOKEN = "test-token"
        settings.OPENAPI_SDI_SANDBOX = True

        respx.get("https://test.sdi.openapi.it/invoices_download/abc-123").mock(
            return_value=Response(200, text="<FatturaElettronica/>")
        )

        from apps.sdi.services.openapi_client import OpenApiSdiClient

        client = OpenApiSdiClient()
        xml = client.download_invoice_xml("abc-123")
        assert "FatturaElettronica" in xml

    @respx.mock
    def test_supplier_invoices_pagination(self, settings):
        """get_supplier_invoices passes pagination params."""
        settings.OPENAPI_SDI_TOKEN = "test-token"
        settings.OPENAPI_SDI_SANDBOX = True

        route = respx.get("https://test.sdi.openapi.it/invoices").mock(
            return_value=Response(200, json={"data": [], "meta": {"total": 0}})
        )

        from apps.sdi.services.openapi_client import OpenApiSdiClient

        client = OpenApiSdiClient()
        client.get_supplier_invoices(page=2, per_page=25)
        assert route.calls[0].request.url.params["page"] == "2"
        assert route.calls[0].request.url.params["per_page"] == "25"

    @respx.mock
    def test_send_invoice_api_error(self, settings):
        """send_invoice raises SdiClientError on API failure."""
        settings.OPENAPI_SDI_TOKEN = "test-token"
        settings.OPENAPI_SDI_SANDBOX = True

        respx.post("https://test.sdi.openapi.it/invoices").mock(
            return_value=Response(200, json={"success": False, "message": "Invalid XML"})
        )

        from apps.common.exceptions import SdiClientError
        from apps.sdi.services.openapi_client import OpenApiSdiClient

        client = OpenApiSdiClient()
        with pytest.raises(SdiClientError):
            client.send_invoice("<bad-xml/>")

    def test_missing_token_raises(self, settings):
        """Client raises SdiClientError if token not configured."""
        settings.OPENAPI_SDI_TOKEN = ""

        from apps.common.exceptions import SdiClientError
        from apps.sdi.services.openapi_client import OpenApiSdiClient

        with pytest.raises(SdiClientError):
            OpenApiSdiClient()

    @respx.mock
    def test_bearer_token_in_header(self, settings):
        """Authorization header contains Bearer token."""
        settings.OPENAPI_SDI_TOKEN = "secret-token-123"
        settings.OPENAPI_SDI_SANDBOX = True

        route = respx.get("https://test.sdi.openapi.it/invoices/x").mock(
            return_value=Response(200, json={"data": {}})
        )

        from apps.sdi.services.openapi_client import OpenApiSdiClient

        client = OpenApiSdiClient()
        client.get_invoice_status("x")
        assert route.calls[0].request.headers["authorization"] == "Bearer secret-token-123"
