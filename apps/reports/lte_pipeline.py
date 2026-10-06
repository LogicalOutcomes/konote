"""Pipeline for Longitudinal Trajectory Export (LTE) — small-population tier.

LTE is a structurally separate export tier from the Evaluation Microdata
Export. See tasks/design-rationale/evaluation-microdata-export.md, "LTE"
section for the full specification.

Key differences from the base DeidentificationPipeline:

1. No QI columns. Demographic fields are stripped at the schema layer,
   not merely generalised. This is a HARD rule — LTE's re-identification
   defence IS the absence of these fields.
2. No k-anonymity check. k is trivially n because there are no QI columns
   to form equivalence classes on.
3. Lower population floor, enforced per-program:
     - default: n >= 10
     - OCAP/EGAP governed programs: n >= 15
4. Metric values, session counts, and total hours are FUZZED — rounded
   to the natural scale unit / banded to 5 / banded to 0.5 respectively
   — to reduce the uniqueness of each trajectory shape.
5. study_id is a random UUID (not the EVL-XXXXXX hex pattern). Random
   UUID with no derivable relationship to the real record id.
6. CSV output uses an LTE-specific metadata header with the "for
   program evaluation, not research" warning.

This pipeline composes with the base DeidentificationPipeline — it
reuses extract/decrypt/consent-filter/bulk-metric logic rather than
forking. If you find yourself duplicating more than a few lines from
the base, refactor into a shared helper instead of copying.
"""

from __future__ import annotations

import csv
import io
import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from django.utils import timezone
from django.db.models import Count, Q, Sum

from apps.clients.models import ServiceEpisode
from apps.notes.models import MetricValue, ProgressNote
from apps.plans.models import MetricDefinition
from apps.reports.csv_utils import sanitise_csv_value
from apps.reports.deidentify import DeidentificationPipeline

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Floors and fuzzing constants (DRR: LTE section)
# ---------------------------------------------------------------------------

LTE_FLOOR_DEFAULT = 10
LTE_FLOOR_OCAP_EGAP = 15
LTE_K_FLOOR = 5  # trivially satisfied — kept here for audit clarity

SESSION_COUNT_BAND = 5           # round session count to nearest 5
TOTAL_HOURS_BAND = 0.5           # round total hours to nearest 0.5

# Metric rounding strategy — inferred from the metric scale. The DRR
# prescribes:
#   0-10 ordinal scales      → nearest integer
#   0-100 percentage scales  → nearest 5
#   continuous scales        → one decimal place or nearest unit,
#                              whichever is coarser
# We detect the scale from the MetricDefinition min/max if present,
# otherwise fall back to one decimal place.


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass
class LTEPreviewResult:
    """Summary of what the LTE pipeline would produce.

    LTE has no QI columns, no suppression rate, and no equivalence-class
    math, so this is shaped differently from the base PreviewResult.
    """

    eligible_count: int
    consented_count: int
    exportable_count: int
    blocked: bool
    block_reason: str | None
    floor_applied: int
    program_governance_framework: str
    # Metric columns that will appear in the output, in order
    metric_columns: list[str] = field(default_factory=list)
    # Snapshot of the client_ids that WILL enter the export — used as
    # the population snapshot when the request is persisted
    snapshot_client_ids: list[int] = field(default_factory=list)


@dataclass
class LTEGenerateResult:
    """Output of a successful LTE pipeline generate run."""

    csv_content: str
    filename: str
    linkage_blob: bytes        # encrypted JSON {study_id: real_client_id}
    preview: LTEPreviewResult
    audit_metadata: dict[str, Any]


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class LTESmallPopulationPipeline(DeidentificationPipeline):
    """LTE pipeline — reuses extract/decrypt/consent from the base, then
    diverges to drop demographics entirely, fuzz trajectory values, and
    enforce the small-population floor.

    Usage (two-phase):

        pipeline = LTESmallPopulationPipeline(
            program=program,
            period_start=date(2025, 9, 1),
            period_end=date(2026, 3, 31),
            evaluator_info={...},
            user=request.user,
        )
        preview = pipeline.run_preview()
        if not preview.blocked:
            result = pipeline.run_generate()

    For the "re-run at window activation" path, pass
    `restrict_to_client_ids` — the extract step will then limit its
    query to that set and the snapshot check is skipped because the
    caller has already enforced it.
    """

    def __init__(
        self,
        program,
        period_start: date,
        period_end: date,
        evaluator_info: dict[str, Any],
        user,
        request=None,
        restrict_to_client_ids: list[int] | None = None,
    ):
        # LTE has no QI columns — pass an empty list to the base so
        # nothing tries to include demographic fields.
        super().__init__(
            program=program,
            period_start=period_start,
            period_end=period_end,
            qi_columns=[],
            evaluator_info=evaluator_info,
            user=user,
            request=request,
        )
        self._restrict_to_client_ids = (
            set(restrict_to_client_ids) if restrict_to_client_ids else None
        )
        # Longitudinal metric values (computed fresh — the base pipeline
        # only produces intake/latest, LTE wants intake/mid/exit).
        self._longitudinal_metrics: dict[int, dict[str, dict[str, Any]]] = {}

    # ------------------------------------------------------------------
    # Public interface — preview + generate
    # ------------------------------------------------------------------

    def run_preview(self) -> LTEPreviewResult:  # type: ignore[override]
        """Run through extract → consent → floor check without producing
        files. Returns an LTEPreviewResult with snapshot client_ids.
        """
        self._reset_state()

        self._extract_raw_data()               # Step 1 (base)
        self._apply_snapshot_restriction()     # LTE-specific
        self._decrypt_and_stage()              # Step 2 (base)
        self._apply_consent_filter()           # Step 3 (base)
        self._compute_longitudinal_metrics()   # LTE-specific
        self._strip_direct_identifiers()       # Step 4 — LTE override

        blocked, reason, floor = self._check_lte_population_floor()

        metric_columns = self._build_lte_metric_columns()
        snapshot_ids = [
            int(r["_real_client_id"]) for r in self._deidentified_records
        ]

        return LTEPreviewResult(
            eligible_count=len(self._raw_records),
            consented_count=len(self._consented_records),
            exportable_count=len(self._deidentified_records),
            blocked=blocked,
            block_reason=reason,
            floor_applied=floor,
            program_governance_framework=(
                self.program.community_governance_framework or ""
            ),
            metric_columns=metric_columns,
            snapshot_client_ids=snapshot_ids,
        )

    def run_generate(self) -> LTEGenerateResult:  # type: ignore[override]
        """Run preview then produce the CSV + linkage blob.

        Raises ValueError if blocked.
        """
        import json

        preview = self.run_preview()
        if preview.blocked:
            raise ValueError(f"LTE export blocked: {preview.block_reason}")

        csv_content = self._generate_lte_csv(preview)
        filename = (
            f"lte_{self.program.pk}_"
            f"{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )

        # Encrypt the linkage table — exists only to support participant
        # withdrawal requests. Destroyed when request is cancelled or expires.
        from konote.encryption import encrypt_field

        linkage_blob = encrypt_field(json.dumps(self._linkage_table))

        audit_metadata = self._build_lte_audit_metadata(preview)
        self._log_audit(
            "export",
            "LTE export generated",
            metadata=audit_metadata,
        )

        return LTEGenerateResult(
            csv_content=csv_content,
            filename=filename,
            linkage_blob=linkage_blob,
            preview=preview,
            audit_metadata=audit_metadata,
        )

    # ------------------------------------------------------------------
    # LTE-specific extract filter
    # ------------------------------------------------------------------

    def _apply_snapshot_restriction(self) -> None:
        """If we're re-running for a snapshot, drop raw records not in it.

        Used at window-activation time to respect the submission-time
        population snapshot — new enrolments since submission must not
        enter the export. Withdrawals are handled by the later consent
        filter step (withdrawn participants fail consent).
        """
        if self._restrict_to_client_ids is None:
            return

        before = len(self._raw_records)
        self._raw_records = [
            r for r in self._raw_records
            if r["_client_id"] in self._restrict_to_client_ids
        ]
        dropped = before - len(self._raw_records)
        if dropped:
            logger.info(
                "LTE snapshot restriction: dropped %d new enrolments "
                "(not in submission-time snapshot)",
                dropped,
            )

    # ------------------------------------------------------------------
    # LTE-specific: longitudinal metric extraction (intake / mid / exit)
    # ------------------------------------------------------------------

    def _compute_longitudinal_metrics(self) -> None:
        """Produce {client_id: {metric_slug: {intake, mid, exit}}}.

        Base pipeline only tracks intake/latest; LTE wants the middle
        measurement too so trajectory analysis is possible. When fewer
        than 3 measurements exist, `mid` is omitted for that client.
        """
        client_ids = [r["_client_id"] for r in self._consented_records]
        if not client_ids or not self._metric_defs:
            return

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
            grouped[(cid, mid)].append(mv)
            if mid not in metric_name_map:
                metric_name_map[mid] = self._sanitise_metric_name(
                    mv.metric_def.name,
                )

        result: dict[int, dict[str, dict[str, Any]]] = defaultdict(dict)
        for (cid, mid), values in grouped.items():
            if not values:
                continue
            safe_name = metric_name_map[mid]
            metric_def = values[0].metric_def
            trio: dict[str, Any] = {
                "intake": self._fuzz_metric_value(values[0].value, metric_def),
                "exit": self._fuzz_metric_value(values[-1].value, metric_def),
            }
            if len(values) >= 3:
                mid_idx = len(values) // 2
                trio["mid"] = self._fuzz_metric_value(
                    values[mid_idx].value, metric_def,
                )
            result[cid][safe_name] = trio

        self._longitudinal_metrics = dict(result)

    # ------------------------------------------------------------------
    # LTE-specific: strip ALL demographics, generate UUID study_ids
    # ------------------------------------------------------------------

    def _strip_direct_identifiers(self):  # type: ignore[override]
        """Override the base step.

        LTE drops demographic fields entirely (not generalised). The
        output record contains only:
          - study_id (random UUID — no linkable pattern)
          - enrolment_quarter / exit_quarter (quarter granularity only)
          - fuzzed sessions_count and total_hours
          - fuzzed longitudinal metric values

        birth_date, postal_code, gender, ethnicity, custom fields — none
        of these enter the output. This is a hard schema guarantee; it
        is not configurable.
        """
        self._log_audit("view", "LTE: stripping all demographic fields")

        used_study_ids: set[str] = set()

        for record in self._consented_records:
            study_id = self._generate_lte_study_id(used_study_ids)
            used_study_ids.add(study_id)

            # Linkage table entry — kept for withdrawal support only
            self._linkage_table[study_id] = record["_client_id"]

            deidentified = {
                "study_id": study_id,
                # Carry forward for the snapshot diff (not exported)
                "_real_client_id": record["_client_id"],
                # Service intensity — will be fuzzed in _record_to_lte_row
                "sessions_count_raw": record.get("sessions_count", 0) or 0,
                "total_hours_raw": record.get("total_hours", 0.0) or 0.0,
                # Enrolment / exit quarters (quarter granularity only)
                "enrolment_quarter": self._date_to_quarter(
                    record.get("enrolment_date"),
                ),
                "exit_quarter": self._date_to_quarter(
                    record.get("exit_date"),
                ),
                # Longitudinal metric values
                "metrics": self._longitudinal_metrics.get(
                    record["_client_id"], {},
                ),
                # Suppression tracking (trivially False — no k-anon step)
                "_suppressed": False,
            }
            self._deidentified_records.append(deidentified)

        # Trivially k = n — no QI columns means every row is in the
        # same equivalence class on the empty QI tuple.
        self._effective_k = len(self._deidentified_records)

        logger.info(
            "LTE: generated %d pseudonymous study_ids (k trivially n=%d)",
            len(self._deidentified_records),
            self._effective_k,
        )

    @staticmethod
    def _generate_lte_study_id(existing: set[str]) -> str:
        """Random UUID prefixed with LTE- for visual distinction.

        UUID4 rather than sequential/hashed — see DRR anti-pattern:
        "Reusing real record IDs as pseudonyms" and "Hashing record IDs
        as pseudonyms".
        """
        for _ in range(1000):
            candidate = f"LTE-{uuid.uuid4().hex[:8].upper()}"
            if candidate not in existing:
                return candidate
        return f"LTE-{uuid.uuid4().hex[:12].upper()}"

    # ------------------------------------------------------------------
    # Disabled base steps — LTE has no QI columns, so these are no-ops
    # ------------------------------------------------------------------

    def _generalise_quasi_identifiers(self):  # type: ignore[override]
        """No-op — LTE has no QI columns. Logged for audit clarity."""
        self._log_audit(
            "view",
            "LTE: no QI columns to generalise (by design)",
        )

    def _compute_k_anonymity(self):  # type: ignore[override]
        """No-op — k is trivially n because there are no QI columns.

        The effective_k field is already set in _strip_direct_identifiers.
        """
        self._log_audit(
            "view",
            "LTE: k-anonymity trivially satisfied (no QI columns)",
        )

    def _resolve_k_violations(self):  # type: ignore[override]
        """No-op — no equivalence classes exist to violate k."""
        return

    def _check_population_threshold(self):  # type: ignore[override]
        """Override — LTE uses its own floor model, not the EME tiers."""
        return "lte"

    # ------------------------------------------------------------------
    # LTE population floor
    # ------------------------------------------------------------------

    def _check_lte_population_floor(self) -> tuple[bool, str | None, int]:
        """Apply the LTE floor (10 default, 15 for OCAP/EGAP).

        Returns (blocked, block_reason, floor_applied).
        """
        framework = (self.program.community_governance_framework or "").lower()
        if framework in ("ocap", "egap"):
            floor = LTE_FLOOR_OCAP_EGAP
        else:
            floor = LTE_FLOOR_DEFAULT

        n = len(self._deidentified_records)
        if n < floor:
            self._blocked = True
            self._block_reason = (
                f"population_below_lte_floor (n={n}, floor={floor}, "
                f"framework={framework or 'default'})"
            )
            logger.warning(
                "LTE: population %d < floor %d (framework=%s) — blocked",
                n, floor, framework or "default",
            )
            return True, self._block_reason, floor

        return False, None, floor

    # ------------------------------------------------------------------
    # Fuzzing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _band_session_count(value: int | float | None) -> int | None:
        """Round session count to the nearest SESSION_COUNT_BAND (5)."""
        if value is None:
            return None
        return int(round(value / SESSION_COUNT_BAND) * SESSION_COUNT_BAND)

    @staticmethod
    def _band_total_hours(value: int | float | None) -> float | None:
        """Round total hours to the nearest TOTAL_HOURS_BAND (0.5)."""
        if value is None:
            return None
        return round(value / TOTAL_HOURS_BAND) * TOTAL_HOURS_BAND

    @staticmethod
    def _fuzz_metric_value(value: Any, metric_def: MetricDefinition) -> Any:
        """Round a metric value to the natural unit of its scale.

        Rules (DRR):
          0-10 ordinal scales      → nearest integer
          0-100 percentage scales  → nearest 5
          continuous / unknown     → one decimal place
        """
        if value is None:
            return None
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return value  # non-numeric passes through (text answers etc.)

        scale_min = getattr(metric_def, "min_value", None)
        scale_max = getattr(metric_def, "max_value", None)

        # 0-10 ordinal → nearest integer
        if scale_min == 0 and scale_max == 10:
            return int(round(numeric))
        # 0-100 percentage → nearest 5
        if scale_min == 0 and scale_max == 100:
            return int(round(numeric / 5) * 5)
        # Continuous / unknown → one decimal place
        return round(numeric, 1)

    # ------------------------------------------------------------------
    # LTE-specific CSV output
    # ------------------------------------------------------------------

    def _build_lte_metric_columns(self) -> list[str]:
        """Produce the ordered list of metric columns that will appear
        in the output, e.g. [metric_wellbeing_intake, metric_wellbeing_mid,
        metric_wellbeing_exit, metric_connectedness_intake, ...]."""
        if not self._metric_defs:
            return []

        has_mid_any = any(
            "mid" in per_metric
            for per_client in self._longitudinal_metrics.values()
            for per_metric in per_client.values()
        )

        columns: list[str] = []
        for md in self._metric_defs:
            slug = self._sanitise_metric_name(md.name)
            columns.append(f"metric_{slug}_intake")
            if has_mid_any:
                columns.append(f"metric_{slug}_mid")
            columns.append(f"metric_{slug}_exit")
        return columns

    def _generate_lte_csv(self, preview: LTEPreviewResult) -> str:
        """Produce the LTE CSV content as a string.

        Unlike the base pipeline, LTE writes to a string buffer rather
        than disk here — the caller (view) is responsible for saving
        the content via _save_export_and_create_link.
        """
        base_columns = [
            "study_id",
            "enrolment_quarter",
            "exit_quarter",
            "sessions_count_banded",
            "total_hours_banded",
        ]
        metric_columns = preview.metric_columns
        columns = base_columns + metric_columns

        buf = io.StringIO()

        # Metadata header (comment lines). Every line starts with "#"
        # so analytical tools can skip them with a standard option.
        buf.write("# Longitudinal Trajectory Export — "
                  f"{sanitise_csv_value(self.program.name)}\n")
        buf.write(f"# Period: {self.period_start} to {self.period_end}\n")
        buf.write(
            f"# Submitted: {timezone.now().isoformat()} by "
            f"{sanitise_csv_value(self.user.get_display_name() or self.user.username)}\n"
        )
        buf.write(
            f"# Evaluator: {sanitise_csv_value(self.evaluator_info.get('name', ''))} "
            f"({sanitise_csv_value(self.evaluator_info.get('email', ''))}), "
            f"{sanitise_csv_value(self.evaluator_info.get('organisation', ''))}\n"
        )
        buf.write(
            f"# Evaluator degree: "
            f"{sanitise_csv_value(self.evaluator_info.get('degree', ''))}\n"
        )
        buf.write(
            f"# Evaluator years experience: "
            f"{self.evaluator_info.get('years_experience', '')}\n"
        )
        buf.write(
            f"# REB: {sanitise_csv_value(self.evaluator_info.get('reb_name', ''))}, "
            f"approval {sanitise_csv_value(self.evaluator_info.get('reb_approval_number', ''))}, "
            f"approved {self.evaluator_info.get('reb_approval_date', '')}\n"
        )
        buf.write(
            f"# Agreement expiry: {self.evaluator_info.get('agreement_expiry', '')}\n"
        )
        buf.write(
            f"# Destruction window: "
            f"{self.evaluator_info.get('destruction_window_days', '')} "
            "days from download (manual attestation)\n"
        )
        buf.write(
            f"# Purpose: "
            f"{sanitise_csv_value(self.evaluator_info.get('purpose', ''))}\n"
        )
        buf.write(
            f"# Population: {preview.eligible_count} eligible, "
            f"{preview.consented_count} consented, "
            f"{preview.exportable_count} exported, 0 suppressed\n"
        )
        buf.write(
            "# NO demographic fields. Metric values rounded to nearest scale unit.\n"
        )
        buf.write(
            f"# Session count banded to nearest {SESSION_COUNT_BAND}. "
            f"Total hours banded to nearest {TOTAL_HOURS_BAND}.\n"
        )
        buf.write(
            "# This file is for PROGRAM EVALUATION, not research.\n"
        )
        buf.write(
            "# Attempting to re-identify participants violates the data "
            "sharing agreement and REB approval.\n"
        )
        buf.write("#\n")

        writer = csv.writer(buf)
        writer.writerow([sanitise_csv_value(c) for c in columns])

        for record in self._deidentified_records:
            row = self._record_to_lte_row(record, columns)
            writer.writerow([sanitise_csv_value(v) for v in row])

        return buf.getvalue()

    def _record_to_lte_row(
        self,
        record: dict[str, Any],
        columns: list[str],
    ) -> list[Any]:
        """Build one CSV row for an LTE record, applying the fuzzing
        rules at write time so rounding is visible in the output.
        """
        metrics = record.get("metrics", {})
        row: list[Any] = []
        for col in columns:
            if col == "study_id":
                row.append(record.get("study_id", ""))
            elif col == "enrolment_quarter":
                row.append(record.get("enrolment_quarter", "") or "")
            elif col == "exit_quarter":
                row.append(record.get("exit_quarter", "") or "")
            elif col == "sessions_count_banded":
                row.append(
                    self._band_session_count(record.get("sessions_count_raw"))
                    or 0,
                )
            elif col == "total_hours_banded":
                row.append(
                    self._band_total_hours(record.get("total_hours_raw"))
                    or 0.0,
                )
            elif col.startswith("metric_") and col.endswith("_intake"):
                slug = col[len("metric_"):-len("_intake")]
                row.append(metrics.get(slug, {}).get("intake", ""))
            elif col.startswith("metric_") and col.endswith("_mid"):
                slug = col[len("metric_"):-len("_mid")]
                row.append(metrics.get(slug, {}).get("mid", ""))
            elif col.startswith("metric_") and col.endswith("_exit"):
                slug = col[len("metric_"):-len("_exit")]
                row.append(metrics.get(slug, {}).get("exit", ""))
            else:
                row.append("")
        return row

    # ------------------------------------------------------------------
    # Audit metadata
    # ------------------------------------------------------------------

    def _build_lte_audit_metadata(
        self, preview: LTEPreviewResult,
    ) -> dict[str, Any]:
        """Build the full audit metadata blob for an LTE export.

        The `export_category` field is `longitudinal_trajectory_export`
        — NOT a flag or subtype of evaluation_microdata. Alerts and
        reports filter on this category independently. See DRR
        "Enhanced Audit Metadata" section.
        """
        framework = self.program.community_governance_framework or ""
        return {
            "export_category": "longitudinal_trajectory_export",
            "program_id": self.program.pk,
            "program_name": self.program.name,
            "period_start": str(self.period_start),
            "period_end": str(self.period_end),
            "population_count": preview.exportable_count,
            "population_eligible": preview.eligible_count,
            "population_consented": preview.consented_count,
            "floor_applied": preview.floor_applied,
            "community_governance_framework": framework,
            "evaluator_name": self.evaluator_info.get("name", ""),
            "evaluator_email": self.evaluator_info.get("email", ""),
            "evaluator_organisation": self.evaluator_info.get("organisation", ""),
            "evaluator_degree": self.evaluator_info.get("degree", ""),
            "evaluator_years_experience": self.evaluator_info.get(
                "years_experience", "",
            ),
            "evaluator_prior_programs": self.evaluator_info.get(
                "prior_programs", "",
            ),
            "reb_name": self.evaluator_info.get("reb_name", ""),
            "reb_approval_number": self.evaluator_info.get(
                "reb_approval_number", "",
            ),
            "reb_approval_date": str(
                self.evaluator_info.get("reb_approval_date", ""),
            ),
            "data_sharing_agreement_expiry": str(
                self.evaluator_info.get("agreement_expiry", ""),
            ),
            "destruction_window_days": self.evaluator_info.get(
                "destruction_window_days", "",
            ),
            "community_reviewer_name": self.evaluator_info.get(
                "community_reviewer_name", "",
            ),
            "community_reviewer_affiliation": self.evaluator_info.get(
                "community_reviewer_affiliation", "",
            ),
            "community_signoff_date": str(
                self.evaluator_info.get("community_signoff_date", ""),
            ),
            "community_framework_description": self.evaluator_info.get(
                "community_framework_description", "",
            ),
            "purpose_statement": self.evaluator_info.get("purpose", ""),
            "metric_rounding_applied": True,
            "session_count_banded_to": SESSION_COUNT_BAND,
            "total_hours_banded_to": TOTAL_HOURS_BAND,
            "k_floor": LTE_K_FLOOR,
            "effective_k_note": "trivially k=n (no QI columns)",
        }

    # ------------------------------------------------------------------
    # Audit log — override category to longitudinal_trajectory_export
    # ------------------------------------------------------------------

    def _log_audit(self, action: str, description: str, metadata=None):  # type: ignore[override]
        """Same append-only audit write as the base, but with the LTE
        export_category injected automatically so audit filters work.
        """
        from apps.audit.models import AuditLog
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
                    "export_category": "longitudinal_trajectory_export",
                    **(metadata or {}),
                },
            )
        except Exception:
            logger.exception("Failed to write LTE audit entry: %s", description)
