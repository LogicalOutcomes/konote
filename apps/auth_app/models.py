"""Custom user model with Azure AD and local auth support."""
import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from konote.encryption import decrypt_field, encrypt_field


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
        return decrypt_field(self._email_encrypted)

    @email.setter
    def email(self, value):
        self._email_encrypted = encrypt_field(value)


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
