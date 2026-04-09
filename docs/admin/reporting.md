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

**OVHcloud VPS or other Linux host:** Use the cron method above (Linux/Mac cron).

### Who Receives the Email

- If `EXPORT_NOTIFICATION_EMAILS` is set in your environment variables, the summary goes to those addresses
- Otherwise, it goes to all active admin users who have an email address on file

The command is **stateless and idempotent** -- running it multiple times in the same week sends duplicate emails, but causes no data changes. If no exports occurred in the period, the email still sends (showing zero counts).

---

## What's New in Reporting

KoNote now automatically tracks additional data about service episodes and goals. This happens in the background — staff don't enter anything new — but it makes reports significantly more detailed.

### Episode-Based Statistics

Every progress note is now automatically linked to the participant's service episode (their enrolment in a program). This means reports can answer questions like:

| Report Question | What It Tells You |
|---|---|
| **Service hours per episode** | Total hours of service delivered to each participant in a program |
| **Number of contacts per episode** | How many sessions, calls, or other interactions per participant |
| **Service intensity** | Average hours or contacts for participants who completed vs. those who withdrew |
| **New vs. returning participants** | How many participants are first-time intakes vs. re-enrolments |
| **Completion rate** | Percentage of participants who completed the program or met their goals |

These statistics were previously impossible to calculate because notes weren't connected to episodes. They now update automatically as staff write notes.

### Goal Source Tracking

KoNote now classifies who initiated each goal:

| Classification | How It's Determined |
|---|---|
| **Jointly developed** | Both the worker's description and the participant's own words are recorded |
| **Participant-initiated** | The participant's own words are recorded but no worker description |
| **Worker-initiated** | Only the worker's description is recorded |
| **Funder-required** | Classified by the system based on program metric templates |

This classification is automatic — it reads what staff already enter and categorises it. No new fields or forms.

**Why it matters:** Funders increasingly ask whether goals are participant-driven. Reports can now show "72% of goals were jointly developed with participants" — a quality metric that demonstrates person-centred practice.

### Goal Timeline Tracking

If you set a **default review period** for a program, every new goal in that program automatically gets a target date.

**To set this:**
1. Go to **Manage** > **Programs**
2. Edit the program
3. Set **Default goal review days** (e.g., 90 for a 3-month review cycle)

Reports can then answer: "Were goals achieved on time?" and "What's the average time to goal achievement?"

### On-Hold Goals

Goals can now be paused ("on hold") when a participant is in crisis or temporarily unavailable. On-hold goals:

- Still appear in the participant's plan (they're not deleted or deactivated)
- Still count toward active goal statistics
- Do **not** prompt for metric entry during progress notes (since the participant isn't actively working on them)
- Can be resumed at any time

This gives more accurate reporting — paused goals aren't counted as failures or dropouts.

---

## Longitudinal Trajectory Export (small-population evaluation)

LTE is a second, structurally separate export tier for programs with
10–14 participants (or 15+ for OCAP/EGAP-governed programs). The
standard Evaluator Export blocks programs below n = 15 because
demographic k-anonymity cannot be guaranteed. LTE is the answer for
smaller programs: it drops demographics entirely, substitutes fuzzed
longitudinal metric trajectories, and gates access behind REB
approval, community governance review, distributed admin oversight,
and a 5-business-day review-and-cancel window.

### When to use LTE

- Small program with fewer than 15 participants
- External evaluator (not internal staff) needs participant-level
  data for outcome or dose-response analysis
- REB approval is in place
- The evaluation has a data sharing agreement
- You have a designated privacy officer with the LTE permission

If demographic breakdowns are required, LTE is **not** the right
tool — use aggregate reports or, for larger programs, the standard
Evaluator Export. Research-grade data access (unfuzzed values,
complete microdata) is out of scope for both EME and LTE and has its
own high-friction workflow.

### Setup

1. A KoNote admin grants `report.evaluation_export_small_population`
   to the designated privacy officer through **Admin → Evaluator
   Export Access**. The grant is strictly separate from the standard
   Evaluator Export permission.
2. For programs that need community governance, set the
   **Community governance framework** field on the program
   (OCAP / EGAP / other). This triggers the conditional community
   reviewer signoff requirement in the LTE form and raises the
   population floor to 15 for OCAP and EGAP.
3. Distribute the [LTE Privacy Officer Guide](../lte-privacy-officer-guide.md)
   to the designated officer.

### How LTE differs from the standard Evaluator Export

| | Standard Evaluator Export | LTE |
|---|---|---|
| Population floor | n ≥ 15 (hard) | n ≥ 10 (15 for OCAP/EGAP) |
| Demographic columns | Age / gender / ethnicity / geography, generalised and k-anonymised | **None** — dropped at the schema layer |
| Metric values | Unrounded | Rounded to nearest scale unit |
| Session count | Exact | Banded to nearest 5 |
| Total hours | Exact | Banded to nearest half-hour |
| Delivery | Immediate download link | 5-business-day review-and-cancel window, then 24h download |
| Permission | `report.evaluation_export` | `report.evaluation_export_small_population` (separate) |
| Preconditions | DSA + evaluator contact details | REB approval, structured evaluator credentials, community signoff (where applicable), destruction attestation window |
| Audit category | `evaluation_microdata` | `longitudinal_trajectory_export` |

### Rate limit

After an LTE request is submitted, KoNote automatically creates a
post-hoc privacy officer review task. **Until the officer resolves
that task, no new LTE requests can be submitted anywhere in the
agency.** The rate limit is agency-wide, not per-program — this is
deliberate, as the review burden sits with a single designee.

See [`tasks/design-rationale/evaluation-microdata-export.md`](../../tasks/design-rationale/evaluation-microdata-export.md)
for the full design rationale, including what LTE explicitly does
not do and why.

---

[Back to Admin Guide](index.md)
