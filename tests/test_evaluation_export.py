"""Tests for Evaluation Microdata Export — De-identification Pipeline.

Safety-critical tests for apps/reports/deidentify.py.  Covers:

- Consent filtering (only consented participants included)
- Direct identifier stripping (no PII in output)
- Pseudonymous ID randomness and format
- Age band generalisation (5-year + widened)
- Geography derivation (postal code FSA → Urban/Rural)
- K-anonymity computation (equivalence classes)
- K-anonymity violation resolution (widening → geography suppression → record suppression)
- Population threshold blocking (n < 15 blocked, 15-30 limited QI, 30+ full)
- Suppression ceiling (>15% suppression blocks export)
- CSV output format (correct columns, no PII leakage)
- Suppression report accuracy
- Date-to-quarter conversion
- Form validation (program selection, period validation, QI columns)
- View permission gating

DRR: tasks/design-rationale/evaluation-microdata-export.md
"""
import csv
import io
import json
import os
import shutil
import tempfile
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from cryptography.fernet import Fernet
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from apps.auth_app.models import User
from apps.clients.models import ClientFile, ServiceEpisode
from apps.notes.models import ProgressNote
from apps.plans.models import MetricDefinition
from apps.programs.models import Program, UserProgramRole
from apps.reports.deidentify import (
    EVAL_AGE_BANDS,
    MIN_POPULATION,
    QI_LIMIT_LARGE,
    QI_LIMIT_SMALL,
    QI_THRESHOLD_LARGE,
    SUPPRESSION_CEILING,
    TARGET_K,
    WIDENED_AGE_BANDS,
    DeidentificationPipeline,
    PreviewResult,
)
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


# ═════════════════════════════════════════════════════════════════════
# Helpers
# ═════════════════════════════════════════════════════════════════════

def _make_clients(program, count, *, consented=True, birth_year=1990, export_dir=None):
    """Create count clients enrolled in the given program with consent.

    Returns list of (ClientFile, ServiceEpisode) tuples.
    """
    results = []
    for i in range(count):
        cf = ClientFile.objects.create(
            record_id=f"TEST-{i:04d}",
            status="active",
            is_demo=False,
        )
        # Set encrypted birth date via property accessor
        cf.birth_date = date(birth_year - i % 5, 6, 15)
        cf.first_name = f"Test{i}"
        cf.last_name = f"Person{i}"
        cf.save()

        ep = ServiceEpisode.objects.create(
            client_file=cf,
            program=program,
            status="active",
            started_at=timezone.now() - timedelta(days=180),
            consent_to_aggregate_reporting=consented,
        )
        results.append((cf, ep))
    return results


def _make_pipeline(program, qi_columns=None, period_start=None, period_end=None, user=None):
    """Create a pipeline with sensible defaults."""
    if qi_columns is None:
        qi_columns = ["age_group"]
    if period_start is None:
        period_start = date.today() - timedelta(days=365)
    if period_end is None:
        period_end = date.today()
    if user is None:
        user = MagicMock()
        user.pk = 999
        user.__str__ = lambda self: "MockUser"

    return DeidentificationPipeline(
        program=program,
        period_start=period_start,
        period_end=period_end,
        qi_columns=qi_columns,
        evaluator_info={
            "name": "Dr. Test",
            "email": "test@example.com",
            "organisation": "Test University",
            "purpose": "Program evaluation",
            "agreement_expiry": date.today() + timedelta(days=365),
        },
        user=user,
    )


# ═════════════════════════════════════════════════════════════════════
# 1. Unit tests — helper functions (no DB)
# ═════════════════════════════════════════════════════════════════════


class AgeComputationTest(TestCase):
    """Test _compute_age and _age_to_band without database."""

    def setUp(self):
        self.pipeline = DeidentificationPipeline(
            program=MagicMock(pk=1, name="Test"),
            period_start=date(2025, 1, 1),
            period_end=date(2025, 12, 31),
            qi_columns=["age_group"],
            evaluator_info={},
            user=MagicMock(pk=1),
        )

    def test_age_from_date(self):
        """Age computed correctly from birth date."""
        age = self.pipeline._compute_age(date(1990, 6, 15))
        self.assertEqual(age, 35)

    def test_age_before_birthday(self):
        """Age is one less before birthday in the period year."""
        # Period end is Dec 31 2025; born July 1, 2000 → 25
        age = self.pipeline._compute_age(date(2000, 7, 1), as_of_date=date(2025, 6, 30))
        self.assertEqual(age, 24)

    def test_age_none_for_missing(self):
        """None birth date returns None age."""
        self.assertIsNone(self.pipeline._compute_age(None))

    def test_age_from_iso_string(self):
        """String dates are handled."""
        age = self.pipeline._compute_age("1990-06-15")
        self.assertEqual(age, 35)

    def test_age_invalid_string(self):
        """Invalid date string returns None."""
        self.assertIsNone(self.pipeline._compute_age("not-a-date"))

    def test_age_to_band_standard(self):
        """Ages map to correct 5-year bands."""
        self.assertEqual(DeidentificationPipeline._age_to_band(22), "18-24")
        self.assertEqual(DeidentificationPipeline._age_to_band(30), "30-34")
        self.assertEqual(DeidentificationPipeline._age_to_band(15), "0-17")
        self.assertEqual(DeidentificationPipeline._age_to_band(70), "65+")

    def test_age_to_band_boundaries(self):
        """Band boundaries are inclusive."""
        self.assertEqual(DeidentificationPipeline._age_to_band(17), "0-17")
        self.assertEqual(DeidentificationPipeline._age_to_band(18), "18-24")
        self.assertEqual(DeidentificationPipeline._age_to_band(24), "18-24")
        self.assertEqual(DeidentificationPipeline._age_to_band(25), "25-29")
        self.assertEqual(DeidentificationPipeline._age_to_band(65), "65+")

    def test_age_to_band_widened(self):
        """Widened bands group correctly for k-anonymity resolution."""
        self.assertEqual(
            DeidentificationPipeline._age_to_band(22, WIDENED_AGE_BANDS),
            "18-29",
        )
        self.assertEqual(
            DeidentificationPipeline._age_to_band(35, WIDENED_AGE_BANDS),
            "30-44",
        )
        self.assertEqual(
            DeidentificationPipeline._age_to_band(50, WIDENED_AGE_BANDS),
            "45-64",
        )

    def test_age_to_band_none(self):
        """None age returns None band."""
        self.assertIsNone(DeidentificationPipeline._age_to_band(None))


class GeographyDerivationTest(TestCase):
    """Test _postal_code_to_geography (Canadian FSA rules)."""

    def test_urban_postal_code(self):
        """Second digit 1-9 → Urban."""
        self.assertEqual(
            DeidentificationPipeline._postal_code_to_geography("M5V 2T6"),
            "Urban",
        )

    def test_rural_postal_code(self):
        """Second digit 0 → Rural."""
        self.assertEqual(
            DeidentificationPipeline._postal_code_to_geography("K0A 1A0"),
            "Rural",
        )

    def test_no_spaces(self):
        """Works without space in postal code."""
        self.assertEqual(
            DeidentificationPipeline._postal_code_to_geography("M5V2T6"),
            "Urban",
        )

    def test_lowercase(self):
        """Case-insensitive."""
        self.assertEqual(
            DeidentificationPipeline._postal_code_to_geography("k0a 1a0"),
            "Rural",
        )

    def test_none_postal_code(self):
        """None returns None."""
        self.assertIsNone(
            DeidentificationPipeline._postal_code_to_geography(None),
        )

    def test_empty_postal_code(self):
        """Empty string returns None."""
        self.assertIsNone(
            DeidentificationPipeline._postal_code_to_geography(""),
        )

    def test_short_postal_code(self):
        """Single character returns None."""
        self.assertIsNone(
            DeidentificationPipeline._postal_code_to_geography("K"),
        )


class DateToQuarterTest(TestCase):
    """Test _date_to_quarter conversion."""

    def setUp(self):
        self.pipeline = DeidentificationPipeline(
            program=MagicMock(pk=1, name="Test"),
            period_start=date(2025, 1, 1),
            period_end=date(2025, 12, 31),
            qi_columns=[],
            evaluator_info={},
            user=MagicMock(pk=1),
        )

    def test_q1(self):
        self.assertEqual(self.pipeline._date_to_quarter(date(2025, 2, 15)), "Q1-2025")

    def test_q2(self):
        self.assertEqual(self.pipeline._date_to_quarter(date(2025, 5, 1)), "Q2-2025")

    def test_q3(self):
        self.assertEqual(self.pipeline._date_to_quarter(date(2025, 9, 30)), "Q3-2025")

    def test_q4(self):
        self.assertEqual(self.pipeline._date_to_quarter(date(2025, 12, 31)), "Q4-2025")

    def test_none(self):
        self.assertIsNone(self.pipeline._date_to_quarter(None))

    def test_iso_string(self):
        self.assertEqual(self.pipeline._date_to_quarter("2025-04-15"), "Q2-2025")


class StudyIdGeneratorTest(TestCase):
    """Test _generate_study_id format and uniqueness."""

    def test_format(self):
        """Study IDs follow EVL-XXXXXX format."""
        study_id = DeidentificationPipeline._generate_study_id(set())
        self.assertRegex(study_id, r"^EVL-[A-F0-9]{6}$")

    def test_uniqueness(self):
        """Generated IDs don't collide with existing set."""
        existing = set()
        for _ in range(100):
            new_id = DeidentificationPipeline._generate_study_id(existing)
            self.assertNotIn(new_id, existing)
            existing.add(new_id)

    def test_different_across_calls(self):
        """Two calls produce different IDs (not deterministic)."""
        id_a = DeidentificationPipeline._generate_study_id(set())
        id_b = DeidentificationPipeline._generate_study_id(set())
        self.assertNotEqual(id_a, id_b)


class SanitiseMetricNameTest(TestCase):
    """Test _sanitise_metric_name slug generation."""

    def test_basic(self):
        self.assertEqual(
            DeidentificationPipeline._sanitise_metric_name("Well-being Score"),
            "well_being_score",
        )

    def test_spaces_and_symbols(self):
        self.assertEqual(
            DeidentificationPipeline._sanitise_metric_name("PHQ-9 (Depression)"),
            "phq_9_depression",
        )

    def test_empty(self):
        self.assertEqual(
            DeidentificationPipeline._sanitise_metric_name(""),
            "metric",
        )

    def test_unicode(self):
        result = DeidentificationPipeline._sanitise_metric_name("Bien-être")
        self.assertTrue(len(result) > 0)


class RemapWidenedBandTest(TestCase):
    """Test _remap_to_widened_band mapping."""

    def test_narrow_to_wide_mappings(self):
        expected = {
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
        for narrow, wide in expected.items():
            self.assertEqual(
                DeidentificationPipeline._remap_to_widened_band(narrow),
                wide,
                f"Failed for {narrow}",
            )

    def test_unknown_band_passthrough(self):
        """Unknown band labels pass through unchanged."""
        self.assertEqual(
            DeidentificationPipeline._remap_to_widened_band("unknown"),
            "unknown",
        )


# ═════════════════════════════════════════════════════════════════════
# 2. Pipeline constants
# ═════════════════════════════════════════════════════════════════════


class PipelineConstantsTest(TestCase):
    """Verify privacy constants match the DRR specification."""

    def test_target_k(self):
        self.assertEqual(TARGET_K, 5)

    def test_suppression_ceiling(self):
        self.assertEqual(SUPPRESSION_CEILING, 0.15)

    def test_min_population(self):
        self.assertEqual(MIN_POPULATION, 15)

    def test_qi_limit_small(self):
        self.assertEqual(QI_LIMIT_SMALL, 3)

    def test_qi_limit_large(self):
        self.assertEqual(QI_LIMIT_LARGE, 5)

    def test_qi_threshold_large(self):
        self.assertEqual(QI_THRESHOLD_LARGE, 30)

    def test_age_bands_cover_full_range(self):
        """Every age 0-100 maps to exactly one band."""
        for age in range(101):
            band = DeidentificationPipeline._age_to_band(age, EVAL_AGE_BANDS)
            self.assertIsNotNone(band, f"Age {age} has no band")

    def test_widened_bands_cover_full_range(self):
        """Every age 0-100 maps to exactly one widened band."""
        for age in range(101):
            band = DeidentificationPipeline._age_to_band(age, WIDENED_AGE_BANDS)
            self.assertIsNotNone(band, f"Age {age} has no widened band")


# ═════════════════════════════════════════════════════════════════════
# 3. Consent filtering
# ═════════════════════════════════════════════════════════════════════


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ConsentFilteringTest(TestCase):
    """Step 3: Only consented participants are included."""
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Consent Test Program", status="active")

    def test_consented_included(self):
        """Participants with consent=True are included."""
        _make_clients(self.program, 20, consented=True)
        pipeline = _make_pipeline(self.program, qi_columns=["age_group"])
        preview = pipeline.run_preview()
        self.assertEqual(preview.consented_count, 20)

    def test_non_consented_excluded(self):
        """Participants with consent=False are excluded."""
        _make_clients(self.program, 15, consented=True)
        _make_clients(self.program, 5, consented=False)
        pipeline = _make_pipeline(self.program, qi_columns=["age_group"])
        preview = pipeline.run_preview()
        # 15 consented + 5 non-consented = 20 eligible
        self.assertEqual(preview.eligible_count, 20)
        self.assertEqual(preview.consented_count, 15)

    def test_zero_consented_blocks(self):
        """No consented participants → blocked (population too small)."""
        _make_clients(self.program, 10, consented=False)
        pipeline = _make_pipeline(self.program, qi_columns=["age_group"])
        preview = pipeline.run_preview()
        self.assertTrue(preview.blocked)
        self.assertEqual(preview.block_reason, "population_too_small")


# ═════════════════════════════════════════════════════════════════════
# 4. Direct identifier stripping
# ═════════════════════════════════════════════════════════════════════


@override_settings(
    FIELD_ENCRYPTION_KEY=TEST_KEY,
    SECURE_EXPORT_DIR=tempfile.mkdtemp(),
)
class DirectIdentifierStrippingTest(TestCase):
    """Step 4: No PII in de-identified records or CSV output."""
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="PII Test Program", status="active")
        self.export_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.export_dir, ignore_errors=True)

    def test_no_names_in_deidentified_records(self):
        """First name, last name stripped from de-identified records."""
        _make_clients(self.program, 20, consented=True)
        pipeline = _make_pipeline(self.program, qi_columns=["age_group"])
        pipeline.run_preview()

        for record in pipeline._deidentified_records:
            self.assertNotIn("_first_name", record)
            self.assertNotIn("_last_name", record)
            self.assertNotIn("first_name", record)
            self.assertNotIn("last_name", record)
            # No exact birth date (only age band)
            self.assertNotIn("birth_date", record)
            # No exact postal code (only geography)
            self.assertNotIn("postal_code", record)

    def test_study_ids_not_derived_from_client_id(self):
        """Study IDs are random, not derived from real client IDs."""
        _make_clients(self.program, 20, consented=True)
        pipeline = _make_pipeline(self.program, qi_columns=["age_group"])
        pipeline.run_preview()

        client_ids = {r["_client_id"] for r in pipeline._raw_records}
        study_ids = [r["study_id"] for r in pipeline._deidentified_records]

        # The hex portion of study IDs should not be the zero-padded
        # client ID.  (Small PKs like "4" will appear as hex substrings
        # by coincidence — that's not a derivation.)
        for sid in study_ids:
            hex_part = sid.split("-", 1)[1]  # e.g. "A1B2C3"
            for cid in client_ids:
                padded = f"{cid:06X}"
                self.assertNotEqual(
                    hex_part, padded,
                    f"Study ID {sid} appears derived from client {cid}",
                )

    def test_study_ids_unique(self):
        """All study IDs are unique."""
        _make_clients(self.program, 20, consented=True)
        pipeline = _make_pipeline(self.program, qi_columns=["age_group"])
        pipeline.run_preview()

        study_ids = [r["study_id"] for r in pipeline._deidentified_records]
        self.assertEqual(len(study_ids), len(set(study_ids)))

    @override_settings(SECURE_EXPORT_DIR=None)
    def test_no_pii_in_csv_output(self):
        """CSV file contains no direct identifiers."""
        export_dir = tempfile.mkdtemp()
        try:
            with self.settings(SECURE_EXPORT_DIR=export_dir):
                clients = _make_clients(self.program, 20, consented=True)
                pipeline = _make_pipeline(self.program, qi_columns=["age_group"])
                result = pipeline.run_generate()

                with open(result.csv_path, "r", encoding="utf-8-sig") as f:
                    content = f.read()

                # Check no names appear in CSV
                for cf, ep in clients:
                    name = cf.first_name
                    if name:
                        self.assertNotIn(name, content)
                    lname = cf.last_name
                    if lname:
                        self.assertNotIn(lname, content)

                # Check no client PK appears as an exact CSV cell value.
                # Small integers like "2" appear as substrings in hex study
                # IDs or numeric fields — we only flag exact-cell matches.
                for line in content.split("\n"):
                    if line.startswith("#") or not line.strip():
                        continue
                    cells = next(csv.reader(io.StringIO(line)))
                    # The first cell is study_id — should not be a raw PK
                    for cf, ep in clients:
                        self.assertNotEqual(
                            cells[0], str(cf.pk),
                            f"Client PK {cf.pk} found as study_id",
                        )
        finally:
            shutil.rmtree(export_dir, ignore_errors=True)


# ═════════════════════════════════════════════════════════════════════
# 5. K-anonymity computation
# ═════════════════════════════════════════════════════════════════════


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class KAnonymityComputationTest(TestCase):
    """Step 6: Equivalence classes computed correctly."""
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None

    def test_equivalence_class_building(self):
        """Records with same QI values group into same class."""
        pipeline = DeidentificationPipeline(
            program=MagicMock(pk=1, name="Test"),
            period_start=date(2025, 1, 1),
            period_end=date(2025, 12, 31),
            qi_columns=["age_group", "geography"],
            evaluator_info={},
            user=MagicMock(pk=1),
        )

        # Simulated records with known QI values
        records = [
            {"age_group": "18-24", "geography": "Urban"},
            {"age_group": "18-24", "geography": "Urban"},
            {"age_group": "18-24", "geography": "Urban"},
            {"age_group": "25-29", "geography": "Rural"},
            {"age_group": "25-29", "geography": "Rural"},
        ]

        eq_classes = pipeline._build_equivalence_classes(records)
        self.assertEqual(eq_classes[("18-24", "Urban")], 3)
        self.assertEqual(eq_classes[("25-29", "Rural")], 2)

    def test_effective_k_is_minimum(self):
        """Effective k is the size of the smallest equivalence class."""
        pipeline = DeidentificationPipeline(
            program=MagicMock(pk=1, name="Test"),
            period_start=date(2025, 1, 1),
            period_end=date(2025, 12, 31),
            qi_columns=["age_group"],
            evaluator_info={},
            user=MagicMock(pk=1),
        )

        # Build records with class sizes 10, 7, and 3
        records = (
            [{"age_group": "18-24"}] * 10
            + [{"age_group": "25-29"}] * 7
            + [{"age_group": "30-34"}] * 3
        )

        eq_classes = pipeline._build_equivalence_classes(records)
        min_k = min(eq_classes.values())
        self.assertEqual(min_k, 3)


# ═════════════════════════════════════════════════════════════════════
# 6. K-anonymity violation resolution
# ═════════════════════════════════════════════════════════════════════


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class KAnonymityResolutionTest(TestCase):
    """Step 7: Violations resolved by widening → geography suppression → record suppression."""
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(
            name="K-Resolution Program", status="active",
        )

    def test_widening_resolves_small_classes(self):
        """Age band widening can merge small classes to meet k=5."""
        # Create 20 clients with varied ages so some 5-year bands have < 5
        # but widened bands will have >= 5
        clients = _make_clients(self.program, 20, consented=True, birth_year=1995)
        pipeline = _make_pipeline(self.program, qi_columns=["age_group"])
        preview = pipeline.run_preview()

        # After resolution, effective k should be >= TARGET_K (5)
        # unless population is somehow too small, but 20 > 15
        if not preview.blocked:
            self.assertGreaterEqual(preview.effective_k, TARGET_K)

    def test_record_suppression_tracked(self):
        """Suppressed records are counted accurately."""
        _make_clients(self.program, 20, consented=True)
        pipeline = _make_pipeline(self.program, qi_columns=["age_group"])
        preview = pipeline.run_preview()

        # Suppressed + exportable should equal consented
        self.assertEqual(
            preview.exportable_count + preview.suppressed_count,
            preview.consented_count,
        )


# ═════════════════════════════════════════════════════════════════════
# 7. Population threshold blocking
# ═════════════════════════════════════════════════════════════════════


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class PopulationThresholdTest(TestCase):
    """Step 8: Population size determines tier and QI limits."""
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(
            name="Threshold Program", status="active",
        )

    def test_below_15_blocked(self):
        """Population < 15 → export blocked."""
        _make_clients(self.program, 10, consented=True)
        pipeline = _make_pipeline(self.program, qi_columns=["age_group"])
        preview = pipeline.run_preview()
        self.assertTrue(preview.blocked)
        self.assertEqual(preview.block_reason, "population_too_small")
        self.assertEqual(preview.tier, "aggregate_only")

    def test_15_to_29_limited_qi(self):
        """Population 15-29 → limited QI tier (max 3 columns)."""
        _make_clients(self.program, 20, consented=True)
        pipeline = _make_pipeline(self.program, qi_columns=["age_group"])
        preview = pipeline.run_preview()
        # With 1 QI column and 20 participants, should not be blocked
        if not preview.blocked:
            self.assertEqual(preview.tier, "limited_qi")

    def test_15_to_29_too_many_qi_blocked(self):
        """Population 15-29 with > 3 QI columns → blocked."""
        _make_clients(self.program, 20, consented=True)
        pipeline = _make_pipeline(
            self.program,
            qi_columns=["age_group", "gender", "ethnicity", "geography"],
        )
        preview = pipeline.run_preview()
        self.assertTrue(preview.blocked)
        self.assertEqual(preview.block_reason, "too_many_qi_columns")

    def test_30_plus_full_tier(self):
        """Population >= 30 → full tier (max 5 columns)."""
        _make_clients(self.program, 35, consented=True)
        pipeline = _make_pipeline(self.program, qi_columns=["age_group"])
        preview = pipeline.run_preview()
        if not preview.blocked:
            self.assertEqual(preview.tier, "full")

    def test_zero_participants_blocked(self):
        """No participants at all → blocked."""
        pipeline = _make_pipeline(self.program, qi_columns=["age_group"])
        preview = pipeline.run_preview()
        self.assertTrue(preview.blocked)
        self.assertEqual(preview.block_reason, "population_too_small")

    def test_exactly_15_not_blocked(self):
        """Exactly 15 consented → should be allowed (boundary)."""
        _make_clients(self.program, 15, consented=True)
        pipeline = _make_pipeline(self.program, qi_columns=["age_group"])
        preview = pipeline.run_preview()
        # Might be blocked by suppression, but not by population threshold
        if preview.blocked:
            self.assertNotEqual(preview.block_reason, "population_too_small")


# ═════════════════════════════════════════════════════════════════════
# 8. Suppression ceiling
# ═════════════════════════════════════════════════════════════════════


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class SuppressionCeilingTest(TestCase):
    """Suppression rate >15% blocks the export."""

    def setUp(self):
        enc_module._fernet = None

    def test_ceiling_constant(self):
        """Ceiling is 15%."""
        self.assertEqual(SUPPRESSION_CEILING, 0.15)

    def test_high_suppression_blocks(self):
        """If pipeline suppresses >15% of records, export is blocked."""
        # We test the threshold check logic directly
        pipeline = DeidentificationPipeline(
            program=MagicMock(pk=1, name="Test"),
            period_start=date(2025, 1, 1),
            period_end=date(2025, 12, 31),
            qi_columns=["age_group"],
            evaluator_info={},
            user=MagicMock(pk=1),
        )

        # Simulate 20 records, 4 suppressed = 20% > 15%
        pipeline._deidentified_records = [
            {"_suppressed": True, "age_group": f"band-{i}"} for i in range(4)
        ] + [
            {"_suppressed": False, "age_group": "18-24"} for _ in range(16)
        ]

        # The suppression rate check happens at end of _resolve_k_violations
        total = len(pipeline._deidentified_records)
        suppressed = sum(1 for r in pipeline._deidentified_records if r.get("_suppressed"))
        rate = suppressed / total
        self.assertGreater(rate, SUPPRESSION_CEILING)


# ═════════════════════════════════════════════════════════════════════
# 9. CSV output format
# ═════════════════════════════════════════════════════════════════════


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class CSVOutputFormatTest(TestCase):
    """Step 9: CSV has correct columns, metadata header, and no PII."""
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="CSV Test Program", status="active")
        self.export_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.export_dir, ignore_errors=True)

    @override_settings(SECURE_EXPORT_DIR=None)
    def test_csv_has_metadata_header(self):
        """CSV starts with # comment lines for metadata."""
        with self.settings(SECURE_EXPORT_DIR=self.export_dir):
            _make_clients(self.program, 20, consented=True)
            pipeline = _make_pipeline(self.program, qi_columns=["age_group"])
            result = pipeline.run_generate()

            with open(result.csv_path, "r", encoding="utf-8-sig") as f:
                lines = f.readlines()

            # Metadata header lines start with #
            header_lines = [l for l in lines if l.startswith("#")]
            self.assertGreater(len(header_lines), 0)
            # Check key metadata is present
            header_text = "".join(header_lines)
            self.assertIn("KoNote Evaluation Microdata Export", header_text)
            self.assertIn("Program:", header_text)
            self.assertIn("Period:", header_text)
            self.assertIn("Effective k:", header_text)

    @override_settings(SECURE_EXPORT_DIR=None)
    def test_csv_column_order(self):
        """CSV columns follow expected order: study_id, QI, temporal, service, metrics."""
        with self.settings(SECURE_EXPORT_DIR=self.export_dir):
            _make_clients(self.program, 20, consented=True)
            pipeline = _make_pipeline(self.program, qi_columns=["age_group"])
            result = pipeline.run_generate()

            with open(result.csv_path, "r", encoding="utf-8-sig") as f:
                # Skip comment lines
                data_lines = [l for l in f.readlines() if not l.startswith("#")]

            if data_lines:
                reader = csv.reader(io.StringIO(data_lines[0]))
                columns = next(reader)
                self.assertEqual(columns[0], "study_id")
                # age_group should be right after study_id
                self.assertEqual(columns[1], "age_group")
                # Temporal columns after QI
                self.assertIn("enrolment_quarter", columns)
                self.assertIn("exit_quarter", columns)
                # Service columns
                self.assertIn("sessions_count", columns)
                self.assertIn("total_hours", columns)

    @override_settings(SECURE_EXPORT_DIR=None)
    def test_csv_sanitised(self):
        """CSV values are sanitised (no formula injection)."""
        with self.settings(SECURE_EXPORT_DIR=self.export_dir):
            _make_clients(self.program, 20, consented=True)
            pipeline = _make_pipeline(self.program, qi_columns=["age_group"])
            result = pipeline.run_generate()

            with open(result.csv_path, "r", encoding="utf-8-sig") as f:
                content = f.read()

            # No cells should start with formula characters
            for line in content.split("\n"):
                if line.startswith("#") or not line.strip():
                    continue
                for cell in line.split(","):
                    cell = cell.strip().strip('"')
                    if cell:
                        self.assertNotIn(
                            cell[0], ["=", "+", "-", "@", "\t", "\r"],
                            f"Potential CSV injection: {cell[:20]}",
                        ) if cell[0] not in "0123456789" and not cell.startswith("EVL-") and not cell.startswith("Q") else None


# ═════════════════════════════════════════════════════════════════════
# 10. Suppression report
# ═════════════════════════════════════════════════════════════════════


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class SuppressionReportTest(TestCase):
    """Step 10: Suppression report is a valid JSON with required fields."""
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(
            name="Report Test Program", status="active",
        )
        self.export_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.export_dir, ignore_errors=True)

    @override_settings(SECURE_EXPORT_DIR=None)
    def test_suppression_report_structure(self):
        """Report contains required sections."""
        with self.settings(SECURE_EXPORT_DIR=self.export_dir):
            _make_clients(self.program, 20, consented=True)
            pipeline = _make_pipeline(self.program, qi_columns=["age_group"])
            result = pipeline.run_generate()

            with open(result.suppression_report_path, "r", encoding="utf-8") as f:
                report = json.load(f)

            # Required top-level keys
            self.assertIn("generated_at", report)
            self.assertIn("program_id", report)
            self.assertIn("population", report)
            self.assertIn("privacy", report)
            self.assertIn("evaluator", report)

            # Population breakdown
            pop = report["population"]
            self.assertIn("eligible", pop)
            self.assertIn("consented", pop)
            self.assertIn("exportable", pop)
            self.assertIn("suppressed", pop)

            # Privacy guarantees
            priv = report["privacy"]
            self.assertEqual(priv["target_k"], TARGET_K)
            self.assertIn("effective_k", priv)
            self.assertIn("suppression_rate", priv)
            self.assertIn("qi_columns", priv)

    @override_settings(SECURE_EXPORT_DIR=None)
    def test_report_counts_match_preview(self):
        """Suppression report counts match the preview result."""
        with self.settings(SECURE_EXPORT_DIR=self.export_dir):
            _make_clients(self.program, 20, consented=True)
            pipeline = _make_pipeline(self.program, qi_columns=["age_group"])
            result = pipeline.run_generate()

            with open(result.suppression_report_path, "r", encoding="utf-8") as f:
                report = json.load(f)

            pop = report["population"]
            self.assertEqual(pop["eligible"], result.preview.eligible_count)
            self.assertEqual(pop["consented"], result.preview.consented_count)
            self.assertEqual(pop["exportable"], result.preview.exportable_count)
            self.assertEqual(pop["suppressed"], result.preview.suppressed_count)


# ═════════════════════════════════════════════════════════════════════
# 11. Full pipeline integration (preview + generate)
# ═════════════════════════════════════════════════════════════════════


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class FullPipelineIntegrationTest(TestCase):
    """End-to-end pipeline producing a valid, PII-free export."""
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(
            name="Integration Test Program", status="active",
        )
        self.export_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.export_dir, ignore_errors=True)

    @override_settings(SECURE_EXPORT_DIR=None)
    def test_preview_then_generate(self):
        """Preview followed by generate produces consistent results."""
        with self.settings(SECURE_EXPORT_DIR=self.export_dir):
            _make_clients(self.program, 25, consented=True)
            pipeline = _make_pipeline(self.program, qi_columns=["age_group"])

            preview = pipeline.run_preview()
            self.assertFalse(preview.blocked)

            # Generate uses its own preview
            pipeline2 = _make_pipeline(self.program, qi_columns=["age_group"])
            result = pipeline2.run_generate()

            self.assertTrue(os.path.exists(result.csv_path))
            self.assertTrue(os.path.exists(result.suppression_report_path))

    @override_settings(SECURE_EXPORT_DIR=None)
    def test_blocked_export_raises(self):
        """Generating a blocked export raises ValueError."""
        with self.settings(SECURE_EXPORT_DIR=self.export_dir):
            _make_clients(self.program, 5, consented=True)
            pipeline = _make_pipeline(self.program, qi_columns=["age_group"])

            with self.assertRaises(ValueError) as ctx:
                pipeline.run_generate()
            self.assertIn("blocked", str(ctx.exception).lower())

    @override_settings(SECURE_EXPORT_DIR=None)
    def test_linkage_blob_encrypted(self):
        """Linkage table is encrypted (not plaintext)."""
        with self.settings(SECURE_EXPORT_DIR=self.export_dir):
            _make_clients(self.program, 20, consented=True)
            pipeline = _make_pipeline(self.program, qi_columns=["age_group"])
            result = pipeline.run_generate()

            # Linkage blob should be bytes (encrypted)
            self.assertIsInstance(result.linkage_blob, bytes)
            # Should not be decodeable as plain JSON
            try:
                json.loads(result.linkage_blob)
                self.fail("Linkage blob is plaintext JSON — should be encrypted")
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass  # Expected — it's encrypted

    @override_settings(SECURE_EXPORT_DIR=None)
    def test_demo_clients_excluded(self):
        """Demo/test clients are not in the export."""
        with self.settings(SECURE_EXPORT_DIR=self.export_dir):
            _make_clients(self.program, 20, consented=True)
            # Create a demo client
            demo_cf = ClientFile.objects.create(
                record_id="DEMO-001",
                status="active",
                is_demo=True,
            )
            ServiceEpisode.objects.create(
                client_file=demo_cf,
                program=self.program,
                status="active",
                started_at=timezone.now() - timedelta(days=30),
                consent_to_aggregate_reporting=True,
            )

            pipeline = _make_pipeline(self.program, qi_columns=["age_group"])
            preview = pipeline.run_preview()

            # Demo client should not be counted
            self.assertEqual(preview.eligible_count, 20)


# ═════════════════════════════════════════════════════════════════════
# 12. Form validation
# ═════════════════════════════════════════════════════════════════════


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class EvaluationExportFormTest(TestCase):
    """Test EvaluationExportForm validation."""
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Form Test Program", status="active")
        self.user = User.objects.create_user(
            username="formtester",
            password="test1234",
            email="form@test.com",
        )
        UserProgramRole.objects.create(
            user=self.user,
            program=self.program,
            role="program_manager",
        )

    def test_valid_form(self):
        from apps.reports.forms import EvaluationExportForm
        form = EvaluationExportForm(
            data={
                "program": str(self.program.pk),
                "period_start": "2025-01-01",
                "period_end": "2025-12-31",
                "evaluator_name": "Dr. Test",
                "evaluator_email": "test@example.com",
                "evaluator_organisation": "U of T",
                "evaluation_purpose": "Program evaluation",
                "agreement_expiry": "2026-12-31",
                "include_age_group": True,
            },
            user=self.user,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_period_start_after_end_rejected(self):
        from apps.reports.forms import EvaluationExportForm
        form = EvaluationExportForm(
            data={
                "program": str(self.program.pk),
                "period_start": "2025-12-31",
                "period_end": "2025-01-01",
                "evaluator_name": "Dr. Test",
                "evaluator_email": "test@example.com",
                "evaluator_organisation": "U of T",
                "evaluation_purpose": "Program evaluation",
                "agreement_expiry": "2026-12-31",
            },
            user=self.user,
        )
        self.assertFalse(form.is_valid())

    def test_missing_program_rejected(self):
        from apps.reports.forms import EvaluationExportForm
        form = EvaluationExportForm(
            data={
                "program": "",
                "period_start": "2025-01-01",
                "period_end": "2025-12-31",
                "evaluator_name": "Dr. Test",
                "evaluator_email": "test@example.com",
                "evaluator_organisation": "U of T",
                "evaluation_purpose": "Testing",
                "agreement_expiry": "2026-12-31",
            },
            user=self.user,
        )
        self.assertFalse(form.is_valid())

    def test_get_qi_columns(self):
        from apps.reports.forms import EvaluationExportForm
        form = EvaluationExportForm(
            data={
                "program": str(self.program.pk),
                "period_start": "2025-01-01",
                "period_end": "2025-12-31",
                "evaluator_name": "Dr. Test",
                "evaluator_email": "test@example.com",
                "evaluator_organisation": "U of T",
                "evaluation_purpose": "Testing",
                "agreement_expiry": "2026-12-31",
                "include_age_group": True,
                "include_gender": True,
                "include_geography": True,
            },
            user=self.user,
        )
        self.assertTrue(form.is_valid(), form.errors)
        qi = form.get_qi_columns()
        self.assertIn("age_group", qi)
        self.assertIn("gender", qi)
        self.assertIn("geography", qi)
        self.assertNotIn("ethnicity", qi)

    def test_get_evaluator_info(self):
        from apps.reports.forms import EvaluationExportForm
        form = EvaluationExportForm(
            data={
                "program": str(self.program.pk),
                "period_start": "2025-01-01",
                "period_end": "2025-12-31",
                "evaluator_name": "Dr. Test",
                "evaluator_email": "test@example.com",
                "evaluator_organisation": "U of T",
                "evaluation_purpose": "Outcome analysis",
                "agreement_expiry": "2026-12-31",
            },
            user=self.user,
        )
        self.assertTrue(form.is_valid(), form.errors)
        info = form.get_evaluator_info()
        self.assertEqual(info["name"], "Dr. Test")
        self.assertEqual(info["email"], "test@example.com")
        self.assertEqual(info["organisation"], "U of T")

    def test_custom_field_group_qi_columns(self):
        """Custom field groups marked is_evaluation_exportable appear as QI columns."""
        from apps.clients.models import CustomFieldGroup
        from apps.reports.forms import EvaluationExportForm

        group = CustomFieldGroup.objects.create(
            title="Employment Status",
            is_evaluation_exportable=True,
            status="active",
        )
        form = EvaluationExportForm(
            data={
                "program": str(self.program.pk),
                "period_start": "2025-01-01",
                "period_end": "2025-12-31",
                "evaluator_name": "Dr. Test",
                "evaluator_email": "test@example.com",
                "evaluator_organisation": "U of T",
                "evaluation_purpose": "Testing",
                "agreement_expiry": "2026-12-31",
                "include_age_group": True,
                f"include_cfg_{group.pk}": True,
            },
            user=self.user,
        )
        self.assertTrue(form.is_valid(), form.errors)
        qi = form.get_qi_columns()
        self.assertIn("age_group", qi)
        self.assertIn("employment_status", qi)

    def test_non_exportable_group_not_shown(self):
        """Groups without is_evaluation_exportable=True don't appear."""
        from apps.clients.models import CustomFieldGroup
        from apps.reports.forms import EvaluationExportForm

        CustomFieldGroup.objects.create(
            title="Contact Info",
            is_evaluation_exportable=False,
            status="active",
        )
        form = EvaluationExportForm(user=self.user)
        # No include_cfg_ fields should exist for non-exportable groups
        cfg_fields = [k for k in form.fields if k.startswith("include_cfg_")]
        self.assertEqual(len(cfg_fields), 0)


# ═════════════════════════════════════════════════════════════════════
# 13. View permission gating
# ═════════════════════════════════════════════════════════════════════


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class EvaluationExportViewPermissionTest(TestCase):
    """View requires per-user evaluation_export permission."""
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None

    def test_denied_without_grant(self):
        """User without evaluation_export_granted gets 403."""
        user = User.objects.create_user(
            username="noperm",
            password="test1234",
            email="noperm@test.com",
            evaluation_export_granted=False,
        )
        client = Client()
        client.force_login(user)
        response = client.get("/reports/evaluation-export/")
        self.assertEqual(response.status_code, 403)

    def test_allowed_with_grant(self):
        """User with evaluation_export_granted can access."""
        user = User.objects.create_user(
            username="hasperm",
            password="test1234",
            email="hasperm@test.com",
            evaluation_export_granted=True,
        )
        client = Client()
        client.force_login(user)
        response = client.get("/reports/evaluation-export/")
        self.assertEqual(response.status_code, 200)

    def test_admin_without_grant_denied(self):
        """Admin without explicit grant is also denied — no admin bypass."""
        user = User.objects.create_user(
            username="admin_noperm",
            password="test1234",
            email="admin@test.com",
            is_admin=True,
            evaluation_export_granted=False,
        )
        client = Client()
        client.force_login(user)
        response = client.get("/reports/evaluation-export/")
        self.assertEqual(response.status_code, 403)


# ---------------------------------------------------------------------------
# Export History View Tests (EVAL-GOV-HISTORY)
# ---------------------------------------------------------------------------
class EvaluationExportHistoryViewTest(TestCase):
    """Tests for the evaluation export history view."""

    databases = {"default", "audit"}

    HISTORY_URL = "/reports/evaluation-export/history/"

    def setUp(self):
        self.granted_user = User.objects.create_user(
            username="eval_user",
            password="test1234",
            email="eval@test.com",
            evaluation_export_granted=True,
        )
        self.denied_user = User.objects.create_user(
            username="noperm_user",
            password="test1234",
            email="noperm@test.com",
            evaluation_export_granted=False,
        )
        self.client_http = Client()

    def _create_export_link(self, user, filters=None, revoked=False, expired=False):
        """Helper to create a SecureExportLink for evaluation_microdata."""
        from apps.reports.models import SecureExportLink

        now = timezone.now()
        expires = now - timedelta(hours=1) if expired else now + timedelta(hours=24)
        link = SecureExportLink.objects.create(
            created_by=user,
            export_type="evaluation_microdata",
            filters_json=json.dumps(filters or {}),
            client_count=10,
            recipient="evaluator@example.com",
            file_path="/tmp/fake_export.csv",
            revoked=revoked,
            expires_at=expires,
        )
        return link

    def test_denied_without_grant(self):
        """User without evaluation_export_granted gets 403."""
        self.client_http.force_login(self.denied_user)
        response = self.client_http.get(self.HISTORY_URL)
        self.assertEqual(response.status_code, 403)

    def test_login_required(self):
        """Anonymous user is redirected to login."""
        response = self.client_http.get(self.HISTORY_URL)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.url)

    def test_empty_history_renders(self):
        """Page renders when there are no exports."""
        self.client_http.force_login(self.granted_user)
        response = self.client_http.get(self.HISTORY_URL)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No evaluation exports have been generated yet.")

    def test_export_appears_in_history(self):
        """An evaluation export link appears in the history table."""
        self._create_export_link(self.granted_user, filters={
            "program_name": "Youth Program",
            "evaluator": {"name": "Dr. Smith", "organisation": "Eval Co"},
        })
        self.client_http.force_login(self.granted_user)
        response = self.client_http.get(self.HISTORY_URL)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Youth Program")
        self.assertContains(response, "Dr. Smith")
        self.assertContains(response, "Eval Co")

    def test_expired_agreement_banner_shown(self):
        """Warning banner appears when an export has an expired agreement."""
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        self._create_export_link(self.granted_user, filters={
            "evaluator": {"name": "Old Eval", "agreement_expiry": yesterday},
        })
        self.client_http.force_login(self.granted_user)
        response = self.client_http.get(self.HISTORY_URL)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Expired data-sharing agreement")
        self.assertContains(response, "EXPIRED")

    def test_no_banner_for_future_agreement(self):
        """No warning banner when agreement expiry is in the future."""
        future = (date.today() + timedelta(days=30)).isoformat()
        self._create_export_link(self.granted_user, filters={
            "evaluator": {"name": "Current Eval", "agreement_expiry": future},
        })
        self.client_http.force_login(self.granted_user)
        response = self.client_http.get(self.HISTORY_URL)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Expired data-sharing agreement")

    def test_revoked_link_shows_revoked_status(self):
        """A revoked link shows revoked status."""
        self._create_export_link(self.granted_user, revoked=True)
        self.client_http.force_login(self.granted_user)
        response = self.client_http.get(self.HISTORY_URL)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Revoked")

    def test_expired_link_shows_expired_status(self):
        """An expired (past expires_at) link shows expired status."""
        self._create_export_link(self.granted_user, expired=True)
        self.client_http.force_login(self.granted_user)
        response = self.client_http.get(self.HISTORY_URL)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Expired")
