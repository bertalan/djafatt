"""Domain exception hierarchy for djafatt.

All application-specific exceptions inherit from DjafattError.
Each exception carries a machine-readable `code` for structured logging and API responses.
"""


class DjafattError(Exception):
    """Base exception for all djafatt domain errors."""

    code = "application_error"

    def __init__(self, message: str = "", *, detail: str = ""):
        self.detail = detail
        super().__init__(message)


class ValidationError(DjafattError):
    """Input validation failed (fiscal codes, amounts, required fields)."""

    code = "validation_error"


class XmlImportError(DjafattError):
    """Generic XML import failure."""

    code = "xml_import_error"


class XmlSchemaError(XmlImportError):
    """XML does not conform to FatturaPA XSD schema."""

    code = "xml_schema_error"


class XmlSecurityError(XmlImportError):
    """XML contains malicious content (XXE, oversized, ZIP bomb)."""

    code = "xml_security_error"


class SdiClientError(DjafattError):
    """Communication error with the OpenAPI SDI service."""

    code = "sdi_client_error"


class SdiWebhookSecurityError(DjafattError):
    """Webhook request failed security validation (HMAC, replay, rate limit)."""

    code = "sdi_webhook_security_error"


class BusinessRuleViolation(DjafattError):
    """A business rule prevents the requested operation."""

    code = "business_rule_violation"


class InvoiceLockedError(BusinessRuleViolation):
    """Invoice is locked (sent to SDI) and cannot be modified."""

    code = "invoice_locked"


class SystemRecordError(BusinessRuleViolation):
    """Cannot delete/modify a system-managed record."""

    code = "system_record_protected"
