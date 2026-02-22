# Executive Dashboard Redesign — Expert Panel Recommendations

**Date:** 2026-02-21
**Status:** Proposed — not yet implemented
**Page:** `/clients/executive/` (`templates/clients/executive_dashboard.html`)

## Panel Members
- Nonprofit Dashboard UX Specialist
- Pico CSS / Server-Rendered Frontend Engineer
- Assistive Technology Tester
- Data Visualisation Designer

## Proposed Changes

### 1. Stats Grid — Keep CSS Grid, fix sizing
```css
.exec-stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(min(100%, 220px), 1fr));
    gap: var(--kn-space-base, 1rem);
}
```
Use `auto-fill` (not `auto-fit`) to prevent orphan cards from stretching.

### 2. Stat Card Markup — No `<dl>`, no `aria-label` on containers
```html
<article class="exec-stat-card">
    <div class="exec-stat-value" aria-hidden="true">42</div>
    <div class="exec-stat-label">Without Notes This Month</div>
    <span class="sr-only">: 42.</span>
    <div class="exec-stat-flag">Needs attention</div>
</article>
```
- Don't use `<dl>` — Pico applies unwanted margins to `<dd>`
- Don't use `aria-label` on `<article>` — swallows interactive children (e.g., "View by program" link in Safety Alerts card)
- Don't use `role="status"` on static flags — causes burst of live-region announcements on page load

### 3. Merge Filters Into Single Form
Use Pico's `fieldset[role="group"]` for horizontal layout:
```html
<form method="get" class="exec-filter-bar">
    <fieldset role="group">
        <select name="program" aria-label="Program">...</select>
        <input type="date" name="start_date" aria-label="Show data from">
        <button type="submit" class="outline">Update</button>
    </fieldset>
</form>
```
Add fiscal quarter presets (executives think in quarters).

### 4. Program Cards — Collapsible Sections
Replace 12 flat metric rows with `<details>` sections:
- **Always visible:** Status chip + "23 active · 5 new · 4 notes this week"
- **Collapsible:** Engagement & Outcomes, Activity & Pipeline, Themes
- Sections with alert conditions open by default: `<details {% if stat.engagement_quality < 70 %}open{% endif %}>`

### 5. Status Chips Per Program
Threshold-based labels instead of composite health score:
| Chip | Condition |
|------|-----------|
| On Track | Engagement >= 70% AND Goal Completion >= 50% |
| Needs Attention | Either metric below threshold |
| New Program | Active < 5 |

**GK must review thresholds before implementation.**

### 6. Action Bar — Top of Page, Two Buttons
- "Download summary (CSV)" — existing export, instant
- "Generate detailed report" — links to export form with context pre-filled

### 7. Remove Highlight Rows
Drop the `.highlight` negative-margin rows entirely. The `<details>` sections provide hierarchy instead.

### 8. Remove `<hr>` Separators
Replace with `<details>` section boundaries. Screen readers announce "separator" for each `<hr>`, creating noise.

### 9. All CSS in main.css
Namespace with `exec-` prefix. No inline `<style>` blocks in the template.
