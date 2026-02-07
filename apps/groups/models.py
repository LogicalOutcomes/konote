"""Group-based service delivery models.

Supports three group types:
- Service groups: ongoing groups tied to a program (e.g., weekly support circle)
- Activity groups: one-off or recurring activities (e.g., field trips, workshops)
- Projects: goal-oriented work with milestones and outcomes
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from konote.encryption import decrypt_field, encrypt_field


# ---------------------------------------------------------------------------
# 1. Group
# ---------------------------------------------------------------------------

class Group(models.Model):
    """A group that delivers services, activities, or projects."""

    GROUP_TYPE_CHOICES = [
        ("service_group", _("Service Group")),
        ("activity_group", _("Activity Group")),
        ("project", _("Project")),
    ]

    STATUS_CHOICES = [
        ("active", _("Active")),
        ("archived", _("Archived")),
    ]

    name = models.CharField(max_length=255)
    group_type = models.CharField(max_length=20, choices=GROUP_TYPE_CHOICES)
    program = models.ForeignKey(
        "programs.Program",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="groups",
    )
    description = models.TextField(default="", blank=True)
    status = models.CharField(max_length=20, default="active", choices=STATUS_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "groups"
        db_table = "groups"
        ordering = ["name"]

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# 2. GroupMembership
# ---------------------------------------------------------------------------

class GroupMembership(models.Model):
    """Links a client (or named non-client) to a group."""

    ROLE_CHOICES = [
        ("member", _("Member")),
        ("leader", _("Leader")),
    ]

    STATUS_CHOICES = [
        ("active", _("Active")),
        ("inactive", _("Inactive")),
    ]

    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    # Nullable — non-clients just have a name stored in member_name.
    client_file = models.ForeignKey(
        "clients.ClientFile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="group_memberships",
    )
    member_name = models.CharField(max_length=255, blank=True, default="")
    role = models.CharField(max_length=20, default="member", choices=ROLE_CHOICES)
    status = models.CharField(max_length=20, default="active", choices=STATUS_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "groups"
        db_table = "group_memberships"
        # unique_together won't enforce uniqueness when client_file is NULL,
        # so we use a conditional constraint instead.
        constraints = [
            models.UniqueConstraint(
                fields=["group", "client_file"],
                name="unique_group_client_file",
                condition=models.Q(client_file__isnull=False, status="active"),
            ),
        ]

    @property
    def display_name(self):
        """Return client's display name + last name if linked, otherwise the member_name."""
        if self.client_file:
            first = self.client_file.display_name or ""
            last = self.client_file.last_name or ""
            full = f"{first} {last}".strip()
            return full or f"Client #{self.client_file.pk}"
        return self.member_name or "Unknown"

    def __str__(self):
        return self.display_name


# ---------------------------------------------------------------------------
# 3. GroupSession
# ---------------------------------------------------------------------------

class GroupSession(models.Model):
    """A single session (meeting/event) for a group."""

    GROUP_VIBE_CHOICES = [
        ("", _("Not recorded")),
        ("rough", _("Rough")),
        ("low", _("Low")),
        ("solid", _("Solid")),
        ("great", _("Great")),
    ]

    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name="sessions",
    )
    session_date = models.DateField()
    facilitator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="facilitated_sessions",
    )
    group_vibe = models.CharField(
        max_length=10,
        choices=GROUP_VIBE_CHOICES,
        blank=True,
        default="",
    )

    # Encrypted session notes
    _notes_encrypted = models.BinaryField(default=b"", blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "groups"
        db_table = "group_sessions"
        ordering = ["-session_date"]

    @property
    def notes(self):
        return decrypt_field(self._notes_encrypted)

    @notes.setter
    def notes(self, value):
        self._notes_encrypted = encrypt_field(value or "")

    def __str__(self):
        return f"{self.group.name} — {self.session_date}"


# ---------------------------------------------------------------------------
# 4. GroupSessionAttendance
# ---------------------------------------------------------------------------

class GroupSessionAttendance(models.Model):
    """Tracks whether a member attended a session.

    Rec #9: defaults to present — the facilitator unchecks absentees rather
    than checking everyone who showed up.
    """

    group_session = models.ForeignKey(
        GroupSession,
        on_delete=models.CASCADE,
        related_name="attendance_records",
    )
    membership = models.ForeignKey(
        GroupMembership,
        on_delete=models.CASCADE,
        related_name="attendance_records",
    )
    present = models.BooleanField(default=True)

    class Meta:
        app_label = "groups"
        db_table = "group_session_attendance"
        unique_together = ["group_session", "membership"]

    def __str__(self):
        status = "present" if self.present else "absent"
        return f"{self.membership} — {status}"


# ---------------------------------------------------------------------------
# 5. GroupSessionHighlight
# ---------------------------------------------------------------------------

class GroupSessionHighlight(models.Model):
    """An individual highlight or observation about a member during a session.

    Rec #3: FK to GroupMembership (not ClientFile) so the highlight is tied
    to the member's role within this specific group.
    """

    group_session = models.ForeignKey(
        GroupSession,
        on_delete=models.CASCADE,
        related_name="highlights",
    )
    membership = models.ForeignKey(
        GroupMembership,
        on_delete=models.CASCADE,
        related_name="highlights",
    )

    # Encrypted highlight notes
    _notes_encrypted = models.BinaryField(default=b"", blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "groups"
        db_table = "group_session_highlights"

    @property
    def notes(self):
        return decrypt_field(self._notes_encrypted)

    @notes.setter
    def notes(self, value):
        self._notes_encrypted = encrypt_field(value or "")

    def __str__(self):
        return f"Highlight: {self.membership} — {self.group_session}"


# ---------------------------------------------------------------------------
# 6. ProjectMilestone
# ---------------------------------------------------------------------------

class ProjectMilestone(models.Model):
    """A milestone within a project-type group."""

    STATUS_CHOICES = [
        ("not_started", _("Not Started")),
        ("in_progress", _("In Progress")),
        ("complete", _("Complete")),
    ]

    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name="milestones",
    )
    title = models.CharField(max_length=255)
    status = models.CharField(max_length=20, default="not_started", choices=STATUS_CHOICES)
    due_date = models.DateField(null=True, blank=True)
    completed_date = models.DateField(null=True, blank=True)
    notes = models.TextField(default="", blank=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "groups"
        db_table = "project_milestones"
        ordering = ["sort_order"]

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"


# ---------------------------------------------------------------------------
# 7. ProjectOutcome
# ---------------------------------------------------------------------------

class ProjectOutcome(models.Model):
    """A recorded outcome or result for a project-type group.

    Rec #8: created_by tracks which staff member recorded the outcome.
    """

    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name="outcomes",
    )
    outcome_date = models.DateField()
    description = models.TextField()
    evidence = models.TextField(default="", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_outcomes",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "groups"
        db_table = "project_outcomes"
        ordering = ["-outcome_date"]

    def __str__(self):
        return f"{self.group.name} outcome — {self.outcome_date}"
