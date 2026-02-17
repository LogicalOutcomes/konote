# Insights Report — Suggestions & Charts Improvements

## Issues Identified

### 1. BUG: Suggestion count doesn't match displayed suggestions (UX-INSIGHT2)

**What's happening:** The header might say "18 suggestions, 5 important" but only 4 suggestions are shown. This is confusing and makes it look like the calculations are wrong.

**Root cause:** Two different data sources:
- The count (`suggestion_total` / `suggestion_distribution`) comes from SQL aggregation of `suggestion_priority` — it counts ALL notes that have a suggestion priority set, regardless of text length
- The displayed suggestions come from `collect_quotes()` which filters out suggestions shorter than 5 words (`word_count >= 5`)
- So a suggestion marked "Important" but with only 3 words (e.g., "More evening sessions") gets counted in the "Important: 5" pill but never displayed as a blockquote

**Fix options:**
- **Option A:** Show all suggestions regardless of word count (remove the 5-word minimum for suggestions — it makes sense for general quotes but not for actionable suggestions)
- **Option B:** Adjust the count to only count suggestions that will actually be displayed
- **Option C (recommended):** Option A + show short suggestions in a compact format (bullet list instead of blockquote) so they don't look sparse

### 2. Charts need plain-language descriptions (UX-INSIGHT3)

**What's happening:** The Progress Trend chart and other visualisations are shown without explanation. A coordinator or coach looking at this might not understand what the lines mean or what to take away.

**What to add:**
- A brief sentence below each chart heading explaining what it shows in plain language
- Example for Progress Trend: "This shows how participants described their progress each month. Rising green ('In a good place') and falling red ('Harder right now') lines generally mean the program is helping."
- Example for Engagement: "How actively participants have been taking part, based on what staff recorded in their notes."
- Example for Suggestions: "Ideas and requests that came up during sessions. Staff record these when participants mention something they'd like to change."

### 3. AI-driven plain-language interpretation below charts (UX-INSIGHT4)

**What's happening:** Charts are visual, but not everyone finds them intuitive. Some people understand things better when they read a sentence like "Most participants are reporting steady or improving progress this quarter."

**What to add:**
- After each chart section, an AI-generated paragraph that describes what the data shows in plain words
- This could be part of the existing "Draft report summary" AI feature, but shown inline rather than requiring a button click
- Alternatively, a simpler non-AI approach: template-driven sentences based on the data (e.g., if `good_place` percentage is rising, show "The proportion of participants reporting they're 'in a good place' has increased over this period.")
- Consider offering both: auto-generated simple interpretations always visible, plus the deeper AI narrative on request

### 4. Surface important suggestions to Executive Dashboard (UX-INSIGHT5)

**Future feature.** Currently the executive dashboard shows aggregate numbers but no suggestions. If multiple participants are asking for similar things (e.g., "evening sessions", "childcare", "more one-on-one time"), that's valuable information for leadership.

**Design considerations:**
- **Consolidation:** Group similar suggestions together (AI-assisted clustering or simple keyword matching)
- **Threshold:** Only surface suggestions that appear 3+ times across participants, or are marked "Important" or "Urgent"
- **Privacy:** Executive dashboard must not reveal individual participant identity — show suggestion themes, not individual quotes
- **Display:** A "Top Suggestions This Quarter" section showing 3-5 themes with counts (e.g., "Evening availability (mentioned by 7 participants)", "Childcare support (4 participants)")
- **Connection to PORTAL-Q1:** If the "Questions for You" survey feature (PORTAL-Q1) is built, structured survey responses could also feed into suggestion consolidation

### 5. Suggestion tracking and consolidation system (UX-INSIGHT6)

**Bigger-picture design question:** How should suggestions be tracked over time?

**Current state:** Suggestions are recorded per-note, tagged with a priority, and surfaced in Insights. But there's no way to:
- Mark a suggestion as "addressed" or "in progress"
- See the same suggestion recurring across multiple participants
- Track whether action was taken

**Possible future approach:**
- When a suggestion is marked "Important" or "Urgent", create a trackable item (like a lightweight issue/ticket)
- AI groups similar suggestions and shows them as a single theme with a count
- Program managers can mark themes as "Reviewed", "In Progress", or "Addressed"
- This creates a feedback loop: participant suggests → staff records → PM reviews → action taken → participant sees change
