# UX Fixes — Implementation Plan

**Created:** 2026-02-17

## All UX Issues (Consolidated)

### From "Phase: UX Fixes" in TODO.md (added today)

| ID | Summary | Effort | Files touched |
|---|---|---|---|
| UX-MSG1 | Leave Message button sizing | Small | `templates/communications/leave_message.html` |
| UX-MSG2 | Replace hardcoded "case worker" with `term.worker` | Small | `templates/communications/leave_message.html`, `_message_card.html`, `.po` |
| UX-DASH1 | Simplify Executive Overview intro text | Small | `templates/clients/executive_dashboard.html`, `.po` |
| UX-DASH2 | Fix "your Program Manager" + hardcoded "client" | Small | `templates/clients/executive_dashboard.html`, `.po` |
| UX-PROG1 | Fix "All Programs in this instance" jargon | Small | `templates/programs/list.html`, `.po` |
| UX-PROG2 | Add staff contact info to Program pages | Medium | `templates/programs/detail.html`, `apps/programs/views.py` |
| UX-INSIGHTS1 | Rewrite Outcome Insights intro | Small | `templates/reports/insights.html`, `.po` |
| UX-INSIGHT2 | BUG: suggestion count ≠ displayed count | Medium | `apps/reports/insights.py`, `insights_views.py`, `_insights_basic.html` |
| UX-INSIGHT3 | Plain-language chart descriptions | Small | `templates/reports/_insights_basic.html`, `.po` |
| UX-INSIGHT4 | AI interpretation below charts | Large | `_insights_basic.html`, `insights_views.py`, new AI call |
| UX-INSIGHT5 | Surface suggestions to executive dashboard | Large | `executive_dashboard.html`, `clients/views.py`, `reports/insights.py` |
| UX-INSIGHT6 | Suggestion tracking/consolidation system | XL | New model, views, forms, templates, migration |
| UX-SAFETY1 | Make "Leave Quickly" URL configurable | Medium | `portal/base_portal.html`, `portal.js`, `admin_settings/models.py`, `forms.py`, `instance_settings.html` |
| UX-ALERT1 | Rewrite Approvals page intro | Small | `templates/events/alert_recommendation_queue.html`, `.po` |
| UX-EXPORT1 | Export delay hardcoded message | Small | `templates/reports/export_form.html`, `reports/views.py` |
| UX-CAL1 | Rewrite calendar sync page | Medium | `templates/events/calendar_feed_settings.html`, `.po` |
| PORTAL-Q1 | "Questions for You" portal feature | XL | New models, views, templates — design only for now |

### From Parking Lot (UX-related)

| ID | Summary | Effort | Notes |
|---|---|---|---|
| UX17 | Bulk discharge/assignment operations | Large | New views, forms, templates in clients app |
| QA-W19 | Onboarding guidance for new users | Large | User model change, new templates, JS tour logic |
| SETUP1-UI | First-run setup wizard UI | Large | Related to QA-W19 — could combine |

### From Phase 8 — ALL COMPLETE

All Phase 8 UX items (UX1–UX12) were completed 2026-02-02/03. See `tasks/ARCHIVE.md` lines 390–415.

---

## Implementation Batches

Grouped to **avoid file conflicts** (no two items in a batch touch the same file) and ordered by impact.

### Batch 1 — Quick Text Rewrites (no code logic, just template text + translations)

All small effort, fully independent files. Can be done by parallel sub-agents.

| Agent | Tasks | Files |
|---|---|---|
| A | UX-DASH1, UX-DASH2 | `executive_dashboard.html` |
| B | UX-PROG1 | `programs/list.html` |
| C | UX-INSIGHTS1 | `reports/insights.html` |
| D | UX-ALERT1 | `events/alert_recommendation_queue.html` |
| E | UX-MSG1, UX-MSG2 | `communications/leave_message.html`, `_message_card.html` |

**After all agents finish:** One translation pass to update `django.po` for all changed strings.

**Estimated time:** ~30 minutes total.

### Batch 2 — Standalone Small Fixes (minor code + template)

Independent files, can run in parallel.

| Agent | Tasks | Files |
|---|---|---|
| A | UX-EXPORT1 | `reports/export_form.html`, `reports/views.py` |
| B | UX-CAL1 | `events/calendar_feed_settings.html` |
| C | UX9, UX11 | `home.html`, `app.js`, `base.html` |
| D | UX5 | `clients/views.py` (prefetch fix) |
| E | UX6 | `_note_detail.html` |
| F | UX7, UX10 | `_section.html`, `_target.html`, `export_form.html` |

**Conflict note:** Agent A and F both touch `export_form.html` — run them **sequentially** (A first, then F).

**After all agents finish:** Translation pass for any new strings.

### Batch 3 — Medium Features (some code changes)

| Order | Task | Files | Why sequential |
|---|---|---|---|
| 1 | UX-PROG2 | `programs/detail.html`, `programs/views.py` | Independent |
| 2 | UX-INSIGHT2 (bug fix) | `insights.py`, `insights_views.py`, `_insights_basic.html` | Must fix before adding descriptions |
| 3 | UX-INSIGHT3 | `_insights_basic.html` | Depends on INSIGHT2 being done |
| 4 | UX-SAFETY1 | `portal/base_portal.html`, `portal.js`, admin settings files | Independent |

**UX-PROG2 and UX-SAFETY1** can run in parallel — no shared files.
**UX-INSIGHT2 → UX-INSIGHT3** must be sequential — both edit `_insights_basic.html`.

### Batch 4 — Larger Features (new functionality)

Do one at a time, each in its own commit.

| Order | Task | Notes |
|---|---|---|
| 1 | UX-INSIGHT4 (AI chart interpretation) | Builds on Batch 3's chart descriptions; extends `_insights_basic.html` and `insights_views.py` |
| 2 | UX8 (admin nav dropdown) | Touches `base.html` — do alone to avoid conflicts with anything else using base |
| 3 | UX3 (note form target selection) | `note_form.html` + JS |
| 4 | UX4 (notes filtering/pagination) | `note_list.html`, `notes/views.py` |
| 5 | UX2 (HTMX client tabs) | Multiple new partial templates |
| 6 | UX12 (custom fields read-only) | Custom fields templates |

### Batch 5 — Major Features (defer or design-only)

These need design decisions before implementation. Recommend **parking** them until Batches 1–4 are done.

| Task | Status | Recommendation |
|---|---|---|
| UX-INSIGHT5 | Depends on INSIGHT2 fix + exec dashboard | Design after Batch 3, implement after Batch 4 |
| UX-INSIGHT6 | New data model needed | Design doc only — too large for this sprint |
| UX1 (staff dashboard) | New page | Design doc, then implement separately |
| UX17 (bulk operations) | New feature | Keep in parking lot |
| QA-W19 + SETUP1-UI | Onboarding/wizard | Combine into one design, keep in parking lot |
| PORTAL-Q1 | Major portal feature | Keep in parking lot — depends on SURVEY1 |

---

## Shared Resources — Conflict Avoidance Rules

These files are touched by many tasks. Only **one agent at a time** should edit them:

| File | Touched by | Rule |
|---|---|---|
| `locale/fr/LC_MESSAGES/django.po` | All text rewrites | Do one translation pass per batch, not per task |
| `static/css/main.css` | UX-MSG1, touch targets, etc. | Queue CSS changes, commit together |
| `static/js/app.js` | UX11, UX10, any new JS | One agent at a time |
| `templates/base.html` | UX8, UX11, QA-W19 | One agent at a time |

---

## Summary

| Batch | Tasks | Parallel? | Estimated scope |
|---|---|---|---|
| **1** | 7 text rewrites | Yes (5 agents) | Small — text only |
| **2** | 8 small fixes | Mostly (1 sequential pair) | Small–medium |
| **3** | 4 medium features | Partially | Medium |
| **4** | 6 larger features | Sequential | Medium–large each |
| **5** | 6 major features | Deferred | Design docs only |

**Total implementable now (Batches 1–4):** 25 tasks
**Deferred to design/parking (Batch 5):** 6 tasks
