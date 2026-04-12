---
role: principle
status: Draft - awaiting GK review
source: foundation-collaborative-practice.md (2026-03-14)
---

# Principle: Collaborative Practice

**The "Ko" in KoNote**

> **In plain language:** KoNote is designed so that staff and participants write notes together, not separately. The participant's voice — their words, their feedback, their rating of the relationship — is a core part of every note, not an afterthought. The name itself means "collaborative note" and works in both English and French.

---

## Core Principle

KoNote means "collaborative note" — the name works in English and French (*co-note / ko-note*). Progress notes are part of the service, not administrative overhead. Documentation happens *with* the participant, not *about* them.

This is the single most important design decision in the system. Every other feature — the portal, the goal builder, the alliance rating, the suggestion pipeline, the strengths-based language — exists to support this principle. If a proposed feature makes documentation feel like something staff do alone at their desk after a session, it is working against the grain of the system. If it brings the participant closer to the documentation process, it is aligned.

## Research Basis

- **Feedback-Informed Treatment (FIT)** shows a 65% improvement in outcomes for at-risk clients when routine feedback is integrated into service delivery (Lambert & Shimokawa, 2011).
- **Collaborative documentation** is rated helpful by 82% of clients in behavioural health settings, and reduces staff documentation time by shifting note-taking into the session itself (Stanhope et al., 2013).
- **Routine Outcome Monitoring (ROM)** produces approximately 8% improvement in outcomes when feedback is collected and reviewed regularly (Gondek et al., 2016).
- **Therapeutic alliance** — the working relationship between participant and worker — is the strongest predictor of outcomes across counselling, case management, and social services. Participant-reported alliance predicts outcomes better than clinician-reported alliance (Horvath et al., 2011).

KoNote is designed to make these practices the path of least resistance, not an add-on requiring extra effort.

## Guiding Tests for Proposed Features

Ask of any proposed feature:

1. **Does it bring the participant closer to the documentation process, or further away?**
2. **Does it give the participant something meaningful to do, or is it surveillance dressed as access?**
3. **Does it treat participant voice as structural, or as decorative?**
4. **Does it frame the data as information about the *service*, or as judgement of the *person*?** (See also: `insights-metric-distributions.md` — "Service-framing, not person-labelling.")

If a feature fails any of these, it is misaligned with the Ko principle. It may still be a worthwhile feature — but the misalignment is the cost that has to be argued for.

## Key Judgement Calls

These are the judgement areas where this principle applies. They cannot be grep-checked; they require human (and/or LLM) review of intent.

- **Language.** System copy, progress band labels, engagement descriptors, alliance anchors — all should use strengths-based, service-framing language. Deficit language ("non-compliant", "resistant", "low-functioning") contradicts the principle.
- **Portal features.** Read-only portal features weaken the principle. Portal features that give the participant an action (journal, message, correct, prepare, rate) strengthen it.
- **Note structure.** Notes that omit participant voice are incomplete by design. The two-lens structure (Their Perspective / Your Observations) is load-bearing.
- **Goal capture.** Goals defined purely in clinical or funder language contradict the principle. The participant's own words must be captured and surfaced.
- **Feedback cadence.** Annual surveys are not enough. Feedback collection must be embedded in ongoing service delivery.

## When to Revisit

This principle should be revisited if:

- Research emerges showing collaborative documentation produces worse outcomes than staff-only notes (current evidence strongly favours collaboration).
- Participant engagement features create adoption barriers that prevent agencies from using the system at all.
- Privacy regulations change in ways that make participant access to their own records legally problematic (currently, privacy law favours participant access).

The principle is load-bearing — changing it would require redesigning most of the application's core features.

---

## Implementation DRRs

Specific, enforceable decisions that implement this principle:

- [bilingual-requirements](../design-rationale/bilingual-requirements.md) — EN/FR translation pipeline; bilingual as design constraint
- [survey-metric-unification](../design-rationale/survey-metric-unification.md) — participant self-report and staff observation through one measurement infrastructure
- [circles-family-entity](../design-rationale/circles-family-entity.md) — relational context beyond the individual
- [insights-metric-distributions](../design-rationale/insights-metric-distributions.md) — service-framing language on dashboards; distribution not average
- [executive-dashboard-redesign](../design-rationale/executive-dashboard-redesign.md) — accessibility as structural requirement
- [access-tiers](../design-rationale/access-tiers.md) — demographic visibility controls that support participant dignity

## Related Principles

- **Data Sovereignty** — bilingual design and participant portal access are also expressions of sovereignty
- **Security by Default** — session security and accessibility protect the portal
- **Nonprofit Sustainability** — the simple tech stack keeps the interface usable alongside participants in session
