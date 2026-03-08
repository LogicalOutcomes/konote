# Goal Workflow Redesign — Implementation Prompt

**Use this prompt in a fresh Claude Code session (close other sessions first).**
**Estimated: 2 sessions. Session 1 = Phases A+B+E. Session 2 = Phases C+D.**

Read `tasks/goal-workflow-redesign.md` for the full design rationale, dependency graph, and technical details.

---

## Session 1: Phases A + B + E (Blockers, Card Polish, Accessibility)

### Pre-flight

```
git pull origin develop
git worktree prune
git status
```

Create a feature branch: `feat/goal-workflow-redesign`

### Overview

The assisted goal creation workflow has critical UX problems. Read these files first to understand the current state:

- `templates/plans/goal_form.html` — main page (entry points, form, all JS)
- `templates/plans/_ai_suggestion.html` — HTMX partial for AI suggestion card
- `konote/ai_views.py` — `suggest_target_view()` (lines ~217-294)
- `apps/plans/views.py` — `goal_create()` and `_create_goal()`
- `apps/plans/forms.py` — `GoalForm` (lines ~284-381)
- `apps/plans/urls.py`
- `tasks/goal-workflow-redesign.md` — full design document

### Agent Plan — 3 parallel agents, then sequential integration

**IMPORTANT:** Phases A and B have dependencies (R1 must exist before R5, R19 can build on R1). Use this execution order:

#### Step 1: Launch 3 agents in parallel

**Agent 1: Backend — New save endpoint + section auto-create (R1, R1a, R2)**

Task: Create a new view `goal_create_from_suggestion` in `apps/plans/views.py` and wire it up in `apps/plans/urls.py`.

Requirements:
- URL: `participant/<int:client_id>/goals/save-suggestion/` named `plans:goal_save_suggestion`
- Accepts POST with `suggestion_key` (string) and `client_id`
- Retrieves validated suggestion from `request.session[suggestion_key]` using `session.pop()`
- If suggestion not found: return `render(request, "plans/_goal_save_error.html", {"error": "...", "client": client})`
- Permission checks: same as `goal_create` — `get_client_or_403`, `_can_edit_plan`
- Section resolution using priority chain (see design doc for detail):
  1. Match AI's `suggested_section` against existing sections on THIS participant (case-insensitive)
  2. Match against sections used by OTHER participants in the same program (case-insensitive) — use that name
  3. Create new section with AI's suggested name
  4. Fall back to "General" if no suggestion
- Create goal using existing `_create_goal()` helper
- Handle custom metric: if `custom_metric` present in suggestion, create `MetricDefinition` with `category="custom"`, `is_library=False`, `owning_program=program`
- On success: set `messages.success` with goal name and metric names (if custom metric: include name + link hint). Return `HttpResponse(status=204)` with `HX-Redirect` header to `plans:plan_view`
- On validation error: return rendered form (reuse `GoalForm` pre-populated from suggestion data) with error banner
- CSRF: the template will include a CSRF token via `hx-headers`
- Create template `templates/plans/_goal_save_error.html` — simple error card with retry button and "fill in manually" link

Also modify `konote/ai_views.py` `suggest_target_view()` (around line 276):
- After validating the AI response, store it in the session:
  ```python
  from uuid import uuid4
  suggestion_key = f"goal_suggestion_{client_id}_{uuid4().hex[:8]}"
  request.session[suggestion_key] = result
  ```
- Pass `suggestion_key` to the template context (alongside existing `suggestion_json` for the "Let me review" path)

Write tests in `tests/test_plans.py`:
- `test_goal_save_suggestion_happy_path`
- `test_goal_save_suggestion_expired_key`
- `test_goal_save_suggestion_auto_section_match_existing`
- `test_goal_save_suggestion_auto_section_match_program`
- `test_goal_save_suggestion_auto_section_fallback`
- `test_goal_save_suggestion_custom_metric`
- `test_goal_save_suggestion_permission_denied`

**Agent 2: Template — Suggestion card redesign (R3, R4, R5, R6, R7, R14, R15, R19-frontend, R1b, T-5)**

Task: Update `templates/plans/_ai_suggestion.html` and the relevant parts of `templates/plans/goal_form.html`.

Changes to `_ai_suggestion.html`:
- The "Use this suggestion" button becomes an HTMX POST button:
  ```html
  <button type="button"
          id="btn-use-suggestion"
          hx-post="{% url 'plans:goal_save_suggestion' client_id=client.pk %}"
          hx-include="[name=csrfmiddlewaretoken]"
          hx-target="#suggestion-container"
          hx-swap="innerHTML"
          hx-indicator="#save-loading"
          hx-disabled-elt="this"
          data-suggestion-key="{{ suggestion_key }}">
      {% trans "Use this suggestion" %}
  </button>
  ```
  Note: `suggestion_key` is passed via `hx-vals` or a hidden input. Include CSRF token.
  Add a hidden input: `<input type="hidden" name="suggestion_key" value="{{ suggestion_key }}">`
  Add a hidden CSRF token inside the card (since it's not in a form): `{% csrf_token %}`
- Add loading state element inside card: `<div id="save-loading" class="htmx-indicator"><small>Saving your goal...</small></div>`
- Keep `data-suggestion="{{ suggestion_json }}"` on `btn-edit-suggestion` (the "Let me review first" button still populates the form client-side)
- Rename "Let me edit it" to "Let me review first" (R6)
- Fix `aria-label`: "AI-suggested goal" not "AI-suggested target" (R14)
- Demote "Suggested area": move it from a `<dt>/<dd>` pair to a `<small class="secondary">` line at the bottom of the card, before the action buttons (R4)
- Custom metric (R5): Remove the "Include this metric" / "Skip" buttons. Instead, show metric name and a brief note: "This custom scale will be added to the goal." Add a small "Remove" link that sets a hidden field. Default `custom-metric-accepted` conceptually to true (the save endpoint includes it unless explicitly removed)
- Add `aria-label="Scale definition, 1 to 5"` on the custom metric `<pre>` block (R15)
- Add screen reader announcement div: `<div aria-live="assertive" class="sr-only" id="save-announce"></div>` (R17)

Changes to `templates/plans/goal_form.html`:
- Rename button text: "Shape this target" -> "Suggest a goal" (R3)
- Add sparkle SVG icon inline before the text (small, 16x16, use a simple path — no external dependency)
- Add `hx-sync="this:abort"` to the shape button (R18)
- In JS `htmx:afterSwap` handler: after suggestion card loads, hide `#entry-points` (R7). In "Start over" handler: show `#entry-points` again.
- In JS: Add handler for `htmx:beforeRequest` on save button to announce "Saving your goal..." to `#save-announce`
- Loading bar animation (T-5): Add CSS keyframe animation to `.loading-bar`. Add JS timeout that changes loading text after 4 seconds: "Working on a suggestion..." -> "Almost there..."
- Change `#form-announce` from `aria-live="polite"` to `aria-live="assertive"` (R16)

Update French translations: run `python manage.py translate_strings` after template changes, then fill new entries in `locale/fr/LC_MESSAGES/django.po`.

**Agent 3: Accessibility quick fixes (R16, R18 — if not already done by Agent 2)**

This agent is small — if Agent 2 covers R14-R18, this agent is not needed. Instead, use Agent 3 for:

Task: Write the CSS additions needed for all visual changes.

In `static/css/` (find the relevant stylesheet — likely `pico-overrides.css` or `app.css`):
- Sparkle icon styling: `.btn-sparkle-icon { width: 1em; height: 1em; vertical-align: -0.1em; margin-right: 0.3em; }`
- Loading bar animation: `@keyframes loading-pulse { 0%, 100% { opacity: 0.4; } 50% { opacity: 1; } }` applied to `.loading-bar`
- Save loading indicator styling
- Suggestion card: ensure `.suggestion-actions` buttons stack on mobile (`@media (max-width: 576px) { flex-direction: column; }`)
- Custom metric card styling (replace `<pre>` look with a cleaner scale card if feasible)
- `.ai-suggestion-card` loading overlay state

#### Step 2: Sequential integration

After all 3 agents complete:
1. Review all changes for consistency
2. Run `python manage.py translate_strings` and fill French translations
3. Run `pytest tests/test_plans.py -v` on VPS
4. Commit, push, create PR to develop, merge

---

## Session 2: Phases C + D (Form Improvements, Entry Point Tuning)

### Pre-flight

```
git pull origin develop
```

Create branch: `feat/goal-workflow-form-improvements`

### Agent Plan — 2 parallel agents

**Agent 1: Form restructuring (R8, R9, R10, T-4)**

Task: Restructure `templates/plans/goal_form.html` form section and `apps/plans/forms.py`.

R8 — Reorder form fields:
- In `GoalForm`, change `field_order` to: `["client_goal", "name", "description", "metrics", "section_choice", "new_section_name"]`
- In the template, reorder the fieldsets to match: participant words -> goal name -> description -> metrics -> section picker
- Wrap description in a `<details open>` when pre-filled by AI, `<details>` (collapsed) when empty

R9 — Section picker improvements:
- When rendering section choices, if sections exist, pre-select the most recently created one (add ordering in `GoalForm.__init__`)
- When the form is shown via "Let me review first" with AI data, if section_choice is "new" and AI suggested a name, show it as a pre-filled text input (not a dropdown with only "new")
- In `GoalForm.clean()`: if `section_choice == "new"` and `new_section_name` is blank, instead of raising an error, set `new_section_name` to "General" (or the program name if available). Remove the "You chose to create a new section" error.

R10 — Add reassurance text:
- Before the submit button div, add: `<p class="secondary"><small>{% trans "You can revise this goal later as things become clearer." %}</small></p>`

T-4 — Unify form HTML:
- Currently there are TWO form structures: one for AI-enabled (lines ~361-568) and one for non-AI (lines ~111-358 roughly). They have SYNC comments.
- Merge them into a SINGLE `<form>` element. The AI path hides it initially (`hidden` attribute, removed by JS). The non-AI path shows it immediately.
- The only AI-specific elements above the form are: entry points div, suggestion container. These are already outside the form.
- Remove the duplicated fieldsets. If the non-AI path has a "Phase 1 / Phase 2" concept, simplify it: Phase 1 is the entry points (same as AI path but without the AI button — just a textarea + "Next" that reveals the form).

**Agent 2: Entry point tuning (R11, R12, R13, R21, R22, R23, R24)**

Task: Update entry points and suggestion display in `templates/plans/goal_form.html` and `templates/plans/_ai_suggestion.html`.

R11 — Conditional layout:
- In `apps/plans/views.py` `goal_create()`, add `quick_pick_first = len(common_goals) >= 3` to context
- In template: `{% if quick_pick_first %}` show quick pick fieldset before AI fieldset, `{% else %}` show AI first (current order)

R12 — Textarea size:
- Change `rows="2"` to `rows="3"` on `#participant-words`
- Add CSS: `#participant-words { min-height: 4.5em; }`

R13 — Move onboarding hint:
- Remove the `<details class="onboarding-hint">` from the top of the page
- Add a help icon (info circle) next to the AI entry legend text with a tooltip containing the same content
- Use `title` attribute or a Pico CSS tooltip pattern

R21 — Persistent participant words:
- In the form (when revealed by "Let me review first"), show a blockquote at the top with the participant's words:
  ```html
  <blockquote id="participant-echo" class="participant-words-echo" hidden>
      <small class="secondary">{% trans "In their words:" %}</small>
      <em id="participant-echo-text"></em>
  </blockquote>
  ```
- In `revealForm()` JS: populate and show this blockquote from the `client_goal` field value
- Style it subtly — not a full blockquote, more like a small italic reference

R22 — Quick pick words prompt:
- After clicking a quick pick card, instead of immediately revealing the form, show a brief prompt:
  ```html
  <div id="quick-pick-words" hidden>
      <label>{% blocktrans with client=term.client %}What did {{ client }} say about this?{% endblocktrans %}</label>
      <textarea name="quick_pick_words" rows="2" placeholder="{% trans 'Optional — in their own words...' %}"></textarea>
      <button type="button" id="btn-continue-quick-pick">{% trans "Continue" %}</button>
  </div>
  ```
- "Continue" copies words to `client_goal` field and reveals the form
- Make the textarea optional (placeholder says "Optional") so it's not a blocker

R23 — Metric tier labels:
- Change "Recommended" -> "Recommended for all participants"
- Change "Used in this program" -> "Commonly used for goals like this"
- Change "All available metrics" -> "Browse all metrics"

R24 — "Why this suggestion":
- In `_ai_suggestion.html`, after the metrics list, add:
  ```html
  {% if suggestion.metrics %}
  <details class="why-suggestion">
      <summary><small>{% trans "Why these metrics?" %}</small></summary>
      <ul>
          {% for m in suggestion.metrics %}
          {% if m.reason %}<li><strong>{{ m.name }}:</strong> {{ m.reason }}</li>{% endif %}
          {% endfor %}
      </ul>
  </details>
  {% endif %}
  ```

After both agents complete:
1. Run translations
2. Test on VPS
3. Commit, push, PR, merge

---

## Checklist Before Declaring Done

- [ ] "Suggest a goal" button with sparkle icon works and calls AI
- [ ] "Use this suggestion" saves directly via HTMX POST — no form shown
- [ ] New participant with no sections: goal saves without section name prompt
- [ ] Returning participant: existing section matched correctly
- [ ] Custom metric included by default, visible in success message
- [ ] "Let me review first" shows pre-populated form with correct field order
- [ ] Section picker is last field in form, pre-filled, non-blocking
- [ ] Entry points hide after suggestion loads
- [ ] Loading states work (AI wait + save)
- [ ] Screen reader announcements present for key state changes
- [ ] French translations filled for all new strings
- [ ] All existing `test_plans.py` tests pass
- [ ] New tests for save endpoint pass
- [ ] Mobile: suggestion card and buttons render correctly at 375px width
