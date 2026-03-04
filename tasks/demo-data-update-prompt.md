# Demo Data Update — Session Prompt

**ID:** DEMO-UPDATE1
**Status:** Parking Lot: Ready to Build
**Estimated scope:** Large (seed_demo_data.py is ~47K lines; expect significant edits)

---

## Goal

Update `seed_demo_data.py` to produce a complete, realistic demo environment that showcases **all** of KoNote's current features — including the new client experience metrics, open-text metrics, multi-select demographics, participant portal interactions, and anonymous surveys. The demo should tell coherent stories about 15 participants across 5 programs, with data that looks like it was entered by real frontline workers over 6 months.

## Why This Matters

The demo environment is KoNote's primary sales and training tool. Agency directors, funders, and frontline workers evaluate KoNote by clicking through demo data. Every feature that lacks demo coverage is invisible during evaluation. The recent metric library update (PR #288) added client experience metrics, open-text metrics, and updated demographics that have zero demo representation.

---

## Pre-Work: Read These Files First

Before making any changes, read and understand:

1. **`apps/admin_settings/management/commands/seed_demo_data.py`** — the entire file. Understand CLIENT_PLANS, CLIENT_SUMMARIES, the metric value generation patterns, note structure, and how groups/circles/events/alerts work.
2. **`seeds/metric_library.json`** — all 32 metrics. Know which are scale, achievement, and open_text. Know the scoring bands for PHQ-9/GAD-7/K10. Know the 5 inclusivity items and 2 open-text items.
3. **`seeds/demo_client_fields.py`** — current custom field values for all 15 clients. You'll add demographic data here.
4. **`apps/clients/management/commands/seed_intake_fields.py`** — the demographic field definitions (Gender Identity, Transgender Experience, 2SLGBTQIA+ Identity, Born in Canada, Time in Canada, Indigenous Identity, Racial Identity, Disability, Caregiver Status). You'll need to create values matching these exact option lists.
5. **`apps/clients/management/commands/update_demo_client_fields.py`** — understand how this command syncs demo_client_fields.py to the database.
6. **`tasks/demo-data-engine-guide.md`** — if it exists, read the guide for how the demo engine works.

## Deliverables

### 1. Add Demographic Data to All 15 Demo Clients

**File:** `seeds/demo_client_fields.py`

Add demographic fields to each client's dict in `CLIENT_CUSTOM_FIELDS`. Use the exact option values from `seed_intake_fields.py`. Design for diversity — the 15 clients should represent a realistic cross-section of a Canadian urban nonprofit's participants.

**Distribution guidance:**

| Field | Distribution across 15 clients |
|-------|-------------------------------|
| Gender Identity | ~7 Woman, ~5 Man, ~2 Non-binary and/or gender-diverse, ~1 Prefer not to say |
| Transgender Experience | ~2 Yes, ~11 No, ~1 Unsure or questioning, ~1 Prefer not to say |
| 2SLGBTQIA+ Identity | ~3 Yes, ~10 No, ~1 Unsure or questioning, ~1 Prefer not to say |
| Born in Canada | ~8 Yes, ~6 No, ~1 Prefer not to say |
| Time in Canada | For those born outside: mix of 0-5, 6-10, >10 years |
| Indigenous Identity | ~2 with Indigenous identity (one First Nations, one Métis), rest No or not answered |
| Racial Identity | Diverse: ~3 White, ~2 Black, ~2 South Asian, ~2 East Asian, ~1 Latin American, ~1 Middle Eastern, ~1 Southeast Asian, ~2 mixed/multiple (use multi_select JSON) |
| Disability | ~3 Yes, ~10 No, ~1 Unsure, ~1 Prefer not to say |
| Caregiver Status | ~4 with children, ~2 caring for family member, rest No |

**Important:** Multi-select fields must be stored as JSON arrays: `'["Yes, First Nations"]'` not `"Yes, First Nations"`. The `update_demo_client_fields` command will need to handle this — check whether it already does JSON serialization or if you need to update it.

**Character consistency:** Match demographics to existing client backstories:
- DEMO-010 Amara Diallo (Newcomer, French-speaking from West Africa) → Born in Canada: No, Time: 0-5 years, Racial Identity: ["Black"]
- DEMO-012 Carlos Reyes (Newcomer, Spanish-speaking) → Born in Canada: No, Time: 0-5 years, Racial Identity: ["Latin American"]
- DEMO-005 Kai Dubois (French-speaking) → Could be Métis, Born in Canada: Yes
- DEMO-007 Jayden Martinez → Racial Identity: ["Latin American", "White"] (mixed)
- etc.

### 2. Add Client Experience Metrics to Demo Notes

**File:** `seed_demo_data.py`

Add the 5 inclusivity metrics and 2 open-text metrics to relevant programs. Not every program needs all of them — they're "client experience" metrics that agencies would deploy selectively.

**Recommended metric assignments:**

| Program | Inclusivity items (5) | Open-text impact | Open-text improvement |
|---------|----------------------|------------------|----------------------|
| Supported Employment | Yes (all 5) | Yes | Yes |
| Housing Stability | Yes (all 5) | Yes | Yes |
| Youth Drop-In | 3 of 5 (welcome, respect, help) | Yes | No |
| Newcomer Connections | Yes (all 5) | Yes | Yes |
| Community Kitchen | 3 of 5 (welcome, valued, help) | No | Yes |

**Inclusivity metric values by trend:**
- Improving clients: start at 2-3, end at 3-4
- Struggling clients: fluctuate between 1-3
- Stable clients: consistently 3-4
- Record these in the last 2-3 notes (they're periodic, not every-note metrics)

**Open-text metric values — this is critical for quality:**

Write 2-3 unique open-text responses per client who has them. These should sound like real participant voices — not clinical language, not perfectly grammatical, varying in length and detail. Match the client's story arc:

**"How has taking part in this program changed things for you?"**

Examples by client:
- DEMO-001 Jordan (employment, improving): "I didn't think anyone would hire me but now I have a real resume and I've been to two interviews. My worker helped me practice what to say and I feel way more confident than before."
- DEMO-004 Sam (housing, crisis→improving): "Before I came here I was sleeping in the shelter every night. Now I have my own room in transitional housing. It's not perfect but it's mine and I can close the door."
- DEMO-005 Kai (housing, struggling): "Honestly I'm still stressed about housing. But at least someone is helping me figure out the paperwork. That's more than I had before."
- DEMO-008 Maya (youth, struggling): "I don't know. Sometimes I feel like it helps and sometimes I just don't want to come. But the food is good." [short, ambivalent — matches withdrawn character]
- DEMO-010 Amara (newcomer, improving): "Mon anglais est meilleur maintenant. Je peux aller au magasin et demander de l'aide. Mes enfants sont contents que je comprends leur école." [bilingual response — the character speaks French primarily]
- DEMO-011 Muhammed (newcomer, struggling): "It is very hard. I do not know many people. But my worker is kind." [minimal English, isolated — matches character]

**"How can we improve our program or services?"**

Examples:
- DEMO-001 Jordan: "More evening sessions would help because I can't always take time off work for appointments during the day."
- DEMO-003 Avery: "Everything is good. Maybe more job fairs? The last one was really helpful."
- DEMO-006 Jesse: "The office is hard to get to by bus. If there was a closer location or video calls that would help a lot."
- DEMO-010 Amara: "Plus de services en français s'il vous plaît. Parfois c'est difficile de tout comprendre en anglais."
- DEMO-013 Priya: "We should cook more vegetarian dishes. Not everyone eats meat."

**Write at least 20 unique open-text responses total** (roughly 2 per client who has the metric). They should vary in:
- Length (1 sentence to 3 sentences)
- Tone (grateful, ambivalent, critical, brief, detailed)
- Language (mostly English; 2-3 in French or mixed for newcomer clients)
- Specificity (some mention specific program activities, some are vague)

### 3. Add Participant Portal Data for Jordan (DEMO-001)

Jordan Rivera is the "showcase" client for portal features. Create portal data that tells a coherent story:

**Portal journal entries (ParticipantJournalEntry):**
Create 4-6 journal entries spread over 3 months, showing Jordan's employment journey:

1. (~90 days ago) "Started the program today. Feeling nervous but hopeful. Haven't worked in a while and I'm not sure my skills are up to date."
2. (~60 days ago) "Had my first mock interview. It was harder than I thought but my worker said I did ok for a first try. Need to work on eye contact."
3. (~40 days ago) "Updated my resume today!! It looks so much better than what I had before. Added my volunteer experience which I didn't think counted but apparently it does."
4. (~25 days ago) "Going for a real interview tomorrow. Can't sleep. Keep going over the questions in my head."
5. (~20 days ago) "I GOT THE JOB!!!! Part time at first but they said there might be full time later. I can't believe it."
6. (~5 days ago) "First week of work done. It's tiring but good. My coworkers are nice. Still getting used to the schedule."

**Portal metric self-reports:**
If portal self-reporting is implemented, create some portal-submitted metric values for Jordan:
- "How are you feeling today?" — 3, 3, 4, 4, 5 (improving trend)
- "How ready do you feel for work?" — 2, 3, 3, 4, 5 (clear improvement)
- Self-Efficacy — 2, 3, 4, 4 (growing confidence)

**Portal messages (staff → participant):**
2-3 messages from Casey (demo-worker-1) to Jordan:
1. "Hi Jordan, just a reminder about our appointment on Thursday at 2pm. Let me know if you need to reschedule."
2. "Great job in the mock interview today! I've attached some tips for the real thing. Remember to breathe!"
3. "Congratulations on the job! So proud of you. Let's meet next week to talk about how the first few days went."

### 4. Add Anonymous Survey Response Data

**File:** `seed_demo_survey.py` or `seed_demo_data.py`

The demo survey "Program Feedback" exists but has no filled responses. Create 8-12 anonymous survey responses that look realistic:

- Mix of positive and constructive responses
- Varied rating_scale values (not all 5s — some 3s and 4s for realism)
- Short_text responses that sound like real people
- Some responses partially complete (skipped optional questions)
- Spread across a 2-week period

### 5. Update CLIENT_PLANS Metric Assignments

**File:** `seed_demo_data.py`

For each program's metric list in CLIENT_PLANS, add the client experience metrics from section 2 above. Make sure the metric names exactly match those in `metric_library.json`.

### 6. Update Note Summaries for Client Experience Metrics

When generating full notes that include client experience metrics, the note summary should occasionally reference them naturally:

- "Completed mid-program survey. Jordan rated inclusivity highly — feels welcomed and respected by staff."
- "Did the program feedback form today. Sam mentioned wanting evening sessions and more bus-accessible locations."

These references make the metrics feel integrated into the service delivery, not like an afterthought.

---

## Quality Standards

### Voice and tone
- Participant words should sound like real people, not AI-generated corporate language
- Vary sentence structure, vocabulary, and emotional register
- Some responses should be imperfect, brief, or ambivalent
- French responses from newcomer clients should use conversational Canadian French
- Youth (DEMO-007, 008, 009) should sound like teenagers/young adults

### Data consistency
- Metric values must be plausible for the scale (e.g., 1-4 for inclusivity, text for open_text)
- Metric trends must match the client's story arc (improving clients improve, struggling clients fluctuate)
- Portal entries must be chronologically consistent with note dates
- Demographics must match existing client backstories (names, languages, referral sources)

### Coverage
- Every new metric type (open_text, client_experience) must appear in at least one demo note
- Multi-select demographics must appear on at least 5 clients
- Portal data for Jordan must exercise journal, messages, and self-reporting
- Survey responses must look like different people wrote them

### What NOT to do
- Don't remove or change existing demo data that works — add to it
- Don't use placeholder text like "Lorem ipsum" or "[TODO]"
- Don't make all responses positive — realism requires mixed sentiment
- Don't duplicate the same text across clients — every response should be unique
- Don't use clinical language in participant voices — they're not therapists
- Don't break the existing metric value generation patterns — extend them

---

## Testing After Implementation

1. Run `python manage.py seed_demo_data --demo-mode --force` and verify no errors
2. Log in as Casey (demo-worker-1) — check that:
   - Client profiles show demographic checkboxes populated
   - Progress notes show inclusivity metrics with values
   - Progress notes show open-text metric responses
3. Log in as Jordan (portal) — check that:
   - Journal entries appear in chronological order
   - Messages from Casey appear
   - Self-reported metrics show on the dashboard
4. Visit the anonymous survey link — check that responses exist in the admin
5. Run `pytest tests/test_demo_data_separation.py` — demo/real data isolation intact
6. Check that `update_demo_client_fields` handles JSON array values for multi-select fields

---

## Files to Modify

| File | Changes |
|------|---------|
| `seeds/demo_client_fields.py` | Add demographic data (JSON arrays for multi-select) |
| `apps/admin_settings/management/commands/seed_demo_data.py` | Add client experience metrics to CLIENT_PLANS, add open-text responses, add portal data for Jordan, add survey responses |
| `apps/clients/management/commands/update_demo_client_fields.py` | Ensure JSON array handling for multi-select fields |
| `apps/admin_settings/management/commands/seed_demo_survey.py` | Add anonymous survey response data (or add to seed_demo_data) |
