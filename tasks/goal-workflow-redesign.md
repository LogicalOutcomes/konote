# Goal Workflow Redesign — Assisted Target & Metric Definition

**Created:** 2026-03-06
**Expert panel:** UX Designer, Interaction Designer, Service Design Consultant, Frontend Architect, Evaluation Methodologist
**DRR:** None yet (create after implementation if warranted)

## Problem Statement

The assisted goal creation workflow is KoNote's central workflow. Current pain points:

1. **Section name blocker** — After accepting a good AI suggestion, the user is dumped onto a form that demands a section name. For new participants with no plan, the only option is "+ Create new section" which requires typing a name. This is a complete blocker.
2. **Unclear button** — "Shape this target" uses jargon ("target") when the page says "Add a Goal." No icon signals it's AI-powered.
3. **Too much friction** — The "Use this suggestion" path tries to auto-submit a hidden form. When validation fails (section name), the user sees a form they didn't expect with a field they don't understand.
4. **Cognitive overload** — The suggestion card shows 6 fields simultaneously. The custom metric is presented as a `<pre>` block requiring clinical evaluation during a time-pressured session.

## Recommendations by Phase

### Phase A — Fix the blockers (do first)

| ID | Recommendation | Files to change |
|----|---------------|----------------|
| R1 | Create dedicated `goal_create_from_suggestion` endpoint. "Use this suggestion" fires HTMX POST directly — no client-side form, no auto-submit. Server creates goal + section + metrics in one transaction. Returns `HX-Redirect` on success. | `apps/plans/views.py`, `apps/plans/urls.py`, `templates/plans/_ai_suggestion.html`, `templates/plans/goal_form.html` |
| R1a | Soft failure (validation error) returns pre-populated form with error banner. Hard failure returns error card with retry + manual fallback. | `apps/plans/views.py`, new template `_goal_save_error.html` |
| R1b | Suggestion card stays visible with "Saving..." loading state during save. Button shows `hx-disabled-elt`, card gets loading overlay. | `templates/plans/_ai_suggestion.html`, CSS |
| R2 | Auto-create sections using priority chain: (1) program templates if they exist, (2) match existing section on this participant, (3) match section name used by other participants in same program, (4) use AI's suggestion, (5) fall back to "General". Never ask user for section name on happy path. | `apps/plans/views.py` (`_create_goal` + new endpoint) |
| R3 | Rename button: "Shape this target" -> "Suggest a goal" with sparkle SVG icon. | `templates/plans/goal_form.html`, CSS, translations |

### Phase B — Suggestion card polish

| ID | Recommendation | Files to change |
|----|---------------|----------------|
| R4 | Demote "Suggested area" to secondary line at bottom of card (not a full dt/dd pair). | `templates/plans/_ai_suggestion.html` |
| R5 | Default custom metric to "included." Remove Include/Skip buttons from card. Show metric name in post-save success message with link to review scale details. | `templates/plans/_ai_suggestion.html`, `templates/plans/goal_form.html` (JS), `apps/plans/views.py` |
| R6 | Rename "Let me edit it" -> "Let me review first". | `templates/plans/_ai_suggestion.html`, translations |
| R7 | Hide `#entry-points` after suggestion card loads via `htmx:afterSwap`. "Start over" brings them back. | `templates/plans/goal_form.html` (JS) |
| R19 | Store validated suggestion in session (server-side). Pass only a reference token to the client. Save endpoint retrieves from session. Avoids JSON roundtrip and escaping issues. | `konote/ai_views.py`, new save endpoint, `templates/plans/_ai_suggestion.html` |
| T-5 | Animated loading bar with text rotation ("Working on a suggestion..." -> "Almost there..." after 4s). | CSS, `templates/plans/goal_form.html` |

### Phase C — Form improvements ("Let me review first" path)

| ID | Recommendation | Files to change |
|----|---------------|----------------|
| R8 | Reorder form fields: participant words (editable) -> goal name -> description (collapsible, pre-filled) -> metrics (show selected count, expandable) -> section (last, least important). | `templates/plans/goal_form.html`, `apps/plans/forms.py` (`field_order`) |
| R9 | Section picker: pre-select most recent for returning participants. For new participants, pre-fill AI suggestion (editable text, not dropdown with only "new"). Remove validation error for empty section — auto-create with default. | `apps/plans/forms.py`, `templates/plans/goal_form.html` |
| R10 | Add reassurance near submit: "You can revise this goal later as things become clearer." | `templates/plans/goal_form.html`, translations |
| T-4 | Unify AI/non-AI form HTML into single `<form>` with conditional display. Remove SYNC-comment duplication. AI path hides form initially; non-AI shows it. Entry points + suggestion card are the only AI-specific additions. | `templates/plans/goal_form.html` |

### Phase D — Entry point tuning

| ID | Recommendation | Files to change |
|----|---------------|----------------|
| R11 | Conditional layout: show quick pick first if `common_goals|length >= 3`, AI textarea first otherwise. | `templates/plans/goal_form.html`, `apps/plans/views.py` (context) |
| R12 | Increase textarea to `rows="3"` with CSS `min-height`. | `templates/plans/goal_form.html`, CSS |
| R13 | Move onboarding hint ("What is a goal?") from page top to contextual help icon/tooltip on the AI entry point. | `templates/plans/goal_form.html` |
| R21 | Persistent participant-words blockquote throughout flow — visible on suggestion card and form, anchoring caseworker to participant's voice. | `templates/plans/goal_form.html`, `templates/plans/_ai_suggestion.html` |
| R22 | Quick pick prompts for participant's words after card selection: "What did [name] say about this?" | `templates/plans/goal_form.html` (JS) |
| R23 | Relabel metric tiers: "Recommended for all participants" / "Commonly used for goals like this" / "Browse all metrics". | `templates/plans/goal_form.html`, translations |
| R24 | Add collapsible "Why this suggestion" section on card showing AI's metric selection reasoning. | `templates/plans/_ai_suggestion.html` |

### Phase E — Accessibility fixes

| ID | Recommendation | Files to change |
|----|---------------|----------------|
| R14 | Fix `aria-label` on suggestion card: "AI-suggested goal" (not "target"). | `templates/plans/_ai_suggestion.html` |
| R15 | Add `aria-label` to custom metric `<pre>` block (or replace with semantic HTML). | `templates/plans/_ai_suggestion.html` |
| R16 | Change `#form-announce` to `aria-live="assertive"` for error messages. | `templates/plans/goal_form.html` |
| R17 | Add "Saving your goal..." screen reader announcement on save submission. | `templates/plans/goal_form.html` |
| R18 | Add `hx-sync="this:abort"` to shape button to prevent double-submission. | `templates/plans/goal_form.html` |

### Phase F — Program setup (longer-term)

| ID | Recommendation | Files to change |
|----|---------------|----------------|
| R20 | Pre-seed programs with domain section templates (housing, employment, health, social, etc.) at program setup. New participants get sections from template. Admin UI to manage. | `apps/programs/models.py`, `apps/programs/admin_views.py`, `apps/plans/views.py`, admin templates |

## Implementation Dependencies

```
R1 ──> R1a (error handling)
R1 ──> R1b (loading state)
R1 ──> R2 (section auto-create in save endpoint)
R1 ──> R5 (custom metric default in save endpoint)
R1 ──> R17 (SR announcement on save)
R1 ──> R19 (session storage for suggestion)
R2 ──> R9 (section picker improvements depend on auto-create logic)
```

All other recommendations are independent of each other.

## Section Auto-Create Priority Chain (R2 detail)

When saving from the AI suggestion and no section is explicitly chosen:

1. If the program has template sections (R20, when implemented), use those
2. If the AI's `suggested_section` matches an existing section on THIS participant (case-insensitive), use it
3. If the AI's `suggested_section` matches a section used by OTHER participants in the same program (case-insensitive), use that name — creates organic consistency
4. If none of the above, create a new section with the AI's suggested name
5. Last resort (no AI suggestion, no program): use "General"

Query for step 3:
```python
PlanSection.objects.filter(program=program).values_list('name', flat=True).distinct()
```

## Server-Side Suggestion Storage (R19 detail)

```python
# In suggest_target_view, after validation:
suggestion_key = f"goal_suggestion_{client_id}_{uuid4().hex[:8]}"
request.session[suggestion_key] = result
# Pass suggestion_key to template as data attribute

# In goal_create_from_suggestion:
suggestion = request.session.pop(suggestion_key, None)
if not suggestion:
    return render(request, "plans/_goal_save_error.html", {
        "error": "Suggestion expired. Please try again.",
        "client": client,
    })
```

## Success Message (R5 detail)

After saving with a custom metric included:
```
"Goal added: 'Find stable housing' with metric 'Housing Stability Scale.' View scale details."
```
The "View scale details" links to the plan view where the metric definition is expandable.

## Test Coverage Needed

- `test_goal_create_from_suggestion_happy_path` — POST with valid suggestion key, verify goal + section + metrics created
- `test_goal_create_from_suggestion_expired_key` — POST with invalid/expired key, verify error partial returned
- `test_goal_create_from_suggestion_auto_section` — verify section priority chain (match existing, match program, AI name, "General")
- `test_goal_create_from_suggestion_custom_metric_included` — verify custom metric created when present
- `test_goal_create_from_suggestion_csrf` — verify CSRF protection on new endpoint
- `test_goal_create_form_reorder` — verify field order in rendered form
- Existing tests in `test_plans.py` should still pass (form path unchanged)
