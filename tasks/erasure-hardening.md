# Erasure System Hardening — Expert Panel Recommendations

**Source:** Expert panel review (2026-02-06) after full implementation of tiered erasure system.
**Panel:** Privacy/Compliance Specialist, UX Designer, Security Engineer, Human Factors Engineer.

## Context

The tiered erasure system (anonymise/purge/full erasure) is complete and tested (89 tests pass).
This task file covers hardening improvements identified by the expert panel, ordered by priority.

**Status: All 7 items (H1–H7) implemented and tested. Completed 2026-02-06.**

---

## ERASE-H1: Scope PDF Receipt Access (High Priority, Low Effort) — DONE

**Problem:** Any PM can download any erasure receipt, even for requests they're not involved in. The receipt contains full client PII (name, DOB, record ID).

**Fix:** In `erasure_receipt_pdf()` view, add access check:
- Requester of this erasure request, OR
- PM in at least one of the required programmes, OR
- Admin

**File:** `apps/clients/erasure_views.py` — `erasure_receipt_pdf()` function

**Implementation:**
```python
# After fetching er, add:
user_pm_ids = set(_get_user_pm_program_ids(request.user))
is_involved = (
    request.user == er.requested_by
    or bool(set(er.programs_required) & user_pm_ids)
    or getattr(request.user, "is_admin", False)
)
if not is_involved:
    return HttpResponseForbidden(_("You do not have access to this receipt."))
```

**Test:** Add `test_unrelated_pm_cannot_download_receipt` to `ErasureViewWorkflowTests`.

---

## ERASE-H2: Write Audit Before Erasure (High Priority, Medium Effort) — DONE

**Problem:** Audit log write is in a try/except that swallows failures. If the audit DB is down when erasure executes, the erasure proceeds but the compliance trail is lost.

**Fix:** Write the audit entry *before* the erasure data modification. If the audit write fails, don't proceed with erasure.

**Files:** `apps/clients/erasure.py` — all three `_execute_tier*` functions

**Implementation:**
1. Move `_log_erasure_audit()` call to *before* the data modification
2. Remove the try/except wrapper — let it raise
3. The outer `transaction.atomic()` in `record_approval()` will roll back if audit fails
4. Note: audit DB is separate, so we need to write audit first (outside the main transaction), then proceed. If erasure fails after audit is written, that's acceptable (audit says "attempted", data still exists).

**Approach:**
```python
def _execute_tier1_anonymise(erasure_request, ip_address):
    client = erasure_request.client_file
    if client is None:
        raise ValueError("Client file no longer exists.")

    client_pk = client.pk
    record_id = client.record_id

    # Write audit FIRST — if this fails, erasure doesn't proceed
    _log_erasure_audit(erasure_request, client_pk, record_id, "update", ip_address)

    # Now proceed with data modification
    _scrub_registration_submissions(client)
    _anonymise_client_pii(client, erasure_request.erasure_code)
    ...
```

And change `_log_erasure_audit()` to NOT swallow exceptions:
```python
def _log_erasure_audit(erasure_request, client_pk, record_id, action, ip_address):
    """Write the audit log entry for an erasure execution.

    Raises on failure — erasure must not proceed without audit trail.
    """
    _log_audit(
        user=None,
        action=action,
        ...
    )
```

**Test:** Add `test_erasure_fails_if_audit_db_unavailable` — mock `_log_audit` to raise, verify client data unchanged.

---

## ERASE-H3: Track Receipt Downloads (Medium Priority, Low Effort) — DONE

**Problem:** The PDF receipt is the single most important document in the workflow. If nobody downloads it before approval, the erasure code links to nothing. Currently there's no way to tell whether anyone downloaded it.

**Fix:** Add `receipt_downloaded_at` field to ErasureRequest. Set it on first download. Show a warning on the approval page if the receipt hasn't been downloaded.

**Files:**
- `apps/clients/models.py` — add field
- `apps/clients/erasure_views.py` — set timestamp on download, pass flag to detail template
- `templates/clients/erasure/erasure_request_detail.html` — show warning banner
- New migration

**Implementation:**

Model:
```python
receipt_downloaded_at = models.DateTimeField(null=True, blank=True)
```

View (`erasure_receipt_pdf`):
```python
# After audit logging, before returning PDF:
if not er.receipt_downloaded_at:
    er.receipt_downloaded_at = timezone.now()
    er.save(update_fields=["receipt_downloaded_at"])
```

Detail view context:
```python
"receipt_not_downloaded": er.status == "pending" and er.receipt_downloaded_at is None,
```

Template warning (above the approval buttons):
```html
{% if receipt_not_downloaded %}
<article aria-label="warning" style="border-left: 4px solid var(--pico-color-amber-500); ...">
    <strong>{% trans "PDF receipt has not been downloaded." %}</strong>
    {% trans "Download the PDF receipt before approving. Once erased, client details cannot be recovered from the system." %}
</article>
{% endif %}
```

**Test:** Add `test_receipt_download_sets_timestamp` and `test_detail_warns_if_receipt_not_downloaded`.

---

## ERASE-H4: Notify Requester on Rejection (Medium Priority, Low Effort) — DONE

**Problem:** When a PM rejects an erasure request, no email is sent. The requester only finds out by checking the pending list. In a busy agency, rejected requests could sit unnoticed.

**Fix:** Send an email to the requester when their request is rejected, including the rejection reason.

**File:** `apps/clients/erasure_views.py` — add `_notify_requester_rejection()` and call from `erasure_reject()`

**Implementation:**
```python
def _notify_requester_rejection(erasure_request, rejecting_user, review_notes):
    """Email the requester that their erasure request was rejected."""
    if not erasure_request.requested_by or not erasure_request.requested_by.email:
        return

    code = erasure_request.erasure_code
    subject = _("Erasure Request Rejected — %(code)s") % {"code": code}
    body = (
        _("Your erasure request %(code)s has been rejected.") % {"code": code}
        + "\n\n"
        + _("Rejected by: %(name)s") % {"name": rejecting_user.get_display_name()}
        + "\n"
        + _("Reason: %(notes)s") % {"notes": review_notes}
        + "\n\n"
        + _("You may submit a new request if circumstances change.")
    )

    try:
        send_mail(subject=subject, message=body, from_email=None,
                  recipient_list=[erasure_request.requested_by.email])
    except Exception:
        logger.warning("Failed to send rejection notification for %s", code, exc_info=True)
```

Call from `erasure_reject()` after setting status to "rejected":
```python
_notify_requester_rejection(er, request.user, review_notes)
```

**Test:** Add `test_rejection_emails_requester` — mock send_mail, verify called with requester's email.

---

## ERASE-H5: Deduplicate build_data_summary Call (Low Priority, Low Effort) — DONE

**Problem:** `erasure_request_create()` calls `build_data_summary()` twice — once on POST (line 103, saved to the request) and once for the template (line 130). The summary could differ if data changes between page load and submission.

**Fix:** Compute once, use for both.

**File:** `apps/clients/erasure_views.py`

**Implementation:**
Move `summary = build_data_summary(client)` above the POST check so it's computed once:
```python
available_tiers = get_available_tiers(client)
summary = build_data_summary(client)  # Compute once

if request.method == "POST":
    form = ErasureRequestForm(request.POST, available_tiers=available_tiers)
    if form.is_valid():
        programs = get_required_programs(client)
        er = ErasureRequest.objects.create(
            ...
            data_summary=summary,  # Use same summary
            ...
        )
        ...
else:
    form = ErasureRequestForm(available_tiers=available_tiers)

# summary already computed above
active_alerts = Alert.objects.filter(...)
```

---

## ERASE-H6: Erasure Code Race Condition Fix (Low Priority, Low Effort) — DONE

**Problem:** The `save()` override uses `.count()` to generate sequential erasure codes. Two simultaneous saves could produce the same code. The `unique=True` constraint catches this as an IntegrityError, but with a confusing error message.

**Fix:** Add a retry loop in the `save()` method.

**File:** `apps/clients/models.py` — `ErasureRequest.save()`

**Implementation:**
```python
def save(self, *args, **kwargs):
    if not self.erasure_code:
        from django.db import IntegrityError
        year = timezone.now().year
        for attempt in range(5):
            last = ErasureRequest.objects.filter(
                erasure_code__startswith=f"ER-{year}-",
            ).count()
            self.erasure_code = f"ER-{year}-{last + 1 + attempt:03d}"
            try:
                super().save(*args, **kwargs)
                return
            except IntegrityError:
                if attempt == 4:
                    raise
                continue
    super().save(*args, **kwargs)
```

---

## ERASE-H7: History View Pagination (Low Priority, Low Effort) — DONE

**Problem:** The erasure history view has no pagination. After a year of operation, this list could grow large.

**Fix:** Add Django's built-in Paginator (20 per page).

**File:** `apps/clients/erasure_views.py` — `erasure_history()`

**Implementation:**
```python
from django.core.paginator import Paginator

def erasure_history(request):
    ...
    requests = _get_visible_requests(request.user)
    paginator = Paginator(requests, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(request, "clients/erasure/erasure_history.html", {
        "erasure_requests": page_obj,
        "page_obj": page_obj,
        "nav_active": "admin",
    })
```

Template: Add pagination links at bottom of table.

---

## ERASE-H8: 24-Hour Delay for Tier 3 Full Erasure (Medium Priority, High Effort)

**Problem:** Once the final PM approves a full erasure (Tier 3), CASCADE delete executes immediately within the same transaction. No undo window. If someone approves the wrong client, data is gone.

**Note:** Tiers 1 and 2 (anonymise) should remain immediate — the record survives, and the worst case is reversible from a backup. Tier 3 is the only irreversible tier.

**Approach:** This requires a background task scheduler (e.g., django-q2, celery, or a management command run via cron). This is a bigger architectural decision.

**Simplified alternative:** Instead of a background scheduler, change the Tier 3 flow so that the final approval sets a `scheduled_execution_at` timestamp (24 hours in the future). A daily management command (`execute_pending_erasures`) runs via cron and processes any requests past their scheduled time. During the 24-hour window, any PM or admin can cancel.

**This is a separate planning exercise** — not a quick fix. Consider whether this complexity is warranted for v1 given the existing multi-PM approval safeguard.

---

## Reviewed and Accepted As-Is

The panel reviewed these items and determined no changes needed:

- **`client_record_id` in tombstone** — Internal reference numbers, not PII
- **Programme names in data summary** — Organisational, not personal
- **Blanking all custom field values in Tier 1** — Conservative approach correct for PII
- **No automated data subject notification** — Agencies handle externally (letter/phone)
- **`_log_audit` private import** — Code smell only, no functional risk
