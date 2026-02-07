"""Self-service registration models."""
import hashlib
import secrets
import string
from datetime import datetime

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from konote.encryption import decrypt_field, encrypt_field


def generate_unique_slug():
    """Generate a URL-friendly, hard-to-guess slug."""
    return secrets.token_urlsafe(8)


def generate_reference_number():
    """Generate a unique reference number for registration submissions.

    Format: REG-XXXXXXXX (uppercase letters and digits)
    """
    chars = string.ascii_uppercase + string.digits
    random_part = "".join(secrets.choice(chars) for _ in range(8))
    return f"REG-{random_part}"


class RegistrationLink(models.Model):
    """A shareable link for self-service program registration."""

    program = models.ForeignKey(
        "programs.Program",
        on_delete=models.CASCADE,
        related_name="registration_links",
    )
    slug = models.SlugField(unique=True, max_length=50, default=generate_unique_slug)
    title = models.CharField(max_length=255)  # e.g., "Summer Soccer 2025 Registration"
    description = models.TextField(blank=True)  # Instructions shown on form

    # Which custom field groups to show on the form
    field_groups = models.ManyToManyField(
        "clients.CustomFieldGroup",
        blank=True,
        help_text="Custom field groups to include on the registration form.",
    )

    # Options
    auto_approve = models.BooleanField(
        default=False,
        help_text="Automatically approve submissions without staff review.",
    )
    max_registrations = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum number of registrations allowed (leave blank for unlimited).",
    )
    closes_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Registration deadline (leave blank for no deadline).",
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_registration_links",
    )

    class Meta:
        app_label = "registration"
        db_table = "registration_links"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def is_open(self):
        """Check if registration is currently accepting submissions."""
        return self.is_closed_reason is None

    @property
    def spots_remaining(self):
        """Return number of spots left, or None if unlimited."""
        if self.max_registrations is None:
            return None
        approved_count = self.submissions.filter(
            status__in=["pending", "approved"]
        ).count()
        return max(0, self.max_registrations - approved_count)

    @property
    def is_closed_reason(self):
        """Return reason registration is closed, or None if open.

        Possible reasons:
        - "inactive": Link has been deactivated
        - "deadline": Registration deadline has passed
        - "capacity": Maximum registrations reached
        """
        if not self.is_active:
            return "inactive"
        if self.closes_at and self.closes_at <= timezone.now():
            return "deadline"
        if self.spots_remaining is not None and self.spots_remaining <= 0:
            return "capacity"
        return None

    def get_absolute_url(self):
        """Return the public registration URL."""
        from django.urls import reverse
        return reverse("registration:public_registration_form", kwargs={"slug": self.slug})


class RegistrationSubmission(models.Model):
    """A submitted registration awaiting review or auto-approved."""

    STATUS_CHOICES = [
        ("pending", _("Pending Review")),
        ("approved", _("Approved")),
        ("rejected", _("Rejected")),
        ("waitlist", _("Waitlisted")),
    ]

    registration_link = models.ForeignKey(
        RegistrationLink,
        on_delete=models.CASCADE,
        related_name="submissions",
    )

    # Core PII — encrypted like ClientFile
    _first_name_encrypted = models.BinaryField(default=b"")
    _last_name_encrypted = models.BinaryField(default=b"")
    _email_encrypted = models.BinaryField(default=b"", blank=True)
    _phone_encrypted = models.BinaryField(default=b"", blank=True)

    # For duplicate detection without decryption
    email_hash = models.CharField(max_length=64, blank=True, db_index=True)

    # Custom field values stored as JSON
    field_values = models.JSONField(default=dict, blank=True)

    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    client_file = models.ForeignKey(
        "clients.ClientFile",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="registration_submissions",
    )

    # Reference number for confirmation
    reference_number = models.CharField(max_length=20, unique=True, blank=True)

    # Metadata
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_submissions",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)

    class Meta:
        app_label = "registration"
        db_table = "registration_submissions"
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.reference_number} - {self.first_name} {self.last_name}"

    def save(self, *args, **kwargs):
        """Generate reference number and email hash if not set."""
        if not self.reference_number:
            # Generate unique reference number
            for _ in range(10):  # Try up to 10 times to avoid collisions
                ref = generate_reference_number()
                if not RegistrationSubmission.objects.filter(reference_number=ref).exists():
                    self.reference_number = ref
                    break
            else:
                # Fallback with timestamp
                self.reference_number = f"REG-{secrets.token_hex(4).upper()}"

        # Update email hash if email is set
        if self._email_encrypted:
            email = self.email.lower().strip() if self.email else ""
            if email:
                self.email_hash = hashlib.sha256(email.encode()).hexdigest()

        super().save(*args, **kwargs)

    # Encrypted property accessors
    @property
    def first_name(self):
        return decrypt_field(self._first_name_encrypted)

    @first_name.setter
    def first_name(self, value):
        self._first_name_encrypted = encrypt_field(value)

    @property
    def last_name(self):
        return decrypt_field(self._last_name_encrypted)

    @last_name.setter
    def last_name(self, value):
        self._last_name_encrypted = encrypt_field(value)

    @property
    def email(self):
        return decrypt_field(self._email_encrypted)

    @email.setter
    def email(self, value):
        self._email_encrypted = encrypt_field(value)
        # Update hash when email is set
        if value:
            self.email_hash = hashlib.sha256(value.lower().strip().encode()).hexdigest()
        else:
            self.email_hash = ""

    @property
    def phone(self):
        return decrypt_field(self._phone_encrypted)

    @phone.setter
    def phone(self, value):
        self._phone_encrypted = encrypt_field(value)

    def get_status_display_class(self):
        """Return CSS class for status badge styling."""
        return {
            "pending": "secondary",
            "approved": "success",
            "rejected": "danger",
            "waitlist": "warning",
        }.get(self.status, "secondary")
