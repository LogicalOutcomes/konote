"""Portal signals -- automatic lifecycle management.

Handles portal account deactivation when client status changes.
"""
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

logger = logging.getLogger(__name__)


@receiver(post_save, sender="clients.ClientFile")
def deactivate_portal_on_discharge(sender, instance, **kwargs):
    """Deactivate portal account when client is discharged or inactive.

    The PortalAuthMiddleware already checks is_active on every request,
    so setting it to False immediately blocks further portal access.
    """
    if instance.status in ("discharged", "inactive"):
        from apps.portal.models import ParticipantUser

        updated = ParticipantUser.objects.filter(
            client_file=instance, is_active=True,
        ).update(is_active=False)

        if updated:
            logger.info(
                "Portal account deactivated for ClientFile %s (status: %s)",
                instance.pk, instance.status,
            )
            # Audit log
            try:
                from apps.audit.models import AuditLog
                AuditLog.objects.using("audit").create(
                    event_timestamp=timezone.now(),
                    user_id=None,
                    user_display="[system]",
                    action="update",
                    resource_type="portal_account",
                    metadata={
                        "client_file_id": instance.pk,
                        "operation": "auto_deactivated_discharge",
                        "client_status": instance.status,
                    },
                )
            except Exception:
                logger.exception("Failed to write portal deactivation audit log")
