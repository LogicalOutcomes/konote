"""Survey trigger rule evaluation engine.

Evaluates active trigger rules against a specific participant and
creates SurveyAssignment records when rules match. Called on:
- Portal dashboard load (time + characteristic rules)
- Staff client view load (time + characteristic rules)
- Event creation via signal (event rules)
- Enrolment creation via signal (enrolment rules)
"""
import logging
from datetime import timedelta

from django.db import IntegrityError
from django.utils import timezone

from apps.surveys.models import (
    SurveyAssignment,
    SurveyTriggerRule,
)

logger = logging.getLogger(__name__)

MAX_PENDING_SURVEYS = 5


def evaluate_survey_rules(client_file, participant_user=None):
    """Evaluate all active trigger rules for a participant.

    Args:
        client_file: The ClientFile to evaluate rules for.
        participant_user: The ParticipantUser (optional — may be None
            if participant has no portal account).

    Returns:
        List of newly created SurveyAssignment instances.
    """
    if client_file.status == "discharged":
        return []

    if participant_user is None:
        return []

    if not participant_user.is_active:
        return []

    # Check overload
    pending_count = SurveyAssignment.objects.filter(
        participant_user=participant_user,
        status__in=["pending", "in_progress", "awaiting_approval"],
    ).count()
    if pending_count >= MAX_PENDING_SURVEYS:
        logger.info(
            "Skipping rule evaluation for %s — %d pending surveys (limit: %d)",
            participant_user, pending_count, MAX_PENDING_SURVEYS,
        )
        return []

    # Get active rules for active surveys only
    # Filter to time and characteristic rules (event/enrolment handled by signals)
    rules = SurveyTriggerRule.objects.filter(
        is_active=True,
        survey__status="active",
        trigger_type__in=["time", "characteristic"],
    ).select_related("survey", "program", "event_type")

    new_assignments = []
    for rule in rules:
        assignment = _evaluate_single_rule(rule, client_file, participant_user)
        if assignment:
            new_assignments.append(assignment)
            # Re-check overload after each assignment
            if pending_count + len(new_assignments) >= MAX_PENDING_SURVEYS:
                break

    return new_assignments


def evaluate_event_rules(client_file, participant_user, event):
    """Evaluate event-type trigger rules after an event is created.

    Args:
        client_file: The participant's ClientFile.
        participant_user: The ParticipantUser (may be None).
        event: The newly created Event instance.

    Returns:
        List of newly created SurveyAssignment instances.
    """
    if client_file.status == "discharged":
        return []
    if participant_user is None:
        return []
    if not participant_user.is_active:
        return []
    if not event.event_type:
        return []

    rules = SurveyTriggerRule.objects.filter(
        is_active=True,
        survey__status="active",
        trigger_type="event",
        event_type=event.event_type,
    ).select_related("survey")

    new_assignments = []
    for rule in rules:
        assignment = _evaluate_single_rule(rule, client_file, participant_user)
        if assignment:
            new_assignments.append(assignment)

    return new_assignments


def evaluate_enrolment_rules(client_file, participant_user, enrolment):
    """Evaluate enrolment-type trigger rules after a program enrolment.

    Args:
        client_file: The participant's ClientFile.
        participant_user: The ParticipantUser (may be None).
        enrolment: The newly created ClientProgramEnrolment instance.

    Returns:
        List of newly created SurveyAssignment instances.
    """
    if client_file.status == "discharged":
        return []
    if participant_user is None:
        return []
    if not participant_user.is_active:
        return []

    rules = SurveyTriggerRule.objects.filter(
        is_active=True,
        survey__status="active",
        trigger_type="enrolment",
        program=enrolment.program,
    ).select_related("survey")

    new_assignments = []
    for rule in rules:
        assignment = _evaluate_single_rule(rule, client_file, participant_user)
        if assignment:
            new_assignments.append(assignment)

    return new_assignments


def _evaluate_single_rule(rule, client_file, participant_user):
    """Check if a single rule matches and create assignment if so.

    Returns:
        SurveyAssignment if created, None otherwise.
    """
    # Check program membership for rules that require it
    if rule.program:
        from apps.clients.models import ClientProgramEnrolment

        is_enrolled = ClientProgramEnrolment.objects.filter(
            client_file=client_file,
            program=rule.program,
            status="enrolled",
        ).exists()
        if not is_enrolled:
            return None

    # Check repeat policy
    if not _repeat_policy_allows(rule, participant_user, client_file):
        return None

    # For time-based rules, check if enough time has elapsed
    if rule.trigger_type == "time":
        if not _time_elapsed(rule, client_file, participant_user):
            return None

    # Create assignment
    status = "pending" if rule.auto_assign else "awaiting_approval"
    due_date = None
    if rule.due_days:
        due_date = (timezone.now() + timedelta(days=rule.due_days)).date()

    try:
        assignment, created = SurveyAssignment.objects.get_or_create(
            survey=rule.survey,
            participant_user=participant_user,
            status__in=["pending", "in_progress", "awaiting_approval"],
            defaults={
                "client_file": client_file,
                "status": status,
                "triggered_by_rule": rule,
                "trigger_reason": str(rule),
                "due_date": due_date,
            },
        )
        if created:
            return assignment
    except (IntegrityError, SurveyAssignment.MultipleObjectsReturned):
        pass

    return None


def _repeat_policy_allows(rule, participant_user, client_file):
    """Check if the repeat policy allows a new assignment."""
    existing = SurveyAssignment.objects.filter(
        survey=rule.survey,
        participant_user=participant_user,
    )

    if rule.repeat_policy == "once_per_participant":
        return not existing.exists()

    elif rule.repeat_policy == "once_per_enrolment":
        if rule.program:
            from apps.clients.models import ClientProgramEnrolment

            enrolment = ClientProgramEnrolment.objects.filter(
                client_file=client_file,
                program=rule.program,
                status="enrolled",
            ).order_by("-enrolled_at").first()
            if enrolment:
                return not existing.filter(
                    created_at__gte=enrolment.enrolled_at,
                ).exists()
        return not existing.exists()

    elif rule.repeat_policy == "recurring":
        # Don't stack: no new assignment if one is already pending/in_progress
        return not existing.filter(
            status__in=["pending", "in_progress", "awaiting_approval"],
        ).exists()

    return False


def _time_elapsed(rule, client_file, participant_user):
    """Check if enough time has elapsed for a time-based trigger."""
    if not rule.recurrence_days:
        return False

    anchor_date = None

    if rule.anchor == "enrolment_date" and rule.program:
        from apps.clients.models import ClientProgramEnrolment

        enrolment = ClientProgramEnrolment.objects.filter(
            client_file=client_file,
            program=rule.program,
            status="enrolled",
        ).order_by("-enrolled_at").first()
        if enrolment:
            anchor_date = enrolment.enrolled_at

    elif rule.anchor == "last_completed":
        last_completed = SurveyAssignment.objects.filter(
            survey=rule.survey,
            participant_user=participant_user,
            status="completed",
        ).order_by("-completed_at").first()
        if last_completed and last_completed.completed_at:
            anchor_date = last_completed.completed_at
        else:
            # No previous completion — fall back to enrolment date
            if rule.program:
                from apps.clients.models import ClientProgramEnrolment

                enrolment = ClientProgramEnrolment.objects.filter(
                    client_file=client_file,
                    program=rule.program,
                    status="enrolled",
                ).order_by("-enrolled_at").first()
                if enrolment:
                    anchor_date = enrolment.enrolled_at

    if anchor_date is None:
        return False

    elapsed = timezone.now() - anchor_date
    return elapsed >= timedelta(days=rule.recurrence_days)
