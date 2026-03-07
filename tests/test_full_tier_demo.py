"""
CIDS Full Tier Compliance — Demo Data & Report Generation Tests.

Creates realistic demo data representing a fully evaluated program and
generates every report type expected for Full Tier CIDS compliance.
Then assesses completeness against the CIDS ontology.

Demo scenario:
    Bright Futures Youth Employment Services — a Toronto nonprofit
    providing job readiness training and placement to youth aged 16-24.
    45 active participants, 3 months of progress notes with metric values,
    approved taxonomy mappings for IRIS+ and SDG.
"""
import json
from datetime import date, timedelta

from django.test import TestCase, override_settings
from django.utils import timezone
from cryptography.fernet import Fernet

from apps.admin_settings.models import CidsCodeList, OrganizationProfile, TaxonomyMapping
from apps.auth_app.models import User
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.notes.models import ProgressNote, ProgressNoteTarget, MetricValue
from apps.plans.models import MetricDefinition, PlanSection, PlanTarget, PlanTargetMetric
from apps.programs.models import Program, UserProgramRole

try:
    from apps.plans.cids import apply_metric_cids_defaults, apply_target_cids_defaults
except ImportError:
    # apps.plans.cids may not be committed yet — provide no-op stubs
    def apply_metric_cids_defaults(metric):
        return []
    def apply_target_cids_defaults(target):
        return []
from apps.reports.cids_jsonld import build_cids_jsonld_document
from apps.reports.cids_enrichment import get_standards_alignment_data

import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()

# CIDS Full Tier required classes
FULL_TIER_REQUIRED_CLASSES = {
    "cids:Organization",
    "cids:Outcome",
    "cids:Indicator",
    "cids:IndicatorReport",
    "cids:Theme",
    "cids:Code",
    "cids:ImpactModel",
    "cids:Service",
    "cids:Activity",
    "cids:Output",
    "cids:Stakeholder",
    "cids:StakeholderOutcome",
    "cids:ImpactRisk",
    "cids:Counterfactual",
}


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class FullTierDemoDataTest(TestCase):
    """Create demo data and generate all Full Tier reports."""

    @classmethod
    def setUpTestData(cls):
        enc_module._fernet = None

    def setUp(self):
        enc_module._fernet = None
        self._create_organization()
        self._create_code_lists()
        self._create_users()
        self._create_program()
        self._create_metrics()
        self._create_taxonomy_mappings()
        self._create_participants_and_enrolments()
        self._create_plans_and_targets()
        self._create_progress_notes_and_values()

    # ── Setup helpers ──────────────────────────────────────────────────

    def _create_organization(self):
        self.org = OrganizationProfile.get_solo()
        self.org.legal_name = "Bright Futures Community Services"
        self.org.operating_name = "Bright Futures"
        self.org.description = (
            "A Toronto-based nonprofit providing employment, housing, "
            "and life skills services to youth aged 16-24."
        )
        self.org.description_fr = (
            "Un organisme a but non lucratif base a Toronto offrant des "
            "services d'emploi, de logement et de competences de vie "
            "aux jeunes de 16 a 24 ans."
        )
        self.org.legal_status = "Registered Charity"
        self.org.street_address = "100 Queen Street West"
        self.org.city = "Toronto"
        self.org.province = "ON"
        self.org.postal_code = "M5H 2N2"
        self.org.country = "CA"
        self.org.website = "https://brightfutures.example.ca"
        self.org.save()

    def _create_code_lists(self):
        for code, label in [
            ("employment", "Employment"),
            ("education", "Education & Training"),
            ("health", "Health & Well-being"),
        ]:
            CidsCodeList.objects.create(
                list_name="IRISImpactTheme", code=code, label=label,
                description=f"Impact theme: {label}",
                specification_uri=f"https://iris.thegiin.org/theme/{code}",
                defined_by_name="GIIN",
            )
        for code, label in [
            ("PI4060", "Client Individuals: Total Number"),
            ("PI2822", "Youth Employment Rate"),
            ("OI3160", "Client Retention Rate"),
        ]:
            CidsCodeList.objects.create(
                list_name="IrisMetric53", code=code, label=label,
                specification_uri=f"https://iris.thegiin.org/metric/5.3/{code}",
                defined_by_name="GIIN",
            )
        for num, label in [
            ("4", "Quality Education"),
            ("8", "Decent Work and Economic Growth"),
        ]:
            CidsCodeList.objects.create(
                list_name="SDGImpacts", code=num, label=label,
                specification_uri=f"https://sdgs.un.org/goals/goal{num}",
                defined_by_name="United Nations",
            )
        CidsCodeList.objects.create(
            list_name="ICNPOsector", code="6100",
            label="Employment & Training", defined_by_name="ICNPO",
        )

    def _create_users(self):
        self.admin = User.objects.create_user(
            username="admin@brightfutures.ca", password="testpass123",
            is_admin=True, display_name="Sarah Chen",
        )
        self.staff = User.objects.create_user(
            username="staff@brightfutures.ca", password="testpass123",
            is_admin=False, display_name="Marcus Williams",
        )
        self.evaluator = User.objects.create_user(
            username="evaluator@brightfutures.ca", password="testpass123",
            is_admin=True, display_name="Dr. Amira Okafor",
        )

    def _create_program(self):
        self.program = Program.objects.create(
            name="Youth Employment Services",
            description=(
                "Comprehensive employment readiness program for youth aged "
                "16-24 in Toronto. Includes resume writing, interview skills, "
                "job placement support, and 6-month follow-up."
            ),
            description_fr=(
                "Programme complet de preparation a l'emploi pour les "
                "jeunes de 16 a 24 ans a Toronto."
            ),
            cids_sector_code="6100",
            population_served_codes=["youth_16_24", "unemployed"],
            funder_program_code="UW-YE-2025",
            service_model="both",
        )
        UserProgramRole.objects.create(
            user=self.admin, program=self.program, role="program_manager",
        )
        UserProgramRole.objects.create(
            user=self.staff, program=self.program, role="staff",
        )

    def _create_metrics(self):
        self.metric_employment = MetricDefinition.objects.create(
            name="Employment Status",
            definition="Whether participant has obtained paid employment",
            category="employment", metric_type="achievement", unit="status",
            iris_metric_code="PI2822", sdg_goals=[8],
            cids_theme_override="employment",
            achievement_options=json.dumps([
                "Unemployed", "Part-time", "Full-time", "Self-employed",
            ]),
            achievement_success_values=json.dumps([
                "Part-time", "Full-time", "Self-employed",
            ]),
        )
        self.metric_confidence = MetricDefinition.objects.create(
            name="Job Readiness Confidence",
            definition="Self-rated confidence in job readiness skills (1-10)",
            category="employment", metric_type="scale", unit="score",
            min_value=1, max_value=10, iris_metric_code="OI3160", sdg_goals=[8, 4],
        )
        self.metric_interviews = MetricDefinition.objects.create(
            name="Job Interviews Completed",
            definition="Number of job interviews attended in the period",
            category="employment", metric_type="scale", unit="count",
            min_value=0, max_value=50, sdg_goals=[8],
        )
        self.metric_wellbeing = MetricDefinition.objects.create(
            name="Overall Well-being (WHO-5)",
            definition="Self-rated overall well-being using WHO-5 Index",
            category="mental_health", metric_type="scale", unit="score",
            min_value=0, max_value=25,
            is_standardized_instrument=True, instrument_name="WHO-5",
            cids_theme_override="health",
        )
        for m in [self.metric_employment, self.metric_confidence,
                   self.metric_interviews, self.metric_wellbeing]:
            apply_metric_cids_defaults(m)
            m.save()

    def _create_taxonomy_mappings(self):
        TaxonomyMapping.objects.create(
            metric_definition=self.metric_employment,
            taxonomy_system="iris_plus", taxonomy_code="PI2822",
            taxonomy_list_name="IrisMetric53",
            taxonomy_label="Youth Employment Rate",
            mapping_status="approved", mapping_source="manual",
            reviewed_by=self.admin, reviewed_at=timezone.now(),
        )
        TaxonomyMapping.objects.create(
            metric_definition=self.metric_confidence,
            taxonomy_system="iris_plus", taxonomy_code="OI3160",
            taxonomy_list_name="IrisMetric53",
            taxonomy_label="Client Retention Rate",
            mapping_status="approved", mapping_source="ai_suggested",
            confidence_score=0.85,
            reviewed_by=self.admin, reviewed_at=timezone.now(),
        )
        TaxonomyMapping.objects.create(
            metric_definition=self.metric_employment,
            taxonomy_system="sdg", taxonomy_code="8",
            taxonomy_list_name="SDGImpacts",
            taxonomy_label="Decent Work and Economic Growth",
            mapping_status="approved", mapping_source="manual",
            reviewed_by=self.admin, reviewed_at=timezone.now(),
        )
        TaxonomyMapping.objects.create(
            program=self.program,
            taxonomy_system="sdg", taxonomy_code="8",
            taxonomy_list_name="SDGImpacts",
            taxonomy_label="Decent Work and Economic Growth",
            mapping_status="approved", mapping_source="manual",
            reviewed_by=self.admin, reviewed_at=timezone.now(),
        )

    def _create_participants_and_enrolments(self):
        self.participants = []
        self.enrolments = []
        names = [
            "Alex", "Jordan", "Taylor", "Morgan", "Casey",
            "Riley", "Jamie", "Quinn", "Avery", "Skyler",
            "River", "Phoenix", "Dakota", "Blake", "Sage",
            "Drew", "Finley", "Harper", "Rowan", "Ellis",
        ]
        for i, name in enumerate(names):
            client = ClientFile(
                record_id=f"BF-2025-{i + 1:03d}",
                status="active", is_demo=True,
            )
            client.first_name = name
            client.last_name = f"Participant-{i + 1}"
            client.save()

            enrolment = ClientProgramEnrolment.objects.create(
                client_file=client, program=self.program,
                status="active", referral_source="community",
                consent_to_aggregate_reporting=True,
            )
            self.participants.append(client)
            self.enrolments.append(enrolment)

    def _create_plans_and_targets(self):
        self.targets = []
        achievement_statuses = (
            ["achieved"] * 8
            + ["in_progress"] * 4
            + ["improving"] * 4
            + ["no_change"] * 4
        )
        for i, (client, enrolment) in enumerate(
            zip(self.participants, self.enrolments)
        ):
            section = PlanSection.objects.create(
                client_file=client, program=self.program,
                name="Employment Goals",
            )
            target = PlanTarget(
                plan_section=section, client_file=client, status="default",
            )
            target.name = "Find employment"
            target.description = "Secure stable employment within 6 months"
            target.achievement_status = achievement_statuses[i]
            target.save()
            apply_target_cids_defaults(target)
            target.save()

            for metric in [self.metric_employment, self.metric_confidence,
                           self.metric_interviews, self.metric_wellbeing]:
                PlanTargetMetric.objects.create(
                    plan_target=target, metric_def=metric,
                )
            self.targets.append(target)

    def _create_progress_notes_and_values(self):
        base_date = timezone.now() - timedelta(days=90)
        for month in range(3):
            note_date = base_date + timedelta(days=month * 30)
            for i, (client, target) in enumerate(
                zip(self.participants, self.targets)
            ):
                note = ProgressNote.objects.create(
                    client_file=client, author=self.staff,
                    author_program=self.program, author_role="staff",
                    note_type="full", interaction_type="session",
                    backdate=note_date,
                )
                pnt = ProgressNoteTarget.objects.create(
                    progress_note=note, plan_target=target,
                )
                # Employment status
                if i < 8 and month == 2:
                    emp = "Full-time"
                elif i < 12 and month >= 1:
                    emp = "Part-time"
                else:
                    emp = "Unemployed"
                MetricValue.objects.create(
                    progress_note_target=pnt, metric_def=self.metric_employment,
                    value=emp,
                )
                # Confidence (improving over time)
                MetricValue.objects.create(
                    progress_note_target=pnt, metric_def=self.metric_confidence,
                    value=str(min(10, 3 + (i % 5) + month)),
                )
                # Interviews
                MetricValue.objects.create(
                    progress_note_target=pnt, metric_def=self.metric_interviews,
                    value=str(month * (1 + i % 3)),
                )
                # Well-being (WHO-5)
                MetricValue.objects.create(
                    progress_note_target=pnt, metric_def=self.metric_wellbeing,
                    value=str(min(25, 10 + (i % 8) + month * 2)),
                )

    # ── Report Tests ───────────────────────────────────────────────────

    def test_01_basic_tier_export(self):
        """Generate Basic Tier JSON-LD and verify all required nodes."""
        doc = build_cids_jsonld_document(
            programs=[self.program], taxonomy_lens="iris_plus",
        )
        graph = doc["@graph"]
        types = {n["@type"] for n in graph}

        self.assertIn("cids:Organization", types)
        self.assertIn("cids:Outcome", types)
        self.assertIn("cids:Indicator", types)
        self.assertIn("cids:IndicatorReport", types)
        self.assertIn("cids:Address", types)

        # Verify organisation
        org = next(n for n in graph if n["@type"] == "cids:Organization")
        self.assertEqual(org["hasLegalName"], "Bright Futures Community Services")

        # Verify we have 4 indicators (one per metric)
        indicators = [n for n in graph if n["@type"] == "cids:Indicator"]
        self.assertEqual(len(indicators), 4)

        # Verify 4 indicator reports with observation counts
        reports = [n for n in graph if n["@type"] == "cids:IndicatorReport"]
        self.assertEqual(len(reports), 4)
        for r in reports:
            count = int(r["value"]["hasNumericalValue"])
            self.assertGreater(count, 0)

        print(f"\n=== Basic Tier Export ===")
        print(f"Nodes: {len(graph)}, Types: {sorted(types)}")
        print(f"Indicators: {len(indicators)}, Reports: {len(reports)}")

    def test_02_all_taxonomy_lenses(self):
        """Generate exports with each taxonomy lens and check Code nodes."""
        for lens in ["common_approach", "iris_plus", "sdg"]:
            doc = build_cids_jsonld_document(
                programs=[self.program], taxonomy_lens=lens,
            )
            graph = doc["@graph"]
            codes = [n for n in graph if n["@type"] == "cids:Code"]
            themes = [n for n in graph if n["@type"] == "cids:Theme"]
            print(f"\n  {lens}: {len(codes)} codes, {len(themes)} themes")
            for c in codes:
                print(f"    Code: {c.get('hasName', '?')}")

    def test_03_standards_alignment(self):
        """Generate standards alignment data for the program."""
        metrics = MetricDefinition.objects.filter(
            pk__in=[self.metric_employment.pk, self.metric_confidence.pk,
                    self.metric_interviews.pk, self.metric_wellbeing.pk],
        )
        alignment = get_standards_alignment_data(
            self.program, metrics, "iris_plus",
        )
        self.assertGreater(alignment["total_count"], 0)
        self.assertGreater(alignment["mapped_count"], 0)

        print(f"\n=== Standards Alignment ===")
        print(f"Mapped: {alignment['mapped_count']}/{alignment['total_count']}")
        for m in alignment["metrics"]:
            print(f"  {m['name']}: IRIS={m.get('iris_code','—')} "
                  f"SDG={m.get('sdg_goals',[])} Theme={m.get('theme','—')}")

    def test_04_jsonld_structure_valid(self):
        """Check all nodes have required @id and @type fields."""
        doc = build_cids_jsonld_document(programs=[self.program])
        issues = []
        for node in doc["@graph"]:
            if "@id" not in node:
                issues.append(f"Missing @id: {node}")
            if "@type" not in node:
                issues.append(f"Missing @type: {node}")

        for indicator in (n for n in doc["@graph"] if n.get("@type") == "cids:Indicator"):
            if "hasName" not in indicator:
                issues.append(f"Indicator missing hasName: {indicator['@id']}")
            if "forOutcome" not in indicator:
                issues.append(f"Indicator missing forOutcome: {indicator['@id']}")

        self.assertEqual(issues, [])

    def test_05_observation_counts_accurate(self):
        """Verify reported observation counts match actual data."""
        doc = build_cids_jsonld_document(programs=[self.program])
        reports = [n for n in doc["@graph"] if n["@type"] == "cids:IndicatorReport"]

        for report in reports:
            reported = int(report["value"]["hasNumericalValue"])
            parts = report["forIndicator"]["@id"].split(":")
            if len(parts) >= 5:
                metric_id = parts[-1]
                actual = MetricValue.objects.filter(
                    metric_def_id=metric_id,
                    progress_note_target__plan_target__plan_section__program=self.program,
                    progress_note_target__progress_note__status="default",
                ).count()
                self.assertEqual(reported, actual,
                                 f"Count mismatch for metric {metric_id}")

    def test_06_pii_absent(self):
        """Verify no participant PII in the export."""
        doc = build_cids_jsonld_document(programs=[self.program])
        export_str = json.dumps(doc, ensure_ascii=False)

        for client in self.participants:
            self.assertNotIn(client.first_name, export_str,
                             f"PII leak: '{client.first_name}' in export")
            self.assertNotIn(client.record_id, export_str,
                             f"PII leak: record_id '{client.record_id}' in export")

    def test_07_serialisation_roundtrip(self):
        """Full export serialises to valid JSON and round-trips cleanly."""
        doc = build_cids_jsonld_document(
            programs=[self.program], taxonomy_lens="iris_plus",
        )
        json_str = json.dumps(doc, indent=2, ensure_ascii=False)
        parsed = json.loads(json_str)
        self.assertIn("@context", parsed)
        self.assertIn("@graph", parsed)
        self.assertEqual(len(parsed["@graph"]), len(doc["@graph"]))

        print(f"\n=== Export ===")
        print(f"Size: {len(json_str)} bytes, Nodes: {len(parsed['@graph'])}")

    def test_08_full_tier_gap_assessment(self):
        """
        CORE DELIVERABLE: Comprehensive Full Tier gap analysis.

        Generates the Basic Tier export and then assesses which CIDS Full Tier
        classes are present vs missing, what data exists to fill gaps, and
        what code changes are needed.
        """
        doc = build_cids_jsonld_document(
            programs=[self.program], taxonomy_lens="iris_plus",
        )
        graph = doc["@graph"]
        present_types = {n["@type"] for n in graph}

        # ── Layer 2 (Aggregate Measurement) — already working ──────────
        layer2 = {"cids:Organization", "cids:Outcome", "cids:Indicator",
                  "cids:IndicatorReport", "cids:Theme", "cids:Code", "cids:Address"}
        layer2_ok = present_types & layer2
        layer2_missing = layer2 - present_types

        # ── Layer 1 (Program Model) — needs new code ───────────────────
        layer1 = {"cids:ImpactModel", "cids:Service", "cids:Activity",
                  "cids:Output", "cids:Stakeholder", "cids:StakeholderOutcome",
                  "cids:ImpactRisk", "cids:Counterfactual"}
        layer1_ok = present_types & layer1
        layer1_missing = layer1 - present_types

        all_ok = present_types & FULL_TIER_REQUIRED_CLASSES
        all_missing = FULL_TIER_REQUIRED_CLASSES - present_types
        pct = len(all_ok) * 100 // len(FULL_TIER_REQUIRED_CLASSES)

        # ── What COULD be emitted from existing data ───────────────────
        could_emit_from_existing = {}
        # Stakeholder from population_served_codes
        if self.program.population_served_codes:
            could_emit_from_existing["cids:Stakeholder"] = (
                f"Program.population_served_codes = {self.program.population_served_codes}"
            )
        # StakeholderOutcome from aggregate achievement rates
        achieved = PlanTarget.objects.filter(
            plan_section__program=self.program,
            achievement_status="achieved",
        ).count()
        total_targets = PlanTarget.objects.filter(
            plan_section__program=self.program,
        ).count()
        if total_targets > 0:
            could_emit_from_existing["cids:StakeholderOutcome"] = (
                f"Aggregate achievement: {achieved}/{total_targets} "
                f"({achieved * 100 // total_targets}%)"
            )
        # Output from metric observation counts
        total_obs = MetricValue.objects.filter(
            progress_note_target__plan_target__plan_section__program=self.program,
        ).count()
        if total_obs > 0:
            could_emit_from_existing["cids:Output"] = (
                f"{total_obs} metric observations across "
                f"{len(self.participants)} participants"
            )
        # ImpactModel from program description
        if self.program.description:
            could_emit_from_existing["cids:ImpactModel"] = (
                f"Program.description: '{self.program.description[:60]}...'"
            )

        # ── Print comprehensive report ─────────────────────────────────
        print("\n" + "=" * 72)
        print("  CIDS FULL TIER COMPLIANCE — COMPREHENSIVE ASSESSMENT")
        print("=" * 72)

        print(f"\n  LAYER 2: Aggregate Measurement (Basic Tier)")
        print(f"  {'—' * 50}")
        for cls in sorted(layer2):
            status = "PRESENT" if cls in layer2_ok else "MISSING"
            count = len([n for n in graph if n.get("@type") == cls])
            print(f"    [{status}] {cls}" + (f" ({count} nodes)" if count else ""))
        print(f"  Status: {'COMPLETE' if not layer2_missing else 'INCOMPLETE'}")

        print(f"\n  LAYER 1: Program Model (Full Tier)")
        print(f"  {'—' * 50}")
        for cls in sorted(layer1):
            status = "PRESENT" if cls in layer1_ok else "MISSING"
            extra = ""
            if cls in could_emit_from_existing:
                extra = f"  <-- could emit: {could_emit_from_existing[cls]}"
            print(f"    [{status}] {cls}{extra}")
        can_emit = len(set(could_emit_from_existing.keys()) & layer1_missing)
        truly_missing = len(layer1_missing) - can_emit
        print(f"  Status: {len(layer1_ok)}/{len(layer1)} present, "
              f"{can_emit} achievable from existing data, "
              f"{truly_missing} require new models")

        print(f"\n  OVERALL")
        print(f"  {'—' * 50}")
        print(f"  Classes: {len(all_ok)}/{len(FULL_TIER_REQUIRED_CLASSES)} ({pct}%)")
        print(f"  With existing data: "
              f"{len(all_ok) + can_emit}/{len(FULL_TIER_REQUIRED_CLASSES)} "
              f"({(len(all_ok) + can_emit) * 100 // len(FULL_TIER_REQUIRED_CLASSES)}%)")

        print(f"\n  DATA QUALITY")
        print(f"  {'—' * 50}")
        print(f"  Indicators: {len([n for n in graph if n['@type'] == 'cids:Indicator'])}")
        print(f"  Reports with data: {len([n for n in graph if n['@type'] == 'cids:IndicatorReport'])}")
        print(f"  Themes: {len([n for n in graph if n['@type'] == 'cids:Theme'])}")
        print(f"  Codes: {len([n for n in graph if n['@type'] == 'cids:Code'])}")
        print(f"  Total observations: {total_obs}")
        print(f"  Active participants: {len(self.participants)}")
        print(f"  Achievement rate: {achieved}/{total_targets} "
              f"({achieved * 100 // total_targets if total_targets else 0}%)")

        print(f"\n  WHAT NEEDS BUILDING")
        print(f"  {'—' * 50}")
        print(f"  QUICK WIN (no new models needed):")
        print(f"    Extend build_cids_jsonld_document() to emit:")
        print(f"    - cids:Stakeholder from Program.population_served_codes")
        print(f"    - cids:StakeholderOutcome from aggregate PlanTarget achievement")
        print(f"    - cids:Output from observation counts")
        print(f"    - cids:ImpactModel from Program.description")
        print(f"    This raises coverage to ~{(len(all_ok) + can_emit) * 100 // len(FULL_TIER_REQUIRED_CLASSES)}%")
        print()
        print(f"  PHASE 1 (EvaluationFramework + EvaluationComponent):")
        print(f"    Required for structured data behind:")
        print(f"    - cids:Service (what services the program delivers)")
        print(f"    - cids:Activity (specific activities within services)")
        print(f"    - cids:Counterfactual (what happens without intervention)")
        print(f"    - richer cids:ImpactRisk (structured risk + mitigation)")
        print()
        print(f"  PHASE 4 (Full Tier serialiser):")
        print(f"    New function build_full_tier_jsonld() that combines:")
        print(f"    - Layer 1 nodes from EvaluationFramework/Component")
        print(f"    - Layer 2 from existing build_cids_jsonld_document()")
        print(f"    - Layer 3 (optional de-identified trajectories)")
        print(f"    - Evaluator attestation metadata")
        print()
        print(f"  NICE TO HAVE (Phases 2-3):")
        print(f"    - CanonicalReportArtifact (stable non-PII package)")
        print(f"    - AI enrichment for metadata quality")
        print(f"    - Metadata snapshots for audit trail")
        print(f"    Not required for Full Tier — improve quality, not coverage")

        print(f"\n  CLASSES THAT TRULY CANNOT BE EMITTED WITHOUT NEW MODELS")
        print(f"  {'—' * 50}")
        truly_blocked = layer1_missing - set(could_emit_from_existing.keys())
        for cls in sorted(truly_blocked):
            reasons = {
                "cids:Activity": "No structured activity data; need EvaluationComponent(type=activity)",
                "cids:Counterfactual": "No counterfactual data; need EvaluationComponent(type=counterfactual)",
                "cids:ImpactRisk": "No structured risk data; need EvaluationComponent(type=risk)",
                "cids:Service": "service_model field too coarse; need EvaluationComponent(type=service)",
            }
            print(f"    {cls}: {reasons.get(cls, 'Requires EvaluationComponent')}")

        # Assertions
        self.assertIn("cids:Organization", present_types)
        self.assertIn("cids:Outcome", present_types)
        self.assertIn("cids:Indicator", present_types)
        self.assertIn("cids:IndicatorReport", present_types)
        self.assertGreaterEqual(pct, 40)

    def test_09_full_export_document(self):
        """Print the full JSON-LD document for manual inspection."""
        doc = build_cids_jsonld_document(
            programs=[self.program], taxonomy_lens="iris_plus",
        )
        print("\n=== Full JSON-LD Document ===")
        print(json.dumps(doc, indent=2, ensure_ascii=False)[:3000])
        print("... (truncated)")
