"""Signals for the notes app.

Triggers achievement status recomputation when progress data is recorded.
"""
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender="notes.ProgressNoteTarget")
def recompute_achievement_on_target_entry(sender, instance, **kwargs):
    """Recompute achievement status when a ProgressNoteTarget is saved."""
    from apps.plans.achievement import update_achievement_status

    if instance.plan_target_id:
        try:
            update_achievement_status(instance.plan_target)
        except Exception:
            logger.exception(
                "Failed to update achievement status for PlanTarget %s",
                instance.plan_target_id,
            )


@receiver(post_save, sender="notes.MetricValue")
def recompute_achievement_on_metric_value(sender, instance, **kwargs):
    """Recompute achievement status when a MetricValue is saved."""
    from apps.plans.achievement import update_achievement_status

    pnt = instance.progress_note_target
    if pnt and pnt.plan_target_id:
        try:
            update_achievement_status(pnt.plan_target)
        except Exception:
            logger.exception(
                "Failed to update achievement status for PlanTarget %s",
                pnt.plan_target_id,
            )
