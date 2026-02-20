# Reporting

How to set up report templates, configure demographic breakdowns, and manage export monitoring.

---

## Report Template Setup

Report templates let you customise how demographic breakdowns appear in reports.

**To create a report template:**

1. Click **Manage** -> **Report Templates**
2. Click **Upload CSV** -- download the sample CSV template first if needed
3. The CSV defines demographic dimensions: age bins, custom field categories, and merged categories
4. Preview the profile, then confirm to save
5. Link programs to the report template

When executives export reports, they can select a report template to use custom demographic breakdowns instead of the defaults.

**Small-cell suppression:** If any demographic group has fewer than 5 participants, the count is suppressed (shown as "<5") to prevent identification of individuals. This is standard practice for Canadian funders.

---

## Weekly Export Summary Email

KoNote can email administrators a weekly digest of all data export activity. This helps with privacy oversight and funder compliance.

### What the Summary Includes

- Total number of exports in the period
- Breakdown by export type (program report, funder report, data extract, etc.)
- Count of elevated exports (exports flagged for extra monitoring)
- Download status (downloaded, pending, revoked)
- Top 5 staff members by export volume

### Running Manually

```bash
# Send the weekly summary email to admins
python manage.py send_export_summary

# Preview without sending
python manage.py send_export_summary --dry-run

# Use a custom lookback window (e.g., 14 days)
python manage.py send_export_summary --days 14
```

### Setting Up as a Scheduled Task

Run this command **once per week** (e.g., every Monday morning):

**Linux/Mac (cron):**

```bash
# Run every Monday at 8:00 AM
0 8 * * 1 cd /path/to/konote && python manage.py send_export_summary >> /var/log/konote-export-summary.log 2>&1
```

**Docker Compose:**

```bash
0 8 * * 1 docker compose -f /path/to/docker-compose.yml exec -T web python manage.py send_export_summary >> /var/log/konote-export-summary.log 2>&1
```

**Railway:**

Add a cron job service that runs `python manage.py send_export_summary` on a weekly schedule (e.g., `0 8 * * 1` for Monday at 8:00 AM).

### Who Receives the Email

- If `EXPORT_NOTIFICATION_EMAILS` is set in your environment variables, the summary goes to those addresses
- Otherwise, it goes to all active admin users who have an email address on file

The command is **stateless and idempotent** -- running it multiple times in the same week sends duplicate emails, but causes no data changes. If no exports occurred in the period, the email still sends (showing zero counts).

---

[Back to Admin Guide](index.md)
