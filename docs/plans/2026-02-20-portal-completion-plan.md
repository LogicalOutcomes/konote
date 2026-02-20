# Portal Completion Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close remaining gaps in the Participant Portal (Phases A-D) to bring it to production readiness.

**Architecture:** All work is in the existing `apps/portal/` Django app, plus small additions to `apps/clients/erasure.py`, `apps/clients/merge.py`, and `apps/clients/apps.py`. Tests follow existing patterns in `apps/portal/tests/`. The portal uses its own session key (`_portal_participant_id`), Fernet encryption for PII, and HMAC-SHA-256 for email lookup.

**Tech Stack:** Django 5, Python 3.12, PostgreSQL (default + audit databases), Fernet encryption, HTMX, Pico CSS.

**Branch:** `feat/portal-q1-implementation`

---

## Dependency Map

```
Task 1 (Password Reset)      — independent
Task 2 (Discharge Signal)    — independent
Task 3 (Client Merge)        — independent
Task 4 (Erasure Extension)   — independent
Task 5 (Inactivity Command)  — independent
Task 6 (Staff-Assisted Login) — independent
Task 7 (PWA Manifest)        — independent
Task 8 (Portal Analytics)    — independent
Task 9 (French Translations) — depends on Tasks 6-8 (needs all new strings to exist first)
Task 10 (WCAG Review)        — depends on Tasks 6-8 (needs all templates finalised)
```

**Parallelisable:** Tasks 1-8 are all independent — they touch different files and can run as parallel sub-agents. Tasks 9-10 should run last.

---

### Task 1: Password Reset (A20 completion)

**Files:**
- Modify: `apps/portal/models.py` — add 3 fields to ParticipantUser
- Modify: `apps/portal/views.py:702-759` — implement password_reset_request and password_reset_confirm
- Modify: `apps/portal/forms.py` — update PortalPasswordResetConfirmForm
- Create: `apps/portal/migrations/0003_password_reset_fields.py` (via makemigrations)
- Test: `apps/portal/tests/test_auth.py` — add password reset tests

**Step 1: Write failing tests for password reset flow**

Add to `apps/portal/tests/test_auth.py`:

```python
def test_password_reset_request_sends_code(self):
    """POST to reset request should store hashed token and return submitted=True."""
    response = self.client.post("/my/password/reset/", {
        "email": "test@example.com",
    })
    self.assertEqual(response.status_code, 200)
    self.participant.refresh_from_db()
    self.assertTrue(self.participant.password_reset_token_hash)
    self.assertIsNotNone(self.participant.password_reset_expires)

def test_password_reset_request_unknown_email_no_leak(self):
    """Unknown email should show same success page (no enumeration)."""
    response = self.client.post("/my/password/reset/", {
        "email": "nonexistent@example.com",
    })
    self.assertEqual(response.status_code, 200)
    self.assertContains(response, "code")  # Shows "we sent a code" message

def test_password_reset_confirm_valid_code(self):
    """Valid reset code should allow setting a new password."""
    # First request a reset to generate a token
    self.client.post("/my/password/reset/", {"email": "test@example.com"})
    self.participant.refresh_from_db()
    # Retrieve the plaintext code from the test mail outbox
    from django.core import mail
    self.assertEqual(len(mail.outbox), 1)
    # Extract the 6-digit code from the email body
    import re
    code_match = re.search(r"\b(\d{6})\b", mail.outbox[0].body)
    self.assertIsNotNone(code_match)
    code = code_match.group(1)

    response = self.client.post("/my/password/reset/confirm/", {
        "email": "test@example.com",
        "code": code,
        "new_password": "NewSecurePass456!",
        "confirm_password": "NewSecurePass456!",
    })
    self.assertEqual(response.status_code, 200)
    # Verify new password works
    self.participant.refresh_from_db()
    self.assertTrue(self.participant.check_password("NewSecurePass456!"))

def test_password_reset_expired_code(self):
    """Expired reset code should fail."""
    self.client.post("/my/password/reset/", {"email": "test@example.com"})
    self.participant.refresh_from_db()
    # Expire the token manually
    from django.utils import timezone
    from datetime import timedelta
    self.participant.password_reset_expires = timezone.now() - timedelta(minutes=1)
    self.participant.save(update_fields=["password_reset_expires"])
    response = self.client.post("/my/password/reset/confirm/", {
        "email": "test@example.com",
        "code": "123456",
        "new_password": "NewSecurePass456!",
        "confirm_password": "NewSecurePass456!",
    })
    self.assertContains(response, "expired")

def test_password_reset_rate_limit(self):
    """More than 3 reset requests in an hour should be rejected."""
    for _ in range(3):
        self.client.post("/my/password/reset/", {"email": "test@example.com"})
    self.participant.refresh_from_db()
    self.assertEqual(self.participant.password_reset_request_count, 3)
    response = self.client.post("/my/password/reset/", {"email": "test@example.com"})
    self.assertEqual(response.status_code, 200)
    # Should still show "success" but NOT send a 4th email
    from django.core import mail
    self.assertEqual(len(mail.outbox), 3)
```

**Step 2: Run tests to verify they fail**

Run: `pytest apps/portal/tests/test_auth.py -k "password_reset" -v`
Expected: FAIL (fields don't exist yet)

**Step 3: Add model fields to ParticipantUser**

In `apps/portal/models.py`, add to the ParticipantUser class after `journal_disclosure_shown`:

```python
# Password reset
password_reset_token_hash = models.CharField(
    max_length=128, blank=True, default="",
    help_text="Hashed 6-digit reset code. Never store plaintext.",
)
password_reset_expires = models.DateTimeField(null=True, blank=True)
password_reset_request_count = models.IntegerField(
    default=0,
    help_text="Requests this hour. Reset by scheduled task or hourly check.",
)
password_reset_last_request = models.DateTimeField(null=True, blank=True)
```

Add a helper method:

```python
def can_request_password_reset(self):
    """Rate limit: max 3 requests per hour."""
    if self.password_reset_request_count < 3:
        return True
    if self.password_reset_last_request:
        from datetime import timedelta
        if timezone.now() - self.password_reset_last_request > timedelta(hours=1):
            self.password_reset_request_count = 0
            self.save(update_fields=["password_reset_request_count"])
            return True
    return False
```

**Step 4: Run makemigrations and migrate**

```bash
python manage.py makemigrations portal --name password_reset_fields
python manage.py migrate
```

**Step 5: Implement password_reset_request view**

Replace the stub in `apps/portal/views.py` (around line 702) with working code:

```python
@portal_feature_required
def password_reset_request(request):
    """Request a password reset code via email."""
    from apps.portal.forms import PortalPasswordResetRequestForm
    from apps.portal.models import ParticipantUser
    import secrets
    from django.contrib.auth.hashers import make_password
    from django.core.mail import send_mail

    submitted = False

    if request.method == "POST":
        form = PortalPasswordResetRequestForm(request.POST)
        if form.is_valid():
            submitted = True
            email = form.cleaned_data["email"].strip().lower()
            email_hash = ParticipantUser.compute_email_hash(email)

            try:
                participant = ParticipantUser.objects.get(
                    email_hash=email_hash, is_active=True
                )
            except ParticipantUser.DoesNotExist:
                # Don't reveal — show success anyway
                _audit_portal_event(request, "portal_password_reset_requested", metadata={
                    "found": False,
                })
            else:
                if participant.can_request_password_reset():
                    # Generate 6-digit code
                    code = f"{secrets.randbelow(1000000):06d}"
                    participant.password_reset_token_hash = make_password(code)
                    participant.password_reset_expires = timezone.now() + timezone.timedelta(minutes=10)
                    participant.password_reset_request_count += 1
                    participant.password_reset_last_request = timezone.now()
                    participant.save(update_fields=[
                        "password_reset_token_hash", "password_reset_expires",
                        "password_reset_request_count", "password_reset_last_request",
                    ])

                    # Send email with the code
                    try:
                        send_mail(
                            subject=_("Your password reset code"),
                            message=_(
                                "Your password reset code is: %(code)s\n\n"
                                "This code expires in 10 minutes.\n"
                                "If you did not request this, you can ignore this email."
                            ) % {"code": code},
                            from_email=None,  # Uses DEFAULT_FROM_EMAIL
                            recipient_list=[participant.email],
                            fail_silently=True,
                        )
                    except Exception:
                        logger.exception("Failed to send portal password reset email")

                _audit_portal_event(request, "portal_password_reset_requested", metadata={
                    "found": True,
                })
    else:
        form = PortalPasswordResetRequestForm()

    return render(request, "portal/password_reset_request.html", {
        "form": form,
        "submitted": submitted,
    })
```

**Step 6: Implement password_reset_confirm view**

Replace the stub (around line 730) with:

```python
@portal_feature_required
def password_reset_confirm(request):
    """Enter the emailed reset code and set a new password."""
    from apps.portal.forms import PortalPasswordResetConfirmForm
    from apps.portal.models import ParticipantUser
    from django.contrib.auth.hashers import check_password

    error = None
    success = False

    if request.method == "POST":
        form = PortalPasswordResetConfirmForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].strip().lower()
            code = form.cleaned_data["code"].strip()
            new_password = form.cleaned_data["new_password"]

            email_hash = ParticipantUser.compute_email_hash(email)
            try:
                participant = ParticipantUser.objects.get(
                    email_hash=email_hash, is_active=True
                )
            except ParticipantUser.DoesNotExist:
                error = _("Invalid code or email address.")
            else:
                # Check expiry
                if not participant.password_reset_expires or participant.password_reset_expires < timezone.now():
                    error = _("This code has expired. Please request a new one.")
                elif not participant.password_reset_token_hash:
                    error = _("No reset code has been requested.")
                elif not check_password(code, participant.password_reset_token_hash):
                    error = _("Invalid code or email address.")
                else:
                    # Code valid — set new password and clear reset fields
                    participant.set_password(new_password)
                    participant.password_reset_token_hash = ""
                    participant.password_reset_expires = None
                    participant.password_reset_request_count = 0
                    participant.save(update_fields=[
                        "password", "password_reset_token_hash",
                        "password_reset_expires", "password_reset_request_count",
                    ])
                    _audit_portal_event(request, "portal_password_reset_completed", metadata={
                        "participant_id": str(participant.pk),
                    })
                    success = True
    else:
        form = PortalPasswordResetConfirmForm()

    return render(request, "portal/password_reset_confirm.html", {
        "form": form,
        "error": error,
        "success": success,
    })
```

**Step 7: Update PortalPasswordResetConfirmForm**

In `apps/portal/forms.py`, ensure the form has an `email` field and `code` field. Find the existing `PortalPasswordResetConfirmForm` and update it to include:

```python
class PortalPasswordResetConfirmForm(forms.Form):
    email = forms.EmailField(label=_("Email"))
    code = forms.CharField(
        label=_("Reset code"),
        max_length=6,
        widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "one-time-code"}),
    )
    new_password = forms.CharField(
        label=_("New password"),
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    confirm_password = forms.CharField(
        label=_("Confirm new password"),
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    def clean(self):
        cleaned = super().clean()
        pw = cleaned.get("new_password")
        cpw = cleaned.get("confirm_password")
        if pw and cpw and pw != cpw:
            raise ValidationError(_("Passwords do not match."))
        if pw:
            validate_password(pw)
        return cleaned
```

**Step 8: Run tests to verify they pass**

Run: `pytest apps/portal/tests/test_auth.py -k "password_reset" -v`
Expected: PASS

**Step 9: Commit**

```bash
git add apps/portal/models.py apps/portal/views.py apps/portal/forms.py apps/portal/migrations/ apps/portal/tests/test_auth.py
git commit -m "feat: implement portal password reset — 6-digit email code with rate limiting and expiry"
```

---

### Task 2: Discharge Deactivation (D2)

**Files:**
- Create: `apps/portal/signals.py` — post_save handler for ClientFile
- Modify: `apps/portal/apps.py` — register signals in `ready()`
- Test: `apps/portal/tests/test_lifecycle.py` (new file)

**Step 1: Write failing test**

Create `apps/portal/tests/test_lifecycle.py`:

```python
"""Lifecycle tests for participant portal accounts.

Verifies automatic deactivation on discharge and other lifecycle events.
"""
from cryptography.fernet import Fernet
from django.test import TestCase, override_settings

from apps.admin_settings.models import FeatureToggle
from apps.clients.models import ClientFile
from apps.portal.models import ParticipantUser
import konote.encryption as enc_module


TEST_KEY = Fernet.generate_key().decode()


@override_settings(
    FIELD_ENCRYPTION_KEY=TEST_KEY,
    EMAIL_HASH_KEY="test-hash-key-for-lifecycle",
    PORTAL_DOMAIN="",
    STAFF_DOMAIN="",
)
class DischargeDeactivationTests(TestCase):
    """D2: Portal account deactivation on client discharge."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.client_file = ClientFile.objects.create(
            record_id="LIFE-001", status="active",
        )
        self.participant = ParticipantUser.objects.create_participant(
            email="discharge@example.com",
            client_file=self.client_file,
            display_name="Discharge Test",
            password="TestPass123!",
        )
        FeatureToggle.objects.get_or_create(
            feature_key="participant_portal",
            defaults={"is_enabled": True},
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_discharge_deactivates_portal_account(self):
        """Changing client status to 'discharged' should deactivate portal account."""
        self.assertTrue(self.participant.is_active)
        self.client_file.status = "discharged"
        self.client_file.save()
        self.participant.refresh_from_db()
        self.assertFalse(self.participant.is_active)

    def test_inactive_status_deactivates_portal_account(self):
        """Changing client status to 'inactive' should also deactivate portal account."""
        self.client_file.status = "inactive"
        self.client_file.save()
        self.participant.refresh_from_db()
        self.assertFalse(self.participant.is_active)

    def test_active_status_does_not_deactivate(self):
        """Client remaining active should not affect portal account."""
        self.client_file.status = "active"
        self.client_file.save()
        self.participant.refresh_from_db()
        self.assertTrue(self.participant.is_active)

    def test_discharge_without_portal_account_no_error(self):
        """Discharging a client without a portal account should not raise errors."""
        other_client = ClientFile.objects.create(
            record_id="LIFE-002", status="active",
        )
        other_client.status = "discharged"
        other_client.save()  # Should not raise
```

**Step 2: Run tests to verify they fail**

Run: `pytest apps/portal/tests/test_lifecycle.py -v`
Expected: FAIL (signal doesn't exist yet)

**Step 3: Create the signal handler**

Create `apps/portal/signals.py`:

```python
"""Portal signals — automatic lifecycle management.

Handles portal account deactivation when client status changes.
"""
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

logger = logging.getLogger(__name__)


@receiver(post_save, sender="clients.ClientFile")
def deactivate_portal_on_discharge(sender, instance, **kwargs):
    """Deactivate portal account when client is discharged or closed.

    The PortalAuthMiddleware already checks is_active on every request,
    so setting it to False immediately blocks further portal access.
    """
    if instance.status in ("discharged", "inactive"):
        from apps.portal.models import ParticipantUser

        updated = ParticipantUser.objects.filter(
            client_file=instance, is_active=True,
        ).update(is_active=False)

        if updated:
            logger.info(
                "Portal account deactivated for ClientFile %s (status: %s)",
                instance.pk, instance.status,
            )
            # Audit log
            try:
                from apps.audit.models import AuditLog
                AuditLog.objects.using("audit").create(
                    event_timestamp=timezone.now(),
                    user_id=None,
                    user_display="[system]",
                    action="update",
                    resource_type="portal_account",
                    metadata={
                        "client_file_id": instance.pk,
                        "operation": "auto_deactivated_discharge",
                        "client_status": instance.status,
                    },
                )
            except Exception:
                logger.exception("Failed to write portal deactivation audit log")
```

**Step 4: Register the signal in apps.py**

Update `apps/portal/apps.py`:

```python
from django.apps import AppConfig


class PortalConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.portal"
    label = "portal"
    verbose_name = "Participant Portal"

    def ready(self):
        import apps.portal.signals  # noqa: F401 — registers signal handlers
```

Note: Also check `INSTALLED_APPS` in settings to confirm the portal app is listed as `"apps.portal"` (or `"apps.portal.apps.PortalConfig"`). If there's a mismatch in label, the signal's `sender="clients.ClientFile"` won't match.

**Step 5: Run tests to verify they pass**

Run: `pytest apps/portal/tests/test_lifecycle.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add apps/portal/signals.py apps/portal/apps.py apps/portal/tests/test_lifecycle.py
git commit -m "feat: auto-deactivate portal account on client discharge (D2)"
```

---

### Task 3: Client Merge Portal Transfer (D3)

**Files:**
- Modify: `apps/clients/merge.py:322-533` — add portal transfer logic after step 7
- Test: `apps/portal/tests/test_lifecycle.py` — add merge tests

**Step 1: Write failing tests**

Add to `apps/portal/tests/test_lifecycle.py`:

```python
from apps.clients.merge import execute_merge
from apps.auth_app.models import User
from apps.portal.models import (
    ParticipantJournalEntry, ParticipantMessage, CorrectionRequest, StaffPortalNote,
)


@override_settings(
    FIELD_ENCRYPTION_KEY=TEST_KEY,
    EMAIL_HASH_KEY="test-hash-key-for-lifecycle",
    PORTAL_DOMAIN="",
    STAFF_DOMAIN="",
)
class ClientMergePortalTests(TestCase):
    """D3: Portal account transfer during client merge."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.kept = ClientFile.objects.create(record_id="MERGE-KEPT", status="active")
        self.archived = ClientFile.objects.create(record_id="MERGE-ARCH", status="active")
        self.staff_user = User.objects.create_user(
            username="mergestaff", password="pass", display_name="Staff",
        )
        FeatureToggle.objects.get_or_create(
            feature_key="participant_portal",
            defaults={"is_enabled": True},
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_merge_transfers_portal_account(self):
        """Portal account on archived client should transfer to kept client."""
        participant = ParticipantUser.objects.create_participant(
            email="archived@example.com",
            client_file=self.archived,
            display_name="Archived User",
            password="TestPass123!",
        )
        execute_merge(self.kept, self.archived, {}, {}, self.staff_user, "127.0.0.1")
        participant.refresh_from_db()
        self.assertEqual(participant.client_file_id, self.kept.pk)

    def test_merge_deactivates_duplicate_portal_account(self):
        """If both clients have portal accounts, archived's should be deactivated."""
        kept_user = ParticipantUser.objects.create_participant(
            email="kept@example.com",
            client_file=self.kept,
            display_name="Kept User",
            password="TestPass123!",
        )
        arch_user = ParticipantUser.objects.create_participant(
            email="archived2@example.com",
            client_file=self.archived,
            display_name="Archived User",
            password="TestPass123!",
        )
        execute_merge(self.kept, self.archived, {}, {}, self.staff_user, "127.0.0.1")
        kept_user.refresh_from_db()
        arch_user.refresh_from_db()
        self.assertTrue(kept_user.is_active)
        self.assertFalse(arch_user.is_active)

    def test_merge_transfers_journal_entries(self):
        """Journal entries on archived client should transfer to kept."""
        participant = ParticipantUser.objects.create_participant(
            email="journal@example.com",
            client_file=self.archived,
            display_name="Journal User",
            password="TestPass123!",
        )
        entry = ParticipantJournalEntry(
            participant_user=participant,
            client_file=self.archived,
        )
        entry.content = "My journal"
        entry.save()

        execute_merge(self.kept, self.archived, {}, {}, self.staff_user, "127.0.0.1")
        entry.refresh_from_db()
        self.assertEqual(entry.client_file_id, self.kept.pk)

    def test_merge_transfers_messages(self):
        """Portal messages should transfer to kept client."""
        participant = ParticipantUser.objects.create_participant(
            email="msg@example.com",
            client_file=self.archived,
            display_name="Message User",
            password="TestPass123!",
        )
        msg = ParticipantMessage(
            participant_user=participant,
            client_file=self.archived,
            message_type="general",
        )
        msg.content = "Hello"
        msg.save()

        execute_merge(self.kept, self.archived, {}, {}, self.staff_user, "127.0.0.1")
        msg.refresh_from_db()
        self.assertEqual(msg.client_file_id, self.kept.pk)
```

**Step 2: Run tests to verify they fail**

Run: `pytest apps/portal/tests/test_lifecycle.py::ClientMergePortalTests -v`
Expected: FAIL (merge.py doesn't handle portal)

**Step 3: Add portal transfer logic to merge.py**

In `apps/clients/merge.py`, add a new import at the top and portal transfer logic in `execute_merge()` between step 7 (group memberships) and step 8 (anonymise archived). Insert after line ~492 (after group memberships section):

```python
    # 7b. Transfer portal data (journal, messages, corrections, staff notes)
    from apps.portal.models import (
        CorrectionRequest, ParticipantJournalEntry,
        ParticipantMessage, ParticipantUser, StaffPortalNote,
    )

    summary["portal_journal_entries"] = ParticipantJournalEntry.objects.filter(
        client_file=archived
    ).update(client_file=kept)
    summary["portal_messages"] = ParticipantMessage.objects.filter(
        client_file=archived
    ).update(client_file=kept)
    summary["portal_correction_requests"] = CorrectionRequest.objects.filter(
        client_file=archived
    ).update(client_file=kept)
    summary["portal_staff_notes"] = StaffPortalNote.objects.filter(
        client_file=archived
    ).update(client_file=kept)

    # 7c. Handle portal account transfer
    # OneToOneField means client_file must be unique — can't have two accounts
    # pointing to the same client
    kept_portal = ParticipantUser.objects.filter(client_file=kept).first()
    archived_portal = ParticipantUser.objects.filter(client_file=archived).first()

    if archived_portal and not kept_portal:
        # Transfer the account
        archived_portal.client_file = kept
        archived_portal.save(update_fields=["client_file"])
        summary["portal_account"] = "transferred"
    elif archived_portal and kept_portal:
        # Can't have two — deactivate archived's
        archived_portal.is_active = False
        archived_portal.save(update_fields=["is_active"])
        summary["portal_account"] = "archived_deactivated"
    else:
        summary["portal_account"] = "none"
```

**Step 4: Run tests to verify they pass**

Run: `pytest apps/portal/tests/test_lifecycle.py::ClientMergePortalTests -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/clients/merge.py apps/portal/tests/test_lifecycle.py
git commit -m "feat: transfer portal data during client merge (D3)"
```

---

### Task 4: Erasure Extension (D4)

**Files:**
- Modify: `apps/clients/erasure.py` — add portal counts to summary, add portal PII scrubbing
- Test: `apps/portal/tests/test_lifecycle.py` — add erasure tests

**Step 1: Write failing tests**

Add to `apps/portal/tests/test_lifecycle.py`:

```python
from apps.clients.erasure import build_data_summary, _anonymise_client_pii, _purge_narrative_content


@override_settings(
    FIELD_ENCRYPTION_KEY=TEST_KEY,
    EMAIL_HASH_KEY="test-hash-key-for-lifecycle",
    PORTAL_DOMAIN="",
    STAFF_DOMAIN="",
)
class ErasurePortalTests(TestCase):
    """D4: Portal data included in erasure workflow."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.client_file = ClientFile.objects.create(
            record_id="ERASE-001", status="active",
        )
        self.participant = ParticipantUser.objects.create_participant(
            email="erase@example.com",
            client_file=self.client_file,
            display_name="Erase Test",
            password="TestPass123!",
        )
        # Create portal content
        entry = ParticipantJournalEntry(
            participant_user=self.participant,
            client_file=self.client_file,
        )
        entry.content = "Secret journal entry"
        entry.save()

        msg = ParticipantMessage(
            participant_user=self.participant,
            client_file=self.client_file,
            message_type="general",
        )
        msg.content = "Secret message"
        msg.save()

    def tearDown(self):
        enc_module._fernet = None

    def test_data_summary_includes_portal_counts(self):
        """build_data_summary should count portal journal entries and messages."""
        summary = build_data_summary(self.client_file)
        self.assertEqual(summary["portal_journal_entries"], 1)
        self.assertEqual(summary["portal_messages"], 1)

    def test_purge_blanks_portal_content(self):
        """_purge_narrative_content should blank portal encrypted content."""
        _purge_narrative_content(self.client_file)
        entry = ParticipantJournalEntry.objects.get(client_file=self.client_file)
        self.assertEqual(entry._content_encrypted, b"")
        msg = ParticipantMessage.objects.get(client_file=self.client_file)
        self.assertEqual(msg._content_encrypted, b"")

    def test_anonymise_deactivates_portal_account(self):
        """_anonymise_client_pii should deactivate the portal account."""
        _anonymise_client_pii(self.client_file, "ER-TEST-001")
        self.participant.refresh_from_db()
        self.assertFalse(self.participant.is_active)
```

**Step 2: Run tests to verify they fail**

Run: `pytest apps/portal/tests/test_lifecycle.py::ErasurePortalTests -v`
Expected: FAIL

**Step 3: Add portal counts to build_data_summary**

In `apps/clients/erasure.py`, in the `build_data_summary()` function, add after the existing summary dict (around line 45):

```python
    # Portal data counts (if portal app is installed)
    try:
        from apps.portal.models import (
            CorrectionRequest, ParticipantJournalEntry,
            ParticipantMessage, StaffPortalNote,
        )
        summary["portal_journal_entries"] = ParticipantJournalEntry.objects.filter(
            client_file=client_file
        ).count()
        summary["portal_messages"] = ParticipantMessage.objects.filter(
            client_file=client_file
        ).count()
        summary["portal_correction_requests"] = CorrectionRequest.objects.filter(
            client_file=client_file
        ).count()
        summary["portal_staff_notes"] = StaffPortalNote.objects.filter(
            client_file=client_file
        ).count()
        summary["has_portal_account"] = hasattr(client_file, "portal_account")
    except ImportError:
        pass
```

**Step 4: Add portal PII scrubbing to _purge_narrative_content**

In `apps/clients/erasure.py`, at the end of `_purge_narrative_content()` (around line 344):

```python
    # Blank portal content (journal entries, messages, correction descriptions)
    try:
        from apps.portal.models import (
            CorrectionRequest, ParticipantJournalEntry,
            ParticipantMessage, StaffPortalNote,
        )
        ParticipantJournalEntry.objects.filter(client_file=client).update(
            _content_encrypted=b"",
        )
        ParticipantMessage.objects.filter(client_file=client).update(
            _content_encrypted=b"",
        )
        CorrectionRequest.objects.filter(client_file=client).update(
            _description_encrypted=b"",
        )
        StaffPortalNote.objects.filter(client_file=client).update(
            _content_encrypted=b"",
        )
    except ImportError:
        pass
```

**Step 5: Add portal deactivation to _anonymise_client_pii**

In `apps/clients/erasure.py`, at the end of `_anonymise_client_pii()` (around line 317):

```python
    # Deactivate portal account and scrub email
    try:
        from apps.portal.models import ParticipantUser
        ParticipantUser.objects.filter(client_file=client, is_active=True).update(
            is_active=False,
            _email_encrypted=b"",
            email_hash="",
            display_name="[Anonymised]",
        )
    except ImportError:
        pass
```

**Step 6: Run tests to verify they pass**

Run: `pytest apps/portal/tests/test_lifecycle.py::ErasurePortalTests -v`
Expected: PASS

**Step 7: Commit**

```bash
git add apps/clients/erasure.py apps/portal/tests/test_lifecycle.py
git commit -m "feat: include portal data in erasure workflow (D4)"
```

---

### Task 5: 90-Day Inactivity Deactivation (D1)

**Files:**
- Create: `apps/portal/management/__init__.py`
- Create: `apps/portal/management/commands/__init__.py`
- Create: `apps/portal/management/commands/deactivate_inactive_portal_accounts.py`
- Test: `apps/portal/tests/test_lifecycle.py` — add management command test

**Step 1: Write failing test**

Add to `apps/portal/tests/test_lifecycle.py`:

```python
from datetime import timedelta
from django.core.management import call_command
from io import StringIO


@override_settings(
    FIELD_ENCRYPTION_KEY=TEST_KEY,
    EMAIL_HASH_KEY="test-hash-key-for-lifecycle",
    PORTAL_DOMAIN="",
    STAFF_DOMAIN="",
)
class InactivityDeactivationTests(TestCase):
    """D1: Deactivate portal accounts inactive for 90+ days."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.client_file = ClientFile.objects.create(
            record_id="INACT-001", status="active",
        )
        self.participant = ParticipantUser.objects.create_participant(
            email="inactive@example.com",
            client_file=self.client_file,
            display_name="Inactive User",
            password="TestPass123!",
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_deactivates_inactive_accounts(self):
        """Accounts with last_login > 90 days ago should be deactivated."""
        self.participant.last_login = timezone.now() - timedelta(days=91)
        self.participant.save(update_fields=["last_login"])

        out = StringIO()
        call_command("deactivate_inactive_portal_accounts", stdout=out)
        self.participant.refresh_from_db()
        self.assertFalse(self.participant.is_active)
        self.assertIn("1", out.getvalue())

    def test_leaves_active_accounts(self):
        """Accounts with recent login should not be deactivated."""
        self.participant.last_login = timezone.now() - timedelta(days=30)
        self.participant.save(update_fields=["last_login"])

        call_command("deactivate_inactive_portal_accounts", stdout=StringIO())
        self.participant.refresh_from_db()
        self.assertTrue(self.participant.is_active)

    def test_deactivates_never_logged_in_old_accounts(self):
        """Accounts created > 90 days ago that never logged in should be deactivated."""
        self.participant.last_login = None
        self.participant.save(update_fields=["last_login"])
        # Backdate created_at
        ParticipantUser.objects.filter(pk=self.participant.pk).update(
            created_at=timezone.now() - timedelta(days=91),
        )

        call_command("deactivate_inactive_portal_accounts", stdout=StringIO())
        self.participant.refresh_from_db()
        self.assertFalse(self.participant.is_active)

    def test_dry_run_does_not_deactivate(self):
        """--dry-run should report but not deactivate."""
        self.participant.last_login = timezone.now() - timedelta(days=91)
        self.participant.save(update_fields=["last_login"])

        call_command("deactivate_inactive_portal_accounts", "--dry-run", stdout=StringIO())
        self.participant.refresh_from_db()
        self.assertTrue(self.participant.is_active)
```

**Step 2: Run tests to verify they fail**

Run: `pytest apps/portal/tests/test_lifecycle.py::InactivityDeactivationTests -v`
Expected: FAIL (command doesn't exist)

**Step 3: Create the management command**

Create directory structure:
```
apps/portal/management/__init__.py          (empty)
apps/portal/management/commands/__init__.py  (empty)
apps/portal/management/commands/deactivate_inactive_portal_accounts.py
```

Content of `deactivate_inactive_portal_accounts.py`:

```python
"""Deactivate participant portal accounts inactive for 90+ days.

Usage:
    python manage.py deactivate_inactive_portal_accounts
    python manage.py deactivate_inactive_portal_accounts --dry-run
    python manage.py deactivate_inactive_portal_accounts --days 60

Intended to run as a scheduled task (cron, Railway cron).
"""
import logging

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

logger = logging.getLogger(__name__)

INACTIVITY_DAYS = 90


class Command(BaseCommand):
    help = "Deactivate portal accounts that have been inactive for 90+ days."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deactivated without making changes.",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=INACTIVITY_DAYS,
            help=f"Days of inactivity before deactivation (default: {INACTIVITY_DAYS}).",
        )

    def handle(self, *args, **options):
        from apps.portal.models import ParticipantUser

        dry_run = options["dry_run"]
        days = options["days"]
        cutoff = timezone.now() - timezone.timedelta(days=days)

        # Find accounts that are:
        # 1. Active
        # 2. Either: last_login before cutoff, OR never logged in and created before cutoff
        inactive = ParticipantUser.objects.filter(
            is_active=True,
        ).filter(
            Q(last_login__lt=cutoff) |
            Q(last_login__isnull=True, created_at__lt=cutoff)
        )

        count = inactive.count()

        if dry_run:
            self.stdout.write(f"Would deactivate {count} account(s) inactive for {days}+ days.")
            for account in inactive[:20]:
                self.stdout.write(f"  - {account.display_name} (last login: {account.last_login})")
            return

        if count == 0:
            self.stdout.write("0 accounts to deactivate.")
            return

        # Deactivate in bulk
        inactive.update(is_active=False)

        # Audit log each deactivation
        try:
            from apps.audit.models import AuditLog
            AuditLog.objects.using("audit").create(
                event_timestamp=timezone.now(),
                user_id=None,
                user_display="[system]",
                action="update",
                resource_type="portal_account",
                metadata={
                    "operation": "inactivity_deactivation",
                    "accounts_deactivated": count,
                    "inactivity_days": days,
                },
            )
        except Exception:
            logger.exception("Failed to write inactivity deactivation audit log")

        self.stdout.write(f"Deactivated {count} account(s) inactive for {days}+ days.")
```

**Step 4: Run tests to verify they pass**

Run: `pytest apps/portal/tests/test_lifecycle.py::InactivityDeactivationTests -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/portal/management/ apps/portal/tests/test_lifecycle.py
git commit -m "feat: add management command to deactivate inactive portal accounts (D1)"
```

---

### Task 6: Staff-Assisted Login (D6)

**Files:**
- Modify: `apps/portal/models.py` — add StaffAssistedLoginToken model
- Create: `apps/portal/migrations/0004_staffassistedlogintoken.py` (via makemigrations)
- Modify: `apps/portal/views.py` — add staff_assisted_login view
- Modify: `apps/portal/urls.py` — add URL
- Modify: `apps/portal/staff_views.py` — add generate_staff_login_token view
- Modify: `apps/clients/urls.py` — add staff-side URL
- Modify: `apps/portal/templates/portal/staff_manage_portal.html` — add button
- Test: `apps/portal/tests/test_lifecycle.py` — add tests

**Step 1: Write failing test**

Add to `apps/portal/tests/test_lifecycle.py`:

```python
@override_settings(
    FIELD_ENCRYPTION_KEY=TEST_KEY,
    EMAIL_HASH_KEY="test-hash-key-for-lifecycle",
    PORTAL_DOMAIN="",
    STAFF_DOMAIN="",
)
class StaffAssistedLoginTests(TestCase):
    """D6: Staff-assisted portal login with one-time token."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.client_file = ClientFile.objects.create(
            record_id="STAFF-001", status="active",
        )
        self.participant = ParticipantUser.objects.create_participant(
            email="assisted@example.com",
            client_file=self.client_file,
            display_name="Assisted User",
            password="TestPass123!",
        )
        FeatureToggle.objects.get_or_create(
            feature_key="participant_portal",
            defaults={"is_enabled": True},
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_valid_token_creates_session(self):
        """Valid staff-assisted login token should create a portal session."""
        from apps.portal.models import StaffAssistedLoginToken
        token_obj = StaffAssistedLoginToken.objects.create(
            participant_user=self.participant,
            expires_at=timezone.now() + timedelta(minutes=15),
        )
        response = self.client.get(f"/my/staff-login/{token_obj.token}/")
        self.assertIn(response.status_code, [302, 303])
        self.assertIn("/my/", response.url)
        # Token should be consumed (deleted)
        self.assertFalse(
            StaffAssistedLoginToken.objects.filter(pk=token_obj.pk).exists()
        )

    def test_expired_token_rejected(self):
        """Expired token should show error."""
        from apps.portal.models import StaffAssistedLoginToken
        token_obj = StaffAssistedLoginToken.objects.create(
            participant_user=self.participant,
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        response = self.client.get(f"/my/staff-login/{token_obj.token}/")
        self.assertEqual(response.status_code, 404)

    def test_used_token_rejected(self):
        """Token can only be used once."""
        from apps.portal.models import StaffAssistedLoginToken
        token_obj = StaffAssistedLoginToken.objects.create(
            participant_user=self.participant,
            expires_at=timezone.now() + timedelta(minutes=15),
        )
        token_str = token_obj.token
        # Use it once
        self.client.get(f"/my/staff-login/{token_str}/")
        # Try again
        response = self.client.get(f"/my/staff-login/{token_str}/")
        self.assertEqual(response.status_code, 404)
```

**Step 2: Run tests to verify they fail**

**Step 3: Add StaffAssistedLoginToken model**

In `apps/portal/models.py`:

```python
class StaffAssistedLoginToken(models.Model):
    """One-time token for staff-assisted participant login.

    Staff generates this from the portal management page. The participant
    uses it in-person at the agency. Token expires in 15 minutes and is
    deleted after use.
    """
    token = models.CharField(
        max_length=64, unique=True, default="",
        help_text="URL-safe token, single use.",
    )
    participant_user = models.ForeignKey(
        ParticipantUser, on_delete=models.CASCADE,
        related_name="staff_login_tokens",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name="+",
    )
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "portal"
        db_table = "portal_staff_assisted_login_tokens"

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(48)
        super().save(*args, **kwargs)

    @property
    def is_valid(self):
        return timezone.now() < self.expires_at
```

**Step 4: Run makemigrations**

```bash
python manage.py makemigrations portal --name staffassistedlogintoken
python manage.py migrate
```

**Step 5: Add staff_assisted_login view to views.py**

```python
@portal_feature_required
def staff_assisted_login(request, token):
    """Log a participant in via a staff-generated one-time token."""
    from apps.portal.models import StaffAssistedLoginToken

    try:
        token_obj = StaffAssistedLoginToken.objects.select_related(
            "participant_user"
        ).get(token=token)
    except StaffAssistedLoginToken.DoesNotExist:
        raise Http404

    if not token_obj.is_valid:
        token_obj.delete()
        raise Http404

    participant = token_obj.participant_user
    if not participant.is_active:
        token_obj.delete()
        raise Http404

    # Consume the token
    token_obj.delete()

    # Create session
    request.session.cycle_key()
    request.session["_portal_participant_id"] = str(participant.pk)
    # Mark this as a staff-assisted session (shorter max age)
    request.session["_portal_staff_assisted"] = True
    request.session.set_expiry(30 * 60)  # 30 minutes max

    participant.last_login = timezone.now()
    participant.save(update_fields=["last_login"])

    _audit_portal_event(request, "portal_staff_assisted_login", metadata={
        "participant_id": str(participant.pk),
        "created_by": str(token_obj.created_by_id) if token_obj.created_by_id else None,
    })

    return redirect("portal:dashboard")
```

**Step 6: Add URL in portal/urls.py**

Add to the urlpatterns:
```python
path("staff-login/<str:token>/", views.staff_assisted_login, name="staff_assisted_login"),
```

**Step 7: Add staff-side token generation view in staff_views.py**

```python
@login_required
@requires_permission("note.create", _get_program_from_client)
def generate_staff_login_token(request, client_id):
    """Generate a one-time staff-assisted login token (POST only)."""
    _portal_enabled_or_404()
    if request.method != "POST":
        raise Http404

    from datetime import timedelta
    from apps.portal.models import StaffAssistedLoginToken

    client_file = get_object_or_404(ClientFile, pk=client_id)
    account = ParticipantUser.objects.filter(
        client_file=client_file, is_active=True,
    ).first()

    if not account:
        raise Http404

    # Create token (15-minute expiry)
    token_obj = StaffAssistedLoginToken.objects.create(
        participant_user=account,
        created_by=request.user,
        expires_at=timezone.now() + timedelta(minutes=15),
    )

    # Build the URL
    from django.urls import reverse
    login_path = reverse("portal:staff_assisted_login", args=[token_obj.token])
    portal_domain = getattr(settings, "PORTAL_DOMAIN", "")
    if portal_domain:
        scheme = "https" if request.is_secure() else "http"
        login_url = f"{scheme}://{portal_domain}{login_path}"
    else:
        login_url = request.build_absolute_uri(login_path)

    AuditLog.objects.using("audit").create(
        event_timestamp=timezone.now(),
        user_id=request.user.pk,
        user_display=request.user.display_name,
        action="create",
        resource_type="staff_assisted_login_token",
        resource_id=token_obj.pk,
        metadata={
            "client_file_id": client_file.pk,
            "participant_id": str(account.pk),
            "expires_at": token_obj.expires_at.isoformat(),
        },
    )

    return render(request, "portal/staff_manage_portal.html", {
        "client_file": client_file,
        "portal_account": account,
        "invites": PortalInvite.objects.filter(client_file=client_file).order_by("-created_at")[:10],
        "pending_corrections": CorrectionRequest.objects.filter(client_file=client_file, status="pending").count(),
        "staff_login_url": login_url,
        "staff_login_expires": token_obj.expires_at,
    })
```

**Step 8: Add URL in clients/urls.py**

```python
path("<int:client_id>/portal/staff-login/", generate_staff_login_token, name="portal_staff_login"),
```

Also add the import of `generate_staff_login_token` from `apps.portal.staff_views`.

**Step 9: Add button to staff_manage_portal.html**

After the "Reset MFA" and "Revoke Access" buttons (around line 49), add:

```html
        <form method="post" action="{% url 'clients:portal_staff_login' client_id=client_file.pk %}" style="display: inline;">
            {% csrf_token %}
            <button type="submit" class="outline">{% trans "Generate Login Link" %}</button>
        </form>
```

And after the account status section, show the generated URL if present:

```html
    {% if staff_login_url %}
    <div class="portal-staff-login-url" role="alert">
        <p>{% trans "Staff-assisted login link (expires in 15 minutes):" %}</p>
        <code>{{ staff_login_url }}</code>
        <p class="secondary">{% blocktrans with time=staff_login_expires|date:"g:i A" %}This link expires at {{ time }}. It can only be used once.{% endblocktrans %}</p>
    </div>
    {% endif %}
```

**Step 10: Run tests**

Run: `pytest apps/portal/tests/test_lifecycle.py::StaffAssistedLoginTests -v`
Expected: PASS

**Step 11: Commit**

```bash
git add apps/portal/models.py apps/portal/views.py apps/portal/urls.py apps/portal/staff_views.py apps/portal/migrations/ apps/clients/urls.py apps/portal/templates/portal/staff_manage_portal.html apps/portal/tests/test_lifecycle.py
git commit -m "feat: add staff-assisted portal login with one-time token (D6)"
```

---

### Task 7: PWA Manifest (D7)

**Files:**
- Create: `static/portal/manifest.json`
- Create: `static/portal/icons/icon-192.png` and `icon-512.png` (generic placeholder)
- Modify: `apps/portal/templates/portal/base_portal.html` — add manifest link
- Modify: `apps/portal/views.py` — add manifest view (or serve as static)

**Step 1: Create manifest.json**

Create `static/portal/manifest.json`:

```json
{
    "name": "My Account",
    "short_name": "My Account",
    "start_url": "/my/",
    "display": "standalone",
    "background_color": "#ffffff",
    "theme_color": "#0d7377",
    "icons": [
        {
            "src": "/static/portal/icons/icon-192.png",
            "sizes": "192x192",
            "type": "image/png"
        },
        {
            "src": "/static/portal/icons/icon-512.png",
            "sizes": "512x512",
            "type": "image/png"
        }
    ]
}
```

**Step 2: Add manifest link to base_portal.html**

In `apps/portal/templates/portal/base_portal.html`, after the apple-touch-icon line (line 14), add:

```html
    <link rel="manifest" href="{% static 'portal/manifest.json' %}">
```

**Step 3: Create placeholder icons**

Use a simple Python script to generate solid-colour placeholder PNGs (the agency can replace later):

```bash
python -c "
from PIL import Image
for size in [192, 512]:
    img = Image.new('RGB', (size, size), color=(13, 115, 119))
    img.save(f'static/portal/icons/icon-{size}.png')
print('Icons created')
"
```

If PIL is not available, create minimal 1x1 PNGs and note they should be replaced. The PWA will work without icons — browsers show a generic icon.

**Step 4: Commit**

```bash
git add static/portal/ apps/portal/templates/portal/base_portal.html
git commit -m "feat: add PWA manifest for portal 'Add to Home Screen' (D7)"
```

---

### Task 8: Portal Usage Analytics (D11)

**Files:**
- Create: `apps/portal/analytics_views.py` — aggregate stats view
- Create: `apps/portal/templates/portal/analytics.html` — staff-side dashboard
- Modify: `konote/urls.py` — add /manage/portal-analytics/ route

**Step 1: Create analytics view**

Create `apps/portal/analytics_views.py`:

```python
"""Portal usage analytics — aggregate stats for staff (D11).

Shows only aggregate counts. NEVER per-participant data (per design decision D13).
"""
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render
from django.utils import timezone

from apps.admin_settings.models import FeatureToggle
from apps.auth_app.decorators import requires_admin_or_pm


@login_required
@requires_admin_or_pm
def portal_analytics(request):
    """Aggregate portal usage statistics."""
    flags = FeatureToggle.get_all_flags()
    if not flags.get("participant_portal"):
        raise Http404

    from apps.portal.models import (
        CorrectionRequest, ParticipantJournalEntry,
        ParticipantMessage, ParticipantUser,
    )
    from apps.audit.models import AuditLog

    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    stats = {
        "total_accounts": ParticipantUser.objects.filter(is_active=True).count(),
        "accounts_created_this_month": ParticipantUser.objects.filter(
            created_at__gte=month_start,
        ).count(),
        "total_journal_entries": ParticipantJournalEntry.objects.count(),
        "journal_entries_this_month": ParticipantJournalEntry.objects.filter(
            created_at__gte=month_start,
        ).count(),
        "total_messages": ParticipantMessage.objects.count(),
        "messages_this_month": ParticipantMessage.objects.filter(
            created_at__gte=month_start,
        ).count(),
        "corrections_pending": CorrectionRequest.objects.filter(status="pending").count(),
        "corrections_total": CorrectionRequest.objects.count(),
    }

    # Login count from audit log (this month)
    try:
        stats["logins_this_month"] = AuditLog.objects.using("audit").filter(
            action="portal_login",
            event_timestamp__gte=month_start,
        ).count()
    except Exception:
        stats["logins_this_month"] = 0

    return render(request, "portal/analytics.html", {"stats": stats})
```

**Step 2: Create analytics template**

Create `apps/portal/templates/portal/analytics.html`:

```html
{% extends "base.html" %}
{% load i18n %}

{% block title %}{% trans "Portal Analytics" %}{% endblock %}

{% block content %}
<h1>{% trans "Portal Analytics" %}</h1>
<p class="secondary">{% trans "Aggregate usage statistics. No per-participant data is shown." %}</p>

<div class="grid">
    <article>
        <header>{% trans "Accounts" %}</header>
        <dl class="info-grid-compact">
            <div class="info-field">
                <dt>{% trans "Active accounts" %}</dt>
                <dd>{{ stats.total_accounts }}</dd>
            </div>
            <div class="info-field">
                <dt>{% trans "Created this month" %}</dt>
                <dd>{{ stats.accounts_created_this_month }}</dd>
            </div>
            <div class="info-field">
                <dt>{% trans "Logins this month" %}</dt>
                <dd>{{ stats.logins_this_month }}</dd>
            </div>
        </dl>
    </article>

    <article>
        <header>{% trans "Activity" %}</header>
        <dl class="info-grid-compact">
            <div class="info-field">
                <dt>{% trans "Journal entries" %}</dt>
                <dd>{{ stats.total_journal_entries }} {% trans "total" %} / {{ stats.journal_entries_this_month }} {% trans "this month" %}</dd>
            </div>
            <div class="info-field">
                <dt>{% trans "Messages sent" %}</dt>
                <dd>{{ stats.total_messages }} {% trans "total" %} / {{ stats.messages_this_month }} {% trans "this month" %}</dd>
            </div>
        </dl>
    </article>

    <article>
        <header>{% trans "Corrections" %}</header>
        <dl class="info-grid-compact">
            <div class="info-field">
                <dt>{% trans "Pending" %}</dt>
                <dd>{{ stats.corrections_pending }}</dd>
            </div>
            <div class="info-field">
                <dt>{% trans "Total" %}</dt>
                <dd>{{ stats.corrections_total }}</dd>
            </div>
        </dl>
    </article>
</div>
{% endblock %}
```

**Step 3: Add URL to konote/urls.py**

In the `/manage/` URL section (around line 54), add:

```python
path("manage/portal-analytics/", include([
    path("", portal_analytics, name="portal_analytics"),
])),
```

And add the import at the top of `konote/urls.py`:

```python
from apps.portal.analytics_views import portal_analytics
```

**Step 4: Commit**

```bash
git add apps/portal/analytics_views.py apps/portal/templates/portal/analytics.html konote/urls.py
git commit -m "feat: add aggregate portal usage analytics dashboard (D11)"
```

---

### Task 9: French Translations

**Files:**
- Modify: `locale/fr/LC_MESSAGES/django.po` — add French translations for portal strings
- Regenerate: `locale/fr/LC_MESSAGES/django.mo`

**Step 1: Extract and compile strings**

```bash
python manage.py translate_strings
```

**Step 2: Review the .po file for untranslated portal strings**

Look for empty `msgstr ""` entries where the `msgid` comes from portal templates. Fill in French translations for all portal strings. Key strings to translate:

- "My Account", "Home", "My Goals", "My Progress", "Milestones"
- "My Journal", "A private space to write your thoughts"
- "Message My {worker}", "Questions for You"
- "Leave quickly", "Leave this page quickly"
- "Hi,", "See the goals you're working on", "See how far you've come"
- "Celebrate what you've achieved"
- "What would you like to do?"
- "Skip to main content"
- Password reset strings: "Your password reset code", "This code expires in 10 minutes"
- Staff-assisted login strings: "Generate Login Link", "Staff-assisted login link"
- Analytics strings: "Portal Analytics", "Active accounts", "Logins this month"

**Step 3: Compile**

```bash
python manage.py translate_strings
```

**Step 4: Commit**

```bash
git add locale/fr/LC_MESSAGES/django.po locale/fr/LC_MESSAGES/django.mo
git commit -m "i18n: add French translations for portal templates and new features"
```

---

### Task 10: WCAG 2.2 AA Review (D8)

This is a review task, not a code task. Use the `accessibility-review` skill.

**Checklist:**
1. All portal templates have proper heading hierarchy (h1 → h2 → h3, no skips)
2. All forms have associated `<label>` elements
3. All interactive elements have focus indicators
4. Quick-exit button is keyboard-accessible
5. Colour contrast meets 4.5:1 ratio (check portal.css)
6. All images/icons have `aria-hidden="true"` or alt text
7. Language toggle has proper `lang` and `hreflang` attributes
8. Session timeout warning is announced to screen readers
9. Error messages are linked to form fields with `aria-describedby`
10. Touch targets meet 44px minimum at mobile breakpoints

**Step 1: Run accessibility review skill**

Invoke the `accessibility-review` skill on all portal templates.

**Step 2: Fix any issues found**

**Step 3: Commit fixes**

```bash
git add apps/portal/templates/ static/css/portal.css
git commit -m "a11y: WCAG 2.2 AA fixes for portal templates (D8)"
```

---

## Summary

| Task | Files Changed | Independent? | Estimated Steps |
|------|--------------|-------------|-----------------|
| 1. Password Reset | models, views, forms, migration, tests | Yes | 9 |
| 2. Discharge Signal | signals.py, apps.py, tests | Yes | 6 |
| 3. Client Merge | merge.py, tests | Yes | 5 |
| 4. Erasure Extension | erasure.py, tests | Yes | 7 |
| 5. Inactivity Command | management command, tests | Yes | 5 |
| 6. Staff-Assisted Login | models, views, urls, template, migration, tests | Yes | 11 |
| 7. PWA Manifest | static files, base template | Yes | 4 |
| 8. Analytics Dashboard | analytics view, template, urls | Yes | 4 |
| 9. French Translations | .po/.mo files | After 1-8 | 4 |
| 10. WCAG Review | templates, CSS | After 1-8 | 3 |

**Parallel execution:** Tasks 1-8 can all run as independent sub-agents. Tasks 9-10 run sequentially after.
