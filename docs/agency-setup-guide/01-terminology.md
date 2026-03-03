# 01 — Terminology

## What This Configures

KoNote lets you change the words used throughout the entire system so it matches how your agency talks. Instead of "Client," your team might say "Participant" or "Member." Instead of "Program," you might say "Service" or "Initiative." These changes apply immediately to every screen, menu, form, and report.

## Decisions Needed

1. **What do you call the people you serve?**
   - "Participant" → default; neutral, widely used in community services
   - "Client" → common in counselling and social work
   - "Member" → common in drop-in centres and community organisations
   - "Learner" → common in education and training programs
   - "Coaching Client" → common in financial coaching
   - Default: "Participant" (appears everywhere — search bar, navigation, file headers, reports)

2. **What do you call your service lines?**
   - "Program" → default; maps to distinct funding streams or service areas
   - "Service" → common when services are less formally structured
   - "Stream" or "Initiative" → common in larger organisations
   - Default: "Program"

3. **What do you call a specific outcome a participant works toward?**
   - "Target" → default; precise and measurable
   - "Goal" → most intuitive for participants and staff
   - "Objective" → common in logic models and evaluation frameworks
   - "Milestone" → common when tracking incremental progress
   - Default: "Target" (appears in plans, note entry forms, progress charts, reports)

4. **What do you call the collection of goals for a participant?**
   - "Plan" → default; simple and clear
   - "Action Plan" → emphasises participant-driven actions
   - "Support Plan" → emphasises the agency's role
   - "Coaching Plan" → common in coaching agencies
   - "Service Plan" → common in social services
   - Default: "Plan"

5. **What do you call the documentation of a session or contact?**
   - "Note" → default; simple
   - "Session Note" → emphasises in-person meetings
   - "Progress Note" → emphasises outcome tracking
   - "Contact Note" → emphasises any form of contact
   - Default: "Note" (appears in note lists, creation forms, participant file tabs)

6. **What do you call a quick, informal contact record?**
   - "Quick Note" → default; lightweight phone/text/email log entries
   - "Contact Log" → more formal
   - Default: "Quick Note"

7. **Will the system be bilingual (English and French)?**
   - Yes → you will need to provide French translations for each customised term
   - No → English only; French fields can be left blank
   - Default: English only. Each term has separate English and French fields. If French is left blank, the English value is used.

## Common Configurations

- **Financial coaching agency:** Client = "Participant," Program = "Program," Target = "Goal," Plan = "Action Plan," Note = "Session Note," bilingual = No
- **Community counselling agency:** Client = "Client," Program = "Program," Target = "Goal," Plan = "Support Plan," Note = "Progress Note," bilingual = No
- **Settlement services agency:** Client = "Client," Program = "Service," Target = "Objective," Plan = "Service Plan," Note = "Note," bilingual = Yes (EN + FR)
- **Youth drop-in centre:** Client = "Member," Program = "Program," Target = "Goal," Plan = "Plan," Note = "Note," bilingual = No

## Output Format

Terminology is applied through the KoNote admin interface or through the `apply_setup` management command using a JSON configuration file.

**Admin interface steps:**
1. Click the gear icon, then "Terminology"
2. Edit each term as needed
3. Click "Save" — changes apply immediately across the entire interface

**JSON configuration (for `apply_setup`):**

```json
{
  "terminology": {
    "client": "Participant",
    "client_plural": "Participants",
    "program": "Program",
    "program_plural": "Programs",
    "target": "Goal",
    "target_plural": "Goals",
    "plan": "Action Plan",
    "plan_plural": "Action Plans",
    "progress_note": "Session Note",
    "progress_note_plural": "Session Notes",
    "quick_note": "Quick Note",
    "quick_note_plural": "Quick Notes"
  }
}
```

If bilingual, add French translations:

```json
{
  "terminology": {
    "client": "Participant",
    "client_fr": "Participant(e)",
    "client_plural": "Participants",
    "client_plural_fr": "Participant(e)s",
    "target": "Goal",
    "target_fr": "Objectif",
    "target_plural": "Goals",
    "target_plural_fr": "Objectifs"
  }
}
```

## Dependencies

- **Requires:** Nothing — terminology has no dependencies and can be done first
- **Feeds into:** Every other configuration step. Terms appear throughout plans, notes, reports, and the participant portal. Set terminology before showing the system to staff.

## Example: Financial Coaching Agency

**Decisions:**
- People served: "Participant" (matches funder language)
- Service lines: "Program" (standard)
- Outcomes: "Goal" (participants understand this intuitively)
- Collection of goals: "Action Plan" (emphasises participant ownership)
- Session documentation: "Session Note" (matches coaching language)
- Quick contacts: "Quick Note" (default is fine)
- Bilingual: No (English-only agency)

**Rationale:** This agency chose "Goal" over "Target" because their coaching model centres on participant-driven language. "Action Plan" reinforces that the participant owns the plan. "Session Note" makes it clear that notes document coaching sessions, not just any contact.

**Result:** Throughout the system, coaches see "Create a new Session Note," "Review Action Plan," and "Add a Goal" — language that feels natural to their work.
