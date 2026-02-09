"""Outcome Insights data collection — SQL aggregation + quote surfacing.

Two separate functions split by the encryption boundary:

  get_structured_insights()  — SQL aggregation of plaintext fields.
                                No decryption, no ceiling, milliseconds.

  collect_quotes()           — Decrypts text fields for quote surfacing.
                                Capped at max_quotes, privacy-gated.

This split exists because all text fields are Fernet-encrypted and cannot
be queried in SQL. Descriptor and engagement fields are plaintext, so we
aggregate those in the database for speed and unlimited scale.
"""
import logging
from collections import Counter, defaultdict
from datetime import date

from django.conf import settings
from django.db.models import Count, DateTimeField, Q
from django.db.models.functions import Coalesce, TruncMonth

from apps.clients.models import ClientProgramEnrolment
from apps.notes.models import ProgressNote, ProgressNoteTarget

logger = logging.getLogger(__name__)

# Minimum number of active participants for programme-level quote display.
# Below this threshold, individual quotes risk re-identification.
MIN_PARTICIPANTS_FOR_QUOTES = 15


def get_structured_insights(program=None, client_file=None, date_from=None, date_to=None):
    """Aggregate descriptor and engagement data from plaintext fields via SQL.

    No decryption is performed. No ceiling on note volume.

    Args:
        program: Program instance (for programme-level insights).
        client_file: ClientFile instance (for client-level insights).
        date_from: Start date (inclusive).
        date_to: End date (inclusive).

    Returns:
        dict with keys:
          note_count: int
          participant_count: int — distinct clients with notes in range
          month_count: int — distinct months with notes
          descriptor_distribution: dict of {label: percentage}
          engagement_distribution: dict of {label: percentage}
          descriptor_trend: list of {month, harder, holding, shifting, good_place}
                           (all as percentages)
    """
    # Build base note queryset — use effective date (backdate if set, else created_at)
    # so backdated notes appear at their session date, not their entry date.
    notes_qs = ProgressNote.objects.filter(status="default").annotate(
        _effective_date=Coalesce("backdate", "created_at", output_field=DateTimeField()),
    )
    if client_file:
        notes_qs = notes_qs.filter(client_file=client_file)
    if program:
        notes_qs = notes_qs.filter(
            client_file__enrolments__program=program,
            client_file__enrolments__status="enrolled",
        )
    if date_from:
        notes_qs = notes_qs.filter(_effective_date__date__gte=date_from)
    if date_to:
        notes_qs = notes_qs.filter(_effective_date__date__lte=date_to)

    # Basic counts
    note_count = notes_qs.count()
    participant_count = notes_qs.values("client_file_id").distinct().count()

    # Distinct months
    month_dates = (
        notes_qs.annotate(month=TruncMonth("_effective_date"))
        .values("month")
        .distinct()
    )
    month_count = month_dates.count()

    # ── Engagement distribution (from ProgressNote.engagement_observation) ──
    engagement_counts = (
        notes_qs.exclude(engagement_observation="")
        .values("engagement_observation")
        .annotate(count=Count("id"))
    )
    engagement_total = sum(row["count"] for row in engagement_counts)
    engagement_labels = dict(ProgressNote.ENGAGEMENT_CHOICES)
    engagement_distribution = {}
    for row in engagement_counts:
        label = engagement_labels.get(row["engagement_observation"], row["engagement_observation"])
        if label == "---------":
            continue
        pct = round(row["count"] / engagement_total * 100, 1) if engagement_total else 0
        engagement_distribution[label] = pct

    # ── Descriptor distribution (from ProgressNoteTarget.progress_descriptor) ──
    targets_qs = ProgressNoteTarget.objects.filter(
        progress_note__in=notes_qs,
    )
    descriptor_counts = (
        targets_qs.exclude(progress_descriptor="")
        .values("progress_descriptor")
        .annotate(count=Count("id"))
    )
    descriptor_total = sum(row["count"] for row in descriptor_counts)
    descriptor_labels = dict(ProgressNoteTarget.PROGRESS_DESCRIPTOR_CHOICES)
    descriptor_distribution = {}
    for row in descriptor_counts:
        label = descriptor_labels.get(row["progress_descriptor"], row["progress_descriptor"])
        if label == "---------":
            continue
        pct = round(row["count"] / descriptor_total * 100, 1) if descriptor_total else 0
        descriptor_distribution[label] = pct

    # ── Descriptor trend by month (percentages) ──
    descriptor_by_month = (
        targets_qs.exclude(progress_descriptor="")
        .annotate(
            _effective_date=Coalesce(
                "progress_note__backdate", "progress_note__created_at",
                output_field=DateTimeField(),
            ),
        )
        .annotate(month=TruncMonth("_effective_date"))
        .values("month", "progress_descriptor")
        .annotate(count=Count("id"))
        .order_by("month")
    )

    # Build monthly data
    monthly_totals = defaultdict(int)
    monthly_descriptors = defaultdict(lambda: defaultdict(int))
    for row in descriptor_by_month:
        month_str = row["month"].strftime("%Y-%m")
        monthly_totals[month_str] += row["count"]
        monthly_descriptors[month_str][row["progress_descriptor"]] += row["count"]

    descriptor_trend = []
    for month_str in sorted(monthly_totals.keys()):
        total = monthly_totals[month_str]
        counts = monthly_descriptors[month_str]
        descriptor_trend.append({
            "month": month_str,
            "harder": round(counts.get("harder", 0) / total * 100, 1) if total else 0,
            "holding": round(counts.get("holding", 0) / total * 100, 1) if total else 0,
            "shifting": round(counts.get("shifting", 0) / total * 100, 1) if total else 0,
            "good_place": round(counts.get("good_place", 0) / total * 100, 1) if total else 0,
        })

    return {
        "note_count": note_count,
        "participant_count": participant_count,
        "month_count": month_count,
        "descriptor_distribution": descriptor_distribution,
        "engagement_distribution": engagement_distribution,
        "descriptor_trend": descriptor_trend,
    }


def collect_quotes(program=None, client_file=None, date_from=None, date_to=None,
                   max_quotes=50, include_dates=True):
    """Decrypt text fields and surface notable quotes.

    Args:
        program: Program instance (programme-level).
        client_file: ClientFile instance (client-level).
        date_from: Start date.
        date_to: End date.
        max_quotes: Maximum quotes to return.
        include_dates: Whether to include dates (False for programme-level privacy).

    Returns:
        list of dicts with keys: text, target_name, note_id, date (if include_dates).
        Returns empty list if programme-level and <15 active participants.
    """
    # Privacy gate: check participant count for programme-level.
    # Demo data is not real people — skip the gate in demo mode.
    if program and not client_file and not getattr(settings, "DEMO_MODE", False):
        participant_count = (
            ClientProgramEnrolment.objects.filter(
                program=program,
                status="enrolled",
            )
            .values("client_file_id")
            .distinct()
            .count()
        )
        if participant_count < MIN_PARTICIPANTS_FOR_QUOTES:
            logger.info(
                "Skipping quotes for programme %s: %d participants (minimum %d)",
                program.name, participant_count, MIN_PARTICIPANTS_FOR_QUOTES,
            )
            return []

    # Build queryset for ProgressNoteTarget entries — use effective date
    targets_qs = ProgressNoteTarget.objects.filter(
        progress_note__status="default",
    ).select_related("progress_note", "plan_target").annotate(
        _effective_date=Coalesce(
            "progress_note__backdate", "progress_note__created_at",
            output_field=DateTimeField(),
        ),
    )

    if client_file:
        targets_qs = targets_qs.filter(progress_note__client_file=client_file)
    if program:
        targets_qs = targets_qs.filter(
            progress_note__client_file__enrolments__program=program,
            progress_note__client_file__enrolments__status="enrolled",
        )
    if date_from:
        targets_qs = targets_qs.filter(_effective_date__date__gte=date_from)
    if date_to:
        targets_qs = targets_qs.filter(_effective_date__date__lte=date_to)

    # Order by most recent first
    targets_qs = targets_qs.order_by("-_effective_date")

    # Collect quotes from client_words field
    quotes = []
    seen_texts = set()

    # Cap the number of records we load for decryption
    max_records = max_quotes * 5  # Load extra to account for filtering
    for entry in targets_qs[:max_records]:
        if len(quotes) >= max_quotes:
            break

        # Decrypt client_words
        text = entry.client_words
        if not text:
            continue

        text = text.strip()

        # Filter: minimum 10 words for meaningful quotes
        word_count = len(text.split())
        if word_count < 10:
            continue

        # De-duplicate by normalised text
        normalised = text.lower().strip()
        if normalised in seen_texts:
            continue
        seen_texts.add(normalised)

        # Get target/goal name for context
        target_name = ""
        try:
            target_name = entry.plan_target.name
        except Exception:
            pass

        quote = {
            "text": text,
            "target_name": target_name,
            "note_id": entry.progress_note_id,
        }
        if include_dates:
            quote["date"] = entry.progress_note.effective_date

        quotes.append(quote)

    # Also collect from participant_reflection and participant_suggestion on ProgressNote
    if len(quotes) < max_quotes:
        notes_qs = ProgressNote.objects.filter(status="default").annotate(
            _effective_date=Coalesce("backdate", "created_at", output_field=DateTimeField()),
        )
        if client_file:
            notes_qs = notes_qs.filter(client_file=client_file)
        if program:
            notes_qs = notes_qs.filter(
                client_file__enrolments__program=program,
                client_file__enrolments__status="enrolled",
            )
        if date_from:
            notes_qs = notes_qs.filter(_effective_date__date__gte=date_from)
        if date_to:
            notes_qs = notes_qs.filter(_effective_date__date__lte=date_to)

        notes_qs = notes_qs.order_by("-_effective_date")

        for note in notes_qs[:max_records]:
            if len(quotes) >= max_quotes:
                break

            # Collect participant_reflection
            text = note.participant_reflection
            if text:
                text = text.strip()
                word_count = len(text.split())
                normalised = text.lower().strip()
                if word_count >= 10 and normalised not in seen_texts:
                    seen_texts.add(normalised)
                    quote = {
                        "text": text,
                        "target_name": "",
                        "note_id": note.pk,
                    }
                    if include_dates:
                        quote["date"] = note.effective_date
                    quotes.append(quote)

            if len(quotes) >= max_quotes:
                break

            # Collect participant_suggestion (tagged as suggestion for the AI)
            suggestion = note.participant_suggestion
            if suggestion:
                suggestion = suggestion.strip()
                word_count = len(suggestion.split())
                normalised = suggestion.lower().strip()
                if word_count >= 5 and normalised not in seen_texts:
                    seen_texts.add(normalised)
                    priority = note.suggestion_priority if note.suggestion_priority else ""
                    quote = {
                        "text": suggestion,
                        "target_name": "",
                        "source": "suggestion",
                        "priority": priority,
                        "note_id": note.pk,
                    }
                    if include_dates:
                        quote["date"] = note.effective_date
                    quotes.append(quote)

    return quotes
