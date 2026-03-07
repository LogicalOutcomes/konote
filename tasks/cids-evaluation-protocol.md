# CIDS Evaluation Protocol

## Purpose

This protocol defines how an evaluator fills in the CIDS Full Tier metadata fields for a KoNote program. It is part of the evaluation planning process and produces the data stored in the `EvaluationFramework` and `EvaluationComponent` models (see [evaluation-planning-enrichment-implementation-spec.md](evaluation-planning-enrichment-implementation-spec.md)).

The output is a complete evaluation framework that maps directly to CIDS Full Tier JSON-LD classes. See [wireframes/demo-full-tier-export.jsonld](wireframes/demo-full-tier-export.jsonld) for a worked example.

## Who is involved

| Role | Person | Responsibility |
|------|--------|---------------|
| **Evaluator** | Professional evaluator (internal or contracted) | Leads the process, makes judgement calls, signs attestation |
| **Program lead** | Program manager or coordinator | Provides program knowledge, validates descriptions, confirms stakeholder groups |
| **LLM assistant** | Frontier LLM (via KoNote or external platform) | Drafts descriptions, suggests risks, synthesises literature, checks completeness |

## What gets filled in

Each CIDS Full Tier class requires specific content. The table below shows the source for each.

| CIDS Class | KoNote Model | Primary source | LLM role |
|------------|-------------|----------------|----------|
| ImpactModel | `EvaluationFramework` | Program documentation + evaluator synthesis | Draft narrative from documents; evaluator edits |
| Service | `EvaluationComponent(service)` | Program lead interview | Draft description from interview notes |
| Activity | `EvaluationComponent(activity)` | Program lead interview | Draft description; suggest dosage questions |
| Stakeholder | `EvaluationComponent(participant_group)` | Program data + evaluator definition | Suggest subgroup distinctions; draft descriptions |
| StakeholderOutcome | Constructed at export from PlanTarget data | KoNote aggregate data + evaluator interpretation | Summarise achievement data; evaluator adds interpretive context |
| Output | `EvaluationComponent(output)` | KoNote aggregate data | Auto-draft from observation counts; evaluator adds context |
| ImpactRisk | `EvaluationComponent(risk)` | Literature + evaluator + program lead | Propose risks as starting menu; program lead provides actual mitigations |
| Counterfactual | `EvaluationComponent(counterfactual)` | Literature review + evaluator judgement | Draft baseline statement; flag where evidence is needed |
| Indicator | `MetricDefinition` (existing) | Already in KoNote | Validate descriptions; suggest taxonomy codes |
| IndicatorReport | `MetricValue` aggregates (existing) | Already in KoNote | Format comments with context |

## Protocol phases

### Phase 1: Document Assembly (evaluator, 1-2 hours)

**Goal:** Gather everything the program has already written about itself.

**Collect:**
- Grant applications and funder proposals
- Logic models or theories of change (if any)
- Program descriptions from websites or brochures
- Funder reporting templates and requirements
- Any prior evaluation reports

**LLM task:** Upload documents to a frontier LLM using the evaluation planning prompt (see [cids-evaluation-planning-prompt.md](cids-evaluation-planning-prompt.md)). The LLM extracts and structures existing content into a preliminary framework, identifying what's already articulated vs. what's missing.

**First-time vs. repeat evaluation:** The timing estimates in this protocol assume the program has existing documentation (grant applications, logic models). For programs being formally evaluated for the first time, Phase 1 may take a full day to help the program articulate what it does before structuring it.

**Output:** A gap analysis showing which CIDS classes have existing documentation and which need interviews or literature.

### Phase 2: Guided Interview (evaluator + program lead, 1-2 hours)

**Goal:** Fill in what documents don't cover — especially service delivery details, stakeholder definitions, and risk awareness.

**Interview topics mapped to CIDS classes:**

1. **Services & Activities** (cids:Service, cids:Activity)
   - What do you deliver? How often? For how long?
   - What makes your approach different from similar programs?
   - What's the participant journey from intake to completion?

2. **Stakeholders** (cids:Stakeholder)
   - Who participates? What are the eligibility criteria?
   - Are there distinct subgroups with different barriers or expected outcomes?
   - How many people are in each group?

3. **Outcome chain** (cids:Outcome, cids:ImpactModel)
   - What changes do you expect to see in participants?
   - What's the sequence: what happens first, what follows?
   - How do you know when someone has achieved the outcome?

4. **Risks** (cids:ImpactRisk)
   - What could prevent participants from achieving outcomes?
   - What risks have you actually encountered?
   - What do you do to mitigate each risk?

5. **Outputs** (cids:Output)
   - Beyond observation counts (which KoNote has), what tangible products or deliverables does the program produce?
   - Job placements, certificates, referrals, etc.

6. **Data quality awareness**
   - How confident are you in the accuracy of your data?
   - What's your biggest data quality concern?
   - Are there metrics where you suspect underreporting or inconsistent recording?

7. **Equity and cultural responsiveness**
   - Does your program serve Indigenous participants? If so, has the evaluation approach been discussed with Indigenous community partners or an Indigenous advisory body? (See OCAP principles: Ownership, Control, Access, Possession.)
   - For programs serving equity-deserving populations (newcomers, people with disabilities, etc.): has the stakeholder group been consulted about how they are described and measured?
   - Note: stakeholder subgroups smaller than the minimum reporting threshold (k=5) should be described in the evaluation framework for internal planning purposes, but their outcome data must not appear in CIDS exports.

**Rolling intake programs:** For programs with rolling intake (no cohort boundaries), define a reporting period (e.g., fiscal year, funder reporting cycle) and treat all participants active during that period as the reporting group. The outcome chain and indicators still apply — the difference is that "cohort" becomes "participants served during the reporting period."

**LLM task:** The evaluator can run the interview with the LLM listening (via transcript) or debrief after. The LLM drafts component descriptions from interview content and flags follow-up questions.

### Phase 3: Literature-Informed Enrichment (evaluator + LLM, 1-2 hours)

**Goal:** Ground the counterfactual, risks, and measurement choices in evidence.

**Three literature tasks:**

1. **Counterfactual baseline** (cids:Counterfactual)
   - What does the evidence say about outcomes for this population without this type of intervention?
   - Are there comparable programs with published outcomes?
   - What's the "natural" rate of the outcome (e.g., employment rate for youth without job training)?
   - **LLM drafts** a counterfactual statement distinguishing assumed vs. evidence-based baselines
   - **Acceptable evidence types:** CIDS does not require experimental evidence. Acceptable counterfactual baselines include: (a) published comparison group data, (b) pre-program baseline from intake assessments, (c) government statistics for the population (e.g., Statistics Canada, ESDC), or (d) clearly labelled assumptions where evidence is unavailable.
   - **Cultural sensitivity:** When the program serves Indigenous participants, the evaluator should consider strengths-based framing and consult with Indigenous advisors about appropriate comparison points. Avoid framing that positions communities as inherently disadvantaged.

2. **Risk factors** (cids:ImpactRisk)
   - What risk factors does the literature identify for this population/intervention type?
   - Which of the program's self-identified risks align with known factors?
   - Are there risks the program hasn't considered?
   - **Two-pass process:** (1) LLM proposes 3-5 risks as a starting menu — these are conversation starters drawn from training data, not evidence-based findings. (2) For each risk the evaluator and program lead confirm as relevant, the program lead describes what they **actually do** about it. Mitigation text must come from the program, not the LLM. If the program has no concrete mitigation for a confirmed risk, record that honestly — it is useful information.

3. **Measurement instruments** (cids:Indicator)
   - Are there validated instruments for the outcomes being measured?
   - Do the program's custom metrics align with standard taxonomies (IRIS+, SDG)?
   - **LLM suggests** taxonomy code mappings with rationale
   - **Handoff to taxonomy review pipeline:** Taxonomy suggestions from this step feed into the existing TaxonomyMapping model with `mapping_source='evaluator_suggested'` (distinct from `ai_suggested`). The suggestions are stored as drafts and go through the same admin review queue as AI-generated mappings.

**Output:** Literature review brief with citations. See [Literature Review Brief](#literature-review-brief-template) template below.

### Phase 4: Framework Assembly (evaluator, 1 hour)

**Goal:** Compile all components into a complete evaluation framework.

**Steps:**
1. Review all drafted components from Phases 1-3
2. Edit descriptions for accuracy, specificity, and clarity
3. Assign quality states to each component:
   - `ai_drafted` — LLM wrote it, not yet reviewed
   - `evaluator_reviewed` — evaluator has read and edited
   - `evaluator_confirmed` — evaluator affirms accuracy
4. Check completeness against CIDS Full Tier requirements (see checklist below)
5. Enter the framework into KoNote's Evaluation Framework editor (or provide to someone who will)

**LLM task:** Run a completeness check against the CIDS Full Tier checklist. Flag missing classes, thin descriptions, or unsupported claims.

### Phase 5: Attestation (evaluator)

**Goal:** Formal sign-off that the evaluation framework accurately represents the program.

The evaluator attests to three scopes:
- **Impact model accuracy** — the theory of change narrative reflects how the program actually works
- **Outcome measurement validity** — the indicators measure what they claim to measure
- **Risk assessment completeness** — known risks are identified with credible mitigations

This attestation is recorded in KoNote and included in the CIDS JSON-LD export as `evaluatorAttestation`.

## Framework Versioning

Evaluation frameworks should be reviewed:
- **Annually**, as part of the program's regular reporting cycle
- **When the program model changes materially** (new services, different population, changed delivery mode)
- **When funder requirements change** (new taxonomy systems, different reporting standards)

CIDS exports include `exportedAt` timestamps. The evaluation framework's `planning_quality_state` should be reset to `needs_review` when the underlying program changes, prompting the evaluator to re-confirm or update the framework before the next export.

## CIDS Full Tier Completeness Checklist

- [ ] **ImpactModel** — narrative description covering inputs, activities, outputs, outcomes, and the causal chain
- [ ] **At least one Stakeholder** — with demographics, size, and description of barriers
- [ ] **At least one Service** — with description of what is delivered, to whom, how
- [ ] **At least one Activity per Service** — with frequency, duration, delivery mode
- [ ] **At least one Output** — quantified (observation counts or tangible deliverables)
- [ ] **At least one Outcome** — with linked Indicators
- [ ] **At least one ImpactRisk** — with likelihood, severity, and mitigation strategy (mitigation from program, not LLM)
- [ ] **Counterfactual** — with baseline comparison (evidence-based preferred, assumed acceptable if labelled)
- [ ] **IndicatorReports** — with measurement values for the reporting period (if data exists)
- [ ] **StakeholderOutcome** — aggregate achievement summary
- [ ] **Taxonomy codes** — at least one taxonomy system applied (IRIS+, SDG, or sector codes)
- [ ] **Evaluator attestation** — scope, name, date, attestation text

## Literature Review Brief Template

For each program, the evaluator produces a brief covering:

### 1. Comparable Programs
- Program name, location, population, intervention type
- Published outcomes (with citations)
- How the evaluated program compares

### 2. Counterfactual Evidence
- Baseline outcome rates for the population without intervention
- Sources (government statistics, meta-analyses, comparable program evaluations)
- Clearly labelled: evidence-based vs. assumed

### 3. Known Risk Factors
- Risk factors identified in the literature for this population/intervention type
- Alignment with the program's self-identified risks
- Any gaps (risks the program hasn't considered)

### 4. Measurement Instruments
- Validated instruments relevant to the program's outcomes
- Whether the program uses standard or custom measures
- Taxonomy code suggestions with rationale (IRIS+, SDG, ICNPO, sector codes)

### 5. Cultural Safety and Equity Considerations
- For programs serving Indigenous peoples: alignment with OCAP principles and culturally safe evaluation practices
- For programs serving newcomers, people with disabilities, or other equity-deserving populations: appropriateness of outcome definitions, measurement approaches, and comparison groups
- Use of terminology preferred by the communities being described

### 6. Sources
- Full citations for all referenced literature
- Preference for: Canadian sources, recent (last 5 years), peer-reviewed or government reports

## Relationship to Other Documents

| Document | Relationship |
|----------|-------------|
| [evaluation-planning-enrichment-implementation-spec.md](evaluation-planning-enrichment-implementation-spec.md) | Technical spec for the models and APIs that store this protocol's outputs |
| [evaluation-planning-and-enrichment-workflow.md](evaluation-planning-and-enrichment-workflow.md) | Broader workflow including post-export enrichment (Stages A-H); this protocol covers Stages A-B |
| [cids-evaluation-planning-prompt.md](cids-evaluation-planning-prompt.md) | The LLM prompt used during this protocol |
| [cids-full-tier-compliance-assessment.md](cids-full-tier-compliance-assessment.md) | Technical gap analysis for Full Tier export code |
| [cids-classification-implementation.md](cids-classification-implementation.md) | Taxonomy mapping pipeline (Phase 3 literature review feeds into this) |
| [wireframes/demo-full-tier-export.jsonld](wireframes/demo-full-tier-export.jsonld) | Worked example of the final JSON-LD output |
| [wireframes/evaluation-framework-editor.html](wireframes/evaluation-framework-editor.html) | UI wireframe for entering framework data in KoNote |

## Timing Estimate

For a single program with existing documentation:
- Phase 1 (Document Assembly): 1-2 hours
- Phase 2 (Guided Interview): 1-2 hours
- Phase 3 (Literature Enrichment): 1-2 hours
- Phase 4 (Framework Assembly): 1 hour
- Phase 5 (Attestation): 30 minutes

**Total: approximately one working day per program.**

For programs being evaluated for the first time (no prior documentation), add a full day for Phase 1 to help the program articulate its model before structuring it.

For agencies with multiple programs, the evaluator can batch Phase 3 (literature review) across similar programs and reuse stakeholder/risk content where programs serve the same population.
