"""De-identification pipeline for evaluation microdata export.

Transforms identified participant data into de-identified, k-anonymous
microdata suitable for external evaluators.  Follows the 10-step pipeline
specified in the DRR (tasks/design-rationale/evaluation-microdata-export.md).

Key privacy guarantees:
- Direct identifiers (name, phone, email, exact birth date, record ID)
  are stripped before any output is produced.
- Quasi-identifiers (age, gender, geography) are generalised into bands.
- k-anonymity (k >= 5) is enforced: every combination of quasi-identifier
  values in the output must appear in at least 5 records.
- Violations are resolved by widening age bands, suppressing geography,
  and finally suppressing records entirely.
- Export is blocked when the population is too small (< 15), the
  suppression rate exceeds 15 %, or too many QI columns are requested
  for the population size.

Canadian spelling is used throughout (generalise, organisation, colour).
"""

from __future__ import annotations

import csv
import io
import json
import logging
import os
import re
import secrets
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Any

from django.conf import settings
from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.clients.models import ClientDetailValue, ClientFile, ServiceEpisode
from apps.notes.models import MetricValue, ProgressNote
from apps.plans.models import MetricDefinition, PlanTargetMetric
from apps.reports.csv_utils import sanitise_csv_value

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Age band definitions
# ---------------------------------------------------------------------------

# Standard 5-year grouping (DRR spec)
EVAL_AGE_BANDS = [
    (0, 17, "0-17"),
    (18, 24, "18-24"),
    (25, 29, "25-29"),
    (30, 34, "30-34"),
    (35, 39, "35-39"),
    (40, 44, "40-44"),
    (45, 49, "45-49"),
    (50, 54, "50-54"),
    (55, 59, "55-59"),
    (60, 64, "60-64"),
    (65, 999, "65+"),
]

# Widened age bands for k-anonymity resolution — used when 5-year bands
# produce equivalence classes smaller than TARGET_K.
WIDENED_AGE_BANDS = [
    (0, 17, "0-17"),
    (18, 29, "18-29"),
    (30, 44, "30-44"),
    (45, 64, "45-64"),
    (65, 999, "65+"),
]


# ---------------------------------------------------------------------------
# Pipeline constants
# ---------------------------------------------------------------------------

TARGET_K = 5                # minimum equivalence class size
SUPPRESSION_CEILING = 0.15  # 15 % — block export if exceeded
MIN_POPULATION = 15         # absolute minimum for any export
QI_LIMIT_SMALL = 3          # max QI columns for 15 <= n < 30
QI_LIMIT_LARGE = 5          # max QI columns for n >= 30
QI_THRESHOLD_LARGE = 30     # population size threshold


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass
class PreviewResult:
    """Summary of what the pipeline would produce, without writing files."""

    eligible_count: int
    consented_count: int
    exportable_count: int
    suppressed_count: int
    suppression_rate: float
    effective_k: int
    qi_columns_used: list[str]
    generalizations_applied: list[dict[str, Any]]
    suppression_details: list[dict[str, Any]]
    blocked: bool
    block_reason: str | None
    tier: str  # "aggregate_only", "limited_qi", "full"


@dataclass
class GenerateResult:
    """Output of a successful pipeline run."""

    csv_path: str
    suppression_report_path: str
    preview: PreviewResult
    linkage_blob: bytes  # encrypted JSON mapping study_id -> real client_id
    audit_metadata: dict[str, Any]


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class DeidentificationPipeline:
    """10-step pipeline that transforms identified participant data
    into de-identified, k-anonymous microdata for evaluation export.

    Each step is a separate method that logs to the audit trail.
    The pipeline is run in preview mode (dry run) first to show the
    user what will happen, then in generate mode to produce output.
    """

    def __init__(
        self,
        program,
        period_start: date,
        period_end: date,
        qi_columns: list[str],
        evaluator_info: dict[str, Any],
        user,
        request=None,
    ):
        self.program = program
        self.period_start = period_start
        self.period_end = period_end
        self.qi_columns = list(qi_columns)
        self.evaluator_info = evaluator_info
        self.user = user
        self.request = request

        # Internal state populated by pipeline steps
        self._raw_records: list[dict[str, Any]] = []
        self._staged_records: list[dict[str, Any]] = []
        self._consented_records: list[dict[str, Any]] = []
        self._deidentified_records: list[dict[str, Any]] = []
        self._linkage_table: dict[str, int] = {}
        self._generalizations_applied: list[dict[str, Any]] = []
        self._suppression_reasons: list[dict[str, Any]] = []
        self._blocked = False
        self._block_reason: str | None = None
        self._effective_k = 0
        self._metric_defs: list[MetricDefinition] = []

    @property
    def _active_records(self) -> list[dict[str, Any]]:
        """Records not suppressed by k-anonymity resolution."""
        return [r for r in self._deidentified_records if not r.get("_suppressed")]

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def run_preview(self) -> PreviewResult:
        """Execute steps 1-8 without generating output files."""
        self._reset_state()

        self._extract_raw_data()               # Step 1
        self._decrypt_and_stage()              # Step 2
        self._apply_consent_filter()           # Step 3
        self._strip_direct_identifiers()       # Step 4
        self._generalise_quasi_identifiers()   # Step 5

        # Check population threshold BEFORE k-anonymity
        tier = self._check_population_threshold()  # Step 8 (early)
        if self._blocked:
            return self._build_preview_result(tier)

        self._compute_k_anonymity()            # Step 6
        self._resolve_k_violations()           # Step 7

        # Re-check after resolution (suppression may have shrunk population)
        tier = self._check_population_threshold()  # Step 8
        return self._build_preview_result(tier)

    def run_generate(self) -> GenerateResult:
        """Execute all 10 steps and produce CSV + suppression report.

        Must only be called after run_preview() confirms the export is
        not blocked.

        Raises:
            ValueError: If the export is blocked (population too small,
                suppression rate exceeded, too many QI columns).
        """
        # Re-run preview steps to get fresh data
        preview = self.run_preview()
        if preview.blocked:
            raise ValueError(f"Export blocked: {preview.block_reason}")

        csv_path = self._generate_csv()                    # Step 9
        report_path = self._generate_suppression_report()  # Step 10

        # Encrypt the linkage table
        from konote.encryption import encrypt_field
        linkage_blob = encrypt_field(json.dumps(self._linkage_table))

        audit_metadata = self._build_audit_metadata(preview)
        self._log_audit("export", "Export generated", metadata=audit_metadata)

        return GenerateResult(
            csv_path=csv_path,
            suppression_report_path=report_path,
            preview=preview,
            linkage_blob=linkage_blob,
            audit_metadata=audit_metadata,
        )

    # ------------------------------------------------------------------
    # Step 1: Extract raw data
    # ------------------------------------------------------------------

    def _extract_raw_data(self):
        """Query database for all participants and metrics in the period.

        Populates self._raw_records with one dict per participant,
        containing the raw encrypted model instances (not yet decrypted).
        """
        self._log_audit("view", "Pipeline initiated — extracting raw data")

        # Find service episodes that overlap the reporting period.
        # An episode overlaps if it started on or before period_end AND
        # has not ended before period_start (or has no end date).
        episodes = ServiceEpisode.objects.filter(
            program=self.program,
            status__in=["active", "on_hold", "finished"],
        ).filter(
            Q(started_at__date__lte=self.period_end) | Q(started_at__isnull=True),
        ).filter(
            Q(ended_at__date__gte=self.period_start)
            | Q(ended_at__isnull=True)
        ).select_related("client_file")

        # Deduplicate: a client may have multiple episodes — we want one
        # record per client, keeping the most relevant episode.
        client_episodes: dict[int, tuple[ClientFile, ServiceEpisode]] = {}
        for ep in episodes:
            client = ep.client_file
            # Skip demo clients
            if client.is_demo:
                continue
            # Keep the most recent episode if multiple exist
            existing = client_episodes.get(client.pk)
            if existing is None or (ep.started_at and (
                not existing[1].started_at or ep.started_at > existing[1].started_at
            )):
                client_episodes[client.pk] = (client, ep)

        # Collect client IDs for metric queries
        client_ids = list(client_episodes.keys())

        # Get all metric definitions used in this program via plan targets
        self._metric_defs = list(
            MetricDefinition.objects.filter(
                plantargetmetric__plan_target__plan_section__client_file_id__in=client_ids,
                plantargetmetric__plan_target__plan_section__program=self.program,
            ).distinct().order_by("name")
        )

        # Build raw records
        for client_id, (client, episode) in client_episodes.items():
            self._raw_records.append({
                "_client": client,
                "_episode": episode,
                "_client_id": client.pk,
            })

        logger.info(
            "Step 1: Extracted %d raw records for program %s",
            len(self._raw_records), self.program.pk,
        )

    # ------------------------------------------------------------------
    # Step 2: Decrypt and stage
    # ------------------------------------------------------------------

    def _decrypt_and_stage(self):
        """Decrypt PII fields and build working dicts.

        Accesses encrypted property accessors (.birth_date, .first_name,
        .last_name) for staging only — these values will be stripped in
        Step 4.

        Uses bulk queries to avoid N+1 patterns — all ProgressNote,
        MetricValue, and ClientDetailValue data is fetched in a handful
        of queries rather than per-client.
        """
        self._log_audit("view", "Decrypting and staging records")

        client_ids = [raw["_client_id"] for raw in self._raw_records]

        # Bulk fetch: session counts and total hours per client
        note_stats_map: dict[int, tuple[int, int]] = {}
        for row in ProgressNote.objects.filter(
            client_file_id__in=client_ids,
            created_at__date__range=(self.period_start, self.period_end),
        ).values("client_file_id").annotate(
            count=Count("id"),
            total_minutes=Sum("duration_minutes"),
        ):
            note_stats_map[row["client_file_id"]] = (
                row["count"], row["total_minutes"] or 0,
            )

        # Bulk fetch: all metric values for all clients
        metric_data_map = self._bulk_get_metric_data(client_ids)

        # Bulk fetch: custom field values and postal codes
        custom_field_map, postal_code_map = self._bulk_get_field_data(client_ids)

        for raw in self._raw_records:
            client: ClientFile = raw["_client"]
            episode: ServiceEpisode = raw["_episode"]
            cid = client.pk

            sessions_count, total_minutes = note_stats_map.get(cid, (0, 0))
            total_hours = round(total_minutes / 60, 1) if total_minutes else 0.0

            staged = {
                "_client_id": cid,
                "_episode": episode,
                "_first_name": client.first_name,
                "_last_name": client.last_name,
                "_birth_date": client.birth_date,
                "_postal_code": postal_code_map.get(cid),
                "_consent": episode.consent_to_aggregate_reporting,
                "enrolment_date": (
                    episode.started_at.date()
                    if episode.started_at else None
                ),
                "exit_date": (
                    episode.ended_at.date()
                    if episode.ended_at else None
                ),
                "sessions_count": sessions_count,
                "total_hours": total_hours,
                "metrics": metric_data_map.get(cid, {}),
                "custom_fields": custom_field_map.get(cid, {}),
            }
            self._staged_records.append(staged)

        logger.info(
            "Step 2: Staged %d records with decrypted fields",
            len(self._staged_records),
        )

    def _bulk_get_metric_data(
        self, client_ids: list[int],
    ) -> dict[int, dict[str, dict[str, Any]]]:
        """Bulk-fetch intake and latest metric values for all clients.

        Returns {client_id: {metric_slug: {"intake": v, "latest": v}}}.
        """
        if not self._metric_defs:
            return {}

        all_values = (
            MetricValue.objects.filter(
                metric_def__in=self._metric_defs,
                progress_note_target__progress_note__client_file_id__in=client_ids,
                progress_note_target__progress_note__created_at__date__range=(
                    self.period_start, self.period_end,
                ),
            )
            .select_related(
                "metric_def",
                "progress_note_target__progress_note",
            )
            .order_by("progress_note_target__progress_note__created_at")
        )

        # Group by (client_id, metric_def_id)
        grouped: dict[tuple[int, int], list] = defaultdict(list)
        metric_name_map: dict[int, str] = {}
        for mv in all_values:
            cid = mv.progress_note_target.progress_note.client_file_id
            mid = mv.metric_def_id
            grouped[(cid, mid)].append(mv.value)
            if mid not in metric_name_map:
                metric_name_map[mid] = self._sanitise_metric_name(
                    mv.metric_def.name,
                )

        result: dict[int, dict[str, dict[str, Any]]] = defaultdict(dict)
        for (cid, mid), values in grouped.items():
            safe_name = metric_name_map[mid]
            result[cid][safe_name] = {
                "intake": values[0] if values else None,
                "latest": values[-1] if values else None,
            }

        return dict(result)

    def _bulk_get_field_data(
        self, client_ids: list[int],
    ) -> tuple[dict[int, dict[str, str]], dict[int, str | None]]:
        """Bulk-fetch custom field values and postal codes for all clients.

        Returns (custom_field_map, postal_code_map) where:
        - custom_field_map: {client_id: {qi_col: value}}
        - postal_code_map: {client_id: postal_code_or_None}
        """
        custom_qi = [
            col for col in self.qi_columns
            if col not in ("age_group", "geography")
        ]

        custom_field_map: dict[int, dict[str, str]] = defaultdict(dict)
        postal_code_map: dict[int, str | None] = {}

        # Single query for all custom field values across all clients.
        # Only include fields from groups marked as evaluation-exportable
        # (plus postal code fields needed for geography derivation).
        all_details = ClientDetailValue.objects.filter(
            client_file_id__in=client_ids,
            field_def__status="active",
        ).filter(
            Q(field_def__group__is_evaluation_exportable=True)
            | Q(field_def__validation_type="postal_code")
            | Q(field_def__name__iexact="Postal Code")
        ).select_related("field_def", "field_def__group")

        for dv in all_details:
            cid = dv.client_file_id

            # Check for postal code fields
            fd = dv.field_def
            if (
                cid not in postal_code_map
                and "geography" in self.qi_columns
                and (
                    getattr(fd, "validation_type", None) == "postal_code"
                    or fd.name.lower() == "postal code"
                )
            ):
                postal_code_map[cid] = dv.get_value() or None

            # Check for QI custom fields
            if custom_qi:
                field_name_lower = fd.name.lower().replace(" ", "_")
                if field_name_lower in custom_qi:
                    raw_val = dv.get_value()
                    if fd.input_type in ("select", "select_other"):
                        raw_val = self._resolve_option_label(fd, raw_val)
                    custom_field_map[cid][field_name_lower] = raw_val or ""

        return dict(custom_field_map), postal_code_map

    def _resolve_option_label(self, field_def, raw_value: str) -> str:
        """Resolve a dropdown value to its display label."""
        if not field_def.options_json or not raw_value:
            return raw_value or ""
        for option in field_def.options_json:
            if isinstance(option, dict):
                if option.get("value", "") == raw_value:
                    return option.get("label", raw_value)
            elif option == raw_value:
                return raw_value
        return raw_value

    @staticmethod
    def _sanitise_metric_name(name: str) -> str:
        """Convert a metric name to a safe column name slug."""
        safe = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
        return safe or "metric"

    # ------------------------------------------------------------------
    # Step 3: Apply consent filter
    # ------------------------------------------------------------------

    def _apply_consent_filter(self):
        """Remove records where the participant has not consented to
        aggregate reporting for this program.
        """
        self._log_audit("view", "Applying consent filter")

        excluded_count = 0
        for record in self._staged_records:
            if record.get("_consent", False):
                self._consented_records.append(record)
            else:
                excluded_count += 1

        logger.info(
            "Step 3: %d consented, %d excluded (no consent)",
            len(self._consented_records), excluded_count,
        )

    # ------------------------------------------------------------------
    # Step 4: Strip direct identifiers
    # ------------------------------------------------------------------

    def _strip_direct_identifiers(self):
        """Remove all direct identifiers and generate pseudonymous
        study IDs.

        Direct identifiers removed: first_name, last_name, exact
        birth_date, postal_code, real client_id.
        """
        self._log_audit("view", "Stripping direct identifiers")

        used_study_ids: set[str] = set()

        for record in self._consented_records:
            # Generate a unique study ID
            study_id = self._generate_study_id(used_study_ids)
            used_study_ids.add(study_id)

            # Build linkage table entry
            self._linkage_table[study_id] = record["_client_id"]

            # Create de-identified record — carry forward only what's needed
            deidentified = {
                "study_id": study_id,
                # Preserve birth_date temporarily for age generalisation
                "_birth_date": record.get("_birth_date"),
                # Preserve postal code temporarily for geography derivation
                "_postal_code": record.get("_postal_code"),
                # Non-PII fields pass through
                "enrolment_date": record.get("enrolment_date"),
                "exit_date": record.get("exit_date"),
                "sessions_count": record.get("sessions_count", 0),
                "total_hours": record.get("total_hours", 0.0),
                "metrics": record.get("metrics", {}),
                "custom_fields": record.get("custom_fields", {}),
                # Suppression tracking
                "_suppressed": False,
            }
            self._deidentified_records.append(deidentified)

        logger.info(
            "Step 4: Generated %d pseudonymous study IDs",
            len(self._deidentified_records),
        )

    @staticmethod
    def _generate_study_id(existing: set[str]) -> str:
        """Generate a unique random study ID in format EVL-XXXXXX."""
        for _ in range(1000):  # safety limit
            candidate = f"EVL-{secrets.token_hex(3).upper()}"
            if candidate not in existing:
                return candidate
        # Extremely unlikely fallback
        return f"EVL-{uuid.uuid4().hex[:6].upper()}"

    # ------------------------------------------------------------------
    # Step 5: Generalise quasi-identifiers
    # ------------------------------------------------------------------

    def _generalise_quasi_identifiers(self):
        """Generalise quasi-identifiers into broader categories.

        - age_group: exact birth_date -> 5-year age band
        - gender: pass through from custom field
        - ethnicity: pass through from custom field
        - geography: postal code FSA -> Urban/Rural
        - Enrolment/exit dates -> quarter/year
        """
        self._log_audit("view", "Generalising quasi-identifiers")

        for record in self._deidentified_records:
            # Age generalisation
            if "age_group" in self.qi_columns:
                birth_date = record.pop("_birth_date", None)
                age = self._compute_age(birth_date)
                band = self._age_to_band(age, EVAL_AGE_BANDS)
                record["age_group"] = band

                if birth_date and band:
                    self._generalizations_applied.append({
                        "field": "age_group",
                        "original": "exact birth date",
                        "widened_to": band,
                    })
            else:
                # Remove the temporary field if not used
                record.pop("_birth_date", None)

            # Geography generalisation (Urban/Rural from postal code FSA)
            if "geography" in self.qi_columns:
                postal_code = record.pop("_postal_code", None)
                geo = self._postal_code_to_geography(postal_code)
                record["geography"] = geo

                if postal_code and geo:
                    self._generalizations_applied.append({
                        "field": "geography",
                        "original": "postal code",
                        "widened_to": geo,
                    })
            else:
                record.pop("_postal_code", None)

            # Custom field QI columns (gender, ethnicity, etc.)
            custom_fields = record.get("custom_fields", {})
            for col in self.qi_columns:
                if col not in ("age_group", "geography"):
                    record[col] = custom_fields.get(col, None)

            # Generalise dates to quarters
            record["enrolment_quarter"] = self._date_to_quarter(
                record.pop("enrolment_date", None),
            )
            record["exit_quarter"] = self._date_to_quarter(
                record.pop("exit_date", None),
            )

        # Deduplicate generalisation log entries
        seen = set()
        unique_generalizations = []
        for g in self._generalizations_applied:
            key = (g["field"], g["widened_to"])
            if key not in seen:
                seen.add(key)
                unique_generalizations.append(g)
        self._generalizations_applied = unique_generalizations

        logger.info(
            "Step 5: Applied %d generalisations",
            len(self._generalizations_applied),
        )

    @staticmethod
    def _postal_code_to_geography(postal_code: str | None) -> str | None:
        """Derive Urban/Rural from a Canadian postal code FSA.

        In Canadian postal codes, the second character of the FSA
        (Forward Sortation Area) indicates urban vs. rural:
        - 0 = rural delivery area
        - 1-9 = urban delivery area
        """
        if not postal_code or len(postal_code) < 2:
            return None

        # Clean up — remove spaces, uppercase
        cleaned = postal_code.strip().upper().replace(" ", "")
        if len(cleaned) < 2:
            return None

        second_char = cleaned[1]
        if not second_char.isdigit():
            return None

        if second_char == "0":
            return "Rural"
        return "Urban"

    # ------------------------------------------------------------------
    # Step 6: Compute k-anonymity
    # ------------------------------------------------------------------

    def _compute_k_anonymity(self):
        """Compute the effective k-anonymity of the current dataset.

        Groups records by their QI column values (equivalence classes)
        and finds the minimum class size.
        """
        self._log_audit("view", "Computing k-anonymity")

        active_records = self._active_records

        if not active_records:
            self._effective_k = 0
            return

        eq_classes = self._build_equivalence_classes(active_records)
        self._effective_k = min(eq_classes.values()) if eq_classes else 0

        logger.info(
            "Step 6: Effective k = %d across %d equivalence classes",
            self._effective_k, len(eq_classes),
        )

    def _build_equivalence_classes(
        self, records: list[dict[str, Any]],
    ) -> dict[tuple, int]:
        """Group records by their QI tuple and return class sizes."""
        eq_classes: dict[tuple, int] = Counter()

        for record in records:
            qi_tuple = self._qi_tuple(record)
            eq_classes[qi_tuple] += 1

        return dict(eq_classes)

    def _qi_tuple(self, record: dict[str, Any]) -> tuple:
        """Build a tuple of QI values for a record."""
        values = []
        for col in self.qi_columns:
            values.append(record.get(col))
        return tuple(values)

    # ------------------------------------------------------------------
    # Step 7: Resolve k-anonymity violations
    # ------------------------------------------------------------------

    def _resolve_k_violations(self):
        """Resolve equivalence classes smaller than TARGET_K.

        Resolution strategy (in order):
        1. Widen age bands from 5-year to coarser bands
        2. Suppress geography (set to null)
        3. Suppress the entire record

        After each step, re-check k-anonymity. Stop when all classes
        meet the threshold.
        """
        self._log_audit("view", "Resolving k-anonymity violations")

        active_records = self._active_records
        if not active_records:
            return

        eq_classes = self._build_equivalence_classes(active_records)
        min_k = min(eq_classes.values()) if eq_classes else 0

        if min_k >= TARGET_K:
            self._effective_k = min_k
            return

        # Strategy 1: Widen age bands
        if "age_group" in self.qi_columns:
            widened = self._try_widen_age_bands(active_records)
            if widened:
                self._generalizations_applied.append({
                    "field": "age_group",
                    "original": "5-year bands",
                    "widened_to": "coarser bands (0-17, 18-29, 30-44, 45-64, 65+)",
                })
                # Re-check
                eq_classes = self._build_equivalence_classes(active_records)
                min_k = min(eq_classes.values()) if eq_classes else 0
                if min_k >= TARGET_K:
                    self._effective_k = min_k
                    return

        # Strategy 2: Suppress geography (set to null for small classes)
        if "geography" in self.qi_columns:
            geography_suppressed = self._try_suppress_geography(active_records)
            if geography_suppressed:
                self._suppression_reasons.append({
                    "reason": "geography_suppressed",
                    "count": geography_suppressed,
                    "description": (
                        f"Geography set to null for {geography_suppressed} "
                        f"records in small equivalence classes"
                    ),
                })
                # Re-check
                eq_classes = self._build_equivalence_classes(active_records)
                min_k = min(eq_classes.values()) if eq_classes else 0
                if min_k >= TARGET_K:
                    self._effective_k = min_k
                    return

        # Strategy 3: Suppress records in classes still below threshold
        suppressed_count = self._suppress_small_classes(active_records)
        if suppressed_count:
            self._suppression_reasons.append({
                "reason": "record_suppressed",
                "count": suppressed_count,
                "description": (
                    f"{suppressed_count} records suppressed — equivalence "
                    f"class too small even after generalisation"
                ),
            })

        # Final k computation on remaining records
        remaining = self._active_records
        if remaining:
            eq_classes = self._build_equivalence_classes(remaining)
            self._effective_k = min(eq_classes.values()) if eq_classes else 0
        else:
            self._effective_k = 0

        # Check suppression rate
        total = len(self._deidentified_records)
        suppressed_total = sum(
            1 for r in self._deidentified_records if r.get("_suppressed")
        )
        if total > 0:
            suppression_rate = suppressed_total / total
            if suppression_rate > SUPPRESSION_CEILING:
                self._blocked = True
                self._block_reason = "suppression_rate_exceeded"
                logger.warning(
                    "Step 7: Suppression rate %.1f%% exceeds ceiling %.1f%%",
                    suppression_rate * 100, SUPPRESSION_CEILING * 100,
                )

        logger.info(
            "Step 7: Resolved violations — effective k = %d, "
            "%d records suppressed",
            self._effective_k, suppressed_total,
        )

    def _try_widen_age_bands(self, records: list[dict[str, Any]]) -> bool:
        """Re-map age_group from 5-year bands to wider bands.

        Returns True if any records were re-mapped.
        """
        changed = False
        for record in records:
            if record.get("_suppressed"):
                continue
            current = record.get("age_group")
            if current is None:
                continue
            # Find which widened band this falls into
            widened = self._remap_to_widened_band(current)
            if widened and widened != current:
                record["age_group"] = widened
                changed = True
        return changed

    @staticmethod
    def _remap_to_widened_band(narrow_band: str) -> str | None:
        """Map a 5-year band label to the corresponding widened band."""
        # Parse the narrow band to extract age range
        narrow_to_wide = {
            "0-17": "0-17",
            "18-24": "18-29",
            "25-29": "18-29",
            "30-34": "30-44",
            "35-39": "30-44",
            "40-44": "30-44",
            "45-49": "45-64",
            "50-54": "45-64",
            "55-59": "45-64",
            "60-64": "45-64",
            "65+": "65+",
        }
        return narrow_to_wide.get(narrow_band, narrow_band)

    def _try_suppress_geography(
        self, records: list[dict[str, Any]],
    ) -> int:
        """Set geography to None for records in small equivalence classes.

        Returns the number of records affected.
        """
        eq_classes = self._build_equivalence_classes(
            [r for r in records if not r.get("_suppressed")]
        )
        # Identify QI tuples with class size < TARGET_K
        small_tuples = {
            qt for qt, count in eq_classes.items() if count < TARGET_K
        }
        if not small_tuples:
            return 0

        affected = 0
        for record in records:
            if record.get("_suppressed"):
                continue
            qt = self._qi_tuple(record)
            if qt in small_tuples and record.get("geography") is not None:
                record["geography"] = None
                affected += 1

        return affected

    def _suppress_small_classes(
        self, records: list[dict[str, Any]],
    ) -> int:
        """Suppress (mark) records in equivalence classes still below
        TARGET_K after generalisation.

        Returns the count of newly suppressed records.
        """
        active = [r for r in records if not r.get("_suppressed")]
        eq_classes = self._build_equivalence_classes(active)
        small_tuples = {
            qt for qt, count in eq_classes.items() if count < TARGET_K
        }
        if not small_tuples:
            return 0

        suppressed_count = 0
        for record in self._deidentified_records:
            if record.get("_suppressed"):
                continue
            qt = self._qi_tuple(record)
            if qt in small_tuples:
                record["_suppressed"] = True
                suppressed_count += 1

        return suppressed_count

    # ------------------------------------------------------------------
    # Step 8: Check population threshold
    # ------------------------------------------------------------------

    def _check_population_threshold(self) -> str:
        """Determine the export tier based on population size and
        QI column count.

        Tiers:
        - "aggregate_only": n < 15, export blocked
        - "limited_qi": 15 <= n < 30, max 3 QI columns
        - "full": n >= 30, max 5 QI columns

        Returns the tier string.
        """
        exportable = self._active_records
        n = len(exportable)
        qi_count = len(self.qi_columns)

        if n < MIN_POPULATION:
            self._blocked = True
            self._block_reason = "population_too_small"
            logger.warning(
                "Step 8: Population %d < minimum %d — export blocked",
                n, MIN_POPULATION,
            )
            return "aggregate_only"

        if n < QI_THRESHOLD_LARGE:
            if qi_count > QI_LIMIT_SMALL:
                self._blocked = True
                self._block_reason = "too_many_qi_columns"
                logger.warning(
                    "Step 8: %d QI columns exceeds limit of %d for "
                    "population %d (< %d)",
                    qi_count, QI_LIMIT_SMALL, n, QI_THRESHOLD_LARGE,
                )
            return "limited_qi"

        # n >= QI_THRESHOLD_LARGE
        if qi_count > QI_LIMIT_LARGE:
            self._blocked = True
            self._block_reason = "too_many_qi_columns"
            logger.warning(
                "Step 8: %d QI columns exceeds limit of %d for "
                "population %d",
                qi_count, QI_LIMIT_LARGE, n,
            )
        return "full"

    # ------------------------------------------------------------------
    # Step 9: Generate CSV
    # ------------------------------------------------------------------

    def _generate_csv(self) -> str:
        """Write de-identified data as CSV with metadata header.

        Returns the absolute path to the generated file.
        """
        self._log_audit("export", "Generating CSV file")

        export_dir = settings.SECURE_EXPORT_DIR
        os.makedirs(export_dir, exist_ok=True)

        timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
        filename = f"eval_microdata_{self.program.pk}_{timestamp}.csv"
        filepath = os.path.join(export_dir, filename)

        exportable = self._active_records

        # Build column headers
        columns = self._build_csv_columns()

        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            # Metadata header (comment lines)
            f.write(f"# KoNote Evaluation Microdata Export\n")
            f.write(f"# Program: {sanitise_csv_value(self.program.name)}\n")
            f.write(f"# Period: {self.period_start} to {self.period_end}\n")
            f.write(f"# Generated: {timezone.now().isoformat()}\n")
            f.write(f"# Records: {len(exportable)}\n")
            f.write(f"# Effective k: {self._effective_k}\n")
            f.write(f"# QI columns: {', '.join(self.qi_columns)}\n")
            f.write(f"#\n")

            writer = csv.writer(f)
            writer.writerow([sanitise_csv_value(c) for c in columns])

            for record in exportable:
                row = self._record_to_row(record, columns)
                writer.writerow([sanitise_csv_value(v) for v in row])

        logger.info("Step 9: CSV written to %s (%d rows)", filepath, len(exportable))
        return filepath

    def _build_csv_columns(self) -> list[str]:
        """Build the ordered list of CSV column headers."""
        columns = ["study_id"]

        # QI columns
        for col in self.qi_columns:
            columns.append(col)

        # Temporal columns
        columns.extend(["enrolment_quarter", "exit_quarter"])

        # Service columns
        columns.extend(["sessions_count", "total_hours"])

        # Metric columns (intake and latest for each metric)
        for metric_def in self._metric_defs:
            safe_name = self._sanitise_metric_name(metric_def.name)
            columns.append(f"metric_{safe_name}_intake")
            columns.append(f"metric_{safe_name}_latest")

        return columns

    def _record_to_row(
        self,
        record: dict[str, Any],
        columns: list[str],
    ) -> list[Any]:
        """Convert a de-identified record dict to a CSV row."""
        row = []
        metrics = record.get("metrics", {})

        for col in columns:
            if col == "study_id":
                row.append(record.get("study_id", ""))
            elif col in self.qi_columns:
                row.append(record.get(col, ""))
            elif col == "enrolment_quarter":
                row.append(record.get("enrolment_quarter", ""))
            elif col == "exit_quarter":
                row.append(record.get("exit_quarter", ""))
            elif col == "sessions_count":
                row.append(record.get("sessions_count", 0))
            elif col == "total_hours":
                row.append(record.get("total_hours", 0.0))
            elif col.startswith("metric_") and col.endswith("_intake"):
                metric_key = col[len("metric_"):-len("_intake")]
                metric_data = metrics.get(metric_key, {})
                row.append(metric_data.get("intake", ""))
            elif col.startswith("metric_") and col.endswith("_latest"):
                metric_key = col[len("metric_"):-len("_latest")]
                metric_data = metrics.get(metric_key, {})
                row.append(metric_data.get("latest", ""))
            else:
                row.append("")

        return row

    # ------------------------------------------------------------------
    # Step 10: Generate suppression report
    # ------------------------------------------------------------------

    def _generate_suppression_report(self) -> str:
        """Write a JSON suppression report alongside the CSV.

        The report documents what was suppressed and why, for audit
        and transparency.
        """
        self._log_audit("export", "Generating suppression report")

        export_dir = settings.SECURE_EXPORT_DIR
        os.makedirs(export_dir, exist_ok=True)

        timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
        filename = f"eval_suppression_report_{self.program.pk}_{timestamp}.json"
        filepath = os.path.join(export_dir, filename)

        exportable = self._active_records
        suppressed_count = len(self._deidentified_records) - len(exportable)

        report = {
            "generated_at": timezone.now().isoformat(),
            "program_id": self.program.pk,
            "program_name": self.program.name,
            "period": {
                "start": str(self.period_start),
                "end": str(self.period_end),
            },
            "population": {
                "eligible": len(self._raw_records),
                "consented": len(self._consented_records),
                "exportable": len(exportable),
                "suppressed": suppressed_count,
            },
            "privacy": {
                "target_k": TARGET_K,
                "effective_k": self._effective_k,
                "suppression_rate": round(
                    suppressed_count / (len(exportable) + suppressed_count)
                    if (len(exportable) + suppressed_count) > 0
                    else 0.0,
                    3,
                ),
                "suppression_ceiling": SUPPRESSION_CEILING,
                "qi_columns": self.qi_columns,
            },
            "generalizations": self._generalizations_applied,
            "suppression_reasons": self._suppression_reasons,
            "evaluator": {
                "name": self.evaluator_info.get("name", ""),
                "organisation": self.evaluator_info.get("organisation", ""),
                "purpose": self.evaluator_info.get("purpose", ""),
            },
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)

        logger.info("Step 10: Suppression report written to %s", filepath)
        return filepath

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    def _reset_state(self):
        """Clear all internal state for a fresh pipeline run."""
        self._raw_records = []
        self._staged_records = []
        self._consented_records = []
        self._deidentified_records = []
        self._linkage_table = {}
        self._generalizations_applied = []
        self._suppression_reasons = []
        self._blocked = False
        self._block_reason = None
        self._effective_k = 0
        self._metric_defs = []

    def _log_audit(self, action: str, description: str, metadata=None):
        """Log a pipeline step to the audit trail."""
        from konote.utils import get_client_ip

        try:
            AuditLog.objects.using("audit").create(
                event_timestamp=timezone.now(),
                user_id=self.user.pk,
                user_display=str(self.user),
                ip_address=(
                    get_client_ip(self.request) if self.request else None
                ),
                action=action,
                resource_type="export",
                program_id=self.program.pk,
                metadata={
                    "pipeline_step": description,
                    "export_category": "evaluation_microdata",
                    **(metadata or {}),
                },
            )
        except Exception:
            # Audit failure should not crash the pipeline — log and continue.
            # The audit database might be temporarily unreachable.
            logger.exception("Failed to write audit log: %s", description)

    def _date_to_quarter(self, d) -> str | None:
        """Convert a date to quarter/year string like Q3-2025."""
        if not d:
            return None
        if isinstance(d, str):
            try:
                d = date.fromisoformat(d)
            except (ValueError, TypeError):
                return None
        quarter = (d.month - 1) // 3 + 1
        return f"Q{quarter}-{d.year}"

    def _compute_age(
        self,
        birth_date,
        as_of_date: date | None = None,
    ) -> int | None:
        """Compute age from birth date.

        Args:
            birth_date: Date of birth (date object or ISO string).
            as_of_date: Calculate age as of this date (default: period_end).

        Returns:
            Integer age, or None if birth_date is missing/invalid.
        """
        if not birth_date:
            return None
        if isinstance(birth_date, str):
            try:
                birth_date = date.fromisoformat(birth_date)
            except (ValueError, TypeError):
                return None
        if as_of_date is None:
            as_of_date = self.period_end
        age = as_of_date.year - birth_date.year
        if (as_of_date.month, as_of_date.day) < (birth_date.month, birth_date.day):
            age -= 1
        return age

    @staticmethod
    def _age_to_band(age: int | None, bands=None) -> str | None:
        """Map an integer age to an age band label."""
        if age is None:
            return None
        if bands is None:
            bands = EVAL_AGE_BANDS
        for min_age, max_age, label in bands:
            if min_age <= age <= max_age:
                return label
        return None

    def _build_preview_result(self, tier: str) -> PreviewResult:
        """Construct a PreviewResult from current pipeline state."""
        exportable = self._active_records
        suppressed_count = len(self._deidentified_records) - len(exportable)
        total = len(self._deidentified_records)

        return PreviewResult(
            eligible_count=len(self._raw_records),
            consented_count=len(self._consented_records),
            exportable_count=len(exportable),
            suppressed_count=suppressed_count,
            suppression_rate=suppressed_count / total if total > 0 else 0.0,
            effective_k=self._effective_k,
            qi_columns_used=list(self.qi_columns),
            generalizations_applied=list(self._generalizations_applied),
            suppression_details=list(self._suppression_reasons),
            blocked=self._blocked,
            block_reason=self._block_reason,
            tier=tier,
        )

    def _build_audit_metadata(self, preview: PreviewResult) -> dict[str, Any]:
        """Build the full audit metadata blob for the export."""
        return {
            "export_category": "evaluation_microdata",
            "evaluator_email": self.evaluator_info.get("email", ""),
            "evaluator_name": self.evaluator_info.get("name", ""),
            "evaluator_organisation": self.evaluator_info.get(
                "organisation", "",
            ),
            "evaluation_purpose": self.evaluator_info.get("purpose", ""),
            "data_sharing_agreement_expiry": str(
                self.evaluator_info.get("agreement_expiry", ""),
            ),
            "program_id": self.program.pk,
            "program_name": self.program.name,
            "period_start": str(self.period_start),
            "period_end": str(self.period_end),
            "pipeline_summary": {
                "eligible_count": preview.eligible_count,
                "consented_count": preview.consented_count,
                "exported_count": preview.exportable_count,
                "suppressed_count": preview.suppressed_count,
                "suppression_rate": round(preview.suppression_rate, 3),
                "effective_k": preview.effective_k,
                "qi_columns": preview.qi_columns_used,
                "generalizations_applied": preview.generalizations_applied,
            },
        }
