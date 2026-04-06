"""SDI audit log model (T26).

Immutable append-only log for every SDI interaction:
sends, status changes, webhook events, errors.
"""

from django.conf import settings
from django.db import models


class SdiLogEvent(models.TextChoices):
    """Events tracked in the audit log."""

    SEND_QUEUED = "send_queued", "Invio accodato"
    SEND_SUCCESS = "send_success", "Invio riuscito"
    SEND_FAILED = "send_failed", "Invio fallito"
    PA_SKIPPED = "pa_skipped", "PA: firma richiesta"
    STATUS_CHANGED = "status_changed", "Stato aggiornato"
    WEBHOOK_RECEIVED = "webhook_received", "Webhook ricevuto"
    WEBHOOK_REJECTED = "webhook_rejected", "Webhook rifiutato"


class SdiLog(models.Model):
    """Immutable audit trail for SDI operations.

    Never updated — only inserted. One row per event.
    """

    invoice = models.ForeignKey(
        "invoices.Invoice",
        on_delete=models.CASCADE,
        related_name="sdi_logs",
        null=True,
        blank=True,
    )
    event = models.CharField(max_length=30, choices=SdiLogEvent.choices)
    sdi_uuid = models.CharField(max_length=100, blank=True, default="")
    old_status = models.CharField(max_length=30, blank=True, default="")
    new_status = models.CharField(max_length=30, blank=True, default="")
    payload = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True, default="")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["invoice", "-created_at"]),
            models.Index(fields=["event", "-created_at"]),
        ]
        verbose_name = "SDI Log"
        verbose_name_plural = "SDI Logs"

    def __str__(self):
        return f"{self.get_event_display()} — {self.created_at:%Y-%m-%d %H:%M}"
