"""TDD tests for error handling — RED phase.

Tests for custom exception hierarchy and structured error responses.
"""
import pytest

from apps.common.exceptions import (
    BusinessRuleViolation,
    DjafattError,
    InvoiceLockedError,
    SdiClientError,
    SdiWebhookSecurityError,
    SystemRecordError,
    ValidationError,
    XmlImportError,
    XmlSchemaError,
    XmlSecurityError,
)


class TestExceptionHierarchy:
    def test_all_exceptions_inherit_base(self):
        """All custom exceptions inherit from DjafattError."""
        for exc_cls in [
            ValidationError, XmlImportError, XmlSchemaError, XmlSecurityError,
            SdiClientError, SdiWebhookSecurityError, BusinessRuleViolation,
            InvoiceLockedError, SystemRecordError,
        ]:
            assert issubclass(exc_cls, DjafattError)

    def test_xml_errors_inherit_import(self):
        """XmlSchemaError and XmlSecurityError inherit from XmlImportError."""
        assert issubclass(XmlSchemaError, XmlImportError)
        assert issubclass(XmlSecurityError, XmlImportError)

    def test_business_rule_errors(self):
        """InvoiceLockedError and SystemRecordError inherit from BusinessRuleViolation."""
        assert issubclass(InvoiceLockedError, BusinessRuleViolation)
        assert issubclass(SystemRecordError, BusinessRuleViolation)

    def test_exception_message(self):
        """Exceptions carry user-friendly messages."""
        err = InvoiceLockedError("Cannot edit: invoice already sent to SDI")
        assert "SDI" in str(err)

    def test_exceptions_are_catchable(self):
        """Catching DjafattError catches all project exceptions."""
        with pytest.raises(DjafattError):
            raise InvoiceLockedError("locked")

        with pytest.raises(DjafattError):
            raise XmlSecurityError("XXE detected")

        with pytest.raises(DjafattError):
            raise SdiClientError("timeout")
