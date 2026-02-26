# QA-PA-ERASURE1 — PIPEDA Compliance Context on Erasure Page

**Task ID:** QA-PA-ERASURE1
**Date:** 2026-02-24
**Status:** Design approved by GK (expert panel, 2 rounds)
**Parking Lot item:** TODO.md line 136

---

## What

Add plain-language explanatory text to the admin erasure approval page describing what happens at the selected erasure tier.

## Design Decisions (GK-approved)

1. **Show only the selected tier's consequences** — not a comparison table of all three tiers. The tier was already chosen at request time; at approval time the admin just needs to confirm what will happen.

2. **Plain language, Grade 8 reading level.** No PIPEDA citations in the UI. No legal jargon. Write for a PM who has never heard of PIPEDA and was trained in a 20-minute walkthrough.

3. **One sentence per tier** describing the practical effect:
   - **Tier 1 (Anonymise):** "Their name and contact details will be blanked. Anonymous service records stay in reports. This cannot be undone."
   - **Tier 2 (Purge):** "All individual information will be removed. Only anonymous counts remain in reports. This cannot be undone."
   - **Tier 3 (Full Delete):** "Everything about this person will be permanently deleted, including from reports. This cannot be undone."

4. **Audit trail survives all tiers** (separate database). This is the correct policy — the audit DB is the compliance trail.

5. **No external policy link.** The in-app text IS the operational policy until the agency creates its own. Don't send staff to a document that may not exist.

## Implementation

**Files:**
- `templates/clients/erasure/erasure_request_detail.html` — add a `<p>` or `<article>` element above the approval buttons showing the selected tier's consequence text
- Use `{% if er.tier == "anonymise" %}` / `{% elif %}` / `{% else %}` to show only the relevant sentence
- Wrap text in `{% trans %}` for French translation
- Run `translate_strings` and add French translations

**Effort:** Small (30 min)

**Tests:** None needed (static template text).

## Expert Panel Context

Two rounds of expert review (2026-02-24) stress-tested the original Round 1 recommendation (a 3-tier comparison table with 12 cells of information). Round 2 panel (Operations Director, Human Factors Specialist, Tech Debt Analyst, Regulatory Pragmatist) concluded:

- A comparison table presents 12 pieces of information at a high-stakes decision point. Research on cognitive load shows people process ~3 items reliably.
- The person clicking "Approve" didn't choose the tier — they're confirming a request someone else made. They need to understand what they're approving, not compare options.
- Progressive disclosure (show only what's relevant) is proven in high-consequence, low-training environments.

## Related Files

- `tasks/erasure-hardening.md` — Completed H1-H7 hardening (2026-02-06). ERASE-H8 (24-hour Tier 3 delay) is separate.
- `apps/clients/erasure_views.py` — `erasure_request_detail()` at line 179
- `templates/clients/erasure/erasure_request_detail.html` — target template
