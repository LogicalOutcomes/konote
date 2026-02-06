# Prompt to paste into Jules

Copy everything below the line into the Jules prompt box.

---

## Task: WCAG 2.2 AA Accessibility Review — Create Report

**DO NOT modify any application code.** Your only task is to create a single file:
`tasks/reviews/2026-02-06-accessibility.md`

This file should contain an accessibility review report based on the analysis below.

## Role

You are a WCAG 2.2 AA accessibility specialist with expertise in testing
web applications used by people with diverse abilities. You understand AODA
(Accessibility for Ontarians with Disabilities Act) requirements for software
used by Ontario organisations.

## Application Context

KoNote2 is used by nonprofit caseworkers in Ontario, Canada. The user base
includes:
- Staff with visual impairments (screen readers, magnification)
- Staff with motor impairments (keyboard-only navigation)
- Staff with cognitive disabilities (need clear, simple interfaces)
- Staff with low digital literacy (need obvious affordances)
- Staff working in noisy environments (cannot rely on audio cues)

**Tech stack relevant to accessibility:**
- Server-rendered Django templates (not a JavaScript SPA)
- Pico CSS framework (provides baseline accessibility)
- HTMX for partial page updates (dynamic content concerns)
- Chart.js for data visualisation (canvas-based, accessibility concerns)
- No custom JavaScript framework

**Known accessibility features already implemented:**
- Skip navigation links
- Semantic HTML (header, nav, main, footer)
- Visible focus indicators
- Screen reader announcements for form errors
- aria-live regions for HTMX updates
- Colour contrast meets AA standards (light mode)

## Scope

**Templates to review (all in templates/ directory):**
- base.html (layout, skip links, landmarks)
- components/ (reusable components: nav, forms, modals)
- clients/ (client list, detail, edit forms)
- notes/ (note creation form — most complex form)
- plans/ (plan detail with accordions)
- reports/ (charts, data tables)
- auth/ (login, registration)
- admin/ (admin settings pages)
- 403.html, 404.html, 500.html (error pages)

**JavaScript to review:**
- static/js/app.js (HTMX configuration, dynamic behaviour)

**CSS to review:**
- static/css/main.css (custom styles, colour overrides)

**Out of scope:** Backend Python code (unless it generates HTML directly
in views without templates)

## Checklist

### WCAG 2.2 AA — Perceivable

**1.1 Text Alternatives**
- [ ] All images have meaningful alt text (or alt="" for decorative)
- [ ] Chart.js canvases have aria-label or fallback text description
- [ ] Icons used without text have accessible labels
- [ ] Form controls have associated labels (not just placeholders)

**1.2 Time-Based Media**
- [ ] N/A (no video or audio content)

**1.3 Adaptable**
- [ ] Heading hierarchy is correct (h1 > h2 > h3, no skips)
- [ ] Tables have proper th elements and scope attributes
- [ ] Forms use fieldset/legend for related groups
- [ ] Reading order matches visual order
- [ ] Content is understandable without CSS

**1.4 Distinguishable**
- [ ] Text colour contrast >= 4.5:1 (normal text)
- [ ] Text colour contrast >= 3:1 (large text, 18pt+)
- [ ] Non-text contrast >= 3:1 (borders, icons, focus indicators)
- [ ] Text can be resized to 200% without loss of content
- [ ] No text in images

### WCAG 2.2 AA — Operable

**2.1 Keyboard Accessible**
- [ ] All interactive elements reachable by Tab key
- [ ] Tab order follows logical reading order
- [ ] No keyboard traps (can always Tab away)
- [ ] Focus visible on all interactive elements
- [ ] Custom widgets (accordions, dropdowns) keyboard-operable
- [ ] HTMX-loaded content is keyboard-accessible

**2.2 Enough Time**
- [ ] Session timeout warning before auto-logout
- [ ] User can extend session
- [ ] No content that auto-advances without user control

**2.3 Seizures**
- [ ] No content flashes more than 3 times per second

**2.4 Navigable**
- [ ] Skip navigation link works and is first focusable element
- [ ] Page titles are descriptive and unique
- [ ] Link text is meaningful (no "click here" without context)
- [ ] Multiple ways to find pages (nav, search, breadcrumbs)
- [ ] Focus indicator is visible and high-contrast

**2.5 Input Modalities**
- [ ] Touch targets are at least 24x24 CSS pixels (WCAG 2.2)
- [ ] No functionality requires specific gestures (pinch, swipe)
- [ ] Drag-and-drop has keyboard alternative

### WCAG 2.2 AA — Understandable

**3.1 Readable**
- [ ] Page language declared (lang="en" on html element)
- [ ] Language changes within page are marked (lang="fr" on French text)

**3.2 Predictable**
- [ ] Focus changes don't cause unexpected navigation
- [ ] Form submission doesn't auto-redirect without warning
- [ ] HTMX content updates don't move focus unexpectedly

**3.3 Input Assistance**
- [ ] Form errors are announced to screen readers (aria-live)
- [ ] Error messages identify which field has the error
- [ ] Required fields are indicated (not just by colour)
- [ ] Error suggestions help the user fix the problem
- [ ] Confirmation before destructive actions (delete, erasure)

### WCAG 2.2 AA — Robust

**4.1 Compatible**
- [ ] HTML validates (no duplicate IDs, proper nesting)
- [ ] ARIA roles and states used correctly
- [ ] HTMX dynamic content triggers screen reader announcements
- [ ] Name, role, value exposed for all custom controls

### HTMX-Specific Accessibility

- [ ] HTMX swap targets have aria-live="polite" or aria-live="assertive"
- [ ] Loading indicators are announced to screen readers
- [ ] Swapped content does not steal focus unless appropriate
- [ ] Error responses from HTMX are announced (htmx:responseError handler)
- [ ] HTMX-loaded forms are properly labelled

### Chart.js Accessibility

- [ ] Each chart has a text description or data table alternative
- [ ] Colour is not the only way to distinguish data series
- [ ] Chart data is available in a non-visual format

## Output Format

Write the report in markdown with the following structure:

### Summary

| Category | Issues Found | Critical | High | Medium | Low |
|----------|-------------|----------|------|--------|-----|
| Perceivable | | | | | |
| Operable | | | | | |
| Understandable | | | | | |
| Robust | | | | | |
| **Total** | | | | | |

WCAG 2.2 AA Compliant: Yes / No / With Fixes

### Findings

For each finding:
**[SEVERITY-NUMBER] Title**
- WCAG Criterion: X.X.X Level AA
- Location: template_file.html:line or description
- Issue: What fails the criterion
- Impact: Who is affected (screen reader users, keyboard users, etc.)
- Fix: Specific HTML/CSS/JS change needed
- Test: How to verify (tool or manual test)

### Testing Notes
Tools used or recommended:
- axe DevTools (browser extension)
- WAVE (web accessibility evaluator)
- NVDA or JAWS screen reader testing
- Keyboard-only navigation testing
- Colour contrast checker

### Recommendations
Improvements beyond AA compliance
