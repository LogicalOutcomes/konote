---
drr: customisable-terminology
status: Draft - awaiting GK review
parent_principle: collaborative-practice
blast_radius: medium
source: foundation-collaborative-practice.md §7 (2026-03-14)
enforcement:
  - type: semgrep
    rule: no-hardcoded-terminology-words
    description: "In **/templates/**/*.html, flag user-visible occurrences of client, clients, participant, participants, member, members, worker, counsellor, coach, plan, goal, pathway outside the terminology include / tag. An allowlist comment `{# terminology-exception: <reason> #}` on the preceding line suppresses a single false positive. Matches are case-insensitive and ignore occurrences inside {{ }} expressions and comments."
  - type: pytest
    file: tests/drr/test_terminology_substitution.py
    description: "Render a canonical set of templates (login, dashboard, participant list, note detail, goal detail, portal dashboard) under a non-default terminology configuration (e.g., term.client='member', term.worker='coach', term.plan='pathway'). Assert the default words ('client', 'participant', 'worker', 'plan', 'goal') do not appear in the rendered output except inside allowlisted fragments."
  - type: codeowner
    paths: [konote/middleware/terminology.py, apps/admin_settings/models.py, apps/admin_settings/forms.py, "**/templates/includes/_terminology*"]
---

# DRR: Customisable Terminology

**Parent Principle:** [Collaborative Practice](../principles/collaborative-practice.md)

## Core Decision

KoNote's user-facing language is a **per-agency configuration**, not hardcoded. Templates must use the terminology context variables (`{{ term.client }}`, `{{ term.worker }}`, `{{ term.plan }}`, `{{ term.goal }}`, etc.) — never hardcoded role, artefact, or relationship words. An agency may render "client" as "member", "participant", "guest", or any other term their community uses; they may render "worker" as "counsellor", "coach", "navigator", "peer"; "plan" as "pathway"; "goal" as "milestone" or "outcome".

If the system doesn't speak the community's language, it isn't truly collaborative.

### What counts as a "terminology word" for this rule

| Default word (forbidden in templates) | Terminology variable |
|---|---|
| client, clients | `{{ term.client }}`, `{{ term.client_plural }}` |
| participant, participants | `{{ term.client }}` (participant is an alias default) |
| member, members | `{{ term.client }}` (alias default) |
| worker | `{{ term.worker }}` |
| counsellor, counselor, coach | `{{ term.worker }}` (alias defaults) |
| plan | `{{ term.plan }}` |
| goal | `{{ term.goal }}` |
| pathway | `{{ term.plan }}` (alias default) |

Words that are **not** on this list (e.g., "note", "program", "report") are out of scope for this rule — they are not customisable and may appear as literals.

## Anti-patterns

| Anti-pattern | Why it is rejected |
|---|---|
| `<h1>Clients</h1>` in a template | An agency that calls them "members" sees the wrong word |
| `_("client")` in a template or Python string shown to users | Translation ≠ terminology; translating "client" to French still bakes the default role word in |
| A terminology variable whose default is itself a forbidden word, used as a workaround to avoid the Semgrep rule | The rule scans for the literal word in template text; a terminology include is not a loophole |
| Hardcoding the terminology in Python view code ("messages.success(request, 'Client updated')") | Same rule applies to user-visible strings in Python — flag with an `# noqa: terminology` comment and a reason, or rewrite to pass the term through context |

## CI enforcement (detail)

1. **Semgrep rule** `no-hardcoded-terminology-words` runs on every `**/templates/**/*.html` diff. It flags the forbidden words when they appear as rendered text (not when they appear inside `{{ }}`, `{% %}`, HTML comments, or a fragment preceded by `{# terminology-exception: <reason> #}` on the line immediately above). False positives are expected and are handled by the allowlist comment, not by weakening the rule.
2. **Pytest** `tests/drr/test_terminology_substitution.py` renders a canonical set of templates under a non-default terminology configuration and asserts the default words do not leak through. This is the backstop — if the Semgrep rule misses a case (e.g., a word inside a partial that isn't scanned as a standalone template), the substitution test catches it.
3. **CODEOWNERS** on the terminology middleware (`konote/middleware/terminology.py`), the `TerminologyOverride` model (`apps/admin_settings/models.py`), the terminology admin form (`apps/admin_settings/forms.py`), and any `_terminology*` template includes. Any change to how terminology is stored or injected into template context must be reviewed by a DRR steward.

## Graduated complexity

Today: a fixed set of ~10 terminology variables covering the most common swaps, enforced by the rule above. If an agency needs a word that isn't on the terminology list (e.g., "cohort" for their groupings), the first response is to add a new variable — not to hardcode the word. Adding a terminology variable is a small code change plus a Semgrep rule update.

## When to revisit

If analytics show that <5% of agencies ever change the default terminology, or if bilingual complexity makes per-term swaps untenable, reconsider whether every swap variable should remain configurable. The principle — agencies speak their own language — should not change; the implementation surface can narrow if usage evidence supports it.

## Related DRRs

- [bilingual-requirements](bilingual-requirements.md) — complementary: translation handles language, terminology handles vocabulary within a language
- [access-tiers](access-tiers.md) — tier labels ("Open Access", "Role-Based", "Clinical Safeguards") are customisable in the same way
