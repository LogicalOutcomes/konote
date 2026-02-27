"""Django signals for survey trigger evaluation.

Listens for Event and ClientProgramEnrolment creation to immediately
evaluate matching trigger rules. Uses transaction.on_commit() to ensure
the triggering record is committed before creating assignments.
"""
import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.clients.models import ClientProgramEnrolment
from apps.events.models import Event

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Event)
def evaluate_event_survey_rules(sender, instance, created, **kwargs):
    """When a new Event is created, check for matching event trigger rules."""
    if not created:
        return
    if not instance.event_type:
        return
    if not instance.client_file:
        return

    def _evaluate():
        from apps.surveys.engine import evaluate_event_rules, is_surveys_enabled

        if not is_surveys_enabled():
            return

        client_file = instance.client_file
        participant_user = getattr(client_file, "portal_account", None)
        if participant_user is None:
            return

        try:
            new_assignments = evaluate_event_rules(
                client_file, participant_user, instance,
            )
            if new_assignments:
                logger.info(
                    "Event %s triggered %d survey assignment(s) for client %s",
                    instance.event_type.name,
                    len(new_assignments),
                    client_file.pk,
                )
        except Exception:
            logger.exception("Error evaluating event survey rules")

    transaction.on_commit(_evaluate)


@receiver(post_save, sender=ClientProgramEnrolment)
def evaluate_enrolment_survey_rules(sender, instance, created, **kwargs):
    """When a new enrolment is created, check for matching enrolment rules."""
    if not created:
        return
    if not instance.client_file:
        return

    def _evaluate():
        from apps.surveys.engine import evaluate_enrolment_rules, is_surveys_enabled

        if not is_surveys_enabled():
            return

        client_file = instance.client_file
        participant_user = getattr(client_file, "portal_account", None)
        if participant_user is None:
            return

        try:
            new_assignments = evaluate_enrolment_rules(
                client_file, participant_user, instance,
            )
            if new_assignments:
                logger.info(
                    "Enrolment in %s triggered %d survey assignment(s) for client %s",
                    instance.program.name,
                    len(new_assignments),
                    client_file.pk,
                )
        except Exception:
            logger.exception("Error evaluating enrolment survey rules")

    transaction.on_commit(_evaluate)
