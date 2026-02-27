# WEB-EVIDENCE1: Add Outcome Measurement Evidence to Website

## Task

Update `evidence.html` in the **konote-website** repo (`c:\Users\gilli\OneDrive\Documents\GitHub\konote-website\`) to incorporate the research foundation for KoNote's outcome measurement system.

## Context

The website already has an Evidence page covering **design principles** (feedback-informed treatment, collaborative documentation, brevity). It needs a second major section covering **outcome measurement** --- the research behind KoNote's targets, metrics, and three-dimensional outcome tracking.

The source content is in the **konote-app** repo at `docs/evidence-outcome-measurement.md` (330 lines, 24 verified academic citations). This is an internal technical document written for an academic audience. It needs to be **adapted** for a public-facing page aimed at nonprofit program managers, funders, and agency decision-makers --- not copied verbatim.

## Source Material

**Read this file first:** `c:\Users\gilli\OneDrive\Documents\GitHub\konote-app\docs\evidence-outcome-measurement.md`

All citations in this document have been verified against Semantic Scholar, CrossRef, PubMed, and OpenAlex (Feb 2026). Use them as-is.

## Website Tech Stack

- **Pure static HTML + CSS** --- no frameworks, no build tools, no npm
- **CSS:** `css/style.css` with custom properties for colours, typography, spacing
- **Patterns already used:** `.card-grid`, `.card`, `.table-wrapper`, `.notice`, `.alt-bg`, `.btn-group`
- **Accessibility:** skip-nav, ARIA labels, semantic HTML, system fonts, focus rings
- **Hosted on GitHub Pages** --- no server-side rendering

## What to Build

### Structure

Add the outcome measurement content **below** the existing "The Research" section in `evidence.html`. The page should flow as:

1. **Existing:** Hero, "Why This Matters", "The Research" (3 cards: FIT, Collaborative Docs, Brevity)
2. **New:** Executive summary of outcome measurement approach (2-minute read)
3. **New:** Research cards for the key constructs (goal-setting, self-report validity, three dimensions)
4. **New:** "How This Shaped KoNote's Metrics" table (like the existing "How This Shaped KoNote" table)
5. **Existing:** "What We're Not Claiming", "Implementation Matters", CTA

### Content Sections to Add

**1. Executive Summary (above the cards)**

A short intro paragraph (3-4 sentences) that says:
- KoNote's metrics aren't arbitrary --- they're built on 50+ years of research
- Three dimensions (Goal Progress, Self-Efficacy, Satisfaction) are empirically distinct
- Every metric is participant self-report, which is the valid methodology for subjective outcomes
- The AI goal builder applies 8 research-grounded criteria to help coaches write better targets

**2. Research Cards (use the existing `.card` pattern)**

Adapt these sections from the evidence doc into plain-language cards. Each card should have:
- A clear heading
- 2-3 paragraphs in plain language (not academic prose)
- A `text-muted` citation block with the key reference(s)

Cards to create:

| Card | Source sections | Key message for audience |
|------|---------------|--------------------------|
| **Specific Goals Work Better** | Goal-Setting Theory (Locke & Latham), SMART Goals (Doran), Behavioural Objectives (Mager) | Vague goals lead to 250% worse performance. KoNote's AI pushes coaches toward specificity because it genuinely helps participants. |
| **Self-Report Is Valid** | Self-Report Validity, Self-Efficacy Theory (Bandura) | For subjective outcomes, participant self-assessment is the gold standard --- not a fallback. What matters is how the question is anchored. |
| **Three Dimensions, Not One** | Three Dimensions of Outcome Measurement, Factor Analysis Evidence | Progress, confidence, and satisfaction are distinct constructs that can diverge in clinically meaningful ways. Each pattern tells the coach something different. |
| **Individualised Measurement** | Goal Attainment Scaling (Kiresuk & Sherman), Practical Tools | KoNote's AI-generated target-specific metrics draw on Goal Attainment Scaling --- each level describes an observable state defined at goal creation. |

**3. Design Decisions Table**

Adapt the "How This Shaped KoNote" table pattern. Include the most compelling design decisions from the evidence doc:

| Research Finding | KoNote Design Response |
|-----------------|------------------------|
| Specific goals produce 250% better outcomes (Locke & Latham) | AI goal builder validates targets against 8 research-grounded criteria |
| Self-efficacy must be domain-specific (Bandura) | Self-efficacy prompt asks about the specific target behaviour, not generic confidence |
| Self-report is gold standard for subjective outcomes (PROMIS) | All three metrics are participant self-report with behaviourally anchored levels |
| Three distinct dimensions emerge in factor analyses | Three universal metrics per target: Goal Progress, Self-Efficacy, Satisfaction |
| "How sure do you feel" is less loaded than "how confident" | Self-efficacy uses softer phrasing that works in trauma-informed practice |
| Independence is a culturally specific value | Goal Progress level 5 says "part of my life" not "independently" |

### Writing Guidelines

- **Audience:** Nonprofit program managers, funders, agency decision-makers --- not researchers
- **Tone:** Confident but honest. Match the existing page's voice --- direct, explains *why* without being preachy
- **Canadian spelling:** colour, centre, behaviour, organisation, program (not programme)
- **No jargon without explanation:** If you use terms like "self-efficacy" or "bifactor model", briefly explain what they mean
- **Keep the "What We're Not Claiming" pattern:** The existing page is honest about what's research vs. what's design. Maintain that tone for the new content too.
- **Length:** Each card should be readable in 30-60 seconds. The whole new section should add ~3 minutes of reading.

### Accessibility Requirements

- Semantic HTML: `<section>`, `<h2>`, `<h3>`, proper heading hierarchy
- All links must have descriptive text (not "click here")
- Tables must have `<thead>` and `<th>` elements
- Maintain alternating `alt-bg` pattern for visual rhythm
- Test with keyboard navigation
- WCAG 2.2 AA colour contrast

### Citations

Include citations in the same `text-muted` pattern used by the existing cards. Key references to include (all verified):

- Locke & Latham (2002). Building a practically useful theory... *American Psychologist, 57*(9), 705-717.
- Doran (1981). SMART goals. *Management Review, 70*(11), 35-36.
- Bandura (2006). Guide for constructing self-efficacy scales. In T. Urdan & F. Pajares (Eds.).
- PROMIS --- NIH Common Fund. commonfund.nih.gov/promis
- Kiresuk & Sherman (1968). Goal attainment scaling. *Community Mental Health Journal, 4*, 443-453.
- Perera et al. (2018). Resolving dimensionality problems with WHOQOL-BREF. *Assessment, 25*(8), 1014-1025.
- Scholz et al. (2002). Is general self-efficacy a universal construct? *European Journal of Psychological Assessment, 18*(3), 242-251.

For the full verified reference list, see `docs/evidence-outcome-measurement.md`.

### What NOT to Do

- Don't copy the evidence doc verbatim --- it's written for an academic audience
- Don't add JavaScript --- the site is pure HTML/CSS
- Don't add external dependencies (Google Fonts, CDNs, etc.)
- Don't change the existing content (FIT, collaborative docs, brevity cards)
- Don't add a separate "References" section at the bottom --- citations go inline with each card
- Don't use "programme" (British) --- use "program" (Canadian English)

## Verification

After building, check:
1. Page validates as HTML5 (`validator.w3.org`)
2. Heading hierarchy is correct (no skipped levels)
3. All links work
4. Page looks right on mobile (responsive)
5. Keyboard navigation works through all interactive elements
6. Alternating sections maintain visual rhythm
7. Commit to konote-website repo, push, and verify on GitHub Pages
