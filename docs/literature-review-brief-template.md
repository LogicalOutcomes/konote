# Literature Review Brief Template

Use this template when completing Phase 3 (Literature-Informed Enrichment) of the [CIDS Evaluation Protocol](../tasks/cids-evaluation-protocol.md). The evaluator fills in one brief per program, working with an LLM assistant to locate and synthesise evidence.

**Purpose:** Ground the program's counterfactual, risk factors, and measurement choices in published evidence. This brief becomes part of the evaluation framework record and is referenced in the CIDS Full Tier export.

**Time estimate:** 1–2 hours per program (less when programs serve similar populations and can share evidence).

---

## Program Information

| Field | Value |
|-------|-------|
| **Program name** | |
| **Agency** | |
| **Population served** | |
| **Intervention type** | (e.g., job readiness, mentorship, housing stabilisation) |
| **Reporting period** | |
| **Evaluator** | |
| **Date completed** | |

---

## 1. Comparable Programs

Identify 2–5 programs that serve a similar population with a similar intervention. These provide the basis for counterfactual comparison and risk identification.

| Program | Location | Population | Intervention | Published outcomes | Citation |
|---------|----------|------------|-------------|-------------------|----------|
| | | | | | |
| | | | | | |
| | | | | | |

**How the evaluated program compares:**
<!-- 2-3 sentences describing similarities and differences with the comparable programs listed above. Focus on population, dosage, delivery mode, and context. -->

---

## 2. Counterfactual Evidence

What would happen to this population without this program? Use published baselines where available; clearly label assumptions where evidence is unavailable.

### Evidence-based baselines

| Outcome | Baseline rate (without intervention) | Source | Year |
|---------|-------------------------------------|--------|------|
| | | | |
| | | | |

### Assumed baselines (where evidence is unavailable)

| Outcome | Assumed baseline | Basis for assumption |
|---------|-----------------|---------------------|
| | | |

### Counterfactual statement (draft)

> Without [program], participants would [alternative pathway]. Evidence suggests [baseline rate] compared to [program rate]. Source: [citation or "needs verification"].

**Label:** ☐ Evidence-based  ☐ Partially evidence-based  ☐ Assumed (needs further evidence)

---

## 3. Known Risk Factors

Risk factors identified in the literature for this population and intervention type. These feed into the ImpactRisk component of the evaluation framework.

### From the literature

| Risk factor | Description | Source | Relevance to this program |
|-------------|-------------|--------|--------------------------|
| | | | |
| | | | |
| | | | |

### From the program's self-assessment (Phase 2 interview)

| Risk identified by program | Aligns with literature? | Mitigation (from program lead) |
|---------------------------|------------------------|-------------------------------|
| | Yes / No / Partially | |
| | | |

### Gaps

<!-- List any risks identified in the literature that the program has not considered. These are not criticisms — they are items for discussion with the program lead. -->

- 

---

## 4. Measurement Instruments

### Validated instruments relevant to the program's outcomes

| Instrument | What it measures | Validation status | Used by this program? |
|-----------|-----------------|-------------------|----------------------|
| | | | Yes / No / Similar custom |
| | | | |

### Taxonomy code suggestions

| Program metric | Suggested taxonomy | Code | Rationale |
|---------------|-------------------|------|-----------|
| | IRIS+ / SDG / ICNPO | | |
| | | | |

**Note:** These suggestions are stored in KoNote as `mapping_source='evaluator_suggested'` and go through the same admin review queue as AI-generated mappings.

---

## 5. Cultural Safety and Equity Considerations

### Indigenous participants (if applicable)

- ☐ OCAP principles (Ownership, Control, Access, Possession) have been considered
- ☐ Evaluation approach has been discussed with Indigenous community partners or advisory body
- ☐ Comparison groups and counterfactual framing avoid deficit-based language
- ☐ Terminology has been confirmed with community partners

### Other equity-deserving populations (if applicable)

- ☐ Outcome definitions are appropriate for the population
- ☐ Measurement approaches account for cultural and linguistic context
- ☐ Comparison groups are appropriate (not comparing across fundamentally different contexts)
- ☐ Community-preferred terminology is used throughout

### Notes
<!-- Record any specific considerations, decisions, or consultation outcomes here. -->

---

## 6. Sources

List all references cited in this brief. Prefer:
- Canadian sources where available
- Recent publications (last 5 years)
- Peer-reviewed articles or government reports (Statistics Canada, ESDC, provincial ministries)

| # | Citation | Type | Notes |
|---|----------|------|-------|
| 1 | | Journal / Government / Grey literature | |
| 2 | | | |
| 3 | | | |
| 4 | | | |
| 5 | | | |

---

## Evaluator Sign-Off

| | |
|---|---|
| **Evaluator name** | |
| **Date** | |
| **Confidence level** | ☐ High — strong evidence base  ☐ Moderate — some evidence gaps  ☐ Low — mostly assumed baselines |
| **Recommended follow-up** | |

---

## How This Feeds Into KoNote

This brief provides evidence for three CIDS Full Tier components:

| Brief section | CIDS class | KoNote model |
|--------------|-----------|-------------|
| Counterfactual Evidence (§2) | `cids:Counterfactual` | `EvaluationComponent(counterfactual)` |
| Known Risk Factors (§3) | `cids:ImpactRisk` | `EvaluationComponent(risk)` |
| Measurement Instruments (§4) | `cids:Indicator` | `MetricDefinition` (existing) + `TaxonomyMapping` |

The evaluator enters or uploads results into the Evaluation Framework editor in KoNote during Phase 4 of the protocol.
