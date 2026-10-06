---
role: folder-readme
status: Draft - awaiting GK review
---

# KoNote Principles

**Draft — proposed split of the design-rationale folder. Not yet approved.**

This folder contains KoNote's foundational **principles**: the philosophy, research basis, and values that shape the system.

## Principles vs. Design Rationale Records

KoNote uses two distinct document types:

| Folder | Purpose | Enforcement |
|---|---|---|
| `tasks/principles/` (this folder) | The *why*. Philosophy, research, values, guiding questions. Read these to understand KoNote's character. | None. Principles inform judgment; they don't block PRs. |
| `tasks/design-rationale/` | The *what*. Specific prescriptive decisions with anti-patterns. Each DRR is enforceable in some way. | Every DRR has an `enforcement:` front-matter block. CI uses this to gate PRs. |

### Why the split

Previously, four large "foundation" documents mixed philosophy with prescriptive rules. This made automated enforcement awkward: some decisions were grep-able, others were matters of judgment, and both lived in the same document. After restructuring:

- **Principles are principles.** Free of enforceable rules. Written for humans, not CI.
- **Design Rationale Records are prescriptive.** Every DRR describes something a PR can violate. Each has enforcement hooks (test, CODEOWNERS, Semgrep rule, or explicit LLM review tag).

## When to read what

- **Onboarding to KoNote** → read this folder first. The four principles tell you what the project *is*.
- **Modifying a specific feature** → read the DRR(s) that govern it. Each principle here links to the implementation DRRs it shapes.
- **Proposing a new feature** → read the relevant principle, then check the DRRs it points to.

## The four principles

| Principle | Core idea |
|---|---|
| [Collaborative Practice](collaborative-practice.md) | The "Ko" in KoNote — documentation WITH participants, not ABOUT them |
| [Data Sovereignty & Rights](data-sovereignty.md) | Individual, community, and national data ownership; structural not contractual |
| [Security by Default](security-by-default.md) | Security must be architectural, not configurable; fail closed |
| [Nonprofit Sustainability](nonprofit-sustainability.md) | Affordable for small agencies without dedicated IT; evaluation-driven |

Each of these previously lived as `foundation-*.md` in the `design-rationale/` folder. Under this proposal they move here and their prescriptive content is extracted into new, smaller DRRs.
