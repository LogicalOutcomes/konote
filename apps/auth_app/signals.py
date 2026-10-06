"""Signals for auth_app — keeps denormalised caches in sync with truth models."""
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import EvaluationExportGrant, LTEExportGrant, User


@receiver(post_save, sender=EvaluationExportGrant)
def sync_user_eval_export_flag(sender, instance, **kwargs):
    """Keep User.evaluation_export_granted in sync with active grants.

    The boolean on User is a hot-path cache — the permission helper and
    template tag both read it as a single attribute lookup on the
    already-loaded user object, which keeps the nav menu and view
    decorators fast. This signal is the only place that writes it.

    We use `.update()` rather than `.save()` to avoid triggering any
    User post_save handlers and to keep the write scoped to one column.
    """
    has_active = EvaluationExportGrant.objects.filter(
        user=instance.user, active=True,
    ).exists()
    # Only write if the cached flag actually differs — avoids unnecessary
    # UPDATE statements when the grant is saved for unrelated reasons.
    if instance.user.evaluation_export_granted != has_active:
        User.objects.filter(pk=instance.user_id).update(
            evaluation_export_granted=has_active,
        )


@receiver(post_save, sender=LTEExportGrant)
def sync_user_lte_export_flag(sender, instance, **kwargs):
    """Keep User.lte_export_granted in sync with active LTE grants.

    Same pattern as sync_user_eval_export_flag. LTE has its own grant
    model because the governance model treats it as a structurally
    separate permission (see tasks/design-rationale/evaluation-microdata-export.md).
    """
    has_active = LTEExportGrant.objects.filter(
        user=instance.user, active=True,
    ).exists()
    if instance.user.lte_export_granted != has_active:
        User.objects.filter(pk=instance.user_id).update(
            lte_export_granted=has_active,
        )
