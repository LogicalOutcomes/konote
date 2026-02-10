# Secure Export/Import Plan (EXP2, IMP1)

**Status:** Revised after expert panel critical review (2026-02-05)

## Background

An expert panel review identified serious risks with the current export system:

1. **Current CSV export decrypts all PII to plaintext** — defeating the purpose of encryption
2. **Staff have emailed plaintext client files via Gmail** — observed real-world behaviour
3. **No audit trail** — no record of who exported what, when, or why
4. **CRITICAL BUG: Current export has no demo/real separation** — demo users with admin rights can export all real client data

## Design Principles

1. **Sustainable security over aspirational security** — build what can be maintained
2. **Year 3 security matters more than launch security** — systems degrade over time
3. **The secure path must be easier than the insecure path** — not just allowed
4. **Visible security beats invisible security** — controls staff understand survive longer
5. **Graceful degradation** — if a feature breaks, fail safe (block), not fail open (allow plaintext)
6. **Logging without review is security theatre** — every audit must have a reviewer

## Known Limitations (Acknowledged)

**Secure links do not prevent email forwarding.** Once a file is downloaded, staff can still email it. Secure links provide:
- Audit trail of who downloaded what
- Link expiry (prevents forwarding old links)
- Friction that makes staff pause before exporting

They do NOT provide:
- Prevention of file sharing after download
- DRM or file-level encryption

**This is a risk-reduction measure, not a complete solution.** Complete prevention would require enterprise DLP tools that are out of scope for nonprofit budgets.

## Encryption Context

The system encrypts sensitive data at the application layer using Fernet (AES):

| Data Type | Currently Encrypted | After SEC1 |
|-----------|---------------------|------------|
| Client name, birth date | Yes | Yes |
| Custom fields (sensitive) | Yes | Yes |
| Progress note content | No | **Yes** |
| Note summary | No | **Yes** |
| Participant reflection | No | **Yes** |
| Target notes | No | **Yes** |
| Metric values | No | No |

---

## Architecture

### Simplified Two-Tier Model

After critical review, we simplified from three tiers to two. The middle tier added complexity without proportional security benefit.

```
┌─────────────────────────────────────────────────────────────────┐
│                     EXPORT REQUEST                               │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              │  What's being exported?       │
              └───────────────┬───────────────┘
                        │           │
                        ▼           ▼
                ┌─────────────┐ ┌─────────────┐
                │  STANDARD   │ │  ELEVATED   │
                │             │ │             │
                │ <100 clients│ │ 100+ clients│
                │ No notes    │ │ OR has notes│
                └─────────────┘ └─────────────┘
                        │           │
                        ▼           ▼
                  Secure link   Secure link
                  + audit       + audit
                  + warning     + warning
                                + admin notify
```

### Tier Definitions

| Tier | Criteria | Controls |
|------|----------|----------|
| **Standard** | <100 clients AND no clinical notes | Secure link (24hr expiry), audit log, warning dialog |
| **Elevated** | 100+ clients OR includes notes/clinical content | All Standard controls + 10-min delay + email to admins |

**Removed from original plan:**
- ~~Tier 1 immediate download~~ — all exports use secure links (prevents gaming by exporting one at a time)
- ~~24-hour delay~~ — delays without response process are security theatre
- ~~Download count limits~~ — if one download is allowed, three isn't worse
- ~~Password-protected ZIP~~ — unused complexity

### Individual Client Export (PIPEDA/GDPR)

Single-client exports still use secure links for consistency and audit trail. This prevents the "export 50 clients one-by-one" workaround.

| Aspect | Design |
|--------|--------|
| Scope | Single client's data only |
| Format | PDF preferred (harder to edit/forward), CSV optional |
| Includes | Client info + notes + plans + metrics |
| Access control | Staff with access to that client |
| Download method | Secure link (same as all exports) |
| Audit | Logged: who, when, which client |

---

## Key Design Decisions

These questions were raised by the critical review panel. Answers documented here:

### Q1: Where are export files stored?

**Answer: Ephemeral temp directory, outside web root.**

```python
# settings.py
import tempfile
SECURE_EXPORT_DIR = os.environ.get(
    'SECURE_EXPORT_DIR',
    os.path.join(tempfile.gettempdir(), 'konote_exports')
)
```

**Per deployment target:**
- **Local dev:** System temp dir (`/tmp/konote_exports` or `%TEMP%\konote_exports`)
- **Railway:** Ephemeral storage (files lost on deploy — acceptable for 24hr links)
- **Azure App Service:** Local temp storage or Azure Blob with SAS URLs (future enhancement)

**Critical:** Directory must NOT be inside `MEDIA_ROOT` or `STATIC_ROOT` (not web-accessible).

### Q2: Can secure links be shared within the organization?

**Answer: Yes, with audit.**

```python
# Anyone in the org can download if they have reporting permission
# But we log WHO actually downloaded, not just who created the link
if not request.user.has_perm('reports.can_export'):
    return HttpResponseForbidden()
```

**Rationale:** If links aren't shareable, staff will email the downloaded file (worse). Shareable links become an internal sharing tool that's audited.

### Q3: Who reviews audit logs?

**Answer: Weekly automated summary to admin, with named reviewer.**

The system sends a weekly email to all admin users:
```
Subject: KoNote Export Summary — Week of Feb 3-9, 2026

This week: 12 exports by 4 users

Largest exports:
- jane@agency.org: 47 clients (Funder report) — Feb 5
- mike@agency.org: 23 clients (Program planning) — Feb 7

Elevated exports (100+ or with notes): 0

Full audit log available in admin panel.
```

**Named reviewer:** The agency's designated Privacy Officer or Executive Director must acknowledge receipt quarterly (documented in onboarding).

### Q4: What's the response when admin notification fires?

**Answer: Document a procedure, or remove the notification.**

For Elevated exports, the notification email includes:
```
ELEVATED EXPORT ALERT

[User] is exporting data for [N] clients including clinical notes.
Export will be available for download in 10 minutes.

If this is unauthorized, you can revoke the export link:
[Admin panel link to revoke]

If this is expected, no action needed.
```

The 10-minute delay (not 24 hours) gives admins time to react to truly unauthorized exports without blocking legitimate work.

---

## Implementation Plan

### Phase 0: Fix Critical Security Bug (DO IMMEDIATELY)

The current `client_data_export` view has no demo/real separation. A demo user with admin rights can export all real client data.

**Files to modify:**
- `apps/reports/views.py` — all export views

**Fix:**
```python
# BEFORE (vulnerable):
clients_qs = ClientFile.objects.all()

# AFTER (secure):
from apps.clients.views import get_client_queryset
clients_qs = get_client_queryset(request.user)
```

**This is a 1-line fix per view. Do it before any other work.**

**Tasks:** (COMPLETED 2026-02-05)
- [x] Fix demo/real separation in client_data_export view (EXP0a)
- [x] Fix demo/real separation in metric export view (EXP0b)
- [x] Fix demo/real separation in funder report export view (EXP0c)
- [x] Add test: demo user cannot export real clients (EXP0d)

### Phase 1: Audit Logging

Add audit logging to existing export before changing anything else.

**Audit log entry structure:**
```python
AuditLog.objects.using("audit").create(
    user=request.user,
    action="client_data_export",
    details={
        "client_count": len(clients),
        "includes_notes": include_notes,
        "filters": {
            "program": program.name if program else None,
            "status": status_filter,
        },
        "recipient": stated_recipient,  # Who is receiving this data?
        "ip_address": get_client_ip(request),
    }
)
```

**Recipient field options:**
- "Keeping for my records"
- "Sharing with colleague" → prompts for colleague name
- "Sharing with funder" → prompts for funder name
- "Other" → free text

This creates a **concrete statement of intent** that's harder to falsify than generic "purpose" dropdown.

**Tasks:** (COMPLETED 2026-02-05)
- [x] Add recipient field to export forms (EXP2a)
- [x] Add recipient and IP to client_data_export audit log (EXP2b)
- [x] Add recipient and IP to export_form (metric export) audit log (EXP2c)
- [x] Add recipient and IP to funder_report_form audit log (EXP2d)

### Phase 2: Warning Dialogs

**Warning text:**
> "You are about to export personal data for **47 clients**.
>
> This file will contain unencrypted names, birth dates, and clinical notes.
>
> **Once downloaded, you are responsible for this data.**
>
> Who is receiving this data? [Dropdown]"

**Tasks:**
- [ ] Add client count display to export confirmation (EXP2e)
- [ ] Add warning banner listing what PII is included (EXP2f)
- [ ] Make recipient field required (EXP2g)

### Phase 3: Secure Links

**New model:**
```python
# apps/reports/models.py

class SecureExportLink(models.Model):
    """Time-limited download link for exports."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='export_links')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    # Download tracking
    download_count = models.PositiveIntegerField(default=0)
    last_downloaded_at = models.DateTimeField(null=True, blank=True)
    last_downloaded_by = models.ForeignKey(
        User, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='downloaded_exports'
    )

    # What was exported
    export_type = models.CharField(max_length=50)  # client_data, metrics, funder_report
    filters_json = models.TextField()
    client_count = models.PositiveIntegerField()
    includes_notes = models.BooleanField(default=False)
    recipient = models.CharField(max_length=200)

    # Elevated export tracking
    is_elevated = models.BooleanField(default=False)
    admin_notified_at = models.DateTimeField(null=True, blank=True)

    # For manual revocation
    revoked = models.BooleanField(default=False)
    revoked_by = models.ForeignKey(
        User, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='revoked_exports'
    )
    revoked_at = models.DateTimeField(null=True, blank=True)

    # File location (not web-accessible)
    file_path = models.CharField(max_length=500)

    def is_valid(self):
        """Check if link is still usable."""
        if self.revoked:
            return False
        if timezone.now() > self.expires_at:
            return False
        return True

    class Meta:
        indexes = [
            models.Index(fields=['expires_at']),
            models.Index(fields=['created_by', 'created_at']),
        ]
```

**Download view with proper file handle and race condition fix:**
```python
from django.db.models import F

@login_required
def download_export(request, link_id):
    """Serve file if link is valid."""
    link = get_object_or_404(SecureExportLink, id=link_id)

    if not link.is_valid():
        return render(request, "reports/export_link_expired.html", {
            "reason": "revoked" if link.revoked else "expired"
        })

    # Permission check: must have reporting permission
    if not request.user.has_perm('reports.can_export'):
        return HttpResponseForbidden("You do not have export permission.")

    # Atomic update to prevent race condition
    SecureExportLink.objects.filter(pk=link.pk).update(
        download_count=F('download_count') + 1,
        last_downloaded_at=timezone.now(),
        last_downloaded_by=request.user,
    )

    # Audit log the download (separate from creation audit)
    AuditLog.objects.using("audit").create(
        user=request.user,
        action="export_downloaded",
        details={
            "link_id": str(link.id),
            "created_by": link.created_by.email,
            "client_count": link.client_count,
        }
    )

    # Serve file with proper cleanup
    file_path = link.file_path
    if not os.path.exists(file_path):
        return render(request, "reports/export_file_missing.html")

    response = FileResponse(
        open(file_path, 'rb'),
        as_attachment=True,
        filename=os.path.basename(file_path)
    )
    return response
```

**Cleanup command with safe ordering (delete record first, then file):**
```python
# management/commands/cleanup_expired_exports.py

class Command(BaseCommand):
    """Delete expired export files. Run daily."""

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=1)
        expired = SecureExportLink.objects.filter(expires_at__lt=cutoff)

        deleted_count = 0
        for link in expired:
            file_path = link.file_path
            # Delete database record first
            link.delete()
            # Then delete file (if record delete succeeds)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    deleted_count += 1
                except OSError as e:
                    self.stderr.write(f"Could not delete {file_path}: {e}")

        self.stdout.write(f"Cleaned up {deleted_count} expired export files")
```

**Tasks:**
- [ ] Create SecureExportLink model (EXP2h)
- [ ] Create migration for SecureExportLink (EXP2i)
- [ ] Create secure link generation view (EXP2j)
- [ ] Create secure link download view with race condition fix (EXP2k)
- [ ] Create "link created" confirmation page (EXP2l)
- [ ] Create "link expired/revoked" error page (EXP2m)
- [ ] Create cleanup management command (EXP2n)
- [ ] Update export views to use secure links (EXP2o)
- [ ] Create link revocation admin view (EXP2p)

### Phase 4: Elevated Export Controls

For exports with 100+ clients OR including clinical notes:

**Tasks:**
- [ ] Add is_elevated flag logic based on count/notes (EXP2q)
- [ ] Add 10-minute delay for elevated exports (EXP2r)
- [ ] Add email notification to admins for elevated exports (EXP2s)
- [ ] Add admin view to revoke pending elevated exports (EXP2t)

### Phase 5: Monitoring and Review

**Weekly audit summary email:**
```python
# management/commands/send_export_summary.py

class Command(BaseCommand):
    """Send weekly export summary to admins. Run every Monday."""

    def handle(self, *args, **options):
        week_ago = timezone.now() - timedelta(days=7)
        exports = SecureExportLink.objects.filter(created_at__gte=week_ago)

        # Build summary
        total = exports.count()
        by_user = exports.values('created_by__email').annotate(
            count=Count('id'),
            total_clients=Sum('client_count')
        ).order_by('-total_clients')[:5]
        elevated = exports.filter(is_elevated=True).count()

        # Send to all admins
        admins = User.objects.filter(is_admin=True)
        send_mail(
            subject=f"KoNote Export Summary — Week of {week_ago.date()}",
            message=render_to_string('reports/email/weekly_summary.txt', {
                'total': total,
                'by_user': by_user,
                'elevated': elevated,
            }),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[u.email for u in admins],
        )
```

**Disk space monitoring:**
```python
# health check endpoint addition
def health_check(request):
    export_dir = settings.SECURE_EXPORT_DIR
    if os.path.exists(export_dir):
        total_size = sum(
            os.path.getsize(os.path.join(export_dir, f))
            for f in os.listdir(export_dir)
            if os.path.isfile(os.path.join(export_dir, f))
        )
        if total_size > 500 * 1024 * 1024:  # 500MB
            return JsonResponse({
                "status": "warning",
                "message": f"Export directory is {total_size // 1024 // 1024}MB"
            }, status=200)
    return JsonResponse({"status": "ok"})
```

**Tasks:**
- [ ] Create weekly export summary email command (EXP2u)
- [ ] Add export directory size to health check (EXP2v)
- [ ] Document cron/scheduled task setup in runbook (EXP2w)

### Phase 6: Individual Client Export

**Tasks:**
- [ ] Create single-client export view (EXP2x)
- [ ] Include all client data: info, notes, plans, metrics (EXP2y)
- [ ] Generate PDF format option using weasyprint or similar (EXP2z)
- [ ] Add export button to client detail page (EXP2aa)

---

## Bulk Import Design (IMP1)

**Deferred until secure export is complete and stable.**

### Key Design Points (from critical review)

1. **Transaction-wrap entire import** — all-or-nothing, no partial imports
2. **Rollback only for creations** — updates are logged but not reversible (too complex)
3. **Demo/real separation enforced** — demo users can only import demo clients
4. **Admin-only** — no delegation to program managers

### Import Model

```python
class ImportBatch(models.Model):
    """Track bulk imports for audit."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    filename = models.CharField(max_length=255)
    total_rows = models.PositiveIntegerField()
    created_count = models.PositiveIntegerField()
    skipped_count = models.PositiveIntegerField()  # Duplicates, errors

    # Simplified: only track created clients, not updates
    # Rollback deletes all clients created in this batch

class ClientFile(models.Model):
    # ... existing fields ...
    import_batch = models.ForeignKey(
        ImportBatch, null=True, blank=True,
        on_delete=models.SET_NULL
    )
```

### Tasks (Deferred)

- [ ] Create ImportBatch model (IMP1a)
- [ ] Add import_batch FK to ClientFile (IMP1b)
- [ ] Create CSV upload form with validation (IMP1c)
- [ ] Implement formula injection sanitisation (IMP1d)
- [ ] Implement duplicate detection (IMP1e)
- [ ] Create preview page showing what will be created (IMP1f)
- [ ] Implement batch import with transaction wrapping (IMP1g)
- [ ] Create rollback functionality (creations only) (IMP1h)
- [ ] Add audit logging for imports (IMP1i)
- [ ] Create import history page for admins (IMP1j)

---

## Documentation Requirements

### Runbook: `docs/runbooks/export-import.md`

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| "Link expired" on fresh link | Server timezone wrong | Check `TZ` env var, should be `America/Toronto` |
| Export files not cleaning up | Cron not running | Check Railway cron job or scheduled task |
| "File not found" on download | Server restarted (Railway) | Normal for ephemeral storage; user must re-export |
| "Permission denied" | Missing reporting role | Admin: assign Reports role to user |
| Disk space warning in health check | Cleanup not running | Run `cleanup_expired_exports` manually, check cron |
| Weekly summary not arriving | Email config or cron | Check `EMAIL_*` settings, check cron schedule |

### Succession Brief (in `docs/security-operations.md`)

For future maintainers:

1. **How secure links work:** Export generates CSV, saves to temp dir, creates database record with UUID. Download view checks expiry, serves file. Cleanup deletes old files daily.

2. **File storage location:** Defined by `SECURE_EXPORT_DIR` env var. On Railway, uses ephemeral `/tmp`. Files disappear on deploy (acceptable — links are short-lived).

3. **To manually clean up orphaned files:**
   ```bash
   python manage.py cleanup_expired_exports
   ```

4. **To disable all exports in emergency:**
   ```bash
   # Set environment variable
   EXPORT_ENABLED=false
   # Restart app
   ```

5. **To revoke a specific export link:**
   Admin panel → Reports → Secure Export Links → Find link → Mark as revoked

---

## Implementation Order

| # | Task | Effort | Dependencies |
|---|------|--------|--------------|
| **0** | Fix demo/real security bug | 1 hour | None — **DO FIRST** |
| **1** | Audit logging | 1 day | Phase 0 |
| **2** | Warning dialogs | 0.5 day | Phase 1 |
| **3** | Secure links | 3 days | Phase 2 |
| **4** | Elevated export controls | 1 day | Phase 3 |
| **5** | Monitoring + weekly summary | 1 day | Phase 3 |
| **6** | Individual client export | 1 day | Phase 3 |
| **7** | Documentation + runbook | 0.5 day | All above |
| — | Import (IMP1) | 3-4 days | After export stable |

**Total estimate:** 8-9 days for export, plus 3-4 days for import later

---

## Success Criteria

### Before Launch

- [ ] Demo/real separation verified in ALL export views (test exists)
- [ ] File storage location documented and verified not web-accessible
- [ ] Cleanup cron job configured and tested
- [ ] Weekly summary email tested
- [ ] Runbook complete

### After 30 Days

- [ ] Weekly audit summaries are being sent (check email logs)
- [ ] Export directory stays under 100MB (check health endpoint)
- [ ] At least one elevated export has triggered admin notification (verify flow works)

### After 90 Days

- [ ] Quarterly acknowledgment from designated Privacy Officer that they're reviewing summaries
- [ ] A different person (not Gillian) has successfully used the runbook to troubleshoot an issue
- [ ] No security incidents from exported data

---

## What This Plan Does NOT Solve

Transparent acknowledgment of limitations:

1. **Staff can still email downloaded files** — Secure links add friction and audit, but don't prevent sharing after download

2. **Staff can screenshot or retype data** — No technical control prevents this

3. **Audit logs are only useful if reviewed** — Weekly summaries help, but require human attention

4. **Railway's ephemeral storage means files disappear on deploy** — Acceptable for 24hr links, but users may need to re-export after a deploy

5. **Single maintainer (Gillian) is still a bus factor** — Documentation helps but doesn't eliminate the risk
