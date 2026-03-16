# FHIR Metadata Enrichment — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add FHIR-informed metadata fields to PlanTarget, PlanSection, ProgressNote, and Program — all AI-inferred or auto-populated, zero worker burden — to enable richer funder reporting without additional data entry.

**Architecture:** Nullable fields on existing models, auto-populated via save() logic (deterministic), heuristic classification from existing field patterns, and LLM inference via management command. A JSONField tracks the source of each auto-populated value for audit and quality reporting.

**Tech Stack:** Django 5, PostgreSQL 16, OpenRouter API (existing konote/ai.py pattern)

**Depends on:** Phase F1 (ServiceEpisode) — already complete. Phase F2 (achievement_status) — already complete.

**Design rationale:** Approved under "Borrow FHIR concepts without FHIR compliance" (tasks/design-rationale/fhir-informed-modelling.md). Expert panel consensus 2026-03-16: AI-inferred metadata is more accurate than human-coded; zero additional form fields; make metadata invisible to workers.

---

## Why Everything at Once

All new fields are nullable with `blank=True, default=""` (or `default=dict` for JSONField). This means:
- Empty fields cause zero harm — reports skip nulls or show "not classified"
- The schema changes are trivially reversible (drop a column)
- Deterministic logic (episode FK) works immediately on save
- Heuristic classification (goal_source) works immediately on save
- AI inference can run as a backfill whenever ready — no dependency on having it Day 1
- No new form fields, no new user-facing UI, no workflow changes

There is no scenario where having the fields empty is worse than not having them at all.

---

## Changes Summary

### New Fields

**ProgressNote** (`apps/notes/models.py`):

| Field | Type | FHIR Source | Population Method |
|---|---|---|---|
| `episode` | FK to ServiceEpisode, null=True, blank=True, SET_NULL | Encounter.episodeOfCare | Auto on save: lookup active episode for client + author_program |

**PlanTarget** (`apps/plans/models.py`):

| Field | Type | FHIR Source | Population Method |
|---|---|---|---|
| `goal_source` | CharField(max_length=20, blank=True) | Goal.source | Heuristic from description/client_goal fields + AI from first session note |
| `target_date` | DateField(null=True, blank=True) | Goal.target.due | Program default (default_goal_review_days) + AI extraction of temporal language |
| `continuous` | BooleanField(default=False) | Goal.continuous | AI classification: maintenance vs. time-bound |
| `metadata_sources` | JSONField(default=dict) | — | Tracks source of each auto-populated value |
| Add `on_hold` to STATUS_CHOICES | — | Goal.lifecycleStatus | Worker action (pause a goal during crisis) |

**PlanSection** (`apps/plans/models.py`):

| Field | Type | FHIR Source | Population Method |
|---|---|---|---|
| `period_start` | DateField(null=True, blank=True) | CarePlan.period.start | Auto from earliest target created_at in section |
| `period_end` | DateField(null=True, blank=True) | CarePlan.period.end | Auto when all targets completed/deactivated |

**Program** (`apps/programs/models.py`):

| Field | Type | Purpose | Population Method |
|---|---|---|---|
| `default_goal_review_days` | PositiveIntegerField(null=True, blank=True) | Default target_date offset for goals in this program | Admin setting (e.g., 90 days) |

### Auto-Population Logic (on save — zero latency impact)

**1. Episode FK** (deterministic, `ProgressNote.save()`):
```python
# In ProgressNote.save(), after existing author_role logic:
if not self.pk and not self.episode_id and self.client_file_id and self.author_program_id:
    from apps.clients.models import ServiceEpisode
    ep = ServiceEpisode.objects.filter(
        client_file_id=self.client_file_id,
        program_id=self.author_program_id,
        status__in=ServiceEpisode.ACCESSIBLE_STATUSES,
    ).first()
    if ep:
        self.episode = ep
```

**2. Goal Source** (heuristic, `PlanTarget.save()` on first save):
```python
if not self.pk and not self.goal_source:
    has_description = bool(self._description_encrypted and self._description_encrypted != b"")
    has_client_goal = bool(self._client_goal_encrypted and self._client_goal_encrypted != b"")
    if has_client_goal and has_description:
        self.goal_source = "joint"
    elif has_client_goal:
        self.goal_source = "participant"
    elif has_description:
        self.goal_source = "worker"
    if self.goal_source:
        self.metadata_sources["goal_source"] = "heuristic"
```

**3. Target Date** (program default, `PlanTarget.save()` on first save):
```python
if not self.pk and not self.target_date:
    program = self.plan_section.program if self.plan_section_id else None
    if program and program.default_goal_review_days:
        from datetime import timedelta
        self.target_date = (timezone.now() + timedelta(days=program.default_goal_review_days)).date()
        self.metadata_sources["target_date"] = "program_default"
```

**4. Plan Section Period** (management command, not on every save):
```python
# Computed by backfill/batch command — not real-time
section.period_start = section.targets.aggregate(Min("created_at"))["created_at__min"].date()
if section.targets.filter(status="default").count() == 0:
    section.period_end = section.targets.aggregate(Max("updated_at"))["updated_at__max"].date()
```

### Goal Source Choices

| Value | Display (EN) | Display (FR) | When |
|---|---|---|---|
| `participant` | Participant-initiated | Initié par le participant | client_goal populated, no worker description |
| `worker` | Worker-initiated | Initié par l'intervenant | Worker description only, no client words |
| `joint` | Jointly developed | Développé conjointement | Both description and client_goal populated |
| `funder_required` | Funder-required | Exigé par le bailleur de fonds | Goal metrics match program's standard metric set (AI-classified) |

### Metadata Sources JSONField

Tracks how each auto-populated field got its value. Example:
```json
{
    "goal_source": "heuristic",
    "target_date": "program_default",
    "continuous": "ai_inferred"
}
```

Helper method on PlanTarget:
```python
def is_auto_inferred(self, field_name):
    return self.metadata_sources.get(field_name) in ("heuristic", "ai_inferred", "program_default")
```

### AI Inference Management Command

`python manage.py infer_fhir_metadata [--backfill] [--dry-run] [--batch-size=50]`

Processes PlanTargets where metadata needs enrichment:

| Field | Signal | AI Prompt |
|---|---|---|
| `goal_source` (when heuristic inconclusive) | First ProgressNote referencing this target | "Given this session note and goal description, classify who initiated this goal: participant, worker, joint, or funder_required" |
| `continuous` | Goal name + description | "Is this an ongoing maintenance goal (e.g., 'maintain sobriety', 'continue attending school') or a time-bound achievement goal (e.g., 'find housing', 'complete GED')? Return true for ongoing, false for time-bound." |
| `target_date` (when no program default) | Goal description | "Extract any temporal deadline from this goal description. Return ISO date or null. Examples: 'within 6 months' → date, 'find housing' → null" |

Uses existing OpenRouter integration pattern from `konote/ai.py` — PII-free prompts only (goal descriptions are encrypted; the management command decrypts in-memory, sends only the text to the LLM, never client names or identifiers).

### Backfill for Existing Data

The same management command with `--backfill` flag processes historical records:

1. **Episode FK on ProgressNotes** (deterministic, no AI):
   - Match each note's `client_file` + `author_program` + `created_at` to a ServiceEpisode that was active at that time
   - Query: episodes where `started_at <= note.created_at` and (`ended_at IS NULL` or `ended_at >= note.created_at`)

2. **Goal source on PlanTargets** (heuristic first, then AI):
   - Apply heuristic (description/client_goal presence) to all existing targets
   - Queue remaining (no heuristic result) for AI classification

3. **Plan section periods** (deterministic):
   - Compute from target dates in each section

### Report-Time Computations (No Schema Changes Needed)

These are derived from existing + new data at query time:

| Metric | Query |
|---|---|
| Goal acceptance | `PlanTarget.objects.exclude(_client_goal_encrypted=b"").count()` → participant engaged |
| Engagement intensity per goal | `ProgressNoteTarget.objects.filter(plan_target=X).count()` |
| Service hours per episode | `ProgressNote.objects.filter(episode=X).aggregate(Sum("duration_minutes"))` |
| Contacts per episode | `ProgressNote.objects.filter(episode=X).count()` |
| Time to achievement | `F("first_achieved_at") - F("created_at")` (or `- F("target_date")` for on-time analysis) |
| Goals achieved on time | `PlanTarget.objects.filter(first_achieved_at__lte=F("target_date"))` |

---

## Task Breakdown

### Task 1: Add All New Model Fields

**Files:**
- Modify: `apps/notes/models.py` (ProgressNote class, ~line 177)
- Modify: `apps/plans/models.py` (PlanTarget ~line 417, PlanSection ~line 388)
- Modify: `apps/programs/models.py` (Program ~line 9)

- [ ] **Step 1: Add `episode` FK to ProgressNote**

In `apps/notes/models.py`, add to ProgressNote after the `circle` field (~line 230):

```python
# ── FHIR metadata (Encounter → EpisodeOfCare link) ──────────────
episode = models.ForeignKey(
    "clients.ServiceEpisode",
    null=True, blank=True,
    on_delete=models.SET_NULL,
    related_name="encounter_notes",
    help_text=_("Auto-linked service episode for this encounter."),
)
```

- [ ] **Step 2: Add FHIR fields to PlanTarget**

In `apps/plans/models.py`, add to PlanTarget after the achievement_status block (~line 475):

```python
# ── FHIR Goal metadata (auto-populated) ──────────────────────────
GOAL_SOURCE_CHOICES = [
    ("participant", _("Participant-initiated")),
    ("worker", _("Worker-initiated")),
    ("joint", _("Jointly developed")),
    ("funder_required", _("Funder-required")),
]

goal_source = models.CharField(
    max_length=20, blank=True, default="",
    choices=GOAL_SOURCE_CHOICES,
    help_text=_("Who established this goal. Auto-classified from content."),
)
target_date = models.DateField(
    null=True, blank=True,
    help_text=_("Target completion date. Auto-set from program default or AI extraction."),
)
continuous = models.BooleanField(
    default=False,
    help_text=_("Ongoing maintenance goal vs. time-bound achievement goal."),
)
metadata_sources = models.JSONField(
    default=dict, blank=True,
    help_text=_("Tracks how each auto-populated field was derived."),
)
```

Also expand STATUS_CHOICES (line ~423) to add `on_hold`:
```python
STATUS_CHOICES = [
    ("default", _("Active")),
    ("on_hold", _("On Hold")),
    ("completed", _("Completed")),
    ("deactivated", _("Deactivated")),
]
```

- [ ] **Step 3: Add period fields to PlanSection**

In `apps/plans/models.py`, add to PlanSection after `sort_order` (~line 404):

```python
# ── FHIR CarePlan.period ─────────────────────────────────────────
period_start = models.DateField(
    null=True, blank=True,
    help_text=_("When this plan section became active. Auto-computed from target activity."),
)
period_end = models.DateField(
    null=True, blank=True,
    help_text=_("When this plan section concluded. Auto-set when all targets complete."),
)
```

- [ ] **Step 4: Add default_goal_review_days to Program**

In `apps/programs/models.py`, add to Program after `funder_program_code` (~line 70):

```python
# ── FHIR-informed defaults ───────────────────────────────────────
default_goal_review_days = models.PositiveIntegerField(
    null=True, blank=True,
    help_text=_("Default target date offset (days) for goals created in this program."),
)
```

- [ ] **Step 5: Add `is_auto_inferred` helper to PlanTarget**

In `apps/plans/models.py`, add method to PlanTarget class:

```python
def is_auto_inferred(self, field_name):
    """Check if a metadata field was auto-populated (for template badges)."""
    return self.metadata_sources.get(field_name) in (
        "heuristic", "ai_inferred", "program_default", "computed",
    )
```

- [ ] **Step 6: Commit schema changes**

```bash
git add apps/notes/models.py apps/plans/models.py apps/programs/models.py
git commit -m "feat: add FHIR metadata fields to PlanTarget, PlanSection, ProgressNote, Program

Add episode FK (Encounter→EpisodeOfCare link), goal_source, target_date,
continuous, metadata_sources JSONField, plan section period, program
default_goal_review_days, and on_hold status. All fields nullable/optional.
Zero worker-facing changes — all auto-populated by save logic or AI inference."
```

---

### Task 2: Add Auto-Population Logic

**Files:**
- Modify: `apps/notes/models.py` (ProgressNote.save)
- Modify: `apps/plans/models.py` (PlanTarget.save)

- [ ] **Step 1: Add episode auto-linking to ProgressNote.save()**

In `apps/notes/models.py`, extend the existing `save()` method (line ~372). Add after the `author_role` auto-fill block:

```python
# Auto-link to active service episode
if not self.pk and not self.episode_id and self.client_file_id and self.author_program_id:
    from apps.clients.models import ServiceEpisode
    ep = ServiceEpisode.objects.filter(
        client_file_id=self.client_file_id,
        program_id=self.author_program_id,
        status__in=ServiceEpisode.ACCESSIBLE_STATUSES,
    ).order_by("-started_at").first()
    if ep:
        self.episode = ep
```

- [ ] **Step 2: Add goal_source heuristic + target_date to PlanTarget.save()**

In `apps/plans/models.py`, PlanTarget does not currently have a custom save() method. Add one before the `name` property (~line 477):

```python
def save(self, *args, **kwargs):
    is_new = self.pk is None

    # Auto-classify goal source from field population patterns
    if is_new and not self.goal_source:
        has_description = bool(self._description_encrypted and self._description_encrypted != b"")
        has_client_goal = bool(self._client_goal_encrypted and self._client_goal_encrypted != b"")
        if has_client_goal and has_description:
            self.goal_source = "joint"
        elif has_client_goal:
            self.goal_source = "participant"
        elif has_description:
            self.goal_source = "worker"
        if self.goal_source:
            if not isinstance(self.metadata_sources, dict):
                self.metadata_sources = {}
            self.metadata_sources["goal_source"] = "heuristic"

    # Auto-set target_date from program default
    if is_new and not self.target_date and self.plan_section_id:
        try:
            program = self.plan_section.program
            if program and program.default_goal_review_days:
                from datetime import timedelta
                from django.utils import timezone
                self.target_date = (timezone.now() + timedelta(days=program.default_goal_review_days)).date()
                if not isinstance(self.metadata_sources, dict):
                    self.metadata_sources = {}
                self.metadata_sources["target_date"] = "program_default"
        except Exception:
            pass  # Plan section may not have a program

    super().save(*args, **kwargs)
```

- [ ] **Step 3: Commit auto-population logic**

```bash
git add apps/notes/models.py apps/plans/models.py
git commit -m "feat: auto-populate episode FK and goal metadata on save

ProgressNote.save() links to active ServiceEpisode for client+program.
PlanTarget.save() classifies goal_source from description/client_goal
field patterns and sets target_date from program default_goal_review_days."
```

---

### Task 3: Write Migration

**Files:**
- Create: `apps/notes/migrations/NNNN_fhir_episode_link.py`
- Create: `apps/plans/migrations/NNNN_fhir_goal_metadata.py`
- Create: `apps/programs/migrations/NNNN_default_goal_review_days.py`

Note: Migration numbers depend on what's already in the migrations directories. Check the latest migration number in each app before creating.

- [ ] **Step 1: Check current migration numbers**

```bash
ls apps/notes/migrations/ | tail -5
ls apps/plans/migrations/ | tail -5
ls apps/programs/migrations/ | tail -5
```

- [ ] **Step 2: Create notes migration (episode FK)**

Create the migration file for the episode FK. The file number depends on what already exists.

```python
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("notes", "NNNN_previous"),  # Replace with actual last migration
        ("clients", "NNNN_previous"),  # Replace with actual last migration
    ]

    operations = [
        migrations.AddField(
            model_name="progressnote",
            name="episode",
            field=models.ForeignKey(
                blank=True,
                help_text="Auto-linked service episode for this encounter.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="encounter_notes",
                to="clients.serviceepisode",
            ),
        ),
    ]
```

- [ ] **Step 3: Create plans migration (goal metadata + section periods)**

```python
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("plans", "NNNN_previous"),  # Replace with actual last migration
    ]

    operations = [
        # PlanTarget fields
        migrations.AddField(
            model_name="plantarget",
            name="goal_source",
            field=models.CharField(
                blank=True, default="", max_length=20,
                choices=[
                    ("participant", "Participant-initiated"),
                    ("worker", "Worker-initiated"),
                    ("joint", "Jointly developed"),
                    ("funder_required", "Funder-required"),
                ],
                help_text="Who established this goal. Auto-classified from content.",
            ),
        ),
        migrations.AddField(
            model_name="plantarget",
            name="target_date",
            field=models.DateField(
                blank=True, null=True,
                help_text="Target completion date. Auto-set from program default or AI extraction.",
            ),
        ),
        migrations.AddField(
            model_name="plantarget",
            name="continuous",
            field=models.BooleanField(
                default=False,
                help_text="Ongoing maintenance goal vs. time-bound achievement goal.",
            ),
        ),
        migrations.AddField(
            model_name="plantarget",
            name="metadata_sources",
            field=models.JSONField(
                blank=True, default=dict,
                help_text="Tracks how each auto-populated field was derived.",
            ),
        ),
        migrations.AlterField(
            model_name="plantarget",
            name="status",
            field=models.CharField(
                max_length=20, default="default",
                choices=[
                    ("default", "Active"),
                    ("on_hold", "On Hold"),
                    ("completed", "Completed"),
                    ("deactivated", "Deactivated"),
                ],
            ),
        ),
        # PlanSection fields
        migrations.AddField(
            model_name="plansection",
            name="period_start",
            field=models.DateField(
                blank=True, null=True,
                help_text="When this plan section became active. Auto-computed from target activity.",
            ),
        ),
        migrations.AddField(
            model_name="plansection",
            name="period_end",
            field=models.DateField(
                blank=True, null=True,
                help_text="When this plan section concluded. Auto-set when all targets complete.",
            ),
        ),
    ]
```

- [ ] **Step 4: Create programs migration**

```python
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "NNNN_previous"),  # Replace with actual last migration
    ]

    operations = [
        migrations.AddField(
            model_name="program",
            name="default_goal_review_days",
            field=models.PositiveIntegerField(
                blank=True, null=True,
                help_text="Default target date offset (days) for goals created in this program.",
            ),
        ),
    ]
```

- [ ] **Step 5: Commit migrations**

```bash
git add apps/notes/migrations/ apps/plans/migrations/ apps/programs/migrations/
git commit -m "feat: add migrations for FHIR metadata fields

Episode FK on ProgressNote, goal_source/target_date/continuous/metadata_sources
on PlanTarget, period_start/period_end on PlanSection, default_goal_review_days
on Program. All nullable — zero-risk migration."
```

---

### Task 4: Write Tests

**Files:**
- Modify: `tests/test_plans.py`
- Modify: `tests/test_notes.py`

- [ ] **Step 1: Add goal source heuristic tests to test_plans.py**

```python
@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class GoalSourceHeuristicTest(TestCase):
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Test Program")
        self.client_file = ClientFile()
        self.client_file.first_name = "Test"
        self.client_file.last_name = "Client"
        self.client_file.save()
        self.section = PlanSection.objects.create(
            client_file=self.client_file,
            name="Test Section",
            program=self.program,
        )

    def test_joint_when_both_fields_populated(self):
        target = PlanTarget(
            plan_section=self.section,
            client_file=self.client_file,
        )
        target.name = "Find housing"
        target.description = "Worker notes about housing plan"
        target.client_goal = "I want a safe place to live"
        target.save()
        self.assertEqual(target.goal_source, "joint")
        self.assertEqual(target.metadata_sources.get("goal_source"), "heuristic")

    def test_participant_when_only_client_goal(self):
        target = PlanTarget(
            plan_section=self.section,
            client_file=self.client_file,
        )
        target.name = "Find housing"
        target.client_goal = "I want a safe place to live"
        target.save()
        self.assertEqual(target.goal_source, "participant")

    def test_worker_when_only_description(self):
        target = PlanTarget(
            plan_section=self.section,
            client_file=self.client_file,
        )
        target.name = "Improve coping skills"
        target.description = "Build resilience strategies"
        target.save()
        self.assertEqual(target.goal_source, "worker")

    def test_empty_when_neither_populated(self):
        target = PlanTarget(
            plan_section=self.section,
            client_file=self.client_file,
        )
        target.name = "Generic goal"
        target.save()
        self.assertEqual(target.goal_source, "")

    def test_target_date_from_program_default(self):
        self.program.default_goal_review_days = 90
        self.program.save()
        target = PlanTarget(
            plan_section=self.section,
            client_file=self.client_file,
        )
        target.name = "Test goal"
        target.save()
        self.assertIsNotNone(target.target_date)
        self.assertEqual(target.metadata_sources.get("target_date"), "program_default")

    def test_no_target_date_without_program_default(self):
        target = PlanTarget(
            plan_section=self.section,
            client_file=self.client_file,
        )
        target.name = "Test goal"
        target.save()
        self.assertIsNone(target.target_date)

    def test_on_hold_status_valid(self):
        target = PlanTarget(
            plan_section=self.section,
            client_file=self.client_file,
        )
        target.name = "Test goal"
        target.save()
        target.status = "on_hold"
        target.save()
        target.refresh_from_db()
        self.assertEqual(target.status, "on_hold")

    def test_goal_source_not_overwritten_on_update(self):
        target = PlanTarget(
            plan_section=self.section,
            client_file=self.client_file,
        )
        target.name = "Test goal"
        target.description = "Worker description"
        target.save()
        self.assertEqual(target.goal_source, "worker")
        # Now add client_goal and resave — should NOT change goal_source
        target.client_goal = "My own words"
        target.save()
        self.assertEqual(target.goal_source, "worker")  # Preserved from creation
```

- [ ] **Step 2: Add episode FK auto-link tests to test_notes.py**

```python
@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class EpisodeAutoLinkTest(TestCase):
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Test Program")
        self.user = get_user_model().objects.create_user(
            username="worker", password="testpass123"
        )
        self.client_file = ClientFile()
        self.client_file.first_name = "Test"
        self.client_file.last_name = "Client"
        self.client_file.save()
        self.episode = ServiceEpisode.objects.create(
            client_file=self.client_file,
            program=self.program,
            status="active",
        )

    def test_note_auto_links_to_active_episode(self):
        note = ProgressNote(
            client_file=self.client_file,
            author=self.user,
            author_program=self.program,
            note_type="quick",
            interaction_type="session",
        )
        note.notes_text = "Session notes"
        note.save()
        self.assertEqual(note.episode, self.episode)

    def test_note_no_link_when_no_active_episode(self):
        self.episode.status = "finished"
        self.episode.save()
        note = ProgressNote(
            client_file=self.client_file,
            author=self.user,
            author_program=self.program,
            note_type="quick",
            interaction_type="session",
        )
        note.notes_text = "Session notes"
        note.save()
        self.assertIsNone(note.episode)

    def test_note_no_link_when_no_program(self):
        note = ProgressNote(
            client_file=self.client_file,
            author=self.user,
            author_program=None,
            note_type="quick",
            interaction_type="session",
        )
        note.notes_text = "Quick note"
        note.save()
        self.assertIsNone(note.episode)

    def test_episode_not_overwritten_on_update(self):
        note = ProgressNote(
            client_file=self.client_file,
            author=self.user,
            author_program=self.program,
            note_type="quick",
            interaction_type="session",
        )
        note.notes_text = "Session notes"
        note.save()
        self.assertEqual(note.episode, self.episode)
        # Finish episode and resave note — should keep original link
        self.episode.status = "finished"
        self.episode.save()
        note.notes_text = "Updated notes"
        note.save()
        self.assertEqual(note.episode_id, self.episode.pk)
```

- [ ] **Step 3: Commit tests**

```bash
git add tests/test_plans.py tests/test_notes.py
git commit -m "test: add tests for FHIR metadata auto-population

Test goal_source heuristic classification, target_date from program default,
on_hold status, episode FK auto-linking, and preservation on update."
```

---

### Task 5: Create Backfill Management Command

**Files:**
- Create: `apps/plans/management/commands/backfill_fhir_metadata.py`
- Create: `apps/plans/management/__init__.py` (if not exists)
- Create: `apps/plans/management/commands/__init__.py` (if not exists)

- [ ] **Step 1: Create management command directory structure**

```bash
mkdir -p apps/plans/management/commands
touch apps/plans/management/__init__.py
touch apps/plans/management/commands/__init__.py
```

- [ ] **Step 2: Write backfill command**

Create `apps/plans/management/commands/backfill_fhir_metadata.py`:

```python
"""Backfill FHIR metadata on existing records.

Handles three types of backfill:
1. Episode FK on ProgressNotes (deterministic — no AI)
2. Goal source on PlanTargets (heuristic — no AI)
3. Plan section periods (deterministic — no AI)

AI-based inference (goal_source refinement, continuous, target_date extraction)
is handled separately by infer_fhir_metadata command.
"""
from django.core.management.base import BaseCommand
from django.db.models import Min, Max, Q


class Command(BaseCommand):
    help = "Backfill FHIR metadata fields on existing records (deterministic only, no AI)"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Show what would change without saving")
        parser.add_argument("--episodes", action="store_true", help="Backfill episode FK on ProgressNotes")
        parser.add_argument("--goals", action="store_true", help="Backfill goal_source on PlanTargets")
        parser.add_argument("--sections", action="store_true", help="Backfill period on PlanSections")
        parser.add_argument("--all", action="store_true", help="Run all backfills")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        run_all = options["all"]

        if run_all or options["episodes"]:
            self._backfill_episodes(dry_run)
        if run_all or options["goals"]:
            self._backfill_goals(dry_run)
        if run_all or options["sections"]:
            self._backfill_sections(dry_run)

        if not any([run_all, options["episodes"], options["goals"], options["sections"]]):
            self.stdout.write("Specify --all or one of --episodes, --goals, --sections")

    def _backfill_episodes(self, dry_run):
        """Link existing ProgressNotes to their ServiceEpisode."""
        from apps.notes.models import ProgressNote
        from apps.clients.models import ServiceEpisode

        notes = ProgressNote.objects.filter(
            episode__isnull=True,
            author_program__isnull=False,
        )
        total = notes.count()
        linked = 0

        self.stdout.write(f"Processing {total} notes without episode link...")

        for note in notes.iterator():
            # Find episode that was active when note was written
            effective_date = note.backdate or note.created_at
            ep = ServiceEpisode.objects.filter(
                client_file_id=note.client_file_id,
                program_id=note.author_program_id,
                started_at__lte=effective_date,
            ).filter(
                Q(ended_at__isnull=True) | Q(ended_at__gte=effective_date)
            ).order_by("-started_at").first()

            if ep:
                if not dry_run:
                    ProgressNote.objects.filter(pk=note.pk).update(episode=ep)
                linked += 1

        prefix = "[DRY RUN] " if dry_run else ""
        self.stdout.write(self.style.SUCCESS(
            f"{prefix}Linked {linked}/{total} notes to episodes"
        ))

    def _backfill_goals(self, dry_run):
        """Apply goal_source heuristic to existing PlanTargets."""
        from apps.plans.models import PlanTarget

        targets = PlanTarget.objects.filter(goal_source="")
        total = targets.count()
        classified = 0

        self.stdout.write(f"Processing {total} targets without goal_source...")

        for target in targets.iterator():
            has_desc = bool(target._description_encrypted and target._description_encrypted != b"")
            has_client = bool(target._client_goal_encrypted and target._client_goal_encrypted != b"")

            source = ""
            if has_client and has_desc:
                source = "joint"
            elif has_client:
                source = "participant"
            elif has_desc:
                source = "worker"

            if source:
                if not dry_run:
                    meta = target.metadata_sources or {}
                    meta["goal_source"] = "heuristic"
                    PlanTarget.objects.filter(pk=target.pk).update(
                        goal_source=source, metadata_sources=meta,
                    )
                classified += 1

        prefix = "[DRY RUN] " if dry_run else ""
        self.stdout.write(self.style.SUCCESS(
            f"{prefix}Classified {classified}/{total} targets"
        ))

    def _backfill_sections(self, dry_run):
        """Compute period_start/period_end for PlanSections."""
        from apps.plans.models import PlanSection

        sections = PlanSection.objects.filter(period_start__isnull=True)
        total = sections.count()
        updated = 0

        self.stdout.write(f"Processing {total} sections without period dates...")

        for section in sections.iterator():
            agg = section.targets.aggregate(
                earliest=Min("created_at"), latest=Max("updated_at"),
            )
            if agg["earliest"]:
                period_start = agg["earliest"].date()
                period_end = None
                # Set period_end only if ALL targets are completed or deactivated
                active_count = section.targets.filter(status="default").count()
                if active_count == 0 and section.targets.exists():
                    period_end = agg["latest"].date()

                if not dry_run:
                    PlanSection.objects.filter(pk=section.pk).update(
                        period_start=period_start, period_end=period_end,
                    )
                updated += 1

        prefix = "[DRY RUN] " if dry_run else ""
        self.stdout.write(self.style.SUCCESS(
            f"{prefix}Updated {updated}/{total} sections"
        ))
```

- [ ] **Step 3: Commit backfill command**

```bash
git add apps/plans/management/
git commit -m "feat: add backfill_fhir_metadata management command

Deterministic backfill for existing records: episode FK on ProgressNotes,
goal_source heuristic on PlanTargets, period dates on PlanSections.
Supports --dry-run for preview."
```

---

### Task 6: Create AI Inference Management Command

**Files:**
- Create: `apps/plans/management/commands/infer_fhir_metadata.py`

- [ ] **Step 1: Write AI inference command**

Create `apps/plans/management/commands/infer_fhir_metadata.py`:

```python
"""AI-powered FHIR metadata inference for PlanTargets.

Uses the existing OpenRouter integration (konote/ai.py pattern) to classify:
- goal_source (when heuristic was inconclusive)
- continuous (maintenance vs. time-bound)
- target_date (extract temporal language from descriptions)

PII safety: Only goal name/description text is sent to LLM.
Never client names, identifiers, or note content.
"""
import json
import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

logger = logging.getLogger(__name__)

# System prompt for goal metadata classification
GOAL_METADATA_PROMPT = """You are a metadata classifier for a nonprofit outcome tracking system.
You will receive a goal name and description. Classify the following:

1. "continuous": Is this an ongoing maintenance goal (true) or a time-bound achievement goal (false)?
   - Ongoing examples: "maintain sobriety", "continue attending school", "stay housed"
   - Time-bound examples: "find housing", "complete GED", "get a job"

2. "target_months": If the description contains temporal language, extract the number of months.
   - "within 6 months" → 6
   - "by the end of the year" → estimate months from now
   - No temporal language → null

Return JSON only: {"continuous": true/false, "target_months": number|null}"""


class Command(BaseCommand):
    help = "AI-powered FHIR metadata inference for PlanTargets"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--batch-size", type=int, default=50)
        parser.add_argument(
            "--fields", nargs="+", default=["continuous", "target_date"],
            help="Which fields to infer (continuous, target_date)",
        )

    def handle(self, *args, **options):
        from apps.plans.models import PlanTarget
        from apps.admin_settings.models import AdminSettings

        dry_run = options["dry_run"]
        batch_size = options["batch_size"]
        fields = options["fields"]

        # Check if AI is available
        try:
            settings_obj = AdminSettings.objects.first()
            if not settings_obj:
                self.stdout.write(self.style.WARNING("No AdminSettings found — cannot run AI inference"))
                return
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Cannot check AI settings: {e}"))
            return

        # Find targets needing classification
        targets = PlanTarget.objects.exclude(
            _name_encrypted=b"",
        ).filter(
            status__in=["default", "on_hold"],
        )

        if "continuous" in fields:
            # Only targets where continuous hasn't been AI-classified yet
            needs_continuous = targets.exclude(
                metadata_sources__has_key="continuous",
            )
            self._infer_batch(needs_continuous, batch_size, dry_run, "continuous")

        if "target_date" in fields:
            needs_target = targets.filter(
                target_date__isnull=True,
            ).exclude(
                metadata_sources__has_key="target_date",
            )
            self._infer_batch(needs_target, batch_size, dry_run, "target_date")

    def _infer_batch(self, queryset, batch_size, dry_run, field_name):
        """Process a batch of targets for a specific field."""
        from konote.ai import _extract_json_payload

        total = queryset.count()
        if total == 0:
            self.stdout.write(f"No targets need {field_name} inference")
            return

        self.stdout.write(f"Processing {min(batch_size, total)}/{total} targets for {field_name}...")
        processed = 0

        for target in queryset[:batch_size]:
            try:
                # Decrypt goal text (in memory only — never sent as PII)
                goal_name = target.name or ""
                goal_desc = target.description or ""
                if not goal_name:
                    continue

                prompt_text = f"Goal: {goal_name}\nDescription: {goal_desc}"

                # Call LLM via existing pattern
                result = self._call_llm(GOAL_METADATA_PROMPT, prompt_text)
                if not result:
                    continue

                parsed = _extract_json_payload(result)
                if not parsed:
                    continue

                meta = target.metadata_sources or {}

                if field_name == "continuous" and "continuous" in parsed:
                    if not dry_run:
                        target.continuous = bool(parsed["continuous"])
                        meta["continuous"] = "ai_inferred"
                        target.metadata_sources = meta
                        target.save(update_fields=["continuous", "metadata_sources"])

                if field_name == "target_date" and parsed.get("target_months"):
                    months = int(parsed["target_months"])
                    new_date = (target.created_at + timedelta(days=months * 30)).date()
                    if not dry_run:
                        target.target_date = new_date
                        meta["target_date"] = "ai_inferred"
                        target.metadata_sources = meta
                        target.save(update_fields=["target_date", "metadata_sources"])

                processed += 1

            except Exception as e:
                logger.warning(f"Failed to infer {field_name} for PlanTarget {target.pk}: {e}")
                continue

        prefix = "[DRY RUN] " if dry_run else ""
        self.stdout.write(self.style.SUCCESS(
            f"{prefix}Processed {processed} targets for {field_name}"
        ))

    def _call_llm(self, system_prompt, user_message):
        """Call LLM via OpenRouter (matches konote/ai.py pattern)."""
        import requests
        from django.conf import settings as django_settings

        api_key = getattr(django_settings, "OPENROUTER_API_KEY", "")
        if not api_key:
            return None

        try:
            resp = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "anthropic/claude-sonnet-4",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    "max_tokens": 200,
                    "temperature": 0.0,
                },
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning(f"LLM call failed: {e}")
            return None
```

- [ ] **Step 2: Commit AI inference command**

```bash
git add apps/plans/management/commands/infer_fhir_metadata.py
git commit -m "feat: add infer_fhir_metadata management command

AI-powered classification of continuous (maintenance vs time-bound) and
target_date (temporal language extraction) on PlanTargets. Uses OpenRouter
via existing konote/ai.py pattern. PII-safe — only goal text sent to LLM."
```

---

### Task 7: Update Translations

**Files:**
- Modify: `locale/fr/LC_MESSAGES/django.po`

- [ ] **Step 1: Run translate_strings to extract new translatable strings**

On VPS:
```bash
ssh konote-vps "docker compose -f /opt/konote-dev/docker-compose.yml exec web python manage.py translate_strings"
```

- [ ] **Step 2: Fill French translations for new strings**

New strings to translate:
- "Participant-initiated" → "Initié par le participant"
- "Worker-initiated" → "Initié par l'intervenant"
- "Jointly developed" → "Développé conjointement"
- "Funder-required" → "Exigé par le bailleur de fonds"
- "On Hold" → "En attente"
- "Auto-linked service episode for this encounter." → "Épisode de service lié automatiquement pour cette rencontre."
- "Who established this goal. Auto-classified from content." → "Qui a établi cet objectif. Classifié automatiquement à partir du contenu."
- "Target completion date..." → "Date cible de réalisation..."
- "Ongoing maintenance goal vs. time-bound achievement goal." → "Objectif de maintien continu vs. objectif de réalisation à durée limitée."
- "Tracks how each auto-populated field was derived." → "Indique comment chaque champ rempli automatiquement a été dérivé."
- "When this plan section became active..." → "Quand cette section du plan est devenue active..."
- "When this plan section concluded..." → "Quand cette section du plan s'est terminée..."
- "Default target date offset (days)..." → "Décalage par défaut de la date cible (jours)..."

- [ ] **Step 3: Recompile and commit translations**

```bash
ssh konote-vps "docker compose -f /opt/konote-dev/docker-compose.yml exec web python manage.py translate_strings"
git add locale/
git commit -m "chore: add French translations for FHIR metadata fields"
```

---

### Task 8: Update Documentation

**Files:**
- Modify: `tasks/fhir-informed-data-modelling.md`
- Modify: `tasks/design-rationale/fhir-informed-modelling.md`

- [ ] **Step 1: Add new section to implementation plan**

Add after Phase F3 in `tasks/fhir-informed-data-modelling.md`:

```markdown
### Phase F3.5: FHIR Metadata Enrichment (auto-populated, zero worker burden)

**Added:** 2026-03-16
**Status:** Implementation ready
**Expert panel:** 5 experts, 3 rounds (Health Informatics Specialist, Nonprofit Evaluation Specialist, AI/NLP Engineer, Product Designer, Data Architect) — consensus: AI-inferred metadata is more accurate than human-coded; zero additional form fields.

**Principle:** "Never add a dropdown, always add an inference."

#### New fields (all auto-populated):

| Model | Field | FHIR Source | How Populated |
|---|---|---|---|
| ProgressNote | episode FK | Encounter.episodeOfCare | Deterministic lookup on save |
| PlanTarget | goal_source | Goal.source | Heuristic from field patterns + AI |
| PlanTarget | target_date | Goal.target.due | Program default + AI extraction |
| PlanTarget | continuous | Goal.continuous | AI classification |
| PlanTarget | metadata_sources | — | Tracks auto-population source |
| PlanTarget | on_hold status | Goal.lifecycleStatus | Worker action (pause goal) |
| PlanSection | period_start/end | CarePlan.period | Computed from target activity |
| Program | default_goal_review_days | — | Admin configuration |

#### Management commands:
- `backfill_fhir_metadata --all` — deterministic backfill (episode links, goal source heuristic, section periods)
- `infer_fhir_metadata` — AI-powered classification (continuous, target_date extraction)
```

- [ ] **Step 2: Update DRR graduated complexity path**

In `tasks/design-rationale/fhir-informed-modelling.md`, update Phase 1 to include the new fields.

- [ ] **Step 3: Commit documentation**

```bash
git add tasks/
git commit -m "docs: update FHIR implementation plan with metadata enrichment phase"
```

---

## FHIR Data Dictionary Reference

This table documents every FHIR concept adopted by KoNote and where it lives:

| FHIR Resource | FHIR Field | KoNote Model | KoNote Field | Status |
|---|---|---|---|---|
| EpisodeOfCare | status | ServiceEpisode | status | Complete (F1) |
| EpisodeOfCare | statusHistory | ServiceEpisodeStatusChange | — | Complete (F1) |
| EpisodeOfCare | period | ServiceEpisode | started_at / ended_at | Complete (F1) |
| EpisodeOfCare | type | ServiceEpisode | episode_type | Complete (F1) |
| EpisodeOfCare | careManager | ServiceEpisode | primary_worker | Complete (F1) |
| EpisodeOfCare | referralRequest | ServiceEpisode | referral_source | Complete (F1) |
| Goal | lifecycleStatus | PlanTarget | status | Extended (+ on_hold) |
| Goal | achievementStatus | PlanTarget | achievement_status | Complete (F2) |
| Goal | source | PlanTarget | goal_source | **New — this plan** |
| Goal | target.due | PlanTarget | target_date | **New — this plan** |
| Goal | continuous | PlanTarget | continuous | **New — this plan** |
| Goal | description | PlanTarget | name + description | Complete |
| Encounter | episodeOfCare | ProgressNote | episode FK | **New — this plan** |
| Encounter | participant.type | ProgressNote | author_role | Complete (F3) |
| Encounter | class | ProgressNote | modality | Mapped |
| Encounter | type | ProgressNote | interaction_type | Mapped |
| Encounter | length | ProgressNote | duration_minutes | Complete |
| Encounter | actualPeriod | ProgressNote | begin_timestamp + duration | Complete |
| CarePlan | period | PlanSection | period_start / period_end | **New — this plan** |
| CarePlan | title | PlanSection | name | Complete |
| CarePlan | goal | PlanSection → PlanTargets | — | Complete (FK) |
| CarePlan | status | PlanSection | status | Complete |

## Reporting Queries Unlocked

After this implementation, these previously-impossible queries become trivial:

```python
# Service hours per episode
ProgressNote.objects.filter(episode=ep).aggregate(Sum("duration_minutes"))

# Contacts per episode
ProgressNote.objects.filter(episode=ep).count()

# Were goals participant-driven?
PlanTarget.objects.filter(goal_source="participant").count()

# Goals achieved on time
PlanTarget.objects.filter(
    achievement_status__in=["achieved", "sustaining"],
    first_achieved_at__lte=F("target_date"),
)

# Time to achievement
PlanTarget.objects.filter(
    first_achieved_at__isnull=False,
).annotate(
    days_to_achieve=F("first_achieved_at") - F("created_at"),
)

# Goal source distribution for funder report
PlanTarget.objects.filter(
    plan_section__program=program,
).values("goal_source").annotate(count=Count("id"))
```
