# KoNote Design Rationale Records

> **Draft restructure — awaiting GK review.**
> This folder now contains **prescriptive, enforceable DRRs only**. The four foundation principles that previously lived here have moved to [`../principles/`](../principles/README.md) and their prescriptive content has been extracted into the dedicated DRRs listed below. See `tasks/principles/README.md` for the rationale.

## What belongs here

Every DRR in this folder is **prescriptive**: it describes something a pull request can violate. Every DRR must have an `enforcement:` front-matter block declaring how CI will catch violations. Permitted enforcement types:

| Enforcement type | When to use |
|---|---|
| `django-system-check` | Invariants checked at app startup (settings, schemas, config) |
| `pytest` | Integration-test-enforceable rules (behaviour, workflows) |
| `semgrep` | Code-pattern anti-patterns detectable by AST / regex |
| `pre-commit-hook` | Repo-level structural constraints (no `package.json`, etc.) |
| `codeowner` | Legal- or safety-critical paths requiring SME approval |
| `llm-review` | Semantic conflicts that deterministic rules cannot catch |
| `judgment-only` | Explicitly no automation possible — paired with `codeowner` |

If a DRR has no enforceable content, it belongs in `../principles/` — not here.

## How to use this directory

1. **Before proposing a new feature:** read the relevant principle in [`../principles/`](../principles/README.md) first. Then check the DRRs it links to.
2. **Before modifying existing code:** if any DRR names a file you are touching, read that DRR before changing anything.
3. **If CI flags your PR against a DRR:** read the DRR's enforcement section, then the full DRR. The enforcement tells you *what* was flagged; the DRR tells you *why*.
4. **If you think a decision should change:** document the new evidence, flag for GK (subject-matter expert) review, and update the DRR *before* implementing.

Use `/design-rationale` in Claude Code to check a proposal against all DRRs.

---

## DRRs by topic

### Privacy, Consent, and Data Rights

| Document | Status | Scope |
|---|---|---|
| [individual-data-rights](individual-data-rights.md) | Draft | PIPEDA/PHIPA correction, access, erasure, append-only consent |
| [phipa-consent-enforcement](phipa-consent-enforcement.md) | Decided | Cross-program clinical note consent filtering |
| [no-live-api-individual-data](no-live-api-individual-data.md) | Decided | Export-only model; no live API for PII |
| [cids-privacy-architecture](cids-privacy-architecture.md) | Decided | Three-layer compliance for CIDS reporting |
| [data-access-residency-policy](data-access-residency-policy.md) | Decided | Canadian residency by data access level |
| [evaluation-microdata-export](evaluation-microdata-export.md) | Decided | De-identified microdata for external evaluators; k-anonymity |

### Security

| Document | Status | Scope |
|---|---|---|
| [encryption-key-rotation](encryption-key-rotation.md) | Decided | Master/tenant key rotation |
| [audit-log-isolation](audit-log-isolation.md) | Draft | Separate audit DB, INSERT-only role |
| [session-security](session-security.md) | Draft | 30-min timeout, cookie flags, CSP nonces |
| [rate-limiting-and-authentication](rate-limiting-and-authentication.md) | Draft | Login rate limit, lockout, Argon2 |
| [two-person-safety-actions](two-person-safety-actions.md) | Draft | Alert cancel, DV flag removal, erasure |
| [demo-mode-isolation](demo-mode-isolation.md) | Draft | Demo/real separation at middleware + ORM |

### Access Control

| Document | Status | Scope |
|---|---|---|
| [access-tiers](access-tiers.md) | Decided | Three permission tiers; negative access blocks; demographic visibility |
| [ai-feature-toggles](ai-feature-toggles.md) | Decided | Two-tier AI split (tools-only vs. participant data) |

### Data Model

| Document | Status | Scope |
|---|---|---|
| [survey-metric-unification](survey-metric-unification.md) | Decided | Surveys and metrics as one construct |
| [circles-family-entity](circles-family-entity.md) | Decided | Family/network entity |
| [fhir-informed-modelling](fhir-informed-modelling.md) | Decided | FHIR concepts without FHIR compliance |
| [cids-metadata-assignment](cids-metadata-assignment.md) | Draft | When metadata gets assigned |

### Evaluation and Reporting

| Document | Status | Scope |
|---|---|---|
| [reporting-architecture](reporting-architecture.md) | Decided | Template-driven vs. ad-hoc reporting |
| [insights-metric-distributions](insights-metric-distributions.md) | Decided | Outcome Insights page; service-framing language |
| [funder-reporting-profiles](funder-reporting-profiles.md) | Parking Lot | Template-based funder reporting |
| [executive-dashboard-redesign](executive-dashboard-redesign.md) | Approved | Dashboard UX with accessibility focus |
| [cids-batch-classification-workflow](cids-batch-classification-workflow.md) | Draft | Batch AI classification for taxonomies |

### Collaborative Practice (UX and Inclusion)

| Document | Status | Scope |
|---|---|---|
| [accessibility-requirements](accessibility-requirements.md) | Draft | WCAG 2.2 AA / AODA on every surface |
| [customisable-terminology](customisable-terminology.md) | Draft | Templates use `{{ term.client }}`; no hardcoded role words |
| [bilingual-requirements](bilingual-requirements.md) | Decided | EN/FR translation; legal obligation |

### Infrastructure and Integration

| Document | Status | Scope |
|---|---|---|
| [multi-tenancy](multi-tenancy.md) | Decided | Schema-per-tenant via django-tenants |
| [ovhcloud-deployment](ovhcloud-deployment.md) | Decided | OVHcloud VPS, self-healing, backup |
| [self-hosted-llm-infrastructure](self-hosted-llm-infrastructure.md) | Decided | Shared Ollama VPS; tenant isolation |
| [tech-stack-constraints](tech-stack-constraints.md) | Draft | No JS framework; dep ceiling; Alpine |
| [document-integration](document-integration.md) | Decided | SharePoint + Google Drive |
| [offline-field-collection](offline-field-collection.md) | Decided | ODK Central |

---

## Status key

| Status | Meaning |
|---|---|
| **Decided** | Approved and enforced. Do not override without stakeholder approval. |
| **Implemented** | Decided AND built. Check implementation before modifying. |
| **Approved** | Reviewed by expert panel, awaiting implementation. |
| **Draft** | Under development. Decisions may change — still read before building. |
| **Parking Lot** | Not yet clear we should build. Do not implement without explicit approval. |

## Deprecated foundation documents

The following four documents previously lived here as "foundation principles." They have been superseded by the split described above. The originals remain in place until GK approves the restructure; once approved, they will be removed from this folder.

- `foundation-collaborative-practice.md` → replaced by [`../principles/collaborative-practice.md`](../principles/collaborative-practice.md) + new [`accessibility-requirements.md`](accessibility-requirements.md) + new [`customisable-terminology.md`](customisable-terminology.md) DRRs
- `foundation-data-sovereignty.md` → replaced by [`../principles/data-sovereignty.md`](../principles/data-sovereignty.md) + new [`individual-data-rights.md`](individual-data-rights.md) DRR
- `foundation-security-by-default.md` → replaced by [`../principles/security-by-default.md`](../principles/security-by-default.md) + 5 new DRRs (audit-log-isolation, session-security, rate-limiting-and-authentication, two-person-safety-actions, demo-mode-isolation)
- `foundation-nonprofit-sustainability.md` → replaced by [`../principles/nonprofit-sustainability.md`](../principles/nonprofit-sustainability.md) + new [`tech-stack-constraints.md`](tech-stack-constraints.md) DRR

## Change history

- **2026-04-12 — Restructure revisions (PR #644).** Second-round review at [`../drr-restructure-review.md`](../drr-restructure-review.md) identified defects in the 2026-03-14 draft (invented file paths, contradictory demo-mode description, `no-silent-record-overwrite` that would flag every create, missing accessibility/terminology DRRs, no meta-check). Revision prompt at [`../drr-restructure-revision-prompt.md`](../drr-restructure-revision-prompt.md) enumerates the must-fix / should-fix / nice-to-have items that became this PR. Test-implementation prompt at [`../drr-enforcement-tests-prompt.md`](../drr-enforcement-tests-prompt.md) describes the enforcement mechanisms (pytests, Semgrep rules, Django system checks, pre-commit hooks) the new DRRs still need built.
- **2026-03-14 — Initial restructure (commit `181cbd4e`).** Four foundation docs split into principles (`tasks/principles/`) and seven new prescriptive DRRs in this directory.
