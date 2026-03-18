# Demo Data Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Increase demo data from 15 clients (3/program) to ~110 clients (20-30/program), populate all FHIR metadata fields, and ensure every KoNote feature displays meaningful data in the demo.

**Architecture:** Four independent file groups are modified: (1) `metric_library.json` gets FHIR metadata fields, (2) `seed.py` gets backfill logic and flow changes, (3) `demo_engine.py` gets volume increases, ServiceEpisode fields, cross-enrolments, FHIR seeding methods, and weighted trends, (4) `generate_demo_data.py` gets a default change. Tasks 1-2 can run in parallel with Task 3. Task 4 depends on Tasks 1-3.

**Named Personas Strategy:** The 15 named personas (DEMO-001 through DEMO-015) are created by `seed.py`'s `_create_demo_users_and_clients()` which calls `seed_demo_data`. The new flow keeps this call, THEN runs the engine to top up each program to 20-30 clients. The engine's `create_demo_clients()` must check how many demo clients already exist in each program and only create enough additional clients to reach the target. Existing DEMO-001 through DEMO-015 clients are counted toward the target.

**Tech Stack:** Django 5, Python 3.12, PostgreSQL 16

**Spec:** `docs/superpowers/specs/2026-03-17-demo-data-overhaul-design.md`

**Important context for all agents:**
- This is a worktree. All paths are under `/c/Users/gilli/GitHub/konote/.worktrees/session-20260317-195943/`
- Git commands: `git -C "/c/Users/gilli/GitHub/konote/.worktrees/session-20260317-195943"`
- There is NO local Django/PostgreSQL — cannot run `manage.py` or `pytest` locally
- Tests that import Django models will fail locally. Only verify JSON validity and Python syntax.
- The existing test suite runs on the VPS in Docker containers

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `seeds/metric_library.json` | Modify | Add `evidence_type`, `measure_basis`, `derivation_method`, `iris_metric_code`, `sdg_goals` to all metrics |
| `apps/admin_settings/management/commands/seed.py` | Modify | (1) Add FHIR field backfill to `_seed_metrics()`, (2) Change DEMO_MODE flow to always use engine |
| `apps/admin_settings/management/commands/generate_demo_data.py` | Modify | Change `--clients-per-program` default from 3 to 20 |
| `apps/admin_settings/demo_engine.py` | Modify | Volume increase, weighted trends, ServiceEpisode fields, cross-enrolments, Program FHIR fields, OrganizationProfile, TaxonomyMapping, CidsCodeList, suggestion themes, PlanTarget fields |

---

## Task 1: Enrich metric_library.json with FHIR Metadata

**Can run in parallel with Tasks 2 and 3.**

**Files:**
- Modify: `seeds/metric_library.json`

This task adds five FHIR metadata fields to every metric in the library. The file contains ~30 metrics as a JSON array.

- [ ] **Step 1: Read the current metric_library.json and understand its structure**

Read `seeds/metric_library.json` in full. Each metric is a JSON object with fields like `name`, `definition`, `category`, `min_value`, `max_value`, etc. Some already have `instrument_name`, `is_standardized_instrument`, `scoring_bands`.

- [ ] **Step 2: Add FHIR fields to all metrics**

Add these fields to every metric object, using the mapping rules from the spec:

**Standardized instruments (PHQ-9, GAD-7, K10):**
```json
"evidence_type": "self_report",
"measure_basis": "published_validated",
"derivation_method": "direct_response",
"sdg_goals": [3]
```
PHQ-9 and GAD-7 also get: `"iris_metric_code": ""` (no direct IRIS+ mapping)
K10 also gets: `"iris_metric_code": ""`

**Participant-voiced scales (How are you feeling today?, Self-Efficacy, Goal Progress, Satisfaction, How connected, Comfort with English, Confidence navigating, Cooking confidence, Since we last met):**
```json
"evidence_type": "self_report",
"measure_basis": "custom_participatory",
"derivation_method": "direct_response"
```
SDG goals vary by category:
- `general` category: `"sdg_goals": []`
- `employment` category: `"sdg_goals": [8]`
- `housing` category: `"sdg_goals": [11]`
- `youth` category: `"sdg_goals": [4]`
- `mental_health` category: `"sdg_goals": [3]`
- `client_experience` category: `"sdg_goals": []`

**Count/rate metrics (Hours Worked, School Attendance Rate, Nights in Shelter, Monthly Income, Healthy meals, Sessions attended, Community connections):**
```json
"evidence_type": "self_report",
"measure_basis": "custom_staff_designed",
"derivation_method": "direct_response"
```
SDG goals by category as above.

**Achievement metrics (Job Placement, Housing Secured, School Enrolment):**
```json
"evidence_type": "staff_observed",
"measure_basis": "custom_staff_designed",
"derivation_method": "staff_rating"
```
- Job Placement: `"iris_metric_code": "PI2061"`, `"sdg_goals": [8]`
- Housing Secured: `"iris_metric_code": ""`, `"sdg_goals": [11]`
- School Enrolment: `"iris_metric_code": ""`, `"sdg_goals": [4]`

**Inclusivity Battery (5 items: Everyone is made to feel welcome, Everyone is valued equally, I am treated with respect, People help each other, I get help when I need it):**
```json
"evidence_type": "self_report",
"measure_basis": "published_adapted",
"derivation_method": "direct_response",
"sdg_goals": [10]
```

**Open-text metrics (How has taking part..., How can we improve...):**
```json
"evidence_type": "self_report",
"measure_basis": "custom_participatory",
"derivation_method": "direct_response",
"sdg_goals": []
```

- [ ] **Step 3: Validate JSON syntax**

Run: `python -c "import json; json.load(open('seeds/metric_library.json'))" && echo "Valid JSON"`

Expected: "Valid JSON"

- [ ] **Step 4: Commit**

```bash
git add seeds/metric_library.json
git commit -m "feat: add FHIR metadata fields to metric library

Add evidence_type, measure_basis, derivation_method, iris_metric_code,
and sdg_goals to all metrics in the library. Maps standardized
instruments to published_validated, participant-voiced scales to
custom_participatory, and achievement metrics to staff_observed."
```

---

## Task 2: Update seed.py — FHIR Backfill and Engine Flow

**Can run in parallel with Tasks 1 and 3.**

**Files:**
- Modify: `apps/admin_settings/management/commands/seed.py`
- Modify: `apps/admin_settings/management/commands/generate_demo_data.py`

### Part A: Add FHIR field backfill to _seed_metrics()

- [ ] **Step 1: Read seed.py _seed_metrics() method**

Read `apps/admin_settings/management/commands/seed.py` lines 94-204 to understand the current `get_or_create` defaults and backfill logic.

- [ ] **Step 2: Add FHIR fields to get_or_create defaults**

In the `defaults={}` dict inside `MetricDefinition.objects.get_or_create()` (around line 106), add after the `assessment_at_discharge` line:

```python
                    # FHIR metadata
                    "evidence_type": m.get("evidence_type", ""),
                    "measure_basis": m.get("measure_basis", ""),
                    "derivation_method": m.get("derivation_method", ""),
                    "iris_metric_code": m.get("iris_metric_code", ""),
                    "sdg_goals": m.get("sdg_goals", []),
```

- [ ] **Step 3: Add FHIR fields to backfill block**

In the backfill block (after the `assessment_at_discharge` backfill, around line 172), add:

```python
                # Backfill FHIR metadata fields
                for fhir_field in ("evidence_type", "measure_basis", "derivation_method", "iris_metric_code"):
                    new_val = m.get(fhir_field, "")
                    if new_val and not getattr(obj, fhir_field):
                        setattr(obj, fhir_field, new_val)
                        changed = True
                if m.get("sdg_goals") and not obj.sdg_goals:
                    obj.sdg_goals = m["sdg_goals"]
                    changed = True
```

- [ ] **Step 4: Commit Part A**

```bash
git add apps/admin_settings/management/commands/seed.py
git commit -m "feat: backfill FHIR metadata fields in seed_metrics

Add evidence_type, measure_basis, derivation_method, iris_metric_code,
and sdg_goals to get_or_create defaults and backfill logic so existing
databases pick up FHIR enrichment from metric_library.json."
```

### Part B: Change DEMO_MODE flow to always use engine

- [ ] **Step 5: Read the current DEMO_MODE branching logic**

Read `apps/admin_settings/management/commands/seed.py` lines 32-68.

- [ ] **Step 6: Replace the DEMO_MODE block**

Replace the entire `if settings.DEMO_MODE:` block (lines 32-41) with:

```python
        if settings.DEMO_MODE:
            # Step 1: Create named personas (DEMO-001 through DEMO-015)
            self._create_demo_users_and_clients()
            self._update_demo_client_fields()
            # Step 2: Top up each program to 20-30 clients with engine
            self._top_up_demo_data()
```

- [ ] **Step 7: Add _top_up_demo_data method**

Add a new method (keep the old `_generate_config_aware_demo_data` and `_create_demo_users_and_clients` methods intact):

```python
    def _top_up_demo_data(self):
        """Top up demo data to 20-30 clients per program using the engine."""
        import os

        from apps.admin_settings.demo_engine import DemoDataEngine

        demo_profile = os.environ.get("DEMO_DATA_PROFILE", "")
        self.stdout.write("  Topping up demo data with config-aware engine...")
        engine = DemoDataEngine(stdout=self.stdout, stderr=self.stderr)

        try:
            success = engine.run(
                clients_per_program=20,
                profile_path=demo_profile if demo_profile else None,
                force=False,
            )
            if success:
                self.stdout.write("  Demo data topped up successfully.")
            else:
                self.stdout.write("  Demo data already at target volume.")
        except Exception as e:
            self.stderr.write(f"  WARNING: Demo data top-up failed: {e}")
            import traceback
            self.stderr.write(traceback.format_exc())
            self.stderr.write("  Named personas are seeded; engine top-up skipped.")
```

- [ ] **Step 8: Commit Part B**

```bash
git add apps/admin_settings/management/commands/seed.py
git commit -m "feat: top up demo data to 20-30 clients per program via engine

Always use DemoDataEngine with clients_per_program=20 when DEMO_MODE
is enabled. Engine skips if demo data already exists (force=False).
No fallback to hardcoded 15-client path."
```

### Part C: Change generate_demo_data.py default

- [ ] **Step 9: Update the default clients-per-program**

In `apps/admin_settings/management/commands/generate_demo_data.py`, change line 55:

```python
            default=3,
```

to:

```python
            default=20,
```

And update the help text on line 56:

```python
            help="Number of demo clients to create per program (default: 20).",
```

- [ ] **Step 10: Commit Part C**

```bash
git add apps/admin_settings/management/commands/generate_demo_data.py
git commit -m "feat: increase default clients-per-program from 3 to 20"
```

---

## Task 3: Update demo_engine.py — Volume, FHIR Fields, and Data Quality

**Can run in parallel with Tasks 1 and 2.**

This is the largest task. It modifies `apps/admin_settings/demo_engine.py` to:
- Use weighted trend distribution
- Create enrolments via ServiceEpisode with FHIR fields
- Add cross-enrolments for PHIPA demo
- Create finished episodes
- Set PlanTarget FHIR fields
- Populate Program FHIR fields
- Seed OrganizationProfile
- Seed TaxonomyMapping and CidsCodeList
- Increase suggestion themes
- Use 30 clients for group programs

**Files:**
- Modify: `apps/admin_settings/demo_engine.py`

### Part A: Weighted Trend Distribution

- [ ] **Step 1: Read the current trend assignment logic**

In `demo_engine.py`, find where trends are assigned to clients in `create_demo_clients()` (around line 1086). The current code uses `TRENDS[i % len(TRENDS)]`.

- [ ] **Step 2: Change to weighted random selection**

Replace the trend assignment line with:

```python
                trend = random.choices(
                    TRENDS, weights=[40, 20, 20, 10, 10], k=1
                )[0]
```

- [ ] **Step 3: Commit**

```bash
git add apps/admin_settings/demo_engine.py
git commit -m "feat: use weighted trend distribution for demo data

40% improving, 20% stable, 20% mixed, 10% struggling,
10% crisis_then_improving — matches realistic nonprofit outcomes."
```

### Part B: ServiceEpisode Fields and Cross-Enrolments

- [ ] **Step 4: Add ServiceEpisode import**

At the top of `demo_engine.py`, change the import from `apps.clients.models`:

```python
from apps.clients.models import ClientFile, ClientProgramEnrolment
```

to:

```python
from apps.clients.models import ClientFile, ClientProgramEnrolment, ServiceEpisode
```

If `ServiceEpisode` is not directly importable (it may be an alias defined in models.py), check `apps/clients/models.py` for the class name. It might be that `ClientProgramEnrolment` IS `ServiceEpisode` via alias. In that case, the existing import is fine — just use the additional FHIR fields on `ClientProgramEnrolment`.

- [ ] **Step 5: Update create_demo_clients() to populate ServiceEpisode fields**

In `create_demo_clients()`, find the `ClientProgramEnrolment.objects.create()` call (around line 1082). Replace it with:

```python
                # Referral source distribution
                referral_weights = {
                    "self": 30, "agency_external": 25, "healthcare": 15,
                    "community": 15, "school": 5, "shelter": 5, "other": 5,
                }
                referral_source = random.choices(
                    list(referral_weights.keys()),
                    weights=list(referral_weights.values()),
                    k=1,
                )[0]

                started_at = self.now - timedelta(
                    days=random.randint(30, days_span),
                )

                enrolment = ClientProgramEnrolment.objects.create(
                    client_file=client,
                    program=program,
                    status="active",
                    referral_source=referral_source,
                    primary_worker=worker,
                    started_at=started_at,
                    consent_to_aggregate_reporting=True,
                )
```

Note: `days_span` is not available in `create_demo_clients()`. Add it as a parameter: modify the method signature to accept `days_span=180` and pass it from `run()`.

- [ ] **Step 6: Add cross-enrolment logic after primary enrolments**

After the main loop in `create_demo_clients()`, add cross-enrolment logic before the return statement:

```python
        # Cross-enrol 5 clients into Community Kitchen for PHIPA consent demo
        kitchen_program = next(
            (p for p in programs if p.service_model == "group"), None
        )
        if kitchen_program:
            non_kitchen = [
                a for a in client_assignments if a.program != kitchen_program
            ]
            cross_enrol_candidates = random.sample(
                non_kitchen, min(5, len(non_kitchen))
            )
            for assignment in cross_enrol_candidates:
                if not ClientProgramEnrolment.objects.filter(
                    client_file=assignment.client, program=kitchen_program,
                ).exists():
                    ClientProgramEnrolment.objects.create(
                        client_file=assignment.client,
                        program=kitchen_program,
                        status="active",
                        referral_source="agency_internal",
                        primary_worker=worker,
                        consent_to_aggregate_reporting=True,
                    )
            self.log(
                f"  Cross-enrolled {len(cross_enrol_candidates)} clients into "
                f"{kitchen_program.name}."
            )
```

- [ ] **Step 7: Add finished episodes**

After the cross-enrolment logic, add finished episode creation:

```python
        # Create 5-8 finished episodes across programs for discharge demo
        finished_count = random.randint(5, 8)
        end_reasons = ["completed", "completed", "goals_met", "goals_met",
                        "withdrew", "lost_contact", "withdrew", "referred_out"]
        for i in range(min(finished_count, len(client_assignments))):
            # Pick clients from the end of the list (least likely to be named personas)
            idx = len(client_assignments) - 1 - i
            if idx < 0:
                break
            assignment = client_assignments[idx]
            enrolment = ClientProgramEnrolment.objects.filter(
                client_file=assignment.client,
                program=assignment.program,
                status="active",
            ).first()
            if enrolment:
                enrolment.status = "finished"
                enrolment.end_reason = end_reasons[i % len(end_reasons)]
                enrolment.ended_at = self.now - timedelta(
                    days=random.randint(14, 90),
                )
                enrolment.save(update_fields=[
                    "status", "end_reason", "ended_at",
                ])
```

- [ ] **Step 8: Commit**

```bash
git add apps/admin_settings/demo_engine.py
git commit -m "feat: populate ServiceEpisode FHIR fields, cross-enrolments, finished episodes

- Set referral_source, primary_worker, started_at on all enrolments
- Cross-enrol 5 clients into Community Kitchen for PHIPA consent demo
- Create 5-8 finished episodes with end_reason for discharge reporting"
```

### Part C: Program FHIR Fields and OrganizationProfile

- [ ] **Step 9: Add Program FHIR field population**

In the `run()` method, after `discover_programs()` (around line 2787), add:

```python
        # Populate Program FHIR fields
        _program_fhir = {
            "Supported Employment": {
                "cids_sector_code": "group6_employment",
                "population_served_codes": ["working_age_adults"],
                "default_goal_review_days": 90,
            },
            "Housing Stability": {
                "cids_sector_code": "group6_housing",
                "population_served_codes": ["working_age_adults", "at_risk_homelessness"],
                "default_goal_review_days": 90,
            },
            "Youth Drop-In": {
                "cids_sector_code": "group4_education_youth",
                "population_served_codes": ["youth_13_18"],
                "default_goal_review_days": 60,
            },
            "Newcomer Connections": {
                "cids_sector_code": "group6_social_services",
                "population_served_codes": ["newcomers_immigrants"],
                "default_goal_review_days": 90,
            },
            "Community Kitchen": {
                "cids_sector_code": "group6_social_services",
                "population_served_codes": ["general_community"],
                "default_goal_review_days": 30,
            },
        }
        for prog in programs:
            fhir = _program_fhir.get(prog.name, {})
            if fhir:
                changed = False
                for field, value in fhir.items():
                    if not getattr(prog, field, None):
                        setattr(prog, field, value)
                        changed = True
                if changed:
                    prog.save()
```

- [ ] **Step 10: Add OrganizationProfile seeding method**

Add a new method to the `DemoDataEngine` class:

```python
    def _seed_organization_profile(self):
        """Seed a realistic Canadian nonprofit OrganizationProfile."""
        from apps.admin_settings.models import OrganizationProfile

        profile = OrganizationProfile.get_solo()
        if profile.legal_name:
            self.log("  OrganizationProfile already populated.")
            return

        profile.legal_name = "Maple Community Services"
        profile.operating_name = "Maple Community Services"
        profile.description = (
            "A multi-service community agency in Ontario providing "
            "employment support, housing stability, youth programming, "
            "newcomer settlement, and community kitchen services."
        )
        profile.description_fr = (
            "Un organisme communautaire multiservices en Ontario offrant "
            "du soutien \u00e0 l'emploi, de la stabilit\u00e9 en logement, des "
            "programmes jeunesse, de l'\u00e9tablissement pour nouveaux "
            "arrivants et des cuisines communautaires."
        )
        profile.legal_status = "Registered charity"
        profile.sector_codes = [
            "group6_employment", "group6_housing", "group6_social_services",
        ]
        profile.street_address = "150 Main Street"
        profile.city = "Ottawa"
        profile.province = "ON"
        profile.postal_code = "K1A 0B1"
        profile.country = "CA"
        profile.website = "https://demo.konote.ca"
        profile.save()
        self.log("  OrganizationProfile seeded: Maple Community Services.")
```

Call it in `run()` after program discovery:

```python
        self._seed_organization_profile()
```

- [ ] **Step 11: Commit**

```bash
git add apps/admin_settings/demo_engine.py
git commit -m "feat: seed Program FHIR fields and OrganizationProfile

Populate cids_sector_code, population_served_codes, and
default_goal_review_days on all demo programs. Seed OrganizationProfile
as Maple Community Services (Ottawa, ON)."
```

### Part D: TaxonomyMapping and CidsCodeList

- [ ] **Step 12: Add CidsCodeList seeding method**

```python
    def _seed_cids_code_lists(self):
        """Seed IRIS theme and SDG goal code list entries."""
        from apps.admin_settings.models import CidsCodeList

        sdg_goals = [
            ("1", "No Poverty", "Pas de pauvret\u00e9"),
            ("2", "Zero Hunger", "Faim z\u00e9ro"),
            ("3", "Good Health and Well-being", "Bonne sant\u00e9 et bien-\u00eatre"),
            ("4", "Quality Education", "\u00c9ducation de qualit\u00e9"),
            ("5", "Gender Equality", "\u00c9galit\u00e9 entre les sexes"),
            ("8", "Decent Work and Economic Growth", "Travail d\u00e9cent et croissance \u00e9conomique"),
            ("10", "Reduced Inequalities", "In\u00e9galit\u00e9s r\u00e9duites"),
            ("11", "Sustainable Cities and Communities", "Villes et communaut\u00e9s durables"),
        ]
        created = 0
        for code, label, label_fr in sdg_goals:
            _, was_created = CidsCodeList.objects.get_or_create(
                list_name="SDGGoals",
                code=code,
                defaults={
                    "label": label,
                    "label_fr": label_fr,
                    "defined_by_name": "United Nations",
                    "defined_by_uri": "https://sdgs.un.org/goals",
                },
            )
            if was_created:
                created += 1

        # IRIS+ metric codes used in the metric library
        iris_codes = [
            ("PI2061", "Job Placement Rate", "Taux de placement en emploi"),
        ]
        for code, label, label_fr in iris_codes:
            _, was_created = CidsCodeList.objects.get_or_create(
                list_name="IrisMetric53",
                code=code,
                defaults={
                    "label": label,
                    "label_fr": label_fr,
                    "defined_by_name": "GIIN",
                    "defined_by_uri": "https://iris.thegiin.org/",
                },
            )
            if was_created:
                created += 1

        self.log(f"  CidsCodeList: {created} entries seeded.")
```

- [ ] **Step 13: Add TaxonomyMapping seeding method**

```python
    def _seed_taxonomy_mappings(self, programs):
        """Seed sample taxonomy mappings for universal and program metrics."""
        from apps.admin_settings.models import TaxonomyMapping
        from apps.plans.models import MetricDefinition

        mappings = [
            ("Goal Progress", "sdg", "1", "SDGGoals", "SDG 1: No Poverty"),
            ("Self-Efficacy", "common_approach", "CA-IND-001", "", "Individual Wellbeing"),
            ("Job Placement", "iris_plus", "PI2061", "IrisMetric53", "Job Placement Rate"),
            ("Job Placement", "sdg", "8", "SDGGoals", "SDG 8: Decent Work"),
            ("Housing Secured", "sdg", "11", "SDGGoals", "SDG 11: Sustainable Cities"),
            ("School Enrolment", "sdg", "4", "SDGGoals", "SDG 4: Quality Education"),
        ]
        created = 0
        for metric_name, system, code, list_name, label in mappings:
            md = MetricDefinition.objects.filter(
                name=metric_name, is_enabled=True,
            ).first()
            if not md:
                continue
            _, was_created = TaxonomyMapping.objects.get_or_create(
                metric_definition=md,
                taxonomy_system=system,
                taxonomy_code=code,
                defaults={
                    "taxonomy_list_name": list_name,
                    "taxonomy_label": label,
                    "mapping_status": "approved",
                    "mapping_source": "manual",
                },
            )
            if was_created:
                created += 1

        self.log(f"  TaxonomyMapping: {created} mappings seeded.")
```

Call both in `run()` after `_seed_organization_profile()`:

```python
        self._seed_cids_code_lists()
        self._seed_taxonomy_mappings(programs)
```

- [ ] **Step 14: Commit**

```bash
git add apps/admin_settings/demo_engine.py
git commit -m "feat: seed CidsCodeList and TaxonomyMapping for FHIR demo

Seed SDG goals 1-11, IRIS+ PI2061 code list entries, and 6 taxonomy
mappings linking universal metrics to SDG/IRIS+/Common Approach."
```

### Part E: PlanTarget FHIR Fields

- [ ] **Step 15: Read generate_plan() method**

Find the `generate_plan()` method in `demo_engine.py` and understand how PlanTargets are created.

- [ ] **Step 16: Set goal_source and target_date on PlanTargets**

In the `generate_plan()` method, after creating each `PlanTarget`, add:

```python
                # Set FHIR goal metadata
                goal_sources = random.choices(
                    ["joint", "participant", "worker", "funder_required"],
                    weights=[50, 30, 15, 5],
                    k=1,
                )[0]
                target.goal_source = goal_sources
                target.goal_source_method = "heuristic"
                if program.default_goal_review_days:
                    target.target_date = (
                        self.now - timedelta(days=random.randint(0, days_span))
                        + timedelta(days=program.default_goal_review_days)
                    ).date()
                target.save(update_fields=[
                    "goal_source", "goal_source_method", "target_date",
                ])
```

Note: `days_span` may not be available in `generate_plan()`. Check the method signature and pass it if needed.

- [ ] **Step 17: Commit**

```bash
git add apps/admin_settings/demo_engine.py
git commit -m "feat: set goal_source and target_date on demo PlanTargets

50% joint, 30% participant, 15% worker, 5% funder_required.
target_date derived from program.default_goal_review_days."
```

### Part F: Suggestion Themes Enhancement

- [ ] **Step 18: Read current generate_suggestion_themes() method**

Find `generate_suggestion_themes()` in `demo_engine.py` and understand how themes are created.

- [ ] **Step 19: Add program-specific theme content**

Add a constant near the top of the file (after the existing text pools):

```python
PROGRAM_SUGGESTION_THEMES = {
    "Supported Employment": [
        ("More flexible scheduling for interviews", "important", "open"),
        ("Resume workshop follow-up", "noted", "addressed"),
        ("Interview practice sessions", "noted", "open"),
    ],
    "Housing Stability": [
        ("Faster landlord reference letters", "urgent", "open"),
        ("Budgeting workshop request", "noted", "open"),
        ("Move-in kit supplies", "noted", "open"),
    ],
    "Youth Drop-In": [
        ("More weekend activities", "important", "open"),
        ("Homework help timing", "noted", "addressed"),
        ("Music and art supplies", "noted", "open"),
    ],
    "Newcomer Connections": [
        ("Conversation circle frequency", "important", "open"),
        ("More translated materials", "noted", "open"),
        ("Childcare during sessions", "important", "open"),
    ],
    "Community Kitchen": [
        ("Recipe books to take home", "noted", "addressed"),
        ("Childcare during sessions", "important", "open"),
        ("Allergen-free options", "noted", "open"),
    ],
}
```

- [ ] **Step 20: Update generate_suggestion_themes() to use program-specific content**

Modify `generate_suggestion_themes()` to check `PROGRAM_SUGGESTION_THEMES` for the program name and use those themes instead of (or in addition to) the generic ones. For each theme, create the `SuggestionTheme` object and link 3-8 recent notes via `SuggestionLink`. Mark themes with status "addressed" using `SuggestionTheme.status = "addressed"`.

- [ ] **Step 21: Commit**

```bash
git add apps/admin_settings/demo_engine.py
git commit -m "feat: add program-specific suggestion themes (3-4 per program)

11 themes across 5 programs with realistic content. 3 marked as
addressed to demonstrate responsiveness tracking."
```

### Part G: Group Program Volume (30 Clients)

- [ ] **Step 22: Modify create_demo_clients() to use 30 for group programs**

In `create_demo_clients()`, before the main loop, determine per-program client count:

```python
            actual_count = clients_per_program
            if program.service_model == "group":
                actual_count = max(clients_per_program, 30)
```

Use `actual_count` instead of `clients_per_program` in the inner loop range.

- [ ] **Step 23: Commit**

```bash
git add apps/admin_settings/demo_engine.py
git commit -m "feat: use 30 clients for group programs in demo data

Group programs (Community Kitchen) get 30 participants instead of 20
to reflect realistic group service volumes."
```

### Part H: Cleanup method update

- [ ] **Step 24: Update cleanup_demo_data() to handle new seeded data**

Add cleanup for OrganizationProfile, TaxonomyMapping, and CidsCodeList in `cleanup_demo_data()`:

```python
        # Clear demo-seeded OrganizationProfile
        from apps.admin_settings.models import OrganizationProfile
        profile = OrganizationProfile.get_solo()
        if profile.legal_name == "Maple Community Services":
            profile.legal_name = ""
            profile.operating_name = ""
            profile.description = ""
            profile.description_fr = ""
            profile.save()

        # Clear demo taxonomy mappings (only manual/system_suggested)
        from apps.admin_settings.models import TaxonomyMapping
        TaxonomyMapping.objects.filter(
            mapping_source="manual", mapping_status="approved",
        ).delete()
```

- [ ] **Step 25: Commit**

```bash
git add apps/admin_settings/demo_engine.py
git commit -m "feat: clean up OrganizationProfile and TaxonomyMapping on force regenerate"
```

---

## Task 4: Verification and Final Commit

**Depends on Tasks 1-3 being complete.**

- [ ] **Step 1: Verify JSON validity**

```bash
python -c "import json; data = json.load(open('seeds/metric_library.json')); print(f'{len(data)} metrics loaded'); assert all('evidence_type' in m for m in data), 'Missing evidence_type'"
```

- [ ] **Step 2: Verify Python syntax of all changed files**

```bash
python -c "import py_compile; py_compile.compile('apps/admin_settings/demo_engine.py', doraise=True); print('demo_engine.py OK')"
python -c "import py_compile; py_compile.compile('apps/admin_settings/management/commands/seed.py', doraise=True); print('seed.py OK')"
python -c "import py_compile; py_compile.compile('apps/admin_settings/management/commands/generate_demo_data.py', doraise=True); print('generate_demo_data.py OK')"
```

- [ ] **Step 3: Review all changes**

```bash
git diff --stat
git log --oneline -10
```

Verify that all commits are present and the diff looks reasonable.

---

## Parallelisation Guide

Tasks 1, 2, and 3 modify different files and can be dispatched to parallel agents:

| Agent | Task | Files Modified |
|-------|------|---------------|
| Agent 1 | Task 1 (metric_library.json) | `seeds/metric_library.json` |
| Agent 2 | Task 2 (seed.py + generate_demo_data.py) | `apps/admin_settings/management/commands/seed.py`, `apps/admin_settings/management/commands/generate_demo_data.py` |
| Agent 3 | Task 3 (demo_engine.py) | `apps/admin_settings/demo_engine.py` |

Task 4 (verification) runs after all three agents complete.

**Agent isolation:** Use `isolation: "worktree"` for each agent so they don't conflict. After all complete, merge their branches.

**Alternatively:** Since Tasks 1-3 touch completely different files, they can run in the same worktree without conflict if dispatched sequentially or if the agents coordinate via separate commits.
