# Foundation: Collaborative Practice

**The "Ko" in KoNote**

Status: Foundation Principle
Created: 2026-03-14

---

## Core Principle

KoNote means "collaborative note" — the name works in both English and French (*co-note / ko-note*). The application is built on the principle that progress notes are part of the service, not administrative overhead. Documentation happens WITH the participant, not ABOUT them.

This is the single most important design decision in the system. Every other feature — the portal, the goal builder, the alliance rating, the suggestion pipeline, the strengths-based language — exists to support this principle. If a proposed feature makes documentation feel like something staff do alone at their desk after a session, it is working against the grain of the system. If it brings the participant closer to the documentation process, it is aligned.

## Why This Matters

The research basis for collaborative practice is strong across helping professions:

- **Feedback-Informed Treatment (FIT)** shows a 65% improvement in outcomes for at-risk clients when routine feedback is integrated into service delivery (Lambert & Shimokawa, 2011).
- **Collaborative documentation** is rated helpful by 82% of clients in behavioural health settings, and reduces staff documentation time by shifting note-taking into the session itself (Stanhope et al., 2013).
- **Routine Outcome Monitoring (ROM)** produces approximately 8% improvement in outcomes when feedback is collected and reviewed regularly (Gondek et al., 2016).
- **Therapeutic alliance** — the working relationship between participant and worker — is the strongest predictor of outcomes across counselling, case management, and social services. Participant-reported alliance predicts outcomes better than clinician-reported alliance (Horvath et al., 2011).

KoNote is designed to make these practices the path of least resistance, not an add-on that requires extra effort.

---

## How This Principle Shapes the System

### 1. Two-Lens Note Design

**What:** Every progress note has two sides — "Their Perspective" (participant voice: reflection, suggestion, alliance rating) and "Your Observations" (staff: engagement level, clinical notes, follow-up items). The note form presents both lenses as equal structural components.

**Why:** A note that only captures what the worker observed is a clinical record. A note that also captures what the participant experienced is a collaborative record. The two-lens structure makes the participant's voice a first-class part of documentation, not a comment box at the bottom.

**Anti-pattern:** Notes that are staff-only clinical documentation written after the session. The participant's voice is not optional decoration — it is structural. A note without "Their Perspective" is incomplete by design, and the system signals this visually.

### 2. Alliance Rating

**What:** The participant self-rates the working relationship on a 1–5 scale using plain-language anchors (e.g., "I really trust my worker" at the high end). Prompt wording rotates to prevent habituation. The rating can happen in-session (staff records what the participant says) or asynchronously via the portal (participant fills it in within 7 days of the session).

**Why:** The alliance between participant and worker is the strongest single predictor of outcomes. Measuring it routinely — and from the participant's perspective — gives programs a real-time signal about service quality that no administrative metric can provide. A sudden drop in alliance ratings across a caseload is an early warning system.

**Anti-pattern:** Alliance measured only by staff observation or clinical judgment. The research is clear: participant-reported alliance predicts outcomes better than clinician-reported alliance. Staff perception of "how it went" is valuable but is not a substitute for asking the participant directly.

### 3. Participant Portal

**What:** Participants can log into their own portal to view their goals (in their own words), see progress over time, write journal entries, send messages to their worker, rate the alliance, request corrections to their record, and flag items to discuss at the next session.

**Why:** If participants can only see what staff wrote about them, the portal is surveillance. If participants can act on their own information — reflect, respond, prepare for sessions, flag concerns — the portal is a tool for shared ownership of the service relationship.

**Anti-pattern:** A portal that is a read-only view of what staff wrote. The portal is designed for participant ACTION: journaling, messaging, preparing for sessions, rating the relationship, requesting corrections. Every portal feature should pass the test: "Does this give the participant something meaningful to do?"

### 4. Goal Builder

**What:** An AI-assisted conversational goal-setting tool that captures the participant's own words alongside professional outcome language. Every goal stores both `client_goal` (the participant's phrasing, encrypted) and structured outcome metrics (scale definitions, target values, measurement frequency). The participant sees their own words in the portal; the structured metrics drive reporting.

**Why:** Goals defined entirely in clinical or funder language ("Increase self-efficacy score from 2.3 to 3.5 on the GSE-10") are meaningless to the participant. Goals in the participant's own words ("I want to feel confident enough to go to a job interview") are meaningful but hard to measure. KoNote stores both, so the participant sees language they recognise and the program has data it can aggregate.

**Anti-pattern:** Goals defined entirely by staff using clinical language, where the participant's own words are absent or treated as informal context. The participant's phrasing is not a nice-to-have — it is displayed back to them in the portal and is a core part of the collaborative relationship.

### 5. Feedback-Informed Continuous Improvement

**What:** Every progress note includes an optional field for participant suggestions — "Is there anything you'd change about the program or how we work together?" — with a priority level. Suggestions are AI-categorised into themes (SuggestionTheme). Themes are aggregated and surfaced on the executive dashboard so program managers and directors can see patterns across the entire agency.

**Why:** Annual satisfaction surveys are the standard approach to participant feedback in nonprofits. They suffer from low response rates, recall bias, and a feedback loop so slow that problems persist for a full program cycle before anyone notices. By embedding feedback collection in every session, KoNote makes participant voice a continuous signal, not an annual event. Theme aggregation means individual suggestions become actionable program intelligence.

**Anti-pattern:** Participant feedback collected through annual surveys that are summarised in a report nobody reads until the next funding cycle. KoNote makes feedback structural and continuous — every session is an opportunity for the participant to shape the program.

### 6. Strengths-Based Language

**What:** All system language — progress descriptors, alliance anchors, engagement levels, dashboard labels — uses growth-oriented framing. Progress bands use language like "Something's shifting" and "In a good place" rather than deficit labels. Alliance anchors use relational language ("I really trust my worker") not clinical pathology. Engagement observations include "Fully invested" as the highest level, not "Compliant."

**Why:** Language shapes perception. When staff document in deficit-focused language ("client is non-compliant," "resistant to treatment," "low functioning"), it frames the participant as the problem. Strengths-based language frames the documentation as a record of growth and capacity. This is not cosmetic — it changes how staff think about the people they serve and how participants feel when they read their own records through the portal.

**Anti-pattern:** Clinical deficit-focused documentation that pathologises participants. Terms like "non-compliant," "resistant," "low-functioning," and "at-risk" frame participants as deficient. KoNote's language consistently frames data as information about whether the service is working, not whether the person is succeeding or failing. (See also: `insights-metric-distributions.md`, Principle 6 — "Service-framing, not person-labelling.")

### 7. Customisable Terminology

**What:** Agencies choose their own language for core concepts — client/participant/member, worker/counsellor/coach, plan/goal/pathway. All templates use `{{ term.client }}` rather than hardcoded words. Terminology is set once in admin settings and applied system-wide.

**Why:** "Client" is standard in some sectors, alienating in others. A youth drop-in centre may use "member." A counselling agency may use "client." An Indigenous healing program may use "participant" or a word in their own language. Forcing clinical terminology on communities that don't use it creates a barrier to adoption and contradicts the collaborative ethos — if the system doesn't speak the community's language, it isn't truly collaborative.

**Anti-pattern:** Hardcoded clinical terminology that assumes every agency uses the same words. The terminology system exists because collaborative practice means respecting how each community describes its own relationships.

---

## Anti-Patterns Summary

| Anti-pattern | Why it's rejected |
|---|---|
| Notes written ABOUT participants after sessions | Undermines the alliance; excludes the participant from their own record |
| Staff-only alliance assessment | Participant self-report is a stronger outcome predictor than clinician judgment |
| Portal as a read-only view of staff notes | Participants need to ACT on their information, not passively receive it |
| Goals defined in clinical language only | Participant's own words reinforce shared ownership; clinical-only goals are meaningless to the person |
| Annual feedback surveys | Too infrequent; low response rates; feedback loop too slow to drive real improvement |
| Deficit-focused clinical language | Pathologises participants; contradicts strengths-based practice; harmful when participants read their own records |
| Hardcoded terminology | Not every community uses clinical language; forced terminology is a barrier to adoption |

---

## Related Implementation Decisions

These existing Design Rationale Records contain the detailed implementation specifics for features shaped by this principle:

- **`insights-metric-distributions.md`** — How suggestion themes and outcome distributions are aggregated for program learning. Includes the "service-framing, not person-labelling" principle for dashboard language.
- **`survey-metric-unification.md`** — Surveys and metrics as a unified construct, enabling participant self-report and staff observation to be captured through the same measurement infrastructure.
- **`circles-family-entity.md`** — Family and network entity design, extending collaborative practice beyond the individual to recognise that participants exist in relational contexts.

---

## When to Revisit

This foundation principle should be revisited if:

- Research emerges showing that collaborative documentation produces worse outcomes than traditional staff-only notes.
- Participant engagement features (portal, alliance rating, suggestion capture) create significant adoption barriers that prevent agencies from using the system at all.
- Privacy regulations change in ways that make participant access to their own records legally problematic (currently, privacy law favours participant access).

Current evidence strongly favours collaborative approaches. The principle is load-bearing — changing it would require redesigning most of the application's core features.
