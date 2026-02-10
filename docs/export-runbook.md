# Export Runbook

Operational guide for managing the KoNote secure export system. Covers setup, scheduled maintenance, common issues, monitoring, and troubleshooting.

For a detailed explanation of how the export system works internally, see [SecureExportLink Lifecycle](secure-export-link-lifecycle.md).

## Setup

### Required Environment Variables

These environment variables must be set in your hosting environment (Railway, Azure, etc.).

**Essential for exports to work:**

| Variable | Required | Default | Description |
|---|---|---|---|
| `SECURE_EXPORT_DIR` | No | System temp folder + `konote_exports` | Where export files are stored on disk. Must be outside the web root. On Railway, the default (`/tmp/konote_exports`) is fine. |
| `SECURE_EXPORT_LINK_EXPIRY_HOURS` | No | `24` | How long download links remain active. |
| `ELEVATED_EXPORT_DELAY_MINUTES` | No | `10` | How long elevated exports (100+ clients or including notes) are held before download is allowed. |

**Essential for elevated export notifications:**

| Variable | Required | Default | Description |
|---|---|---|---|
| `EMAIL_BACKEND` | Yes (production) | `django.core.mail.backends.console.EmailBackend` | Set to `django.core.mail.backends.smtp.EmailBackend` in production. |
| `EMAIL_HOST` | Yes (production) | (empty) | Your SMTP server address (e.g., `smtp.gmail.com`, `smtp.office365.com`). |
| `EMAIL_PORT` | No | `587` | SMTP port. Usually `587` for TLS. |
| `EMAIL_HOST_USER` | Yes (production) | (empty) | SMTP username (often an email address). |
| `EMAIL_HOST_PASSWORD` | Yes (production) | (empty) | SMTP password or app-specific password. |
| `EMAIL_USE_TLS` | No | `True` | Whether to use TLS encryption for email. Keep this as `True`. |
| `DEFAULT_FROM_EMAIL` | No | `KoNote <noreply@konote2.app>` | The "From" address on notification emails. |

**If email is not configured:** Exports will still work, but admin notifications for elevated exports will fail silently (a warning is logged). Admins will not be alerted when large exports are created.

### PDF Export Dependencies

PDF exports (funder reports, client progress reports) require **WeasyPrint**, which needs native GTK libraries installed on the server.

**On Docker/Railway:** These are installed in the Dockerfile automatically.

**On a local Windows machine:** PDF generation may not be available. If WeasyPrint is not installed, users will see a "PDF generation unavailable" page, but CSV exports will still work.

## Scheduled Tasks (Cron)

### Cleaning Up Expired Exports

Run this command daily to remove expired download links and their files from disk:

```
python manage.py cleanup_expired_exports
```

**What it does:**

1. Deletes database records for links that expired more than 24 hours ago
2. Removes the associated files from disk
3. Finds and removes any "orphan" files that have no matching database record

**Preview mode** -- see what would be deleted without actually deleting anything:

```
python manage.py cleanup_expired_exports --dry-run
```

### Setting Up the Cron Job

**On Railway:** Railway does not have built-in cron. Options:

1. **Use Railway's cron service** -- create a separate service in your Railway project that runs the cleanup command on a schedule
2. **Use an external scheduler** -- services like cron-job.org or GitHub Actions can call a management command via a health-check endpoint
3. **Accept ephemeral cleanup** -- on Railway, the `/tmp` folder is wiped on every deploy, so files are cleaned up naturally. You still need the command to clean up database records, but it is less urgent

**On a Linux server (Azure VM, Elest.io, etc.):**

Add this to your crontab (`crontab -e`):

```
# Clean up expired export links daily at 3 AM
0 3 * * * cd /path/to/konote-web && python manage.py cleanup_expired_exports >> /var/log/konote_cleanup.log 2>&1
```

**On Docker Compose:**

Add a one-off service or use the host machine's cron to run:

```
docker compose exec web python manage.py cleanup_expired_exports
```

## Common Issues

### "Export link expired"

**What the user sees:** A page saying "This link has expired" with a suggestion to create a new export.

**What happened:** The user clicked a download link more than 24 hours after it was created (or whatever `SECURE_EXPORT_LINK_EXPIRY_HOURS` is set to).

**What to do:**
- The user needs to go back to the Reports page and create a new export
- Expired links cannot be reactivated -- this is by design for security
- If users frequently complain about expiry, you can increase `SECURE_EXPORT_LINK_EXPIRY_HOURS` (e.g., set it to `48` for 2 days)

### "Export file no longer available"

**What the user sees:** A page saying "The export file is no longer available on the server."

**What happened:** The download link is still valid (not expired, not revoked), but the actual file has been deleted from disk. This typically happens on Railway when the container restarts or redeploys.

**What to do:**
- The user needs to create a new export
- This is expected behaviour on Railway because of ephemeral storage
- On persistent servers, this could indicate the cleanup command ran too aggressively, or someone manually deleted files from the export directory

### "Permission denied" (403 error)

**What the user sees:** A message saying "You do not have permission."

**Possible causes and solutions:**

| Scenario | Explanation | Solution |
|---|---|---|
| User tries to create a metric/funder report export | They are not an admin or program manager | Assign them the `program_manager` role for the relevant program |
| User tries to create a client data export | They are not an admin | Only admins can export client data. This is by design -- it contains full PII |
| User tries to download someone else's export link | Only the creator and admins can download | The creator should share the file directly, or an admin can download it |
| Receptionist tries to export individual client data | Receptionists do not have export access | Staff role or higher is required for individual client exports |

**Role requirements summary:**

| Export Type | Minimum Role |
|---|---|
| Metric Report | Program Manager (for their programs) or Admin (any program) |
| Funder Report | Program Manager (for their programs) or Admin (any program) |
| Client Data Export | Admin only |
| Individual Client Export | Staff (must have program role for that client) |

### PDF generation failures

**What the user sees:** A "PDF generation unavailable" page.

**What happened:** The WeasyPrint library or its GTK dependencies are not installed on the server.

**What to do:**
1. Check if WeasyPrint is listed in `requirements.txt` -- it should be
2. Check Docker build logs for GTK installation errors
3. On Windows development machines, WeasyPrint may not work -- use CSV exports instead
4. If PDF is not needed, this is not a problem -- CSV exports work without WeasyPrint

### Large exports timing out

**What might happen:** Exports with thousands of clients could take a long time to generate, potentially hitting a server timeout.

**Mitigations already in place:**
- The system loads clients into memory for decryption (encrypted fields cannot be queried in SQL)
- This is designed to work for up to approximately 2,000 clients
- Beyond that, performance may degrade

**What to do if exports time out:**
1. Apply filters to reduce the number of clients (filter by program, status, or date range)
2. If your agency has more than 2,000 active clients, contact your technical support for optimisation options
3. Check your server's request timeout settings (e.g., Gunicorn's `--timeout` flag)

## Monitoring

### What to Watch For

**Daily checks (recommended for the first month, then weekly):**

1. **Manage Export Links page** (`/admin/` area, or `/reports/export-links/`): Review recent exports for anything unexpected
2. **Elevated export alerts**: Make sure you are receiving email notifications when large exports are created

**Signs of a problem:**

| Symptom | Possible Cause | Action |
|---|---|---|
| No email notifications for elevated exports | Email not configured, or SMTP credentials wrong | Check `EMAIL_BACKEND` and SMTP settings in environment variables |
| "File Missing" status on recent exports | Container restarted (Railway), or cleanup ran early | Expected on Railway; on persistent servers, check disk and cleanup schedule |
| Unexpectedly high download counts | Link may have been shared too widely | Review the audit log; consider revoking the link |
| Exports from unexpected users | Permission misconfiguration | Review user roles on the Admin > Users page |
| Disk space growing in export directory | Cleanup not running | Run `cleanup_expired_exports` manually; set up cron |

### Audit Log Queries

The audit log records all export activity in a separate database. Here are useful queries for monitoring.

**View all exports in the last 7 days:**

```sql
SELECT event_timestamp, user_display, action, resource_type,
       metadata->>'recipient' as recipient,
       metadata->>'total_clients' as client_count,
       metadata->>'secure_link_id' as link_id
FROM audit_auditlog
WHERE action = 'export'
  AND event_timestamp > NOW() - INTERVAL '7 days'
ORDER BY event_timestamp DESC;
```

**View all downloads (who actually downloaded files):**

```sql
SELECT event_timestamp, user_display,
       metadata->>'link_id' as link_id,
       metadata->>'created_by' as original_creator,
       metadata->>'export_type' as export_type,
       metadata->>'client_count' as client_count
FROM audit_auditlog
WHERE resource_type = 'export_download'
ORDER BY event_timestamp DESC
LIMIT 50;
```

**View all revocations:**

```sql
SELECT event_timestamp, user_display,
       metadata->>'link_id' as link_id,
       metadata->>'created_by' as original_creator,
       metadata->>'export_type' as export_type
FROM audit_auditlog
WHERE resource_type = 'export_link_revoked'
ORDER BY event_timestamp DESC;
```

**Note:** These queries run against the **audit database**, not the main application database. In Django, audit records are accessed with `AuditLog.objects.using("audit")`.

## Troubleshooting

### Step-by-step: User cannot download their export

1. **Get the link URL** from the user (it contains the UUID)
2. **Check the Manage Export Links page** (`/reports/export-links/`) -- find the link by its creation time or creator
3. **Check the status:**
   - **Active** -- the link should work. Ask the user to try again, and check if they are logged in
   - **Pending** -- it is an elevated export still in the delay period. Tell the user to wait
   - **Expired** -- the link has passed its expiry time. The user needs to create a new export
   - **Revoked** -- an admin revoked this link. Check with the admin team why
   - **File Missing** -- the file was deleted from disk (common after Railway redeploys). The user needs to create a new export

### Step-by-step: Admin not receiving elevated export emails

1. **Check email configuration** -- verify these environment variables are set:
   - `EMAIL_BACKEND` = `django.core.mail.backends.smtp.EmailBackend`
   - `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`
2. **Check admin email addresses** -- go to Admin > Users and verify admin users have email addresses on file
3. **Check server logs** -- look for warnings like "Failed to send elevated export notification" or "No admin email addresses found"
4. **Test email sending** -- run `python manage.py sendtestemail admin@example.com` to verify SMTP works

### Step-by-step: Disk space filling up with export files

1. **Check if cleanup is running** -- look for recent runs in your cron logs
2. **Run cleanup manually:**
   ```
   python manage.py cleanup_expired_exports --dry-run  # preview first
   python manage.py cleanup_expired_exports            # then actually clean up
   ```
3. **Check for orphan files** -- the cleanup command handles these automatically
4. **Set up cron** if not already configured (see the Scheduled Tasks section above)

### Step-by-step: Investigating a suspicious export

1. **Check the Manage Export Links page** for the export in question
2. **Note the details:** who created it, how many clients, who the stated recipient is, how many times it was downloaded
3. **Check the audit log** (using the SQL queries above, or through your database tool) for:
   - The creation event -- what filters were used?
   - Any download events -- who downloaded, and when?
4. **If the export should not have happened:**
   - Revoke the link immediately (if it is still active)
   - Review the user's role and permissions
   - Document the incident according to your organisation's data breach procedures
5. **If you need to see what was exported:**
   - The file may still be on disk at the path shown in the database record
   - The `filters_json` field on the `SecureExportLink` record shows exactly what parameters were used

## Quick Reference

| Task | Command / Location |
|---|---|
| Create an export | Reports page in the main menu |
| View active export links | `/reports/export-links/` (admin only) |
| Revoke an export link | Manage Export Links page, click "Revoke" |
| Clean up expired links | `python manage.py cleanup_expired_exports` |
| Preview cleanup | `python manage.py cleanup_expired_exports --dry-run` |
| Check export audit trail | Audit database (see SQL queries above) |
| Configure link expiry | Set `SECURE_EXPORT_LINK_EXPIRY_HOURS` env var |
| Configure elevated delay | Set `ELEVATED_EXPORT_DELAY_MINUTES` env var |
| Configure email notifications | Set `EMAIL_BACKEND`, `EMAIL_HOST`, etc. env vars |
