# 05 — Surveys & Metrics

## What This Configures

What your agency measures, how you measure it, and what assessment tools you use. Metrics are standardised measurements attached to participant goals (e.g., "Financial Capability Score," "Housing Stability Index," "PHQ-9 Score"). Surveys are structured questionnaires assigned to participants or shared through public links. Together, they form the foundation for outcome tracking and funder reporting.

## Decisions Needed

### Outcome Metrics

1. **Which metrics from the built-in library does your organisation already use?**
   - KoNote ships with a library of metrics covering mental health, housing, employment, substance use, youth, and general categories
   - Walk through the library category by category. Enable the ones you use, disable the rest.
   - Default: All built-in metrics are available but can be individually enabled or disabled

2. **What does your funder require you to report on?**
   - Match funder-required outcome measures to existing metrics in the library
   - Flag any gaps where a required measure is not in the library — these become custom metrics
   - Default: No funder-specific configuration until you identify requirements

3. **Do you use any standardised assessment tools?**
   - For financial empowerment agencies: financial capability scales, income change tracking, employment status measures, housing stability indices, wellbeing measures
   - For counselling agencies: PHQ-9 (depression), GAD-7 (anxiety), outcome rating scales
   - For youth services: developmental assets, educational engagement, life skills assessments
   - Default: None pre-configured; enable from library or create custom

4. **Are there outcomes specific to your organisation that are not in the library?**
   - If yes, create custom metrics. For each, you will need:
     - Name (what staff see when recording outcomes)
     - Definition (how to score or measure it — guides consistent data entry)
     - Category (how it is grouped: mental health, housing, employment, substance use, youth, general, or custom)
     - Min/max values (valid range, e.g., 0-10 or 0-27)
     - Unit (label for the value: score, days, percentage, dollars)
   - Default: No custom metrics until you define them

5. **How do you want to review and set up metrics — one by one, or all at once?**
   - **CSV workflow (recommended for initial setup):** Export the full metric library to CSV, review and edit in a spreadsheet, re-import with changes. This lets you see everything at once and make bulk decisions.
   - **One at a time:** Add or edit metrics individually through the admin interface
   - Default: Either approach works; CSV is faster for initial setup

### Surveys

6. **Do you need structured feedback forms (surveys)?**
   - Yes → enable the Surveys feature (if not already enabled in Document 02)
   - No → skip this section
   - Default: Surveys feature is off by default

7. **What surveys will you use?**
   - Common types: client satisfaction survey, intake assessment, program feedback, exit survey, follow-up check-in
   - For each survey, decide:
     - Will it be anonymous? (responses not linked to a participant file)
     - Should participants see their scores after submitting?
     - Should it be visible in the participant portal (if enabled)?
   - Default: Staff-assigned, non-anonymous, scores hidden from participants

8. **Should surveys be assigned automatically?**
   - Yes → set up trigger rules:
     - **Event-based:** assign a survey when a specific event occurs (e.g., intake survey at enrolment)
     - **Time-based:** assign a survey after a set number of days (e.g., follow-up survey 90 days after enrolment)
     - **Enrolment-based:** assign a survey when someone joins a specific program
   - No → staff assign surveys manually as needed
   - Default: Manual assignment

9. **Do you need to collect feedback from people who are not enrolled participants?**
   - Yes → use shareable survey links (public URL, no login required)
   - No → surveys are assigned to existing participants only
   - Default: No shareable links until created

10. **Do you have surveys prepared in spreadsheets that you want to import?**
    - Yes → use the CSV import feature. Prepare a CSV with columns for section, question, type, required, options, and score values.
    - No → create surveys manually in the admin interface
    - Default: Manual creation

## Common Configurations

- **Financial coaching agency:** Enable financial capability, income change, employment status, and housing stability metrics. Disable mental health, substance use, and youth categories. Create one custom metric for "Budget Adherence" (0-100%). Client satisfaction survey assigned at discharge.
- **Community counselling agency:** Enable PHQ-9, GAD-7, and general wellbeing metrics. Disable employment and housing categories. Intake assessment survey auto-assigned at enrolment. Follow-up satisfaction survey at 90 days.
- **Youth drop-in centre:** Enable youth-category metrics and general engagement measures. Custom metric for "Program Attendance Rate." No surveys initially.

## Output Format

### Metrics

**CSV workflow (recommended):**
1. Go to the gear icon, then "Metric Library"
2. Click "Export to CSV" — download the full library
3. Open in a spreadsheet. For each row, set `is_enabled` to "yes" or "no"
4. Add new rows at the bottom for custom metrics (leave the `id` column blank)
5. Save as CSV and re-import through "Import from CSV"

**Manual setup:**
1. Go to the gear icon, then "Metric Library"
2. Toggle the "Enabled" switch for each metric
3. Click "Add Custom Metric" for agency-specific measures

**Custom metric format:**

| Field | Example |
|-------|---------|
| Name | Budget Adherence |
| Definition | Percentage of monthly budget categories where spending stayed within planned amounts |
| Category | Custom |
| Min value | 0 |
| Max value | 100 |
| Unit | % |

### Surveys

**Manual creation:**
1. Go to Admin (or Manage), then "Surveys"
2. Click "New Survey"
3. Add sections and questions
4. Activate when ready

**CSV import:**
1. Go to Admin, then "Surveys"
2. Click "Import from CSV"
3. Upload a CSV with these columns: section, question, type, required, options, score_values

**Example CSV:**
```csv
section,question,type,required,options,score_values
General Feedback,How satisfied are you with our services?,single_choice,yes,Very satisfied;Satisfied;Neutral;Dissatisfied;Very dissatisfied,5;4;3;2;1
General Feedback,What did you find most helpful?,long_text,no,,
Suggestions,Would you recommend us to others?,yes_no,yes,,
Suggestions,Any suggestions for improvement?,long_text,no,,
```

## Dependencies

- **Requires:** Document 04 (Programs) — metrics can be enabled per program, and surveys can be assigned per program. Programs must exist before configuring program-specific metrics.
- **Feeds into:** Document 06 (Templates) — plan templates reference metrics as goal measures. Document 07 (Reports) — reports aggregate metric data across participants and programs.

## Example: Financial Coaching Agency

**Metrics enabled from library:**
- Financial Capability Score (0-100, general)
- Income Level (dollars, employment)
- Employment Status (categorical, employment)
- Housing Stability Index (1-10, housing)
- Debt-to-Income Ratio (percentage, general)

**Metrics disabled:**
- All mental health category (PHQ-9, GAD-7, etc.)
- All substance use category
- All youth category

**Custom metrics created:**
- Budget Adherence (0-100%, custom) — "Percentage of monthly budget categories where spending stayed within planned amounts"
- Savings Rate (0-100%, custom) — "Percentage of monthly income allocated to savings"

**Surveys:**
- "Participant Satisfaction Survey" — assigned at discharge via trigger rule, anonymous, 10 questions across 2 sections, scores visible to participant
- "Intake Experience Survey" — assigned 7 days after enrolment via time-based trigger, non-anonymous, 5 questions

**Rationale:** The agency enabled metrics that match their funder's reporting requirements (financial capability, income, employment, housing). They created two custom metrics specific to their coaching model. Mental health and substance use metrics were disabled because the agency does not provide clinical services — if a participant's needs extend to those areas, they are referred externally.
