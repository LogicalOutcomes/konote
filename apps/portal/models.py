"""Participant portal models.

These models support a participant-facing portal where clients can view
their plans, write journal entries, send messages to staff, and request
corrections to their records. All PII is Fernet-encrypted at rest; email
addresses are additionally HMAC-hashed for constant-time lookup without
exposing plaintext.
"""
import hashlib
import hmac
import secrets
import uuid

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from konote.encryption import decrypt_field, encrypt_field


# ---------------------------------------------------------------------------
# A) ParticipantUser — portal login account linked to a ClientFile
# ---------------------------------------------------------------------------

class ParticipantUserManager(BaseUserManager):
    """Manager for participant portal accounts."""

    def create_participant(self, email, client_file, display_name, password):
        """Create and return a new ParticipantUser with hashed password.

        Args:
            email: Plaintext email (stored encrypted + HMAC-hashed).
            client_file: The ClientFile this account belongs to.
            display_name: Preferred display name for the participant.
            password: Plaintext password (hashed before storage).

        Returns:
            The newly created ParticipantUser instance.
        """
        if not email:
            raise ValueError(_("Email is required."))
        if not client_file:
            raise ValueError(_("Client file is required."))

        user = self.model(
            email_hash=ParticipantUser.compute_email_hash(email),
            display_name=display_name,
            client_file=client_file,
        )
        user.email = email  # triggers Fernet encryption via property setter
        user.set_password(password)
        user.save(using=self._db)
        return user


class ParticipantUser(AbstractBaseUser):
    """A participant's portal login account.

    This is entirely separate from the staff User model. Participants
    authenticate via email + password (not username). The email is stored
    in two forms:
      - ``email_hash``: HMAC-SHA-256 for O(1) lookup during login
      - ``_email_encrypted``: Fernet-encrypted for display and password reset

    The UUID primary key is used as USERNAME_FIELD for Django internals only
    — it is never shown to the participant or used for login.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    # Email: HMAC hash for lookup, Fernet-encrypted for display/reset
    email_hash = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="HMAC-SHA-256 of normalised email for constant-time lookup.",
    )
    _email_encrypted = models.BinaryField(default=b"", blank=True)

    display_name = models.CharField(
        max_length=255,
        help_text="Preferred name shown in the portal UI.",
    )

    client_file = models.OneToOneField(
        "clients.ClientFile",
        on_delete=models.CASCADE,
        related_name="portal_account",
    )

    is_active = models.BooleanField(default=True)

    preferred_language = models.CharField(
        max_length=10,
        default="en",
        help_text="ISO language code for portal UI.",
    )

    # Multi-factor authentication
    MFA_METHOD_CHOICES = [
        ("totp", _("TOTP")),
        ("email", _("Email code")),
        ("exempt", _("Exempt")),
    ]
    mfa_method = models.CharField(
        max_length=20,
        choices=MFA_METHOD_CHOICES,
        default="totp",
    )
    _totp_secret_encrypted = models.BinaryField(default=b"", blank=True)

    # Account lockout
    failed_login_count = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    # One-time journal privacy disclosure
    journal_disclosure_shown = models.BooleanField(
        default=False,
        help_text="True after the participant has seen the journal privacy notice.",
    )

    # Timestamps — last_login is inherited from AbstractBaseUser
    # IMPORTANT: last_login must NEVER be exposed to staff users
    created_at = models.DateTimeField(auto_now_add=True)

    objects = ParticipantUserManager()

    USERNAME_FIELD = "id"
    # No REQUIRED_FIELDS — creation goes through create_participant()

    class Meta:
        app_label = "portal"
        db_table = "portal_participant_users"
        verbose_name = _("participant account")
        verbose_name_plural = _("participant accounts")

    def __str__(self):
        return self.display_name or str(self.id)

    # --- Encrypted property: email ---

    @property
    def email(self):
        return decrypt_field(self._email_encrypted)

    @email.setter
    def email(self, value):
        self._email_encrypted = encrypt_field(value)

    # --- Encrypted property: totp_secret ---

    @property
    def totp_secret(self):
        return decrypt_field(self._totp_secret_encrypted)

    @totp_secret.setter
    def totp_secret(self, value):
        self._totp_secret_encrypted = encrypt_field(value)

    # --- Email hash computation ---

    @classmethod
    def compute_email_hash(cls, email):
        """Compute HMAC-SHA-256 of the normalised email address.

        Uses ``settings.EMAIL_HASH_KEY`` as the HMAC secret. The email
        is lowercased before hashing to ensure consistent lookups
        regardless of how the user typed their address.

        Args:
            email: Plaintext email address.

        Returns:
            64-character hex string (HMAC-SHA-256 digest).
        """
        return hmac.new(
            settings.EMAIL_HASH_KEY.encode(),
            email.lower().strip().encode(),
            hashlib.sha256,
        ).hexdigest()


# ---------------------------------------------------------------------------
# B) PortalInvite — staff-created invite for a participant to join the portal
# ---------------------------------------------------------------------------

class PortalInvite(models.Model):
    """A single-use invite for a participant to create a portal account.

    Staff generate an invite tied to a ClientFile. The invite includes a
    secure token (URL) and an optional 4-digit verbal code for in-person
    verification. Consent screens are tracked as the participant progresses
    through the onboarding flow.
    """

    STATUS_CHOICES = [
        ("pending", _("Pending")),
        ("accepted", _("Accepted")),
        ("expired", _("Expired")),
        ("revoked", _("Revoked")),
    ]

    client_file = models.ForeignKey(
        "clients.ClientFile",
        on_delete=models.CASCADE,
        related_name="portal_invites",
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="portal_invites_created",
    )

    token = models.CharField(
        max_length=64,
        unique=True,
        default="",
        help_text="URL-safe token generated with secrets.token_urlsafe(48).",
    )
    verbal_code = models.CharField(
        max_length=4,
        blank=True,
        default="",
        help_text="Optional 4-digit code for in-person verbal verification.",
    )

    # Consent tracking
    consent_screens_shown = models.JSONField(
        default=dict,
        blank=True,
        help_text="Maps screen_id to ISO timestamp when shown.",
    )
    consent_document_version = models.CharField(
        max_length=20,
        default="1.0",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "portal"
        db_table = "portal_invites"
        verbose_name = _("portal invite")
        verbose_name_plural = _("portal invites")

    def __str__(self):
        return f"Invite {self.token[:8]}... ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(48)
        super().save(*args, **kwargs)

    @property
    def is_valid(self):
        """True if the invite has not expired and is still pending."""
        return self.status == "pending" and timezone.now() < self.expires_at


# ---------------------------------------------------------------------------
# C) ParticipantJournalEntry — private journal entries written by participant
# ---------------------------------------------------------------------------

class ParticipantJournalEntry(models.Model):
    """A private journal entry written by a participant.

    Journal entries are encrypted at rest and optionally linked to a
    specific plan target (goal). The participant sees these in their
    portal; staff may see them only if the participant has acknowledged
    the journal privacy disclosure.
    """

    participant_user = models.ForeignKey(
        ParticipantUser,
        on_delete=models.CASCADE,
        related_name="journal_entries",
    )
    # Redundant FK ensures CASCADE even if ParticipantUser is deleted first
    client_file = models.ForeignKey(
        "clients.ClientFile",
        on_delete=models.CASCADE,
        related_name="portal_journal_entries",
    )
    plan_target = models.ForeignKey(
        "plans.PlanTarget",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="portal_journal_entries",
    )

    _content_encrypted = models.BinaryField(default=b"")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "portal"
        db_table = "portal_journal_entries"
        ordering = ["-created_at"]
        verbose_name = _("journal entry")
        verbose_name_plural = _("journal entries")

    def __str__(self):
        return f"Journal by {self.participant_user} — {self.created_at:%Y-%m-%d}"

    # --- Encrypted property: content ---

    @property
    def content(self):
        return decrypt_field(self._content_encrypted)

    @content.setter
    def content(self, value):
        self._content_encrypted = encrypt_field(value)


# ---------------------------------------------------------------------------
# D) ParticipantMessage — messages from participant to staff
# ---------------------------------------------------------------------------

class ParticipantMessage(models.Model):
    """A message from a participant to their staff team.

    Messages can be general or pre-session (sent before an upcoming
    appointment). Content is Fernet-encrypted at rest. Staff can archive
    messages once addressed.
    """

    MESSAGE_TYPE_CHOICES = [
        ("general", _("General")),
        ("pre_session", _("Pre-session")),
    ]

    participant_user = models.ForeignKey(
        ParticipantUser,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    client_file = models.ForeignKey(
        "clients.ClientFile",
        on_delete=models.CASCADE,
        related_name="portal_messages",
    )

    message_type = models.CharField(
        max_length=20,
        choices=MESSAGE_TYPE_CHOICES,
    )

    _content_encrypted = models.BinaryField(default=b"")

    created_at = models.DateTimeField(auto_now_add=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "portal"
        db_table = "portal_messages"
        ordering = ["-created_at"]
        verbose_name = _("participant message")
        verbose_name_plural = _("participant messages")

    def __str__(self):
        return f"{self.get_message_type_display()} message by {self.participant_user}"

    # --- Encrypted property: content ---

    @property
    def content(self):
        return decrypt_field(self._content_encrypted)

    @content.setter
    def content(self, value):
        self._content_encrypted = encrypt_field(value)


# ---------------------------------------------------------------------------
# E) CorrectionRequest — participant requests a correction to their record
# ---------------------------------------------------------------------------

class CorrectionRequest(models.Model):
    """A participant's request to correct data in their record.

    Under PHIPA and PIPEDA, participants have the right to request
    corrections to personal information. Staff review the request and
    record the outcome (corrected, discussed, or no change needed).
    """

    DATA_TYPE_CHOICES = [
        ("goal", _("Goal")),
        ("metric", _("Metric")),
        ("reflection", _("Reflection")),
    ]

    STATUS_CHOICES = [
        ("pending", _("Pending")),
        ("discussed", _("Discussed")),
        ("corrected", _("Corrected")),
        ("no_change", _("No change needed")),
    ]

    participant_user = models.ForeignKey(
        ParticipantUser,
        on_delete=models.CASCADE,
        related_name="correction_requests",
    )
    client_file = models.ForeignKey(
        "clients.ClientFile",
        on_delete=models.CASCADE,
        related_name="portal_correction_requests",
    )

    data_type = models.CharField(
        max_length=20,
        choices=DATA_TYPE_CHOICES,
        help_text="What kind of record the participant wants corrected.",
    )
    object_id = models.IntegerField(
        help_text="Primary key of the specific record to correct.",
    )

    _description_encrypted = models.BinaryField(default=b"")

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )
    staff_response = models.TextField(
        blank=True,
        default="",
        help_text="Staff explanation of the correction outcome.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "portal"
        db_table = "portal_correction_requests"
        ordering = ["-created_at"]
        verbose_name = _("correction request")
        verbose_name_plural = _("correction requests")

    def __str__(self):
        return (
            f"Correction ({self.get_data_type_display()}) "
            f"by {self.participant_user} — {self.get_status_display()}"
        )

    # --- Encrypted property: description ---

    @property
    def description(self):
        return decrypt_field(self._description_encrypted)

    @description.setter
    def description(self, value):
        self._description_encrypted = encrypt_field(value)
