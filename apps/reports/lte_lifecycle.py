"""Lifecycle helpers for Longitudinal Trajectory Export (LTE) requests.

The LTE review-and-cancel window is a 5-business-day pause between
submission and download-link activation. During the window any agency
admin can cancel the request, flag concerns, or let it elapse. When it
elapses without intervention, the request transitions to "active" and
a SecureExportLink is generated from the prepared file.

See tasks/design-rationale/evaluation-microdata-export.md, "Review and
Cancel Window" for the full design.

Lifecycle evaluation strategy: **view-time + management command**. Each
time an LTE list/detail view renders, `refresh_pending_requests()` is
called to transition any request whose window has elapsed. A daily
management command (`check_lte_window_lifecycle`) handles the cases
where no admin hits the list view for >5 business days (e.g., a quiet
weekend or holiday run).
"""

from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta
from typing import Iterable

from django.conf import settings
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Business day arithmetic
# ---------------------------------------------------------------------------

LTE_WINDOW_BUSINESS_DAYS_DEFAULT = 5
LTE_DESTRUCTION_WINDOW_DEFAULT = 90


def _get_excluded_holidays() -> set[date]:
    """Return the configured holiday set (empty by default in v1)."""
    holidays = getattr(settings, "LTE_EXCLUDED_HOLIDAYS", [])
    out: set[date] = set()
    for h in holidays:
        if isinstance(h, date):
            out.add(h)
        elif isinstance(h, str):
            try:
                out.add(date.fromisoformat(h))
            except ValueError:
                logger.warning("LTE: invalid LTE_EXCLUDED_HOLIDAYS entry: %r", h)
    return out


def add_business_days(
    start: datetime,
    business_days: int = LTE_WINDOW_BUSINESS_DAYS_DEFAULT,
) -> datetime:
    """Return the datetime `business_days` business days after `start`.

    A business day is Monday–Friday in the agency's configured timezone,
    excluding any configured holidays (settings.LTE_EXCLUDED_HOLIDAYS).
    The returned datetime preserves the time-of-day of `start` and
    lands on a business day.

    Examples (empty holiday list):
      - Monday 09:00 + 5 business days → Monday 09:00 (next week)
      - Friday 09:00 + 5 business days → Friday 09:00 (next week)
      - Saturday 09:00 + 5 business days → Friday 09:00 (next week)
    """
    if business_days <= 0:
        return start

    holidays = _get_excluded_holidays()
    current = start
    # If start falls on a weekend/holiday, advance to the next business
    # day first, so "5 business days from Saturday" means "Friday".
    while current.weekday() >= 5 or current.date() in holidays:
        current = current + timedelta(days=1)

    added = 0
    while added < business_days:
        current = current + timedelta(days=1)
        if current.weekday() < 5 and current.date() not in holidays:
            added += 1
    return current


def calculate_window_end(
    submitted_at: datetime,
    business_days: int = LTE_WINDOW_BUSINESS_DAYS_DEFAULT,
) -> datetime:
    """Return the datetime at which the review-and-cancel window ends
    (i.e. the download link activates) if no flags or cancellations
    intervene. Wraps add_business_days with a descriptive name.
    """
    return add_business_days(submitted_at, business_days)


# ---------------------------------------------------------------------------
# State transitions
# ---------------------------------------------------------------------------

def activate_window_if_elapsed(request, *, actor=None) -> bool:
    """If the window has elapsed and status is 'submitted', activate it.

    Returns True if the request was activated, False otherwise.
    Generates the SecureExportLink by re-running the LTE pipeline
    against the submission-time snapshot (minus any withdrawals).
    """
    from apps.reports.models import LTELifecycleEvent, LTEExportRequest

    if request.status != LTEExportRequest.STATUS_SUBMITTED:
        return False

    now = timezone.now()
    if now < request.effective_window_activates_at:
        return False

    # Re-run the pipeline against the current consent state, restricted
    # to the submission-time client_ids. This is where withdrawal-
    # during-window drops rows from the file — the pipeline's consent
    # filter will skip withdrawn participants.
    from apps.reports.lte_pipeline import LTESmallPopulationPipeline

    evaluator_info = _evaluator_info_from_request(request)

    pipeline = LTESmallPopulationPipeline(
        program=request.program,
        period_start=request.period_start,
        period_end=request.period_end,
        evaluator_info=evaluator_info,
        user=request.submitted_by,
        restrict_to_client_ids=list(request.population_client_ids or []),
    )

    try:
        result = pipeline.run_generate()
    except ValueError as exc:
        # Population dropped below floor during the window → auto-cancel
        logger.warning(
            "LTE #%s: auto-cancelling at activation — %s",
            request.pk, exc,
        )
        auto_cancel_for_floor_drop(request)
        return False

    # Persist the CSV via the standard secure link helper. We need a
    # mock request-like object to reuse _save_export_and_create_link —
    # but the management command path has no HttpRequest, so instead
    # we create the SecureExportLink directly here.
    from apps.reports.models import SecureExportLink

    link = _create_lte_secure_link(
        request=request,
        csv_content=result.csv_content,
        filename=result.filename,
        population_count=result.preview.exportable_count,
    )

    with transaction.atomic():
        LTEExportRequest.objects.filter(pk=request.pk).update(
            status=LTEExportRequest.STATUS_ACTIVE,
            secure_export_link=link,
            linkage_blob_encrypted=result.linkage_blob,
        )
        LTELifecycleEvent.objects.create(
            request=request,
            actor=actor,
            event_type="window_activated",
            notes=(
                f"Window elapsed — download link active. "
                f"Exported {result.preview.exportable_count} rows."
            ),
        )
    request.refresh_from_db()

    _write_audit_entry(
        request,
        action="export",
        event_type="window_activated",
        metadata={
            "lte_request_id": request.pk,
            "population_count": result.preview.exportable_count,
            "secure_export_link_id": str(link.pk),
        },
    )

    logger.info(
        "LTE #%s activated — %d rows exported",
        request.pk, result.preview.exportable_count,
    )
    return True


def auto_cancel_for_floor_drop(request) -> None:
    """Transition a request to auto_cancelled because the population
    dropped below the LTE floor during the review-and-cancel window.
    """
    from apps.reports.models import LTELifecycleEvent, LTEExportRequest

    with transaction.atomic():
        LTEExportRequest.objects.filter(pk=request.pk).update(
            status=LTEExportRequest.STATUS_AUTO_CANCELLED,
            cancelled_at=timezone.now(),
            cancellation_reason="Population dropped below LTE floor",
            linkage_blob_encrypted=b"",
        )
        LTELifecycleEvent.objects.create(
            request=request,
            event_type="auto_cancelled",
            notes="Population dropped below the LTE floor during the review window.",
        )
    request.refresh_from_db()
    _write_audit_entry(
        request,
        action="cancel",
        event_type="auto_cancelled",
        metadata={"lte_request_id": request.pk, "reason": "floor_drop"},
    )


def invalidate_for_withdrawal(request) -> None:
    """Mark a request invalidated because a participant withdrew consent.

    The DRR requires that the pipeline be re-run after withdrawal so the
    withdrawn participant never appears in the final file. The simplest
    implementation is to mark the in-progress request invalidated and
    force the user to re-submit; that matches the DRR's "starts a fresh
    review-and-cancel window" rule.
    """
    from apps.reports.models import LTELifecycleEvent, LTEExportRequest

    if request.is_terminal:
        return

    with transaction.atomic():
        LTEExportRequest.objects.filter(pk=request.pk).update(
            status=LTEExportRequest.STATUS_INVALIDATED_BY_WITHDRAWAL,
            cancelled_at=timezone.now(),
            cancellation_reason=(
                "Participant withdrew consent — request invalidated."
            ),
            linkage_blob_encrypted=b"",
        )
        LTELifecycleEvent.objects.create(
            request=request,
            event_type="withdrawal_invalidation",
            notes=(
                "A participant withdrew consent during the review-and-cancel "
                "window. The prepared file is discarded and the submitter "
                "must re-submit."
            ),
        )
    request.refresh_from_db()
    _write_audit_entry(
        request,
        action="cancel",
        event_type="invalidated_by_withdrawal",
        metadata={"lte_request_id": request.pk},
    )


def check_population_snapshot_for_lte(request) -> None:
    """Re-run the consent check for an in-window request and detect
    withdrawals or floor drops.

    Intended to be called:
      - From the daily management command
      - From a withdrawal signal (if one is wired up later)
      - From view-time refresh of the LTE list
    """
    from apps.clients.models import ServiceEpisode
    from apps.reports.models import LTEExportRequest

    if not request.is_window_running and request.status != LTEExportRequest.STATUS_ACTIVE:
        return

    snapshot_ids = set(request.population_client_ids or [])
    if not snapshot_ids:
        return

    # Which of the snapshotted clients still have aggregate reporting
    # consent on an active/finished episode? (The pipeline uses the
    # same filter.)
    still_consenting = set(
        ServiceEpisode.objects.filter(
            client_file_id__in=snapshot_ids,
            program=request.program,
            status__in=["active", "on_hold", "finished"],
            consent_to_aggregate_reporting=True,
        ).values_list("client_file_id", flat=True)
    )
    withdrawn = snapshot_ids - still_consenting
    if not withdrawn:
        return

    # Apply the applicable floor
    from apps.reports.lte_pipeline import (
        LTE_FLOOR_DEFAULT,
        LTE_FLOOR_OCAP_EGAP,
    )

    framework = (request.program.community_governance_framework or "").lower()
    floor = LTE_FLOOR_OCAP_EGAP if framework in ("ocap", "egap") else LTE_FLOOR_DEFAULT

    remaining = len(still_consenting)
    if remaining < floor:
        auto_cancel_for_floor_drop(request)
    else:
        invalidate_for_withdrawal(request)


def refresh_pending_requests(
    *, requests: Iterable | None = None,
) -> int:
    """Evaluate pending requests and trigger any state transitions.

    Called from the LTE list view and the management command. Returns
    the number of requests whose state changed.
    """
    from apps.reports.models import LTEExportRequest

    if requests is None:
        requests = LTEExportRequest.objects.filter(
            status__in=[
                LTEExportRequest.STATUS_SUBMITTED,
                LTEExportRequest.STATUS_ACTIVE,
            ],
        )
    else:
        requests = list(requests)  # allow re-iteration

    changed = 0
    for req in requests:
        # Check for withdrawals / floor drops first — withdrawal
        # invalidation short-circuits activation.
        check_population_snapshot_for_lte(req)
        req.refresh_from_db()
        if req.status == LTEExportRequest.STATUS_SUBMITTED:
            if activate_window_if_elapsed(req):
                changed += 1
        elif req.status == LTEExportRequest.STATUS_ACTIVE:
            # Once active, expire the request if the 24-hour download
            # window has elapsed without a download.
            if req.secure_export_link and not req.secure_export_link.is_valid():
                _expire_request(req)
                changed += 1
    return changed


# ---------------------------------------------------------------------------
# Flag handling — freeze the countdown, resume on dismissal
# ---------------------------------------------------------------------------

def start_flag_hold(request, *, actor=None, reason: str = "") -> None:
    """Freeze the review-and-cancel countdown by recording a flag.

    The remaining window duration is preserved — on resume, we add the
    elapsed hold time to flag_hold_seconds so the computed
    effective_window_activates_at shifts forward by that amount.
    """
    from apps.reports.models import LTEExportRequest, LTELifecycleEvent

    if request.status not in (
        LTEExportRequest.STATUS_SUBMITTED,
        LTEExportRequest.STATUS_FLAGGED,
    ):
        return
    if request.status == LTEExportRequest.STATUS_FLAGGED:
        return  # already frozen

    now = timezone.now()
    with transaction.atomic():
        LTEExportRequest.objects.filter(pk=request.pk).update(
            status=LTEExportRequest.STATUS_FLAGGED,
            flag_hold_started_at=now,
        )
        LTELifecycleEvent.objects.create(
            request=request,
            actor=actor,
            event_type="flagged",
            notes=reason or "Flagged for privacy officer review.",
        )
    request.refresh_from_db()
    _write_audit_entry(
        request,
        action="update",
        event_type="flagged",
        metadata={"lte_request_id": request.pk, "reason": reason},
    )


def resolve_flag(request, *, actor=None, dismissed: bool, notes: str = "") -> None:
    """Resolve a flag — either dismiss it (resume countdown) or cancel
    the request. On dismissal, the elapsed hold time is added to
    flag_hold_seconds so the window resumes from where it was frozen
    (no fast-forwarding).
    """
    from apps.reports.models import LTEExportRequest, LTELifecycleEvent

    if request.status != LTEExportRequest.STATUS_FLAGGED:
        return

    now = timezone.now()
    hold_duration = 0
    if request.flag_hold_started_at:
        hold_duration = max(
            0,
            int((now - request.flag_hold_started_at).total_seconds()),
        )

    if dismissed:
        with transaction.atomic():
            LTEExportRequest.objects.filter(pk=request.pk).update(
                status=LTEExportRequest.STATUS_SUBMITTED,
                flag_hold_started_at=None,
                flag_hold_seconds=request.flag_hold_seconds + hold_duration,
            )
            LTELifecycleEvent.objects.create(
                request=request,
                actor=actor,
                event_type="flag_resolved",
                notes=notes or "Flag dismissed — countdown resumed.",
            )
        _write_audit_entry(
            request,
            action="update",
            event_type="flag_resolved_dismissed",
            metadata={
                "lte_request_id": request.pk,
                "hold_seconds_added": hold_duration,
                "notes": notes,
            },
        )
    else:
        # Resolution = cancellation
        cancel_request(request, actor=actor, reason=notes or "Flag resolved as cancellation.")


def cancel_request(request, *, actor, reason: str) -> None:
    """Cancel an LTE request. Allowed during the window or after
    activation (before download).
    """
    from apps.reports.models import LTEExportRequest, LTELifecycleEvent

    if request.is_terminal:
        return

    with transaction.atomic():
        LTEExportRequest.objects.filter(pk=request.pk).update(
            status=LTEExportRequest.STATUS_CANCELLED,
            cancelled_at=timezone.now(),
            cancelled_by=actor,
            cancellation_reason=reason[:500],
            linkage_blob_encrypted=b"",
        )
        LTELifecycleEvent.objects.create(
            request=request,
            actor=actor,
            event_type="cancelled",
            notes=reason,
        )
    request.refresh_from_db()
    _write_audit_entry(
        request,
        action="cancel",
        event_type="cancelled",
        metadata={
            "lte_request_id": request.pk,
            "cancelled_by_id": actor.pk if actor else None,
            "reason": reason,
        },
    )


def mark_downloaded(request, *, actor) -> None:
    """Transition an active request to downloaded."""
    from apps.reports.models import LTEExportRequest, LTELifecycleEvent

    if request.status != LTEExportRequest.STATUS_ACTIVE:
        return

    with transaction.atomic():
        LTEExportRequest.objects.filter(pk=request.pk).update(
            status=LTEExportRequest.STATUS_DOWNLOADED,
        )
        LTELifecycleEvent.objects.create(
            request=request,
            actor=actor,
            event_type="downloaded",
            notes="File downloaded.",
        )
    _write_audit_entry(
        request,
        action="export",
        event_type="downloaded",
        metadata={
            "lte_request_id": request.pk,
            "downloaded_by_id": actor.pk if actor else None,
        },
    )


def _expire_request(request) -> None:
    """Transition an expired-without-download request."""
    from apps.reports.models import LTEExportRequest, LTELifecycleEvent

    with transaction.atomic():
        LTEExportRequest.objects.filter(pk=request.pk).update(
            status=LTEExportRequest.STATUS_EXPIRED,
            linkage_blob_encrypted=b"",
        )
        LTELifecycleEvent.objects.create(
            request=request,
            event_type="expired",
            notes="Download window lapsed without a download.",
        )
    _write_audit_entry(
        request,
        action="update",
        event_type="expired",
        metadata={"lte_request_id": request.pk},
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _evaluator_info_from_request(request) -> dict:
    """Reconstruct an evaluator_info dict from a persisted LTEExportRequest.

    Used when re-running the pipeline at window-activation time.
    """
    return {
        "name": request.evaluator_name,
        "email": request.evaluator_email,
        "organisation": request.evaluator_organisation,
        "degree": request.evaluator_degree,
        "years_experience": request.evaluator_years_experience,
        "prior_programs": request.evaluator_prior_programs,
        "purpose": request.purpose_statement,
        "reb_name": request.reb_name,
        "reb_approval_number": request.reb_approval_number,
        "reb_approval_date": request.reb_approval_date,
        "agreement_expiry": request.data_sharing_agreement_expiry,
        "destruction_window_days": request.destruction_window_days,
        "community_reviewer_name": request.community_reviewer_name,
        "community_reviewer_affiliation": request.community_reviewer_affiliation,
        "community_framework_description": request.community_framework_description,
        "community_signoff_date": request.community_signoff_date,
    }


def _create_lte_secure_link(
    request, csv_content: str, filename: str, population_count: int,
):
    """Create a SecureExportLink carrying the LTE file.

    Unlike the EME path (which goes through _save_export_and_create_link
    and requires an HttpRequest), we may be called from a management
    command, so we write the file + create the link manually.
    """
    import json
    import os
    import uuid
    from datetime import timedelta

    from apps.reports.models import SecureExportLink

    export_dir = settings.SECURE_EXPORT_DIR
    os.makedirs(export_dir, exist_ok=True)

    link_id = uuid.uuid4()
    safe_filename = f"{link_id}_{filename}"
    file_path = os.path.join(export_dir, safe_filename)
    with open(file_path, "w", encoding="utf-8-sig") as f:
        f.write(csv_content)

    expiry_hours = getattr(settings, "SECURE_EXPORT_LINK_EXPIRY_HOURS", 24)

    return SecureExportLink.objects.create(
        id=link_id,
        created_by=request.submitted_by,
        expires_at=timezone.now() + timedelta(hours=expiry_hours),
        export_type="longitudinal_trajectory_export",
        filters_json=json.dumps({
            "lte_request_id": request.pk,
            "program_id": request.program_id,
            "period_start": str(request.period_start),
            "period_end": str(request.period_end),
        }),
        client_count=population_count,
        includes_notes=False,
        contains_pii=False,  # LTE has no direct identifiers
        recipient=(
            f"{request.evaluator_name} ({request.evaluator_email}), "
            f"{request.evaluator_organisation}"
        ),
        filename=filename,
        file_path=file_path,
        is_elevated=False,  # review-and-cancel window already provides the delay
    )


def _write_audit_entry(
    request, *, action: str, event_type: str, metadata: dict,
) -> None:
    """Append an LTE lifecycle entry to the audit DB.

    The export_category is always longitudinal_trajectory_export so
    LTE lifecycle events are filterable independently of EME events.
    """
    from apps.audit.models import AuditLog

    full_metadata = {
        "export_category": "longitudinal_trajectory_export",
        "lte_event_type": event_type,
        **metadata,
    }
    try:
        AuditLog.objects.using("audit").create(
            event_timestamp=timezone.now(),
            user_id=None,
            user_display="",
            ip_address=None,
            action=action,
            resource_type="export",
            resource_id=request.pk,
            program_id=request.program_id,
            metadata=full_metadata,
        )
    except Exception:
        logger.exception(
            "LTE: failed to write audit entry for request %s event %s",
            request.pk, event_type,
        )
