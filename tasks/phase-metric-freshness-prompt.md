# Phase: Metric Freshness & Alliance Improvements

## Goal

Implement four related features that keep outcome measurement meaningful over time by preventing habituation, enforcing cadence, and prompting periodic review. These are currently in the Parking Lot (Needs Review) and have been approved for implementation.

## Tasks (in dependency order)

### Task 1: METRIC-CADENCE1 — Metric Cadence System

**What:** Not every metric should be recorded at every session. Add a configurable cadence so the note form only prompts for a metric when it's due.

**Model changes (`apps/plans/models.py`):**

Add to `MetricDefinition`:
- `cadence_sessions` — PositiveSmallIntegerField, nullable, default=null (null = every session, i.e. current behaviour)
  - Example values: 1 (every session), 3 (every 3rd session), null (every session)

**View changes (`apps/notes/views.py`):**

In `_build_target_forms()` (around line 179):
- For each metric linked to a target via `PlanTargetMetric`, check whether it's due:
  1. Count how many `ProgressNote` records exist for this client since the metric was last recorded (query `MetricValue` for this metric_def + client, order by `-created_at`, get the latest)
  2. If `cadence_sessions` is null or the count >= `cadence_sessions`, include the metric form
  3. If not due, skip it (don't render the form)
- Add a small "Next due in X sessions" badge on skipped metrics so staff understand why it's missing

**Admin changes:**
- Add `cadence_sessions` to the MetricDefinition admin form (already in `/admin/` metric library page)
- Help text: "How often to prompt for this metric. Leave blank to prompt every session. Enter 3 to prompt every 3rd session."

**Template changes (`templates/notes/note_form.html`):**
- In the metric entry area of target cards, show a muted line for skipped metrics: "Goal Progress — next due in 2 sessions" (not a form field, just info text)

**Tests (`tests/test_notes.py`):**
- Test: metric with `cadence_sessions=3` appears on 1st note, skipped on 2nd and 3rd, appears on 4th
- Test: metric with `cadence_sessions=null` appears every time (backward compat)
- Test: skipping doesn't affect achievement status computation

**Migration:** One new field on MetricDefinition.

---

### Task 2: METRIC-REVIEW1 — 90-Day Metric Relevance Check

**What:** After 90 days of tracking a metric on a plan target, prompt the worker to confirm it's still the right metric or swap it out.

**Model changes (`apps/plans/models.py`):**

Add to `PlanTargetMetric`:
- `assigned_date` — DateField, auto_now_add=True (when was this metric linked to this target?)
- `last_reviewed_date` — DateField, nullable (when did the worker last confirm this metric is still relevant?)

**View changes (`apps/notes/views.py`):**

In `_build_target_forms()`:
- For each `PlanTargetMetric`, check if `last_reviewed_date` is null or older than 90 days from today
- If review is due, annotate the metric form with `review_due=True`

**Template changes (`templates/notes/note_form.html`):**
- When `review_due` is True, show a subtle banner above the metric input:
  > "This metric has been tracked for 90+ days. Is it still the right measure for this goal?"
  > [Still right] [Change metric]
- "Still right" = HTMX POST to update `last_reviewed_date` to today, dismiss banner
- "Change metric" = link to plan target edit page where they can swap metrics

**New endpoint (`apps/plans/views.py`):**
- `POST /plans/target-metric/<pk>/confirm-review/` — sets `last_reviewed_date = today`, returns HTMX partial that replaces the banner with a checkmark

**Tests (`tests/test_plans.py`):**
- Test: metric assigned 91 days ago with no review shows banner
- Test: metric assigned 91 days ago with review 10 days ago does NOT show banner
- Test: confirming review updates `last_reviewed_date`
- Test: newly assigned metric (< 90 days) does not show banner

**Migration:** Two new fields on PlanTargetMetric.

---

### Task 3: ALLIANCE-ROTATE1 — Alliance Prompt Rotation

**What:** Cycle through 3-4 phrasings of the alliance rating question to prevent habituation. Currently the 5 rating labels are hardcoded in `ProgressNote.ALLIANCE_RATING_CHOICES`.

**Important design constraint:** The numeric scale (1-5) must stay constant for longitudinal comparison. Only the **prompt question** and **anchor labels** rotate. The stored value is always 1-5.

**Model changes (`apps/notes/models.py`):**

Add a constant defining rotation sets:

```python
ALLIANCE_PROMPT_SETS = [
    {
        "prompt": "How well are we working together?",
        "prompt_fr": "Dans quelle mesure travaillons-nous bien ensemble?",
        "anchors": {
            1: "I don't feel heard by my worker",
            2: "My worker and I aren't on the same page",
            3: "We're working okay together",
            4: "My worker gets what I need",
            5: "I really trust my worker",
        },
        "anchors_fr": {
            1: "Je ne me sens pas écouté(e) par mon intervenant(e)",
            2: "Mon intervenant(e) et moi ne sommes pas sur la même longueur d'onde",
            3: "Nous travaillons assez bien ensemble",
            4: "Mon intervenant(e) comprend ce dont j'ai besoin",
            5: "Je fais vraiment confiance à mon intervenant(e)",
        },
    },
    {
        "prompt": "Do you feel understood in our sessions?",
        "prompt_fr": "Vous sentez-vous compris(e) lors de nos rencontres?",
        "anchors": {
            1: "Not at all understood",
            2: "Somewhat misunderstood",
            3: "Mostly understood",
            4: "Well understood",
            5: "Completely understood",
        },
        "anchors_fr": {
            1: "Pas du tout compris(e)",
            2: "Un peu incompris(e)",
            3: "Plutôt compris(e)",
            4: "Bien compris(e)",
            5: "Tout à fait compris(e)",
        },
    },
    {
        "prompt": "Is our work together heading in the right direction?",
        "prompt_fr": "Notre travail ensemble va-t-il dans la bonne direction?",
        "anchors": {
            1: "Completely off track",
            2: "Mostly off track",
            3: "On the right track",
            4: "Making good progress",
            5: "Exactly where I need to be",
        },
        "anchors_fr": {
            1: "Complètement hors piste",
            2: "Plutôt hors piste",
            3: "Sur la bonne voie",
            4: "En bonne progression",
            5: "Exactement là où je dois être",
        },
    },
]
```

Add to `ProgressNote`:
- `alliance_prompt_index` — PositiveSmallIntegerField, nullable (which prompt set was shown)

**View changes (`apps/notes/views.py`):**

In `note_create()`:
- Query the client's last `ProgressNote` that has an `alliance_prompt_index`
- Pick the next index in rotation: `(last_index + 1) % len(ALLIANCE_PROMPT_SETS)`
- If no previous note, start at index 0
- Pass `prompt_set` to the template context
- On save, store `alliance_prompt_index` on the note

**Template changes (`templates/notes/note_form.html`):**
- Replace the hardcoded alliance fieldset legend with `{{ alliance_prompt }}`
- Replace the hardcoded radio labels with `{{ alliance_anchors.1 }}` through `{{ alliance_anchors.5 }}`
- Keep the help text and "Skip today" option unchanged

**Tests (`tests/test_notes.py`):**
- Test: first note for client uses prompt set 0
- Test: second note uses prompt set 1, third uses 2, fourth wraps to 0
- Test: stored `alliance_prompt_index` matches what was shown
- Test: French language context uses `anchors_fr`

**Migration:** One new field on ProgressNote.

---

### Task 4: PORTAL-ALLIANCE1 — Portal-Based Async Alliance Rating

**What:** After a session, send the participant a notification (via the portal) asking them to self-rate the alliance. This decouples the rating from the in-person session so participants feel freer to be honest.

**Prerequisite check:** Verify the portal app exists and has notification/messaging capability. Look at `apps/portal/` for existing infrastructure.

**Model changes (`apps/notes/models.py`):**

Add:
- `PortalAllianceRequest` — new model:
  - `progress_note` → ProgressNote (one-to-one)
  - `client_file` → ClientFile
  - `prompt_index` — which alliance prompt set to show
  - `status` — "pending", "completed", "expired"
  - `created_at` — DateTimeField
  - `completed_at` — DateTimeField, nullable
  - `rating` — PositiveSmallIntegerField (1-5), nullable
  - `expires_at` — DateTimeField (default: 7 days after created_at)

**View changes:**

New portal view (`apps/portal/views.py`):
- `GET /portal/alliance/<uuid>/` — shows the alliance rating form (uses the prompt set from `prompt_index`)
- `POST /portal/alliance/<uuid>/` — saves the rating, marks request as completed
- Expired requests show a friendly "This rating has expired" message

Worker-side (`apps/notes/views.py`):
- In `note_create()`, after saving the note, if the client has portal access and `alliance_rater` was not set (worker didn't record an in-person rating), create a `PortalAllianceRequest`
- Add a toggle in agency settings: "Enable portal alliance ratings" (off by default)

**Portal notification:**
- Use existing portal notification mechanism (check `apps/portal/` for how notifications work)
- Notification text: "Your worker recorded a session on [date]. How did you feel about working together?"

**Template (`templates/portal/alliance_rating.html`):**
- Clean, mobile-friendly page
- Shows the prompt question and 5 radio options (from `ALLIANCE_PROMPT_SETS[prompt_index]`)
- Submit button
- "Skip" option

**Dashboard integration:**
- On the progress note detail view, show whether a portal alliance request was sent and its status
- If completed, show the participant's self-rating alongside any worker-observed rating

**Tests:**
- Test: creating a note without in-person alliance rating creates a portal request
- Test: creating a note WITH in-person rating does NOT create a portal request
- Test: portal rating form renders correctly
- Test: submitting a rating updates the request status
- Test: expired requests show expiry message
- Test: portal ratings appear on note detail view

**Migration:** One new model.

---

## Implementation Order

Tasks 1-3 are independent and can be parallelised with sub-agents. Task 4 depends on understanding the portal app structure, so start it after a quick exploration of `apps/portal/`.

Suggested agent split:
- **Agent A:** METRIC-CADENCE1 (model + view + template + tests)
- **Agent B:** ALLIANCE-ROTATE1 (model + view + template + tests)
- **Agent C:** METRIC-REVIEW1 (model + view + template + tests)
- **Agent D:** PORTAL-ALLIANCE1 (exploration + model + view + template + tests) — start after A/B/C or in parallel if portal structure is clear

## Files You'll Touch

| File | Tasks |
|------|-------|
| `apps/plans/models.py` | CADENCE1, REVIEW1 |
| `apps/notes/models.py` | ROTATE1, PORTAL1 |
| `apps/notes/views.py` | CADENCE1, REVIEW1, ROTATE1, PORTAL1 |
| `apps/notes/forms.py` | CADENCE1, ROTATE1 |
| `apps/plans/views.py` | REVIEW1 |
| `apps/portal/views.py` | PORTAL1 |
| `templates/notes/note_form.html` | CADENCE1, REVIEW1, ROTATE1 |
| `templates/portal/alliance_rating.html` | PORTAL1 (new) |
| `tests/test_notes.py` | CADENCE1, ROTATE1, PORTAL1 |
| `tests/test_plans.py` | REVIEW1 |

## After Implementation

1. Run relevant tests: `pytest tests/test_notes.py tests/test_plans.py -v`
2. Run translations: `python manage.py translate_strings`
3. Fill any new French translations in `locale/fr/LC_MESSAGES/django.po`
4. Update TODO.md: move all four tasks to Recently Done
5. Check if `konote-qa-scenarios/pages/page-inventory.yaml` needs new entries (portal alliance page)
