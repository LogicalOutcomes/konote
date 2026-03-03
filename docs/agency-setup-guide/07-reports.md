# 07 — Reports

## What This Configures

How your agency produces outcome reports for funders, leadership, and internal reviews. KoNote can generate formatted reports with demographic breakdowns, outcome summaries, and program statistics. This document covers what data goes into reports, how demographics are categorised, who can generate and receive reports, and how export monitoring works.

## Decisions Needed

### Funder Reporting Requirements

1. **What does your funder require you to report on?**
   - Common funder requirements: participant counts, demographic breakdowns (age, gender, income), outcome measures (pre/post scores), service hours, completion rates
   - List each funder and what they need. This determines which metrics and demographic categories to configure.
   - Default: No funder-specific reports until configured

2. **How often do you report to funders?**
   - Quarterly → most common for Canadian funders
   - Semi-annually or annually → less frequent but may require larger data sets
   - Ad hoc → as requested
   - Default: No scheduled reports until set up

3. **What format do funders expect?**
   - KoNote exports → CSV data extracts that you paste into funder templates
   - KoNote program reports → formatted PDF-style reports with demographic breakdowns and outcome summaries
   - Both → use program reports for your own review, CSV exports for funder templates
   - Default: CSV export is always available. Formatted program reports require the "Program Reports" feature to be enabled (Document 02).

### Demographic Breakdowns

4. **What demographic categories does your funder require?**
   - Age groups (e.g., 18-24, 25-34, 35-44, 45-54, 55-64, 65+)
   - Gender categories
   - Income levels
   - Custom categories from your agency's custom fields (e.g., referral source, housing status)
   - Default: Standard age and gender breakdowns. Custom breakdowns require a report template.

5. **Do you need custom age ranges or merged categories?**
   - Report templates let you define custom age bins (e.g., "Youth: 16-24" instead of the standard bins), merge demographic categories for small-cell protection, and include custom field values as report dimensions
   - Default: Standard age ranges and demographic categories

### Report Templates

6. **Do you need a report template for custom demographic breakdowns?**
   - Yes → create a report template (CSV upload) that defines your demographic dimensions, then link it to programs
   - No → standard demographic breakdowns are sufficient
   - Default: No custom report template

### Export Monitoring

7. **Who should be notified when someone exports participant data?**
   - Every export of individual participant data generates an email notification
   - Options: all system administrators (default), or specific people (e.g., privacy officer, ED)
   - Default: All system administrators. To change, set the `EXPORT_NOTIFICATION_EMAILS` environment variable.

8. **Do you want a weekly export summary email?**
   - Yes → a digest of all export activity for the week, including who exported what and download status
   - No → rely on individual export notifications only
   - Default: Not set up automatically. Requires a scheduled task (`send_export_summary` management command) to be configured.

9. **Who should review the export log?**
   - A designated person (privacy officer, ED, or system administrator) should review export activity regularly
   - Recommended: quarterly review at minimum
   - Default: Must designate someone

### Small-Cell Suppression

10. **Are you aware of the small-cell suppression rule?**
    - When any demographic group in a report has fewer than 5 participants, the count is automatically suppressed (shown as "<5") to prevent identification of individuals
    - This is standard practice for Canadian funders and cannot be turned off
    - Default: Always active. No decision needed — this is informational.

## Common Configurations

- **Financial coaching agency (quarterly funder reports):** Program Reports enabled, one report template per funder with custom age bins matching funder requirements, CSV exports for funder spreadsheets, ED and privacy officer receive export notifications, quarterly export log review
- **Community counselling agency:** Program Reports enabled for internal quality review, standard demographic breakdowns, weekly export summary enabled, privacy officer receives all export notifications
- **Youth drop-in centre:** Program Reports disabled (funder accepts simple attendance counts), CSV exports only, ED receives export notifications

## Output Format

### Report Template Setup

Report templates are created by uploading a CSV that defines demographic dimensions.

**Admin interface steps:**
1. Click "Manage," then "Report Templates"
2. Click "Upload CSV" (download the sample CSV template first if needed)
3. The CSV defines: age bins, custom field categories, and merged categories
4. Preview the profile, then confirm to save
5. Link programs to the report template

### Export Notification Configuration

**Default (all administrators):** No action needed — all active admin users with email addresses receive notifications.

**Specific recipients:** Set the `EXPORT_NOTIFICATION_EMAILS` environment variable to a comma-separated list of email addresses:

```
EXPORT_NOTIFICATION_EMAILS=privacy@agency.ca,ed@agency.ca
```

### Weekly Export Summary

Set up a scheduled task to run `python manage.py send_export_summary` once per week (e.g., every Monday morning). The summary includes:
- Total number of exports in the period
- Breakdown by export type
- Count of elevated exports
- Download status
- Top 5 staff members by export volume

**Preview without sending:**
```bash
python manage.py send_export_summary --dry-run
```

## Dependencies

- **Requires:** Document 04 (Programs) — reports are generated per program. Document 05 (Surveys & Metrics) — reports aggregate metric data. The "Program Reports" feature must be enabled (Document 02).
- **Feeds into:** Document 09 (Verification) — the walkthrough includes running a test export to confirm reports look correct and notifications arrive. Document 10 (Data Responsibilities) — export handling responsibilities.

## Example: Financial Coaching Agency

**Funder requirements:**
- Quarterly reports with participant counts, demographic breakdowns (age, gender, income bracket), and pre/post outcome scores for financial capability and employment status
- Age bins: 18-24, 25-34, 35-44, 45-54, 55+
- Income brackets: Under $20,000 / $20,000-$39,999 / $40,000-$59,999 / $60,000+

**Configuration:**
- Program Reports: Enabled
- Report template: Created with custom age bins and income brackets matching funder requirements, linked to all three programs
- Export notifications: Program Director and ED (set via `EXPORT_NOTIFICATION_EMAILS`)
- Weekly export summary: Enabled, runs Monday at 8:00 AM, sent to Program Director
- Export log review: Program Director reviews quarterly before submitting funder reports

**Report workflow:**
1. At quarter end, Program Director generates a program report for each funder stream
2. KoNote produces a formatted report with demographic breakdowns and outcome summaries
3. Program Director reviews the report, then exports CSV data to paste into the funder's spreadsheet template
4. Export notification emails confirm who downloaded what
5. Quarterly review of the export log confirms all exports were appropriate

**Rationale:** The agency uses both formatted reports (for internal review) and CSV exports (for funder templates). Custom demographic bins match the funder's exact requirements, so no manual recategorisation is needed. The weekly export summary gives the ED ongoing visibility into data leaving the system.
