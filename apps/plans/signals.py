"""Signals for the plans app.

Handles auto-updating of achievement status and default CIDS metadata.
"""
import logging

from django.db.models.signals import post_init, post_save
from django.dispatch import receiver

from .cids import apply_metric_cids_defaults, apply_target_cids_defaults

logger = logging.getLogger(__name__)


@receiver(post_init, sender="plans.PlanTarget")
def cache_plan_target_status(sender, instance, **kwargs):
    """Cache the status value right after the instance is loaded from the DB.

    This lets the post_save signal detect whether status actually changed.
    """
    instance.__original_status = instance.status


@receiver(post_save, sender="plans.PlanTarget")
def sync_achievement_on_status_change(sender, instance, created, **kwargs):
    """When a PlanTarget's status changes, update linked metric records.

    - completed  → mark achievement_status as "achieved" (worker_assessed)
    - deactivated → mark achievement_status as "not_achieved" (worker_assessed)

    Only fires when status genuinely changes — does not update on creation
    or on saves that leave status unchanged.

    MetricValues themselves are historical note records and are not modified.
    The achievement_status field on PlanTarget is the aggregate "metric" that
    reflects the final outcome of the goal.
    """
    from django.utils import timezone

    if created:
        # No prior status to compare against; nothing to propagate.
        return

    original = getattr(instance, "__original_status", None)
    if original == instance.status:
        # Status did not change — nothing to do.
        return

    new_status = instance.status

    if new_status == "completed":
        _set_achievement_status(instance, "achieved", timezone.now())
    elif new_status == "deactivated":
        _set_achievement_status(instance, "not_achieved", timezone.now())
    # "default" (re-activation) — leave achievement_status alone; it will
    # be recalculated the next time a ProgressNoteTarget is saved.

    # Update the cached original so repeated saves in the same request
    # don't re-fire unnecessarily.
    instance.__original_status = instance.status


def _set_achievement_status(plan_target, status, now):
    """Write achievement_status directly to the database via QuerySet.update().

    Uses QuerySet.update() instead of model.save() to avoid re-triggering the
    post_save signal (which would cause infinite recursion).

    Always marks source as 'worker_assessed' because this change is driven by
    a deliberate worker action (changing the goal's lifecycle status), not by
    computed metric trends.

    Sets first_achieved_at when status is 'achieved' for the first time — in
    line with the same rule in apps/plans/achievement.py.
    """
    from apps.plans.models import PlanTarget

    update_kwargs = {
        "achievement_status": status,
        "achievement_status_source": "worker_assessed",
        "achievement_status_updated_at": now,
    }

    if status == "achieved" and not plan_target.first_achieved_at:
        update_kwargs["first_achieved_at"] = now

    try:
        PlanTarget.objects.filter(pk=plan_target.pk).update(**update_kwargs)
        # Keep the in-memory instance consistent so callers don't see stale data.
        for field, value in update_kwargs.items():
            setattr(plan_target, field, value)
    except Exception:
        logger.exception(
            "Failed to update achievement_status for PlanTarget %s",
            plan_target.pk,
        )


@receiver(post_save, sender="plans.PlanTarget")
def ensure_plan_target_cids_defaults(sender, instance, **kwargs):
    """Assign a local outcome URI when one was not provided explicitly."""
    changed_fields = apply_target_cids_defaults(instance)
    if changed_fields:
        sender.objects.filter(pk=instance.pk).update(
            **{field: getattr(instance, field) for field in changed_fields}
        )


@receiver(post_save, sender="plans.MetricDefinition")
def ensure_metric_cids_defaults(sender, instance, **kwargs):
    """Assign stable local metric metadata without requiring IRIS+ mappings."""
    changed_fields = apply_metric_cids_defaults(instance)
    if changed_fields:
        sender.objects.filter(pk=instance.pk).update(
            **{field: getattr(instance, field) for field in changed_fields}
        )
