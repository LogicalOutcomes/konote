# Funder Demographic Profiles

Funder profiles let you define custom demographic breakdowns for reports. Different funders may define age categories differently (e.g. "youth" as 13–24 vs 15–29) or require additional demographic groupings beyond age.

## How It Works

1. **Analyse funder requirements** — Use a Claude session with your funder's reporting template or guidelines. Ask Claude to generate a funder profile CSV.
2. **Upload the CSV** — Go to **Settings → Funder Profiles → Upload New Profile**. Upload the CSV file or paste the CSV text directly.
3. **Preview and confirm** — Review the parsed breakdowns and assign the profile to the relevant programs.
4. **Use in reports** — When generating a report, select the funder profile from the dropdown. The report will use the funder's specific age bins and category merges.

## Who Can Do What

| Action | Role |
|---|---|
| Create/edit/delete funder profiles | Administrator only |
| View and select profiles in reports | Executive, Program Manager, Administrator |
| Generate profile CSVs | Anyone (outside the app, using Claude) |

## CSV Format

The CSV uses a simple row-type format. Each row starts with a type keyword:

| Row Type | Columns | Description |
|---|---|---|
| `profile_name` | name | The profile's display name |
| `profile_description` | description | Optional description |
| `breakdown` | label, source_type, [field_name] | Start a new breakdown section. Source type is `age` or `custom_field` |
| `bin` | breakdown_label, min_age, max_age, label | An age bin (only for `age` breakdowns) |
| `merge` | breakdown_label, target_label, "source1,source2,..." | Merge multiple category values into one label |
| `keep_all` | breakdown_label | Use the field's original categories without merging |

### Example CSV

```csv
profile_name,Youth Services Funder
profile_description,Custom age bins for the XYZ Foundation youth grant

breakdown,Age Categories,age
bin,Age Categories,0,14,Child (0-14)
bin,Age Categories,15,24,Youth (15-24)
bin,Age Categories,25,64,Adult (25-64)
bin,Age Categories,65,999,Senior (65+)

breakdown,Employment Status,custom_field,Employment Status
merge,Employment Status,Employed,"Full-time,Part-time,Self-employed,Contract"
merge,Employment Status,Not Employed,"Unemployed,Seeking employment"
merge,Employment Status,Student,"Full-time student,Part-time student"

breakdown,Gender Identity,custom_field,Gender Identity
keep_all,Gender Identity
```

## Default Profile

KoNote includes a **Standard Canadian Nonprofit** default profile with these age categories:

- Child (0–12)
- Youth (13–17)
- Young Adult (18–24)
- Adult (25–64)
- Senior (65+)

To create this default, run: `python manage.py seed_default_funder_profile`

## Tips

- **Use Claude to generate CSVs** — Provide your funder's reporting template and ask Claude to produce the CSV. This avoids manual formatting errors.
- **One profile per funder** — Create a separate profile for each funder with distinct reporting requirements.
- **Assign to programs** — A profile must be linked to at least one program to appear in report forms.
- **Download and re-upload** — You can download a profile's CSV from the detail page, edit it, and upload as a new profile.

## Privacy Safeguards

Funder profiles control how aggregate data is grouped — they do not expose individual client data. The reporting system enforces these safeguards regardless of profile configuration:

- **Confidential programs** — No demographic grouping is allowed.
- **Small programs** — Programs with fewer than 50 enrolled clients cannot use demographic grouping.
- **Small-cell suppression** — Groups with fewer than 10 individuals are suppressed (shown as "< 10").
- **PII fields blocked** — Fields like Preferred Name, Postal Code, and Emergency Contact are never available for grouping, even in legacy mode.
