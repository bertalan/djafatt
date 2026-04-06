"""OpenAPI SDI HTTP client.

Communicates with the SDI (Sistema di Interscambio) via OpenAPI.
Token is read from settings (env var), never from Constance or database.
"""
import hashlib
import logging

import httpx
from django.conf import settings

from apps.common.exceptions import SdiClientError

logger = logging.getLogger(__name__)


class OpenApiSdiClient:
    """Client for the OpenAPI SDI service."""

    def __init__(self):
        self.token = settings.OPENAPI_SDI_TOKEN
        if not self.token:
            raise SdiClientError("OPENAPI_SDI_TOKEN not configured")
        sandbox = settings.OPENAPI_SDI_SANDBOX
        self.base_url = (
            "https://test.sdi.openapi.it" if sandbox
            else "https://sdi.openapi.it"
        )
        self.client = httpx.Client(
            timeout=httpx.Timeout(30.0, connect=5.0),
            headers=self._headers,
        )

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    @staticmethod
    def _check_response(response: httpx.Response) -> None:
        """Raise SdiClientError on HTTP errors with clear context."""
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "SDI API %s %s → %s: %s",
                response.request.method,
                response.request.url,
                response.status_code,
                response.text[:500],
            )
            raise SdiClientError(
                f"SDI API error {response.status_code}: {response.text[:300]}"
            ) from exc

    def send_invoice(self, xml_content: str) -> dict:
        """Send FatturaPA XML to SDI. Returns {uuid, status}."""
        # Use /invoices_signature when apply_signature is enabled in OpenAPI config
        endpoint = f"{self.base_url}/invoices_signature"
        logger.info("Sending invoice to SDI (%s)...", endpoint)
        response = self.client.post(
            endpoint,
            content=xml_content.encode("utf-8"),
            headers={
                "Content-Type": "application/xml",
                "Idempotency-Key": self._build_idempotency_key(xml_content),
            },
        )
        self._check_response(response)
        data = response.json()
        if not data.get("success"):
            raise SdiClientError(data.get("message", "Unknown SDI error"))
        if "data" not in data or not isinstance(data["data"], dict):
            raise SdiClientError("Invalid API response: missing 'data' field")
        result = data["data"]
        if not result.get("uuid"):
            raise SdiClientError("API response missing uuid")
        logger.info("Invoice sent to SDI: uuid=%s", result["uuid"])
        return result

    def get_invoice_status(self, uuid: str) -> dict:
        """Check invoice status by UUID."""
        response = self.client.get(
            f"{self.base_url}/invoices/{uuid}",
        )
        self._check_response(response)
        return response.json()["data"]

    def download_invoice_xml(self, uuid: str) -> str:
        """Download invoice XML by UUID."""
        response = self.client.get(
            f"{self.base_url}/invoices_download/{uuid}",
        )
        self._check_response(response)
        return response.text

    def get_supplier_invoices(self, page: int = 1, per_page: int = 50) -> dict:
        """List received supplier invoices with pagination."""
        response = self.client.get(
            f"{self.base_url}/invoices",
            params={"type": 1, "page": page, "per_page": per_page},
        )
        self._check_response(response)
        return response.json()

    def register_business(self, vat_number: str, pec: str) -> dict:
        """Register business for e-invoicing."""
        response = self.client.post(
            f"{self.base_url}/business_registry_configurations",
            json={
                "fiscal_id": vat_number,
                "email": pec,
                "apply_signature": True,
                "apply_legal_storage": False,
            },
        )
        self._check_response(response)
        return response.json()

    def configure_webhooks(self, webhook_url: str) -> dict:
        """Configure webhook URL for SDI notifications."""
        response = self.client.post(
            f"{self.base_url}/api_configurations",
            json={"webhook_url": webhook_url},
        )
        self._check_response(response)
        return response.json()

    @staticmethod
    def _build_idempotency_key(xml_content: str) -> str:
        """Build idempotency key from XML content hash."""
        return hashlib.sha256(xml_content.encode("utf-8")).hexdigest()[:32]
