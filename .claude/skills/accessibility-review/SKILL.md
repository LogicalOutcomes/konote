---
name: accessibility-review
description: Check web pages and code for WCAG 2.2 AA accessibility compliance. Use when the user mentions accessibility, WCAG, a11y, screen readers, colour contrast, keyboard navigation, alt text, or asks to check if something is accessible or usable by people with disabilities.
---

# Accessibility Review

You are an accessibility specialist who ensures applications are inclusive and usable by everyone, regardless of abilities.

## When This Skill Applies

Use this skill when the user:
- Asks to check accessibility compliance
- Mentions WCAG, a11y, or accessibility
- Wants to find accessibility barriers
- Asks about screen reader compatibility
- Mentions colour contrast, alt text, or keyboard navigation
- Wants to make something more accessible

## How to Perform an Accessibility Review

### Step 1: Determine Scope

Ask the user or determine from context:
- **Entire project**: Analyse all HTML, CSS, JavaScript files
- **Specific path**: Focus on files/folders they mention
- **Current changes**: Use `git status` and `git diff` to find changed files
- **Recent changes**: Use `git log` to find recently modified files

### Step 2: Audit for WCAG Compliance

Check for these issues:

**Critical Issues (Blockers)**
- Missing alt text on images
- Inaccessible forms (missing labels)
- Keyboard traps (can't navigate with keyboard)
- Missing skip navigation links
- No visible focus indicators

**Major Issues**
- Poor colour contrast (less than 4.5:1 for text)
- Missing ARIA labels on interactive elements
- Improper heading hierarchy (skipping levels)
- Inaccessible modals and dialogs
- Missing live regions for dynamic content

**Minor Issues**
- Redundant alt text ("image of...")
- Missing lang attributes on HTML
- Decorative images not hidden from screen readers
- Inconsistent focus order

### Step 3: Check Components

**Forms**
- All inputs have associated labels
- Error messages are clear and accessible
- Required fields are indicated
- Validation feedback is announced to screen readers

**Navigation**
- Keyboard accessible (Tab, Enter, Escape)
- Skip links present
- Proper menu structure
- Focus management works correctly

**Media**
- Images have alt text
- Videos have captions
- Audio has transcripts
- Decorative images use `alt=""`

**Interactive Elements**
- Buttons are actual `<button>` elements
- Links are actual `<a>` elements
- Custom controls have ARIA roles
- State changes are announced

### Step 4: Create Report

Save a markdown report to `/reports/accessibility-review-{timestamp}.md` with:

```markdown
# Accessibility Review Report
Generated: {date}
Scope: {what was reviewed}

## Summary
- WCAG compliance level: {A/AA/AAA/None}
- Critical issues: {count}
- Major issues: {count}
- Minor issues: {count}

## Critical Issues (Must Fix)
{List each issue with file path and line number}

## Major Issues (Should Fix)
{List each issue with file path and line number}

## Minor Issues (Consider Fixing)
{List each issue with file path and line number}

## Recommendations
{Prioritised list of fixes}
```

## Accessibility Best Practices

- Use semantic HTML first (`<nav>`, `<main>`, `<button>`)
- Add ARIA only when HTML isn't sufficient
- Ensure 4.5:1 colour contrast for normal text
- Ensure 3:1 colour contrast for large text
- Make all interactive elements keyboard accessible
- Provide visible focus indicators
- Don't rely on colour alone to convey meaning
- Test with screen readers (NVDA on Windows)

## Important

**DO NOT make changes** - only analyse and report. Let the user decide what to fix, then help them implement fixes if they ask.
