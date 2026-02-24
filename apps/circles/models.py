"""Circle models — family, household, and support network groupings.

Circles Lite (Phase 1): minimal viable implementation following the
Design Rationale Record in tasks/design-rationale/circles-family-entity.md.

Key constraints (from two expert panels):
- No program FK — circles are cross-program; visibility derived from membership
- No global relationships — circle-scoped only (PHIPA containment)
- No separate CircleNote model — ProgressNote gets an optional circle FK
- No circle_type enum — a circle is a circle
- No RelationshipType table — free-text relationship_label
"""
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from konote.encryption import decrypt_field, encrypt_field


# ---------------------------------------------------------------------------
# 1. Circle
# ---------------------------------------------------------------------------

class CircleQuerySet(models.QuerySet):
    """Custom queryset for Circle with demo/real filtering."""

    def real(self):
        """Return only real (non-demo) circles."""
        return self.filter(is_demo=False)

    def demo(self):
        """Return only demo circles."""
        return self.filter(is_demo=True)


class CircleManager(models.Manager):
    """Custom manager for Circle that enforces demo data separation."""

    def get_queryset(self):
        return CircleQuerySet(self.model, using=self._db)

    def real(self):
        return self.get_queryset().real()

    def demo(self):
        return self.get_queryset().demo()


class Circle(models.Model):
    """A circle of connected people — family, household, or support network.

    Circle names are encrypted (PII — names reveal family relationships).
    No program FK: circles are cross-program by design. Visibility is
    derived from membership (see helpers.get_visible_circles).
    """

    STATUS_CHOICES = [
        ("active", _("Active")),
        ("archived", _("Archived")),
    ]

    _name_encrypted = models.BinaryField(default=b"")
    status = models.CharField(max_length=20, default="active", choices=STATUS_CHOICES)
    is_demo = models.BooleanField(
        default=False,
        help_text="Demo circles are only visible to demo users.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_circles",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CircleManager()

    class Meta:
        app_label = "circles"
        db_table = "circles"
        ordering = ["-updated_at"]

    @property
    def name(self):
        return decrypt_field(self._name_encrypted)

    @name.setter
    def name(self, value):
        self._name_encrypted = encrypt_field(value)

    def __str__(self):
        return self.name or f"Circle #{self.pk}"


# ---------------------------------------------------------------------------
# 2. CircleMembership
# ---------------------------------------------------------------------------

class CircleMembership(models.Model):
    """Links a participant (or named non-participant) to a circle.

    Non-participants use member_name (client_file is null). To "promote"
    a non-participant, set client_file and clear member_name — no complex
    merge logic needed.
    """

    STATUS_CHOICES = [
        ("active", _("Active")),
        ("inactive", _("Inactive")),
    ]

    circle = models.ForeignKey(
        Circle,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    # Nullable — non-participants just have a name stored in member_name.
    client_file = models.ForeignKey(
        "clients.ClientFile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="circle_memberships",
    )
    member_name = models.CharField(max_length=255, blank=True, default="")
    relationship_label = models.CharField(
        max_length=100, blank=True, default="",
        help_text="Free text — e.g. parent, spouse, sibling, grandparent.",
    )
    is_primary_contact = models.BooleanField(default=False)
    status = models.CharField(max_length=20, default="active", choices=STATUS_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "circles"
        db_table = "circle_memberships"
        # Prevent the same participant from being added to the same circle twice.
        # NULL client_file won't match (PostgreSQL NULL != NULL), so non-participant
        # duplicates are allowed (same name can appear in same circle if needed).
        constraints = [
            models.UniqueConstraint(
                fields=["circle", "client_file"],
                name="unique_circle_client_file",
                condition=models.Q(client_file__isnull=False, status="active"),
            ),
        ]

    @property
    def display_name(self):
        """Return client's display name + last name if linked, otherwise member_name."""
        if self.client_file:
            first = self.client_file.display_name or ""
            last = self.client_file.last_name or ""
            full = f"{first} {last}".strip()
            return full or f"Participant #{self.client_file.pk}"
        return self.member_name or _("Unknown")

    def __str__(self):
        return self.display_name
