# Naming & Versioning Recommendations

## Decision needed: Confirm with David before renaming

## Product Name: KoNote

**Recommendation:** Drop "KoNote" and call the web version simply **KoNote**.

**Rationale:**
- This is a ground-up rewrite, not an incremental upgrade — it deserves the name
- You were involved in the original and own the naming rights
- Only one organization uses the original — no user base to confuse
- "KoNote" creates awkward versioning ("KoNote v1.2") and adds an unnecessary syllable
- New users (99.9% of future audience) encounter a clean, simple name with no baggage

**Prerequisite:** Get David's agreement to carry the name forward.

## Referring to the Original: Don't Formally Rename It

**Recommendation:** Use **"KoNote Classic"** informally in your own materials when you need to distinguish, but don't touch the original's code or branding.

**Rationale:**
- One organization uses the original — they know what they're running
- "Classic" is warm and respectful ("the one that started it all")
- "Desktop" is descriptive but limits you if the web version ever ships as a desktop app
- "Legacy" sounds like "abandoned" — slightly insulting
- Formally renaming the original means modifying code you're not actively maintaining

**In practice:** One sentence on the About page or README is enough:

> "KoNote is a ground-up rebuild inspired by KoNote Classic, the original desktop application."

## Versioning: Semantic Versioning from 1.0.0

Use **SemVer** (`MAJOR.MINOR.PATCH`), starting fresh at 1.0.0:

| Version | Meaning |
|---------|---------|
| KoNote 1.0.0 | First stable release |
| KoNote 1.1.0 | New features, backward compatible |
| KoNote 1.1.1 | Bugfix/patch |
| KoNote 2.0.0 | Breaking changes (major DB migration, API changes, etc.) |

- In the UI/About page: "KoNote 1.2"
- In conversation: drop the patch number unless relevant
- In code: the Python module stays `konote` (no change needed)

## Rename Scope (when ready)

These references to "KoNote" will need updating:

- UI strings and page titles
- Environment variables (e.g. `KONOTE_MODE`)
- README and documentation
- Website and marketing materials

The Python module name `konote` does **not** need to change — it's already correct.

## Status

- [ ] Discuss with David — get agreement to use "KoNote" for the web version
- [ ] Rename "KoNote" references in codebase (deferred until after agreement)
