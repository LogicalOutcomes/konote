---
drr: accessibility-requirements
status: Draft - awaiting GK review
parent_principle: collaborative-practice
blast_radius: high
source: foundation-collaborative-practice.md §9 (2026-03-14)
enforcement:
  - type: pytest
    file: tests/test_a11y_ci.py
    status: implemented
    description: "axe-core smoke tests over the login page, dashboard, participant list, admin feature settings, outcome insights, and portal dashboard/journal/goals; fail on any critical or serious violation"
  - type: pytest
    file: tests/test_accessibility_templates.py
    status: implemented
    description: "Assert key templates (500, offline, base) emit lang attribute matching the active language and include skip-to-main-content link; confirm offline fallback page has language detection and skip link"
  - type: pytest
    file: tests/test_blocker_a11y.py
    status: implemented
    description: "Assert no a11y regressions on pages flagged during launch readiness review"
  - type: semgrep
    rule: no-image-without-alt
    description: "In **/templates/**/*.html, forbid <img ...> tags that lack an alt attribute (including empty alt='' for decorative images — empty alt is explicit, missing alt is forbidden)"
  - type: semgrep
    rule: no-button-without-accessible-text
    description: "In **/templates/**/*.html, forbid <button>...</button> with no inner text AND no aria-label / aria-labelledby; same for <a> elements that act as buttons (role='button' or hx-* attributes) with no accessible name"
  - type: codeowner
    paths: ["**/templates/base*.html", "**/templates/**/_form_field.html", tests/test_a11y_ci.py, tests/test_accessibility_templates.py]
---

# DRR: Accessibility Requirements (WCAG 2.2 AA, AODA)

**Parent Principle:** [Collaborative Practice](../principles/collaborative-practice.md)

## Core Decision

KoNote targets **WCAG 2.2 Level AA** on every staff and participant interface. This is both:

- **A legal obligation** under the Accessibility for Ontarians with Disabilities Act (AODA) — public-sector and large private-sector organisations in Ontario must meet WCAG 2.0 AA; agencies contracting with the province or federal government typically require 2.1 or 2.2 AA.
- **An expression of the "Ko" in collaborative practice.** A participant who cannot use the portal (screen reader, keyboard-only, cognitive-load, colour-blindness, motor-impairment) is excluded from the collaboration the system is meant to enable. The principle doc puts it this way: *"If the portal is inaccessible, that participant is excluded from the 'Ko' in KoNote."*

Accessibility is **a constraint on every template and component from the start**, not a polish task applied after launch.

### What "WCAG 2.2 AA" means concretely in this codebase

- **Semantic HTML first.** Use real `<button>`, `<nav>`, `<main>`, `<label for="…">`. Avoid `<div role="button">` unless there is no semantic alternative.
- **Keyboard-reachable.** Every interactive element is focusable and operable without a mouse. Skip-to-main-content link on every page.
- **Screen-reader friendly.** Every image has an `alt` attribute (`alt=""` for purely decorative; a description for informative). Every form field has an associated `<label>`. Icon-only buttons carry `aria-label`. Live-region updates (HTMX partials) use `aria-live` where status matters.
- **Colour contrast.** Text meets 4.5:1 against its background; large text and UI components meet 3:1. Colour is never the sole signal (an error is red *and* carries an icon *and* has a textual message).
- **Language tag.** Every rendered page emits `<html lang="…">` matching the active Django language, so screen readers switch pronunciation between EN and FR.
- **Predictable focus order** and visible focus outlines. Do not `outline: none` without a replacement style.

## Anti-patterns

| Anti-pattern | Why it is rejected |
|---|---|
| `<img>` without `alt=` | Screen readers announce the filename instead; a missing `alt` is not the same as a decorative `alt=""` |
| `<button>` or button-like `<a>` with no visible text AND no `aria-label` | Nameless control; AODA violation and unusable with assistive tech |
| `<div role="button">` used instead of `<button>` | Requires manual focus and keyboard handlers that are easy to omit; the native element is already correct |
| Colour as the sole signal for errors or required fields | Fails WCAG 1.4.1 Use of Color; inaccessible to colour-blind users |
| "We'll do accessibility in a later sprint" | Retrofitting is 10× the cost and usually fails; prevention is cheaper than remediation |
| `outline: none` without a visible replacement focus style | Removes the only indicator keyboard users have of their position |
| Hardcoded `<html lang="en">` in templates that render under both languages | Screen readers mispronounce the opposite language |

## CI enforcement (detail)

1. **Pytest** `tests/test_a11y_ci.py` runs axe-core against the smoke-test pages listed in `SMOKE_PAGES` / `PORTAL_PAGES` (login, dashboard, participant list, admin settings, outcome insights, portal dashboard / journal / goals) under Playwright. The test fails on any violation with impact `critical` or `serious`; `moderate` and `minor` are reported but do not block.
2. **Pytest** `tests/test_accessibility_templates.py` renders the `500.html`, `offline.html`, and other standalone templates under both EN and FR and asserts the `<html lang>` attribute switches and the skip-to-main-content link is present.
3. **Pytest** `tests/test_blocker_a11y.py` holds specific regression guards added during launch-readiness review.
4. **Semgrep rule** `no-image-without-alt` scans every file in `**/templates/**/*.html` and fails the commit on any `<img …>` tag that lacks an `alt=` attribute. An empty alt (`alt=""`) is explicitly allowed for decorative images — the rule forbids *missing*, not *empty*.
5. **Semgrep rule** `no-button-without-accessible-text` scans templates for `<button></button>` with no text content and no `aria-label` / `aria-labelledby`, and for `<a>` elements acting as buttons (role="button" or HTMX trigger attributes) without an accessible name.
6. **CODEOWNERS** — base templates, the shared `_form_field.html` include, and the accessibility test files require DRR-steward review before modification.

## Relation to existing DRRs

- [executive-dashboard-redesign](executive-dashboard-redesign.md) — the dashboard redesign applied accessibility review to one specific surface. This DRR generalises that practice to every surface.
- [bilingual-requirements](bilingual-requirements.md) — the language-tag rule here is the accessibility side of that DRR's translation requirement.

## When to revisit

WCAG 2.2 AA is the current baseline. If WCAG 2.3 or a successor standard is adopted provincially or federally, bump the requirement and re-baseline the axe-core ruleset. The principle — accessibility is a constraint on every surface, not a post-launch checklist — should not change.

## Related DRRs

- [executive-dashboard-redesign](executive-dashboard-redesign.md) — specific dashboard accessibility work
- [bilingual-requirements](bilingual-requirements.md) — complementary: language tagging supports both translation and assistive tech
