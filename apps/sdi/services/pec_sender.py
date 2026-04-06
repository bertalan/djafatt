"""Send FatturaPA XML to SDI via PEC (Aruba/generic SMTPS).

The XML is attached to a plain-text PEC email sent to the SDI
mailbox (default: sdi01@pec.fatturapa.it).

File naming follows SDI convention:
  IT{partita_iva}_{progressivo}.xml
"""
import logging
import smtplib
from email.message import EmailMessage

from django.conf import settings

from apps.common.exceptions import SdiClientError

logger = logging.getLogger(__name__)


class PecSdiSender:
    """Send FatturaPA invoices to SDI via PEC."""

    def __init__(self):
        self.host = settings.PEC_EMAIL_HOST
        self.user = settings.PEC_EMAIL_HOST_USER
        self.password = settings.PEC_EMAIL_HOST_PASSWORD
        self.port = settings.PEC_EMAIL_PORT
        self.use_ssl = settings.PEC_EMAIL_USE_SSL
        self.dest = settings.SDI_PEC_DEST

        if not all([self.host, self.user, self.password]):
            raise SdiClientError(
                "PEC credentials not configured "
                "(PEC_EMAIL_HOST, PEC_EMAIL_HOST_USER, PEC_EMAIL_HOST_PASSWORD)"
            )

    def send_invoice(self, xml_content: str, filename: str) -> dict:
        """Send a single FatturaPA XML to SDI via PEC.

        Args:
            xml_content: The FatturaPA XML string.
            filename: SDI-compliant filename, e.g. IT02743630069_00001.xml

        Returns:
            dict with keys: message_id, filename
        """
        msg = self._build_message(xml_content, filename)

        try:
            if self.use_ssl:
                with smtplib.SMTP_SSL(self.host, self.port, timeout=30) as smtp:
                    smtp.login(self.user, self.password)
                    smtp.send_message(msg)
            else:
                with smtplib.SMTP(self.host, self.port, timeout=30) as smtp:
                    smtp.starttls()
                    smtp.login(self.user, self.password)
                    smtp.send_message(msg)
        except smtplib.SMTPException as exc:
            logger.error("PEC send failed for %s: %s", filename, exc)
            raise SdiClientError(f"PEC send failed: {exc}") from exc

        message_id = msg["Message-ID"] or ""
        logger.info(
            "Invoice sent via PEC: %s → %s (Message-ID: %s)",
            filename,
            self.dest,
            message_id,
        )
        return {"message_id": message_id, "filename": filename}

    def _build_message(self, xml_content: str, filename: str) -> EmailMessage:
        """Build the PEC email with XML attachment."""
        msg = EmailMessage()
        msg["From"] = self.user
        msg["To"] = self.dest
        msg["Subject"] = filename
        msg.set_content(
            f"Trasmissione fattura elettronica: {filename}"
        )
        msg.add_attachment(
            xml_content.encode("utf-8"),
            maintype="application",
            subtype="xml",
            filename=filename,
        )
        return msg

    @staticmethod
    def build_filename(vat_number: str, progressive: int) -> str:
        """Build SDI-compliant filename: IT{vat}_{progressive:05d}.xml"""
        return f"IT{vat_number}_{progressive:05d}.xml"
