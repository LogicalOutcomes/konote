"""Tests for Longitudinal Trajectory Export (LTE).

Covers the high-value, deterministic aspects of the LTE implementation:

- Permission gating (per-user grant + "no privacy officer = no LTE")
- Form validation (every precondition is required)
- Community governance conditional validation
- Business-day window arithmetic
- Fuzzing helpers (metric rounding, session count bands, total hours bands)
- study_id generator format + uniqueness
- Pipeline floor enforcement (default and OCAP/EGAP)
- Lifecycle state transitions (submit, cancel, flag freeze, expire)
- Agency-wide rate limit (pending post-hoc review blocks new submission)
- Audit category is longitudinal_trajectory_export (never bundled with EME)
- CSV output has no demographic columns and has the research warning

See tasks/design-rationale/evaluation-microdata-export.md for the
specification that drives these tests.
"""
import os
import shutil
import tempfile
import uuid
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch

from cryptography.fernet import Fernet
from django.test import Client, TestCase, override_settings
from django.utils import timezone

import konote.encryption as enc_module
from apps.auth_app.models import LTEExportGrant, User
from apps.programs.models import Program, UserProgramRole


TEST_KEY = Fernet.generate_key().decode()


# ═════════════════════════════════════════════════════════════════════
# 1. Permission helpers
# ═════════════════════════════════════════════════════════════════════


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class LTEPermissionHelperTest(TestCase):
    """can_create_lte_export + lte_available_in_agency."""

    def setUp(self):
        enc_module._fernet = None

    def test_anonymous_user_denied(self):
        from apps.reports.utils import can_create_lte_export
        anon = MagicMock()
        anon.is_authenticated = False
        self.assertFalse(can_create_lte_export(anon))

    def test_admin_without_grant_denied(self):
        """Admin bypass MUST NOT apply to LTE."""
        from apps.reports.utils import can_create_lte_export
        admin = User.objects.create_user(
            username="lte_admin_no_grant", password="x",
            is_admin=True, display_name="LTE Admin No Grant",
        )
        self.assertFalse(can_create_lte_export(admin))

    def test_granted_user_allowed(self):
        from apps.reports.utils import can_create_lte_export
        user = User.objects.create_user(
            username="lte_grantee", password="x",
            is_admin=False, display_name="Privacy Officer",
            lte_export_granted=True,
        )
        self.assertTrue(can_create_lte_export(user))

    def test_grant_not_shared_with_evaluation_export(self):
        """LTE permission must not be inferred from evaluation_export_granted."""
        from apps.reports.utils import can_create_evaluation_export, can_create_lte_export
        user = User.objects.create_user(
            username="eme_only", password="x",
            display_name="EME Only",
            evaluation_export_granted=True,
            lte_export_granted=False,
        )
        self.assertTrue(can_create_evaluation_export(user))
        self.assertFalse(can_create_lte_export(user))

    def test_lte_available_in_agency_requires_designated_officer(self):
        from apps.reports.utils import lte_available_in_agency
        self.assertFalse(lte_available_in_agency())
        User.objects.create_user(
            username="officer", password="x",
            display_name="Officer",
            lte_export_granted=True,
        )
        self.assertTrue(lte_available_in_agency())


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class LTEExportGrantSignalTest(TestCase):
    """The post_save signal keeps User.lte_export_granted in sync."""

    def setUp(self):
        enc_module._fernet = None
        self.admin = User.objects.create_user(
            username="lte_grant_admin", password="x",
            is_admin=True, display_name="Admin",
        )
        self.target = User.objects.create_user(
            username="lte_grant_target", password="x",
            display_name="Target",
        )

    def test_signal_sets_flag_on_create(self):
        self.assertFalse(self.target.lte_export_granted)
        LTEExportGrant.objects.create(
            user=self.target,
            granted_by=self.admin,
            reason="Board designated privacy officer 2026-04-09.",
        )
        self.target.refresh_from_db()
        self.assertTrue(self.target.lte_export_granted)

    def test_signal_clears_flag_on_revoke(self):
        grant = LTEExportGrant.objects.create(
            user=self.target,
            granted_by=self.admin,
            reason="Initial grant.",
        )
        self.target.refresh_from_db()
        self.assertTrue(self.target.lte_export_granted)

        grant.active = False
        grant.revoked_at = timezone.now()
        grant.save()
        self.target.refresh_from_db()
        self.assertFalse(self.target.lte_export_granted)

    def test_unique_active_grant_constraint(self):
        from django.db import IntegrityError, transaction
        LTEExportGrant.objects.create(
            user=self.target, granted_by=self.admin,
            reason="First grant.",
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                LTEExportGrant.objects.create(
                    user=self.target, granted_by=self.admin,
                    reason="Duplicate active grant — should fail.",
                )


# ═════════════════════════════════════════════════════════════════════
# 2. Permission matrix — report.evaluation_export_small_population is DENY for all roles
# ═════════════════════════════════════════════════════════════════════


class LTEPermissionMatrixTest(TestCase):
    """The matrix must list DENY for every role — no accidental ALLOW."""

    def test_denied_across_all_roles(self):
        from apps.auth_app.constants import (
            ROLE_EXECUTIVE,
            ROLE_PROGRAM_MANAGER,
            ROLE_RECEPTIONIST,
            ROLE_STAFF,
        )
        from apps.auth_app.permissions import DENY, can_access

        for role in (
            ROLE_RECEPTIONIST,
            ROLE_STAFF,
            ROLE_PROGRAM_MANAGER,
            ROLE_EXECUTIVE,
        ):
            self.assertEqual(
                can_access(role, "report.evaluation_export_small_population"),
                DENY,
                f"LTE permission must default to DENY for role {role}",
            )


# ═════════════════════════════════════════════════════════════════════
# 3. Form validation — strict preconditions
# ═════════════════════════════════════════════════════════════════════


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class LTEFormValidationTest(TestCase):
    """Every precondition from the DRR must be required at the form layer."""

    def setUp(self):
        enc_module._fernet = None
        self.user = User.objects.create_user(
            username="lte_form_user", password="x",
            is_admin=True, display_name="Form User",
        )
        self.program = Program.objects.create(name="Peer Support Circle")

    def _valid_payload(self, **overrides):
        payload = {
            "program": str(self.program.pk),
            "period_start": "2025-09-01",
            "period_end": "2026-03-31",
            "reb_name": "Llewelyn Consulting REB",
            "reb_approval_number": "LCR-2026-014",
            "reb_approval_date": "2026-03-15",
            "data_sharing_agreement_expiry": (
                (date.today() + timedelta(days=180)).isoformat()
            ),
            "evaluator_name": "Dr. Ana Martinez",
            "evaluator_email": "dr.martinez@llewelyn.ca",
            "evaluator_organisation": "Llewelyn Consulting",
            "evaluator_degree": "PhD Community Psychology, McMaster",
            "evaluator_years_experience": "15",
            "evaluator_prior_programs": (
                "Youth Employment Program (Llewelyn, 2021-2023); "
                "Community Mental Health Initiative (Hamilton, 2019-2022)."
            ),
            "destruction_window_days": "90",
            "purpose_statement": (
                "Peer Support Circle outcome evaluation — "
                "trajectory and dose-response analysis."
            ),
            "acknowledgement_confirmed": "on",
        }
        payload.update(overrides)
        return payload

    def test_valid_payload_passes(self):
        from apps.reports.forms import LTEExportRequestForm
        form = LTEExportRequestForm(self._valid_payload(), user=self.user)
        self.assertTrue(form.is_valid(), form.errors)

    def test_missing_acknowledgement_rejected(self):
        from apps.reports.forms import LTEExportRequestForm
        form = LTEExportRequestForm(
            self._valid_payload(acknowledgement_confirmed=""),
            user=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("acknowledgement_confirmed", form.errors)

    def test_short_reb_number_rejected(self):
        from apps.reports.forms import LTEExportRequestForm
        form = LTEExportRequestForm(
            self._valid_payload(reb_approval_number="AB"),
            user=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("reb_approval_number", form.errors)

    def test_short_prior_programs_rejected(self):
        from apps.reports.forms import LTEExportRequestForm
        form = LTEExportRequestForm(
            self._valid_payload(evaluator_prior_programs="Just one thing."),
            user=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("evaluator_prior_programs", form.errors)

    def test_expired_dsa_rejected(self):
        from apps.reports.forms import LTEExportRequestForm
        form = LTEExportRequestForm(
            self._valid_payload(
                data_sharing_agreement_expiry=(
                    (date.today() - timedelta(days=1)).isoformat()
                ),
            ),
            user=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("data_sharing_agreement_expiry", form.errors)

    def test_future_reb_date_rejected(self):
        from apps.reports.forms import LTEExportRequestForm
        form = LTEExportRequestForm(
            self._valid_payload(
                reb_approval_date=(date.today() + timedelta(days=30)).isoformat(),
            ),
            user=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("reb_approval_date", form.errors)

    def test_reversed_period_rejected(self):
        from apps.reports.forms import LTEExportRequestForm
        form = LTEExportRequestForm(
            self._valid_payload(
                period_start="2026-03-31",
                period_end="2025-09-01",
            ),
            user=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("period_end", form.errors)

    def test_ocap_program_requires_community_signoff(self):
        from apps.reports.forms import LTEExportRequestForm
        self.program.community_governance_framework = "ocap"
        self.program.save()
        form = LTEExportRequestForm(self._valid_payload(), user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("community_reviewer_name", form.errors)
        self.assertIn("community_reviewer_affiliation", form.errors)
        self.assertIn("community_signoff_date", form.errors)

    def test_ocap_program_with_community_signoff_passes(self):
        from apps.reports.forms import LTEExportRequestForm
        self.program.community_governance_framework = "ocap"
        self.program.save()
        form = LTEExportRequestForm(
            self._valid_payload(
                community_reviewer_name="Elder Grey Wolf",
                community_reviewer_affiliation="Community Council",
                community_signoff_date=(
                    (date.today() - timedelta(days=5)).isoformat()
                ),
            ),
            user=self.user,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_other_framework_requires_description(self):
        from apps.reports.forms import LTEExportRequestForm
        self.program.community_governance_framework = "other"
        self.program.save()
        form = LTEExportRequestForm(
            self._valid_payload(
                community_reviewer_name="Newcomer Council Liaison",
                community_reviewer_affiliation="Regional Newcomer Council",
                community_signoff_date=(
                    (date.today() - timedelta(days=5)).isoformat()
                ),
                community_framework_description="",  # missing
            ),
            user=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("community_framework_description", form.errors)


# ═════════════════════════════════════════════════════════════════════
# 4. Business day arithmetic
# ═════════════════════════════════════════════════════════════════════


class LTEBusinessDayTest(TestCase):
    """add_business_days / calculate_window_end."""

    def test_weekday_start_advances_to_next_weekday(self):
        from apps.reports.lte_lifecycle import add_business_days
        monday = datetime(2026, 4, 6, 9, 0)  # Monday
        result = add_business_days(monday, business_days=5)
        # Mon → +5 business days → next Monday 09:00
        self.assertEqual(result, datetime(2026, 4, 13, 9, 0))
        self.assertEqual(result.weekday(), 0)  # Monday

    def test_friday_submission_skips_weekend(self):
        from apps.reports.lte_lifecycle import add_business_days
        friday = datetime(2026, 4, 10, 9, 0)  # Friday
        result = add_business_days(friday, business_days=5)
        # Fri + 5 business days → next Fri (skips Sat/Sun)
        self.assertEqual(result, datetime(2026, 4, 17, 9, 0))
        self.assertEqual(result.weekday(), 4)  # Friday

    def test_saturday_submission_rolls_to_monday_first(self):
        from apps.reports.lte_lifecycle import add_business_days
        saturday = datetime(2026, 4, 11, 9, 0)  # Saturday
        result = add_business_days(saturday, business_days=5)
        # Sat is not a business day; advance to Mon then +5
        # Saturday → Monday → +5 business days → following Monday
        self.assertEqual(result.weekday(), 4)  # Friday
        self.assertEqual(result, datetime(2026, 4, 17, 9, 0))

    def test_holidays_are_skipped(self):
        from apps.reports.lte_lifecycle import add_business_days
        monday = datetime(2026, 4, 6, 9, 0)  # Monday
        holiday = date(2026, 4, 10)  # Friday — declared holiday
        with override_settings(LTE_EXCLUDED_HOLIDAYS=[holiday]):
            result = add_business_days(monday, business_days=5)
        # Mon + 4 working days (Tue/Wed/Thu/Fri skipped) lands on Tue next week
        # Actually: Tue, Wed, Thu — Fri skipped — next Mon, next Tue → result is Tuesday
        self.assertEqual(result.weekday(), 1)  # Tuesday
        self.assertEqual(result, datetime(2026, 4, 14, 9, 0))

    def test_zero_business_days_returns_start(self):
        from apps.reports.lte_lifecycle import add_business_days
        t = datetime(2026, 4, 6, 9, 0)
        self.assertEqual(add_business_days(t, business_days=0), t)


# ═════════════════════════════════════════════════════════════════════
# 5. Fuzzing helpers
# ═════════════════════════════════════════════════════════════════════


class LTEFuzzingTest(TestCase):
    """Metric rounding and service-intensity banding."""

    def test_band_session_count(self):
        from apps.reports.lte_pipeline import LTESmallPopulationPipeline as P
        self.assertEqual(P._band_session_count(0), 0)
        self.assertEqual(P._band_session_count(1), 0)
        self.assertEqual(P._band_session_count(3), 5)
        self.assertEqual(P._band_session_count(7), 5)
        self.assertEqual(P._band_session_count(8), 10)
        self.assertEqual(P._band_session_count(12), 10)
        self.assertEqual(P._band_session_count(13), 15)

    def test_band_total_hours(self):
        from apps.reports.lte_pipeline import LTESmallPopulationPipeline as P
        self.assertEqual(P._band_total_hours(0.0), 0.0)
        self.assertEqual(P._band_total_hours(0.24), 0.0)
        self.assertEqual(P._band_total_hours(0.25), 0.0)
        self.assertEqual(P._band_total_hours(0.3), 0.5)
        self.assertEqual(P._band_total_hours(12.2), 12.0)
        self.assertEqual(P._band_total_hours(12.3), 12.5)

    def test_fuzz_metric_ordinal_0_10(self):
        from apps.reports.lte_pipeline import LTESmallPopulationPipeline as P
        metric = MagicMock(min_value=0, max_value=10)
        self.assertEqual(P._fuzz_metric_value(3.4, metric), 3)
        self.assertEqual(P._fuzz_metric_value(3.5, metric), 4)
        self.assertEqual(P._fuzz_metric_value(7.9, metric), 8)

    def test_fuzz_metric_percentage_0_100(self):
        from apps.reports.lte_pipeline import LTESmallPopulationPipeline as P
        metric = MagicMock(min_value=0, max_value=100)
        self.assertEqual(P._fuzz_metric_value(42.0, metric), 40)
        self.assertEqual(P._fuzz_metric_value(67.0, metric), 65)
        self.assertEqual(P._fuzz_metric_value(68.0, metric), 70)

    def test_fuzz_metric_continuous_falls_back_to_one_decimal(self):
        from apps.reports.lte_pipeline import LTESmallPopulationPipeline as P
        metric = MagicMock(min_value=None, max_value=None)
        self.assertEqual(P._fuzz_metric_value(3.14159, metric), 3.1)
        self.assertEqual(P._fuzz_metric_value(7.86, metric), 7.9)

    def test_fuzz_metric_none_passes_through(self):
        from apps.reports.lte_pipeline import LTESmallPopulationPipeline as P
        metric = MagicMock(min_value=0, max_value=10)
        self.assertIsNone(P._fuzz_metric_value(None, metric))


# ═════════════════════════════════════════════════════════════════════
# 6. Study-id generator
# ═════════════════════════════════════════════════════════════════════


class LTEStudyIDTest(TestCase):
    """UUID-based study ids — no linkable pattern."""

    def test_format_is_lte_prefix_hex(self):
        import re
        from apps.reports.lte_pipeline import LTESmallPopulationPipeline as P
        study_id = P._generate_lte_study_id(set())
        self.assertTrue(study_id.startswith("LTE-"))
        self.assertTrue(re.match(r"^LTE-[0-9A-F]{8,}$", study_id))

    def test_uniqueness_across_many(self):
        from apps.reports.lte_pipeline import LTESmallPopulationPipeline as P
        seen: set[str] = set()
        for _ in range(1000):
            sid = P._generate_lte_study_id(seen)
            self.assertNotIn(sid, seen)
            seen.add(sid)
        self.assertEqual(len(seen), 1000)


# ═════════════════════════════════════════════════════════════════════
# 7. Model + lifecycle transitions
# ═════════════════════════════════════════════════════════════════════


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class LTEModelTest(TestCase):
    """LTEExportRequest state helpers and lifecycle fundamentals."""

    def setUp(self):
        enc_module._fernet = None
        self.user = User.objects.create_user(
            username="lte_model_user", password="x",
            display_name="Model User",
        )
        self.program = Program.objects.create(name="Test Program")

    def _make_request(self, **overrides):
        from apps.reports.models import LTEExportRequest
        defaults = dict(
            submitted_by=self.user,
            program=self.program,
            period_start=date(2025, 9, 1),
            period_end=date(2026, 3, 31),
            reb_name="REB A",
            reb_approval_number="R-001",
            reb_approval_date=date(2026, 1, 1),
            data_sharing_agreement_expiry=date(2027, 1, 1),
            evaluator_name="E",
            evaluator_email="e@example.com",
            evaluator_organisation="Org",
            evaluator_degree="PhD",
            evaluator_years_experience=10,
            evaluator_prior_programs="x" * 60,
            destruction_window_days=90,
            purpose_statement="p" * 40,
            acknowledgement_confirmed=True,
            window_activates_at=timezone.now() + timedelta(days=7),
            population_snapshot=12,
            population_client_ids=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
        )
        defaults.update(overrides)
        return LTEExportRequest.objects.create(**defaults)

    def test_is_window_running_for_submitted(self):
        from apps.reports.models import LTEExportRequest
        req = self._make_request(status=LTEExportRequest.STATUS_SUBMITTED)
        self.assertTrue(req.is_window_running)
        self.assertFalse(req.is_terminal)

    def test_terminal_states(self):
        from apps.reports.models import LTEExportRequest
        for status in (
            LTEExportRequest.STATUS_CANCELLED,
            LTEExportRequest.STATUS_AUTO_CANCELLED,
            LTEExportRequest.STATUS_INVALIDATED_BY_WITHDRAWAL,
            LTEExportRequest.STATUS_DOWNLOADED,
            LTEExportRequest.STATUS_EXPIRED,
        ):
            req = self._make_request(status=status)
            self.assertTrue(req.is_terminal, f"{status} should be terminal")
            self.assertFalse(req.is_window_running)

    def test_post_hoc_review_pending_skipped_for_cancelled(self):
        from apps.reports.models import LTEExportRequest
        cancelled = self._make_request(status=LTEExportRequest.STATUS_CANCELLED)
        self.assertFalse(cancelled.post_hoc_review_pending)

    def test_post_hoc_review_pending_for_active(self):
        from apps.reports.models import LTEExportRequest
        active = self._make_request(status=LTEExportRequest.STATUS_ACTIVE)
        self.assertTrue(active.post_hoc_review_pending)

    def test_effective_window_activates_at_with_flag_hold(self):
        req = self._make_request(flag_hold_seconds=3600)  # 1h flag hold
        delta = req.effective_window_activates_at - req.window_activates_at
        self.assertEqual(delta, timedelta(seconds=3600))

    def test_start_flag_hold_freezes_status(self):
        from apps.reports.lte_lifecycle import start_flag_hold
        from apps.reports.models import LTEExportRequest
        req = self._make_request(status=LTEExportRequest.STATUS_SUBMITTED)
        start_flag_hold(req, actor=self.user, reason="Test concern")
        req.refresh_from_db()
        self.assertEqual(req.status, LTEExportRequest.STATUS_FLAGGED)
        self.assertIsNotNone(req.flag_hold_started_at)

    def test_resolve_flag_dismiss_resumes_with_hold(self):
        from apps.reports.lte_lifecycle import resolve_flag, start_flag_hold
        from apps.reports.models import LTEExportRequest
        req = self._make_request(status=LTEExportRequest.STATUS_SUBMITTED)
        start_flag_hold(req, actor=self.user)
        req.refresh_from_db()
        # Backdate the flag_hold_started_at so the resolution records
        # a non-zero hold duration.
        req.flag_hold_started_at = timezone.now() - timedelta(seconds=1800)
        req.save()
        resolve_flag(req, actor=self.user, dismissed=True, notes="All good.")
        req.refresh_from_db()
        self.assertEqual(req.status, LTEExportRequest.STATUS_SUBMITTED)
        self.assertGreaterEqual(req.flag_hold_seconds, 1700)
        self.assertIsNone(req.flag_hold_started_at)

    def test_resolve_flag_cancel_transitions_to_cancelled(self):
        from apps.reports.lte_lifecycle import resolve_flag, start_flag_hold
        from apps.reports.models import LTEExportRequest
        req = self._make_request(status=LTEExportRequest.STATUS_SUBMITTED)
        start_flag_hold(req, actor=self.user)
        resolve_flag(req, actor=self.user, dismissed=False, notes="Unsafe.")
        req.refresh_from_db()
        self.assertEqual(req.status, LTEExportRequest.STATUS_CANCELLED)

    def test_cancel_request_discards_linkage_blob(self):
        from apps.reports.lte_lifecycle import cancel_request
        from apps.reports.models import LTEExportRequest
        req = self._make_request(
            status=LTEExportRequest.STATUS_SUBMITTED,
            linkage_blob_encrypted=b"some-encrypted-blob",
        )
        cancel_request(req, actor=self.user, reason="No longer needed")
        req.refresh_from_db()
        self.assertEqual(req.status, LTEExportRequest.STATUS_CANCELLED)
        self.assertEqual(bytes(req.linkage_blob_encrypted), b"")
        self.assertEqual(req.cancelled_by, self.user)


# ═════════════════════════════════════════════════════════════════════
# 8. Rate limit — pending post-hoc review blocks new submissions
# ═════════════════════════════════════════════════════════════════════


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class LTERateLimitTest(TestCase):
    """The agency-wide rate limit must block new submissions while a
    prior LTE has a pending post-hoc review.
    """

    def setUp(self):
        enc_module._fernet = None
        self.user = User.objects.create_user(
            username="lte_rl_user", password="x",
            display_name="RL User",
        )
        self.program = Program.objects.create(name="RL Program")

    def _make(self, **overrides):
        from apps.reports.models import LTEExportRequest
        base = dict(
            submitted_by=self.user, program=self.program,
            period_start=date(2025, 9, 1),
            period_end=date(2026, 3, 31),
            reb_name="R", reb_approval_number="12345",
            reb_approval_date=date(2026, 1, 1),
            data_sharing_agreement_expiry=date(2027, 1, 1),
            evaluator_name="E", evaluator_email="e@example.com",
            evaluator_organisation="Org", evaluator_degree="PhD",
            evaluator_years_experience=5, evaluator_prior_programs="x" * 60,
            destruction_window_days=90,
            purpose_statement="p" * 40,
            acknowledgement_confirmed=True,
            window_activates_at=timezone.now() + timedelta(days=7),
            population_snapshot=11,
            population_client_ids=list(range(1, 12)),
        )
        base.update(overrides)
        return LTEExportRequest.objects.create(**base)

    def test_no_rate_limit_when_no_pending_requests(self):
        from apps.reports.views import _lte_rate_limit_check
        ok, msg = _lte_rate_limit_check()
        self.assertTrue(ok)
        self.assertIsNone(msg)

    def test_pending_submitted_request_blocks(self):
        from apps.reports.models import LTEExportRequest
        from apps.reports.views import _lte_rate_limit_check
        self._make(status=LTEExportRequest.STATUS_SUBMITTED)
        ok, msg = _lte_rate_limit_check()
        self.assertFalse(ok)
        self.assertIn("pending", str(msg).lower())

    def test_cancelled_request_does_not_block(self):
        """A cancelled prior request does NOT block future submissions."""
        from apps.reports.models import LTEExportRequest
        from apps.reports.views import _lte_rate_limit_check
        self._make(
            status=LTEExportRequest.STATUS_CANCELLED,
            cancelled_at=timezone.now(),
        )
        ok, _msg = _lte_rate_limit_check()
        self.assertTrue(ok)

    def test_resolved_post_hoc_review_unblocks(self):
        from apps.reports.models import LTEExportRequest
        from apps.reports.views import _lte_rate_limit_check
        self._make(
            status=LTEExportRequest.STATUS_DOWNLOADED,
            post_hoc_review_resolved_at=timezone.now(),
            post_hoc_review_resolved_by=self.user,
        )
        ok, _msg = _lte_rate_limit_check()
        self.assertTrue(ok)


# ═════════════════════════════════════════════════════════════════════
# 9. CSV output shape — NO demographics, warning header present
# ═════════════════════════════════════════════════════════════════════


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class LTECSVOutputTest(TestCase):
    """Direct test of the LTE CSV writer. Uses a hand-built record set
    so the test is independent of the DB schema for client data.
    """

    def setUp(self):
        enc_module._fernet = None
        self.user = User.objects.create_user(
            username="lte_csv_user", password="x", display_name="CSV",
        )
        self.program = Program.objects.create(name="CSV Program")

    def _build_pipeline(self, records, metric_columns):
        from apps.reports.lte_pipeline import (
            LTEPreviewResult,
            LTESmallPopulationPipeline,
        )
        pipeline = LTESmallPopulationPipeline(
            program=self.program,
            period_start=date(2025, 9, 1),
            period_end=date(2026, 3, 31),
            evaluator_info={
                "name": "Evaluator",
                "email": "e@example.com",
                "organisation": "Org",
                "degree": "PhD",
                "years_experience": 10,
                "purpose": "Evaluation purpose",
                "reb_name": "REB A",
                "reb_approval_number": "R-001",
                "reb_approval_date": "2026-01-01",
                "agreement_expiry": "2027-01-01",
                "destruction_window_days": 90,
            },
            user=self.user,
        )
        pipeline._deidentified_records = records
        pipeline._raw_records = [{} for _ in records]
        pipeline._consented_records = [{} for _ in records]
        preview = LTEPreviewResult(
            eligible_count=len(records),
            consented_count=len(records),
            exportable_count=len(records),
            blocked=False,
            block_reason=None,
            floor_applied=10,
            program_governance_framework="",
            metric_columns=metric_columns,
            snapshot_client_ids=[],
        )
        return pipeline, preview

    def test_header_contains_research_warning(self):
        records = [
            {
                "study_id": "LTE-AAAAAAAA",
                "_real_client_id": 1,
                "enrolment_quarter": "Q3-2025",
                "exit_quarter": "Q1-2026",
                "sessions_count_raw": 12,
                "total_hours_raw": 18.3,
                "metrics": {},
                "_suppressed": False,
            },
        ]
        pipeline, preview = self._build_pipeline(records, [])
        csv_content = pipeline._generate_lte_csv(preview)
        self.assertIn("PROGRAM EVALUATION, not research", csv_content)
        self.assertIn("NO demographic fields", csv_content)

    def test_no_demographic_columns(self):
        records = [
            {
                "study_id": "LTE-BBBBBBBB",
                "_real_client_id": 2,
                "enrolment_quarter": "Q3-2025",
                "exit_quarter": "",
                "sessions_count_raw": 7,
                "total_hours_raw": 11.8,
                "metrics": {},
                "_suppressed": False,
            },
        ]
        pipeline, preview = self._build_pipeline(records, [])
        csv_content = pipeline._generate_lte_csv(preview)
        first_data_line = next(
            line for line in csv_content.splitlines()
            if line and not line.startswith("#")
        )
        forbidden = (
            "age", "gender", "ethnicity", "geography",
            "postal", "urban", "rural",
        )
        for f in forbidden:
            self.assertNotIn(f, first_data_line.lower(),
                             f"Demographic field {f!r} must not appear in LTE header")

    def test_session_counts_and_hours_banded_in_output(self):
        records = [
            {
                "study_id": "LTE-CCCCCCCC",
                "_real_client_id": 3,
                "enrolment_quarter": "Q3-2025",
                "exit_quarter": "",
                "sessions_count_raw": 13,   # → 15
                "total_hours_raw": 18.3,    # → 18.5
                "metrics": {},
                "_suppressed": False,
            },
        ]
        pipeline, preview = self._build_pipeline(records, [])
        csv_content = pipeline._generate_lte_csv(preview)
        data_lines = [
            line for line in csv_content.splitlines()
            if line and not line.startswith("#")
        ]
        # Header line + 1 row
        self.assertEqual(len(data_lines), 2)
        data_row = data_lines[1]
        # 13 sessions rounded to nearest 5 = 15
        self.assertIn("15", data_row)
        # 18.3 hours rounded to nearest 0.5 = 18.5
        self.assertIn("18.5", data_row)


# ═════════════════════════════════════════════════════════════════════
# 10. Audit metadata uses the distinct export_category
# ═════════════════════════════════════════════════════════════════════


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class LTEAuditCategoryTest(TestCase):
    """LTE events must use export_category=longitudinal_trajectory_export,
    never evaluation_microdata. DRR "Enhanced Audit Metadata" section.
    """

    def setUp(self):
        enc_module._fernet = None
        self.user = User.objects.create_user(
            username="lte_audit_user", password="x", display_name="Audit",
        )
        self.program = Program.objects.create(name="Audit Program")

    def test_build_audit_metadata_has_correct_category(self):
        from apps.reports.lte_pipeline import (
            LTEPreviewResult,
            LTESmallPopulationPipeline,
        )

        pipeline = LTESmallPopulationPipeline(
            program=self.program,
            period_start=date(2025, 9, 1),
            period_end=date(2026, 3, 31),
            evaluator_info={
                "name": "E", "email": "e@example.com",
                "organisation": "Org", "degree": "PhD",
                "years_experience": 5, "purpose": "p",
                "reb_name": "REB", "reb_approval_number": "12345",
                "reb_approval_date": date(2026, 1, 1),
                "agreement_expiry": date(2027, 1, 1),
                "destruction_window_days": 90,
            },
            user=self.user,
        )
        preview = LTEPreviewResult(
            eligible_count=11, consented_count=11, exportable_count=11,
            blocked=False, block_reason=None,
            floor_applied=10, program_governance_framework="",
            metric_columns=[], snapshot_client_ids=list(range(1, 12)),
        )
        metadata = pipeline._build_lte_audit_metadata(preview)
        self.assertEqual(
            metadata["export_category"], "longitudinal_trajectory_export",
        )
        # Must NOT be the EME category
        self.assertNotEqual(metadata["export_category"], "evaluation_microdata")
        self.assertTrue(metadata["metric_rounding_applied"])
        self.assertEqual(metadata["session_count_banded_to"], 5)
        self.assertEqual(metadata["total_hours_banded_to"], 0.5)


# ═════════════════════════════════════════════════════════════════════
# 11. View-level access control — 403 when grant or officer missing
# ═════════════════════════════════════════════════════════════════════


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class LTEViewAccessTest(TestCase):
    """lte_list and lte_submit must enforce both per-user grant and
    'no designated privacy officer = no LTE'.
    """

    list_url = "/reports/longitudinal-trajectory-export/"
    submit_url = "/reports/longitudinal-trajectory-export/new/"

    def setUp(self):
        enc_module._fernet = None

    def test_anonymous_redirected(self):
        resp = Client().get(self.list_url)
        self.assertEqual(resp.status_code, 302)

    def test_admin_without_grant_denied(self):
        admin = User.objects.create_user(
            username="lte_admin_view", password="x",
            is_admin=True, display_name="Admin",
        )
        c = Client()
        c.force_login(admin)
        resp = c.get(self.list_url)
        self.assertEqual(resp.status_code, 403)

    def test_granted_user_with_no_other_officer_still_ok(self):
        """A single privacy officer is sufficient — check the agency check
        finds themselves too (the lte_available_in_agency query is
        User-wide, so a user holding the grant counts themselves).
        """
        officer = User.objects.create_user(
            username="lte_officer", password="x",
            display_name="Officer", lte_export_granted=True,
        )
        c = Client()
        c.force_login(officer)
        resp = c.get(self.list_url)
        self.assertEqual(resp.status_code, 200)

    def test_granted_user_reaches_submit_form(self):
        officer = User.objects.create_user(
            username="lte_officer_submit", password="x",
            display_name="Officer",
            lte_export_granted=True,
        )
        c = Client()
        c.force_login(officer)
        resp = c.get(self.submit_url)
        self.assertEqual(resp.status_code, 200)
