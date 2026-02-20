# Evidence Base: Outcome Measurement in KoNote

This document explains the research foundations behind how KoNote designs targets, metrics, and outcome measurement. It complements the [Design Principles](design-principles.md) document, which covers the philosophy of collaborative documentation and participant engagement.

---

## The Problem with Vague Goals

A target like "build confidence with English" fails on multiple fronts: it has no observable behaviour, no measurement scale, no threshold for success, and no timeframe. Research consistently shows this leads to worse outcomes --- not just worse measurement, but worse actual participant progress.

### Goal-Setting Theory (Locke & Latham)

The most cited goal-setting research in psychology. Meta-analyses across 35 years showed that specific, difficult goals led to **250% higher performance** than vague "do your best" goals. Effect sizes ranged from .42 to .80. Four mechanisms: goals direct attention, energise effort, increase persistence, and trigger strategy development.

This is why KoNote's AI goal builder pushes coaches toward specificity --- it isn't pedantic, it produces materially better participant outcomes.

**References:**

- Locke, E.A. & Latham, G.P. (1990). *A Theory of Goal Setting & Task Performance.* Prentice-Hall.
- Locke, E.A. & Latham, G.P. (2002). Building a practically useful theory of goal setting and task motivation: A 35-year odyssey. *American Psychologist, 57*(9), 705--717.
- Locke, E.A. & Latham, G.P. (2006). New directions in goal-setting theory. *Current Directions in Psychological Science, 15*(5), 265--268.

---

## How to Write a Measurable Target

### SMART Goals (Doran, 1981)

Goals should be Specific, Measurable, Assignable, Realistic, and Time-related. This is the most widely adopted framework in social services and the baseline KoNote uses for target descriptions.

- Doran, G.T. (1981). There's a S.M.A.R.T. way to write management's goals and objectives. *Management Review, 70*(11), 35--36.

### Behavioural Objectives (Mager, 1962/1997)

A more rigorous three-part structure than SMART. Every objective must specify:

1. **Performance** --- what the participant will do (observable verb)
2. **Condition** --- under what circumstances (with or without support)
3. **Criterion** --- the minimum acceptable standard (accuracy, quality, frequency)

*Example:* "Participant will complete a phone call to book a medical appointment (performance) without interpreter assistance (condition) successfully conveying symptoms and receiving a confirmed appointment (criterion)."

KoNote's AI applies this three-part test when generating SMART outcome statements. If a target is missing any component, the AI prompts the coach to add it.

- Mager, R.F. (1997). *Preparing Instructional Objectives: A Critical Tool in the Development of Effective Instruction* (3rd ed.). Center for Effective Performance.

---

## Measuring Subjective Outcomes: Why Self-Report Is Valid

A common concern is that self-report metrics are "soft" or less reliable than objective measures. The evidence says otherwise.

### When Self-Report Is the Gold Standard

For subjective experiences --- pain, confidence, satisfaction, perceived progress --- the participant's own report is not a fallback. **It is the primary valid measure.** There is no external measurement that is more valid than the participant's own assessment of their subjective state.

This is well-established in healthcare:

- The **Numeric Rating Scale** for pain (0--10) is the gold standard in clinical trials. Pain is irreducibly subjective; asking the person experiencing it is the correct methodology.
- The **NIH PROMIS** (Patient-Reported Outcomes Measurement Information System) --- the most comprehensive patient-reported outcome framework ever built --- is explicitly founded on participant self-report as the primary data source for subjective constructs. PROMIS self-efficacy item banks have been validated with Cronbach's alphas of .85--.97 across five domains.

The same logic applies to constructs like confidence, satisfaction, and perceived progress. A participant rating "How confident are you that you can cook a healthy meal independently?" on a 1--5 scale with behaviourally described levels is producing **valid, reliable data**.

**What makes self-report valid is not who reports, but how the question is anchored.** The problem with a vague metric like "How confident do you feel?" (generic, unanchored) is not that it's self-report --- it's that it's not domain-specific and the levels don't describe anything concrete.

**References:**

- [PROMIS --- NIH Common Fund](https://commonfund.nih.gov/promis)
- [Validation of the PROMIS Self-Efficacy Measures](https://pmc.ncbi.nlm.nih.gov/articles/PMC5479750/)
- [Response scale selection in adult pain measures](https://pmc.ncbi.nlm.nih.gov/articles/PMC6127068/)
- [Pain self-report as gold standard debate](https://pubmed.ncbi.nlm.nih.gov/25370143/)

---

## How to Measure "Confidence" Properly

### Self-Efficacy Theory (Bandura, 1977, 2006)

"Confidence" in the research literature is properly called **self-efficacy** --- a person's belief in their ability to perform specific tasks. Bandura's key insight: self-efficacy must be measured **domain-specifically**, not generically. You can't just ask "are you confident?" --- you must ask about specific tasks at escalating difficulty levels.

A generic "Confidence" metric (1--5, "How confident do you feel about this?") violates this principle directly. A domain-specific self-efficacy question ("How confident are you that you can [specific target behaviour]?") follows it.

- Bandura, A. (1977). Self-efficacy: Toward a unifying theory of behavioral change. *Psychological Review, 84*(2), 191--215.
- Bandura, A. (2006). Guide for constructing self-efficacy scales. In F. Pajares & T. Urdan (Eds.), *Self-efficacy beliefs of adolescents* (pp. 307--337). Information Age Publishing.
- Schwarzer, R. & Jerusalem, M. (1995). Generalized Self-Efficacy Scale. Validated across 25 countries with ~20,000 participants.

---

## Individualised Outcome Measurement

### Goal Attainment Scaling (Kiresuk & Sherman, 1968)

The gold standard for individualised outcome measurement in social and health services. Each participant's goals are scaled on a 5-point continuum:

| Level | Description |
|-------|-------------|
| -2 | Much worse than expected |
| -1 | Somewhat less than expected |
| 0 | Expected level of attainment |
| +1 | Somewhat more than expected |
| +2 | Much more than expected |

The key innovation: the "expected" level (0) is defined collaboratively with the participant in concrete, observable terms before the intervention begins.

KoNote's AI-generated target-specific metrics draw on this approach --- each level describes an observable state, defined at goal creation.

- Kiresuk, T.J. & Sherman, R.E. (1968). Goal attainment scaling: A general method for evaluating comprehensive community mental health programs. *Community Mental Health Journal, 4*, 443--453.
- Kiresuk, T.J., Smith, A., & Cardillo, J.E. (Eds.) (1994). *Goal Attainment Scaling: Applications, Theory, and Measurement.* Lawrence Erlbaum.

---

## The Three Dimensions of Outcome Measurement

KoNote's universal metrics are designed around three empirically distinct dimensions that consistently emerge in factor analyses of outcome measurement frameworks.

### Factor Analysis Evidence

Multiple validated frameworks converge on these three dimensions:

| Dimension | Framework evidence | What it captures |
|-----------|-------------------|-----------------|
| **Functional status** (what the person is *doing*) | Wilson & Cleary model level 3; Recovery Star two-factor solution (48% variance); Prochaska's Transtheoretical Model stages of change | Observable behaviour, stage of change, action taken |
| **Self-efficacy** (what the person *believes they can do*) | Bandura (1977, 2006); PROMIS Self-Efficacy banks (5 domains, Cronbach's alpha .85--.97); Schwarzer GSE (25 countries) | Domain-specific perceived capability |
| **General perception** (how the person *feels about* their situation) | WHOQOL-BREF bifactor model (general QoL factor + domain factors); Wilson & Cleary model level 4; GAS client-meaningful criterion | Subjective appraisal, satisfaction |

**Are these three actually independent?** The literature shows they are moderately correlated (.3--.5) but factorially distinct. This is exactly what you want --- they should move together broadly, but they can diverge in clinically meaningful ways:

- **High progress + low self-efficacy** = "I'm doing it but I don't trust myself yet" (fragile change, needs encouragement)
- **High self-efficacy + low progress** = "I know I can but I haven't started" (motivation or barrier issue)
- **High progress + low satisfaction** = "I'm doing what was planned but it's not what I actually need" (misaligned goal --- revisit the target)

Each divergence pattern tells the coach something different. That is the diagnostic value of measuring three distinct dimensions rather than one.

**Key references:**

- Wilson, I.B. & Cleary, P.D. (1995). [Linking clinical variables with health-related quality of life: A conceptual model of patient outcomes.](https://pubmed.ncbi.nlm.nih.gov/7996652/) *JAMA, 273*(1), 59--65.
- [Recovery Star: Validating user recovery](https://www.cambridge.org/core/journals/the-psychiatrist/article/recovery-star-validating-user-recovery/1D1F193ED6EF820A778AA04972A17B1B) --- Two-factor structure, 48% variance.
- Prochaska, J.O. & Velicer, W.F. (1997). [The transtheoretical model of health behavior change.](https://pubmed.ncbi.nlm.nih.gov/10170434/) *American Journal of Health Promotion, 12*(1), 38--48.
- [WHOQOL-BREF: Bifactor model analysis](https://pmc.ncbi.nlm.nih.gov/articles/PMC3395923/)

---

## KoNote's Universal Metrics

Based on the evidence above, KoNote uses three universal metrics for every target. All three are participant self-report --- the valid methodology for subjective constructs.

### 1. Goal Progress

*What the participant is doing.*

Measures the participant's stage of behaviour change using generic action stages that apply consistently across all target types.

| Level | Description |
|-------|-------------|
| 1 | Haven't started working on this yet |
| 2 | Exploring or learning about this |
| 3 | Practising or trying this out |
| 4 | Doing this regularly or consistently |
| 5 | Doing this independently --- it's part of my life now |

**Construct basis:** Prochaska's Transtheoretical Model (stages of change); Wilson & Cleary functional status level; Mager's observable performance criterion.

**Why these stages work across targets:** Whether the goal is cooking, job searching, managing anxiety, or learning English, the progression from "haven't started" through "exploring" to "doing it independently" describes the same underlying dimension of behaviour change. This makes the metric aggregatable across participants and targets for program-level reporting.

### 2. Self-Efficacy

*What the participant believes they can do.*

Domain-specific confidence, referenced to the specific target behaviour.

Prompt: "How confident are you that you can [target-specific behaviour]?"

| Level | Description |
|-------|-------------|
| 1 | Not at all --- I don't think I can do this |
| 2 | A little --- I might be able to with a lot of help |
| 3 | Somewhat --- I can do this with support |
| 4 | Quite --- I can usually do this on my own |
| 5 | Very --- I'm sure I can do this |

**Construct basis:** Bandura's self-efficacy theory (1977, 2006); PROMIS Self-Efficacy item banks (validated, alpha .85--.97); Schwarzer & Jerusalem GSE (25 countries, ~20,000 participants).

**Why domain-specific matters:** Bandura's 2006 guide explicitly states that self-efficacy scales must reference specific behaviours, not general confidence. "How confident do you feel about this?" is too vague. "How confident are you that you can [cook a healthy meal / complete a job application / manage your anxiety when it arises]?" produces valid, reliable data.

### 3. Satisfaction

*How the participant feels about their situation in this area.*

Captures the participant's subjective appraisal --- whether the change matters to them and whether they feel good about how things are going.

Prompt: "How satisfied are you with how things are going in this area?"

| Level | Description |
|-------|-------------|
| 1 | Very unsatisfied |
| 2 | Unsatisfied |
| 3 | Neutral --- it's okay |
| 4 | Satisfied |
| 5 | Very satisfied |

**Construct basis:** Wilson & Cleary general health perceptions level; WHOQOL-BREF general quality-of-life factor; GAS client-meaningful criterion; Outcome Star's emphasis on participant-defined outcomes.

**Why satisfaction is distinct from progress and self-efficacy:** A participant can be making progress (doing the behaviour) and feel confident (believe they can do it) but still be unsatisfied --- because the goal wasn't what they actually wanted, or because external circumstances overshadow their progress. Satisfaction captures the participant's voice about whether the change is meaningful to them. This is essential for person-centred practice and for identifying misaligned goals early.

### Target-Specific Metrics (Optional)

In addition to the three universal metrics, KoNote's AI can generate a **target-specific metric** with richer behavioural anchors for each target. This is a simplified Goal Attainment Scale --- each level describes an observable state specific to the target content.

*Example for "Cook healthy meals independently":*

| Level | Description |
|-------|-------------|
| 1 | Haven't tried cooking yet |
| 2 | Have watched someone cook or looked at recipes |
| 3 | Have cooked a simple meal with help |
| 4 | Cook a few meals per week on my own |
| 5 | Plan and cook healthy meals for the week independently |

Target-specific metrics are participant-rated and optional. Coaches can accept, edit, or decline them. The universal metrics always provide a valid baseline; the target-specific metric adds granularity where coaches want it.

---

## Validation Criteria for Targets

KoNote's AI applies these eight criteria when helping coaches write targets. Each criterion is grounded in the research above.

| Criterion | Source | Test |
|-----------|--------|------|
| Observable behaviour | Mager (1962) | Does the target use an action verb you can see or hear? |
| Specific, not vague | Locke & Latham (2002) | Would two people agree on whether this was achieved? |
| Measurable indicator | Bandura (2006), GAS | Is there a scale, score, count, or threshold? |
| Conditions stated | Mager (1962) | Under what circumstances? With or without support? |
| Success threshold | Mager (1962), SMART | What level counts as "met"? |
| Time-bound | Doran (1981) | By when? |
| Causally linked | Weiss (1995) | Does achieving this plausibly lead to the participant's larger goal? |
| Participant-meaningful | GAS, Outcome Star | Did the participant help define this, and does it matter to them? |

### Example

A coach enters: *"Build confidence with English."*

KoNote's AI would guide them toward something like:

> *"By September 2026, participant will independently complete a phone call to schedule a medical appointment in English without interpreter support, and will self-rate their speaking confidence at 4/5 or higher on the self-efficacy scale (up from current 2/5)."*

This version has an observable behaviour, a condition (without interpreter), a self-efficacy measure with baseline and target, a timeframe, and is clearly linked to the larger goal of community integration.

---

## Practical Tools in Social Services

Several validated tools informed KoNote's approach:

### Outcome Star (Burns & MacKeith, 2006 onwards)

Developed by Triangle Consulting Social Enterprise. Embeds outcome measurement within person-centred support. Measures both soft outcomes (attitudes, skills, behaviour change) and hard outcomes (employment, housing status). The Recovery Star's two-factor structure (explaining 48% of variance) supports measuring both action and perception dimensions.

- [Outcomes Star](https://www.outcomesstar.org.uk/about-triangle/our-approach-to-outcomes/)

### Soft Outcomes and Distance Travelled (Dewson et al., 2000)

Published by the UK Institute for Employment Studies for the European Social Fund. Defines "distance travelled" as the measurable progress a participant makes toward a hard outcome, even when they haven't achieved it yet. This concept underpins KoNote's Goal Progress metric --- it captures forward movement through stages, not just final achievement.

- Dewson, S., Eccles, J., Tackey, N.D., & Aston, J. (2000). *Guide to Measuring Soft Outcomes and Distance Travelled.* Institute for Employment Studies.
- Barnes, S.A. & Wright, S. (2019). *Measuring Distance Travelled and Soft Outcomes for Long-Term Unemployed People.* Warwick Institute for Employment Research / European Commission.

### Results-Based Accountability (Friedman, 2005)

Distinguishes population accountability (community-level results) from performance accountability (did this program work?). For program-level targets, asks three questions: How much did we do? How well did we do it? Is anyone better off? KoNote's three universal metrics map to these questions: Goal Progress (is anyone better off?), Self-Efficacy (how well --- are participants gaining capability?), Satisfaction (does it matter to them?).

- Friedman, M. (2005). *Trying Hard Is Not Good Enough: How to Produce Measurable Improvements for Customers and Communities.* FPSI Publishing.

### Theory of Change (Weiss, 1995)

Each target should connect to a clear causal chain: activities leads to outputs leads to intermediate outcomes leads to long-term outcomes. A target is only meaningful if you can articulate why achieving it leads to the participant's ultimate goal.

- Weiss, C.H. (1995). Nothing as practical as good theory: Exploring theory-based evaluation for comprehensive community initiatives for children and families. In J.P. Connell et al. (Eds.), *New Approaches to Evaluating Community Initiatives.* Aspen Institute.

### Canadian Language Benchmarks (CLB)

For Ontario settlement agencies, the Canadian Language Benchmarks provide a 12-level descriptive scale with "can-do" performance descriptors across listening, speaking, reading, and writing. Instead of "build confidence with English," a proper target would reference CLB levels:

> *"Participant will advance from CLB Level 3 to CLB Level 4 in speaking, as assessed by PBLA portfolio tasks, within 6 months."*

---

## Summary

KoNote's outcome measurement approach is built on three principles:

1. **Specificity produces better outcomes.** Vague goals lead to 250% worse performance (Locke & Latham). The AI enforces specificity not as bureaucratic rigour, but because it genuinely helps participants.

2. **Self-report is valid methodology.** For subjective constructs, the participant's own assessment is the gold standard (PROMIS, pain measurement literature). What makes it valid is domain-specific anchoring, not external observation.

3. **Three distinct dimensions capture the full picture.** Goal Progress (action), Self-Efficacy (capability belief), and Satisfaction (subjective appraisal) are empirically distinct constructs that move together but diverge in clinically meaningful ways.

---

**KoNote** --- Participant Outcome Management

*Measurement that serves participants, not just funders.*
