"""Structured logging utilities with sensitive data redaction."""
import logging
import re

# Fields to redact in log output
SENSITIVE_PATTERNS = re.compile(
    r"(token|password|secret|iban|authorization|x-csrftoken|api_key)"
    r"\s*[:=]\s*\S+",
    re.IGNORECASE,
)

REDACTED = "[REDACTED]"


class RedactingFilter(logging.Filter):
    """Log filter that redacts sensitive data from log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = SENSITIVE_PATTERNS.sub(
                lambda m: m.group().split("=")[0] + "=" + REDACTED
                if "=" in m.group()
                else m.group().split(":")[0] + ": " + REDACTED,
                record.msg,
            )
        return True


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the redacting filter applied."""
    logger = logging.getLogger(name)
    logger.addFilter(RedactingFilter())
    return logger
