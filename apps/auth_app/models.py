"""Custom user model with Azure AD and local auth support."""
import hashlib
import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from konote.encryption import decrypt_field, encrypt_field, DecryptionError


class UserManager(BaseUserManager):
    """Manager for the custom User model."""

    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError("Username is required.")
        user = self.model(username=username, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault("is_admin", True)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(username, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user supporting both Azure AD SSO and local password auth.

    Roles:
        is_admin = True → system configuration (programs, users, settings) — no client data
        UserProgramRole with role='program_manager' → Program Manager: all data in assigned programs
        UserProgramRole with role='staff' → Direct Service: full client records in assigned programs
        UserProgramRole with role='receptionist' (displayed as "Front Desk"): limited client info in assigned programs
    """

    # Identity
    username = models.CharField(max_length=150, unique=True)
    external_id = models.CharField(
        max_length=255, unique=True, null=True, blank=True,
        help_text="Azure AD object ID for SSO users.",
    )
    display_name = models.CharField(max_length=255)
    _email_encrypted = models.BinaryField(default=b"", blank=True)

    # Roles
    is_admin = models.BooleanField(default=False, help_text="Full instance access.")
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False, help_text="Django admin access (rarely used).")
    is_demo = models.BooleanField(
        default=False,
        help_text="Demo users see demo data only. Set at creation, never changed.",
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_at = models.DateTimeField(null=True, blank=True)

    # Language preference (synced on login for multi-device roaming)
    preferred_language = models.CharField(
        max_length=10, default="", blank=True,
        help_text="Stored on login. Empty = use cookie/session preference.",
    )

    # GDPR readiness
    consent_given_at = models.DateTimeField(null=True, blank=True)
    data_retention_days = models.IntegerField(default=2555, help_text="~7 years default.")

    # MFA (TOTP) — local auth only; Azure AD users get MFA from Microsoft
    mfa_enabled = models.BooleanField(default=False)
    _mfa_secret_encrypted = models.BinaryField(default=b"", blank=True)
    mfa_backup_codes = models.JSONField(default=list, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["display_name"]

    class Meta:
        app_label = "auth_app"
        db_table = "users"

    def __str__(self):
        return self.display_name or self.username

    def get_display_name(self):
        return self.display_name or self.username

    # Encrypted email property
    @property
    def email(self):
        try:
            return decrypt_field(self._email_encrypted)
        except DecryptionError:
            return "[DECRYPTION ERROR]"

    @email.setter
    def email(self, value):
        self._email_encrypted = encrypt_field(value)

    # Encrypted MFA secret property
    @property
    def mfa_secret(self):
        try:
            return decrypt_field(self._mfa_secret_encrypted)
        except DecryptionError:
            return "[DECRYPTION ERROR]"

    @mfa_secret.setter
    def mfa_secret(self, value):
        self._mfa_secret_encrypted = encrypt_field(value)

    # Hashed backup code helpers
    @staticmethod
    def _hash_code(code):
        """SHA-256 hash a backup code for storage."""
        return hashlib.sha256(code.encode("utf-8")).hexdigest()

    def set_backup_codes(self, plaintext_codes):
        """Store backup codes as SHA-256 hashes."""
        self.mfa_backup_codes = [self._hash_code(c) for c in plaintext_codes]

    def check_backup_code(self, code):
        """Verify and consume a backup code. Returns True if valid."""
        hashed = self._hash_code(code)
        if hashed in self.mfa_backup_codes:
            self.mfa_backup_codes.remove(hashed)
            self.save(update_fields=["mfa_backup_codes"])
            return True
        return False


class Invite(models.Model):
    """Single-use invite link for new user registration.

    An admin creates an invite with a role and optional program assignments.
    The new user visits the link, creates their own username/password,
    and is automatically assigned the specified role and programs.
    """

    ROLE_CHOICES = [
        ("receptionist", _("Front Desk")),
        ("staff", _("Direct Service")),
        ("program_manager", _("Program Manager")),
        ("executive", _("Executive")),
        ("admin", _("Administrator")),
    ]

    code = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    programs = models.ManyToManyField(
        "programs.Program", blank=True,
        help_text="Programs to assign. Not used for admin invites.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="invites_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        help_text="Invite expires after this date.",
    )
    used_by = models.OneToOneField(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="used_invite",
    )
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "auth_app"
        db_table = "invites"

    def __str__(self):
        return f"Invite {self.code} ({self.get_role_display()})"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_used(self):
        return self.used_by is not None

    @property
    def is_valid(self):
        return not self.is_expired and not self.is_used


class AccessGrantReason(models.Model):
    """Configurable justification reasons for GATED clinical access.

    Agencies can add, rename, or deactivate reasons. Five defaults are
    created automatically by data migration.
    """

    label = models.CharField(max_length=100)
    label_fr = models.CharField(
        max_length=100, blank=True, default="",
        help_text="French translation. Leave blank to use English label.",
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "auth_app"
        db_table = "access_grant_reasons"
        ordering = ["sort_order", "label"]

    def __str__(self):
        return self.label


class AccessGrant(models.Model):
    """Records a PM's documented justification for viewing clinical data.

    Only enforced at Tier 3 (Clinical Safeguards). At Tiers 1-2, GATED
    permissions are relaxed to ALLOW automatically by the decorator.

    Two grant scopes:
    - Program-level: grants access to all clinical data in a program
      (routine supervision). client_file is null.
    - Client-level: grants access to a specific client's clinical data
      (cross-program or targeted review). client_file is set.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="access_grants",
    )
    program = models.ForeignKey(
        "programs.Program",
        on_delete=models.CASCADE,
        related_name="access_grants",
    )
    client_file = models.ForeignKey(
        "clients.ClientFile",
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="access_grants",
        help_text="If null, grant covers all clients in the program.",
    )
    reason = models.ForeignKey(
        AccessGrantReason,
        on_delete=models.PROTECT,
        related_name="grants",
    )
    justification = models.TextField(
        help_text="Brief description of why access is needed.",
    )
    granted_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = "auth_app"
        db_table = "access_grants"
        ordering = ["-granted_at"]

    def __str__(self):
        scope = f"client {self.client_file_id}" if self.client_file_id else f"program {self.program_id}"
        return f"Grant #{self.pk} for {self.user} → {scope}"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        return self.is_active and not self.is_expired
