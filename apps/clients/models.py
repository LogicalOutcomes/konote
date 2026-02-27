"""Client file and custom field models."""
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from konote.encryption import decrypt_field, encrypt_field, DecryptionError


class ClientFileQuerySet(models.QuerySet):
    """Custom queryset for ClientFile with demo/real filtering."""

    def real(self):
        """Return only real (non-demo) clients."""
        return self.filter(is_demo=False)

    def demo(self):
        """Return only demo clients."""
        return self.filter(is_demo=True)


class ClientFileManager(models.Manager):
    """
    Custom manager for ClientFile that enforces demo data separation.

    Security requirement: Views should use .real() or .demo() to explicitly
    filter by demo status. Using .all() without filtering is discouraged.
    """

    def get_queryset(self):
        return ClientFileQuerySet(self.model, using=self._db)

    def real(self):
        """Return only real (non-demo) clients."""
        return self.get_queryset().real()

    def demo(self):
        """Return only demo clients."""
        return self.get_queryset().demo()


class ClientFile(models.Model):
    """A client record with encrypted PII fields."""

    STATUS_CHOICES = [
        ("active", _("Active")),
        ("inactive", _("Inactive")),
        ("discharged", _("Discharged")),
    ]

    # Encrypted PII
    _first_name_encrypted = models.BinaryField(default=b"")
    _preferred_name_encrypted = models.BinaryField(default=b"", blank=True)
    _middle_name_encrypted = models.BinaryField(default=b"", blank=True)
    _last_name_encrypted = models.BinaryField(default=b"")
    _birth_date_encrypted = models.BinaryField(default=b"", blank=True)
    _phone_encrypted = models.BinaryField(default=b"", blank=True)

    record_id = models.CharField(max_length=100, default="", blank=True)
    status = models.CharField(max_length=20, default="active", choices=STATUS_CHOICES)
    status_reason = models.TextField(default="", blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Demo data separation
    is_demo = models.BooleanField(
        default=False,
        help_text="Demo clients are only visible to demo users. Set at creation, never changed.",
    )

    # GDPR readiness
    consent_given_at = models.DateTimeField(null=True, blank=True)
    consent_type = models.CharField(max_length=50, default="", blank=True)
    retention_expires = models.DateField(null=True, blank=True)
    erasure_requested = models.BooleanField(default=False)
    erasure_completed_at = models.DateTimeField(null=True, blank=True)

    # Custom manager for demo data separation
    objects = ClientFileManager()

    class Meta:
        app_label = "clients"
        db_table = "client_files"
        ordering = ["-updated_at"]

    # Anonymisation flag — set after PII is stripped
    is_anonymised = models.BooleanField(
        default=False,
        help_text="True after PII has been stripped. Record kept for statistical purposes.",
    )

    # DV safety — hides sensitive custom fields from front desk
    is_dv_safe = models.BooleanField(
        default=False,
        help_text=_(
            "When enabled, DV-sensitive custom fields (address, emergency contact, "
            "employer) are hidden from front desk staff for this participant."
        ),
    )

    def __str__(self):
        if self.is_anonymised:
            return _("[ANONYMISED]")
        return f"{self.display_name} {self.last_name}" if self.display_name else f"Participant #{self.pk}"

    # Encrypted property accessors
    @property
    def first_name(self):
        try:
            return decrypt_field(self._first_name_encrypted)
        except DecryptionError:
            return "[DECRYPTION ERROR]"

    @first_name.setter
    def first_name(self, value):
        self._first_name_encrypted = encrypt_field(value)

    @property
    def preferred_name(self):
        try:
            return decrypt_field(self._preferred_name_encrypted)
        except DecryptionError:
            return "[DECRYPTION ERROR]"

    @preferred_name.setter
    def preferred_name(self, value):
        self._preferred_name_encrypted = encrypt_field(value)

    @property
    def display_name(self):
        """Return preferred name if set, otherwise first name.

        Use this for everyday display (headers, lists, breadcrumbs).
        Use first_name directly for legal/formal contexts (exports, erasure receipts).
        """
        return self.preferred_name or self.first_name

    @property
    def middle_name(self):
        try:
            return decrypt_field(self._middle_name_encrypted)
        except DecryptionError:
            return "[DECRYPTION ERROR]"

    @middle_name.setter
    def middle_name(self, value):
        self._middle_name_encrypted = encrypt_field(value)

    @property
    def last_name(self):
        try:
            return decrypt_field(self._last_name_encrypted)
        except DecryptionError:
            return "[DECRYPTION ERROR]"

    @last_name.setter
    def last_name(self, value):
        self._last_name_encrypted = encrypt_field(value)

    @property
    def birth_date(self):
        try:
            val = decrypt_field(self._birth_date_encrypted)
            return val if val else None
        except DecryptionError:
            return "[DECRYPTION ERROR]"

    @birth_date.setter
    def birth_date(self, value):
        self._birth_date_encrypted = encrypt_field(str(value) if value else "")

    @property
    def phone(self):
        try:
            return decrypt_field(self._phone_encrypted)
        except DecryptionError:
            return "[DECRYPTION ERROR]"

    @phone.setter
    def phone(self, value):
        self._phone_encrypted = encrypt_field(value)

    @property
    def email(self):
        try:
            return decrypt_field(self._email_encrypted)
        except DecryptionError:
            return "[DECRYPTION ERROR]"

    @email.setter
    def email(self, value):
        self._email_encrypted = encrypt_field(value)

    @property
    def initials(self):
        """Return initials for privacy-safe display (e.g. calendar feeds)."""
        first = self.first_name
        last = self.last_name
        return f"{first[0]}{last[0]}" if first and last else "??"

    # Cross-program sharing (PHIPA compliance)
    # Controls whether clinical notes from other programs are visible for this
    # client. "default" follows the agency-level feature toggle. "consent"
    # always shares. "restrict" never shares across programs.
    SHARING_CHOICES = [
        ("default", _("Follow agency setting")),
        ("consent", _("Share across programs")),
        ("restrict", _("Restrict to one program")),
    ]
    cross_program_sharing = models.CharField(
        max_length=20,
        choices=SHARING_CHOICES,
        default="default",
        help_text=_(
            "Controls whether clinical notes are visible across programs "
            "for this participant. Most participants use the agency default."
        ),
    )

    # ── Messaging consent & contact fields (Phase 3) ──────────────────

    # Encrypted email (same pattern as phone)
    _email_encrypted = models.BinaryField(default=b"", blank=True)

    # Quick existence checks without decryption
    has_email = models.BooleanField(default=False)
    has_phone = models.BooleanField(default=False)

    # Phone number staleness tracking
    phone_last_confirmed = models.DateField(null=True, blank=True)

    # Client's preferred language for messages (not UI language)
    preferred_language = models.CharField(
        max_length=5,
        choices=[("en", _("English")), ("fr", _("French"))],
        default="en",
    )

    # Contact preferences
    preferred_contact_method = models.CharField(
        max_length=10,
        choices=[
            ("sms", _("Text Message")),
            ("email", _("Email")),
            ("both", _("Both")),
            ("none", _("None")),
        ],
        default="none",
        blank=True,
    )

    # CASL consent tracking — full model in DB, simple UI
    sms_consent = models.BooleanField(default=False)
    sms_consent_date = models.DateField(null=True, blank=True)
    email_consent = models.BooleanField(default=False)
    email_consent_date = models.DateField(null=True, blank=True)
    consent_messaging_type = models.CharField(
        max_length=10,
        choices=[("express", _("Express")), ("implied", _("Implied"))],
        default="express",
        blank=True,
    )

    # Consent withdrawal tracking (CASL requires proof)
    sms_consent_withdrawn_date = models.DateField(null=True, blank=True)
    email_consent_withdrawn_date = models.DateField(null=True, blank=True)
    consent_notes = models.TextField(blank=True, default="")

    def save(self, *args, **kwargs):
        # Auto-set existence flags for quick checks without decryption
        self.has_phone = bool(self._phone_encrypted and self._phone_encrypted != b"")
        self.has_email = bool(self._email_encrypted and self._email_encrypted != b"")
        super().save(*args, **kwargs)

    def get_visible_fields(self, role):
        """Return dict of field visibility for a given role.

        For non-receptionist roles: all fields visible (subject to clinical
        permission check for clinical fields).

        For receptionist at Tier 1: safe defaults from FieldAccessConfig.
        For receptionist at Tier 2+: per-field config from FieldAccessConfig
        (admin-configurable via the field access page).

        Custom fields (EAV) are NOT covered here — they use the per-field
        front_desk_access setting on CustomFieldDefinition instead.

        Usage in templates:
            {% if visible_fields.birth_date %}{{ client.birth_date }}{% endif %}
            {% if visible_fields.phone_editable %}...edit form...{% endif %}
        """
        from apps.auth_app.permissions import can_access, ALLOW, PROGRAM, GATED

        # All core fields
        all_fields = {
            'first_name', 'last_name', 'preferred_name', 'display_name',
            'middle_name', 'phone', 'email', 'record_id', 'status',
            'birth_date',
        }

        visible = {}

        if role == 'receptionist':
            # Always-visible fields (identity + status)
            for f in FieldAccessConfig.ALWAYS_VISIBLE:
                visible[f] = True

            # Configurable fields — check FieldAccessConfig
            access_map = FieldAccessConfig.get_all_access()
            for field_name, access_level in access_map.items():
                visible[field_name] = access_level in ('view', 'edit')
                visible[f'{field_name}_editable'] = access_level == 'edit'

            # Clinical fields are always hidden from receptionist
            visible['birth_date'] = access_map.get('birth_date', 'none') in ('view', 'edit')
            visible['birth_date_editable'] = access_map.get('birth_date', 'none') == 'edit'

        else:
            # Non-receptionist: all fields visible
            for f in all_fields:
                visible[f] = True
                visible[f'{f}_editable'] = True

            # Clinical fields depend on role permission
            clinical_access = can_access(role, 'client.view_clinical')
            has_clinical = clinical_access in (ALLOW, PROGRAM, GATED)
            visible['birth_date'] = has_clinical
            visible['birth_date_editable'] = has_clinical

        return visible


class ServiceEpisode(models.Model):
    """A service episode linking a client to a program.

    Extended from the original ClientProgramEnrolment with FHIR-informed
    fields for richer lifecycle tracking. Keeps the same database table.
    """

    STATUS_CHOICES = [
        ("planned", _("Planned")),
        ("waitlist", _("Waitlisted")),
        ("active", _("Active")),
        ("on_hold", _("On Hold")),
        ("finished", _("Finished")),
        ("cancelled", _("Cancelled")),
    ]

    # Statuses that grant staff access to the client file.
    # Used by middleware, access.py, client list, and search.
    # Update this ONE place when adding new accessible statuses.
    ACCESSIBLE_STATUSES = ["active", "on_hold"]

    EPISODE_TYPE_CHOICES = [
        ("new_intake", _("New Intake")),
        ("re_enrolment", _("Re-enrolment")),
        ("transfer_in", _("Transfer In")),
        ("crisis", _("Crisis")),
        ("short_term", _("Short-term")),
    ]

    REFERRAL_SOURCE_CHOICES = [
        ("", _("— Not specified —")),
        ("self", _("Self")),
        ("family", _("Family")),
        ("agency_internal", _("Agency (internal)")),
        ("agency_external", _("Agency (external)")),
        ("healthcare", _("Healthcare")),
        ("school", _("School")),
        ("court", _("Court")),
        ("shelter", _("Shelter")),
        ("community", _("Community")),
        ("other", _("Other")),
    ]

    END_REASON_CHOICES = [
        ("", _("— Not specified —")),
        ("completed", _("Completed")),
        ("goals_met", _("Goals Met")),
        ("withdrew", _("Withdrew")),
        ("transferred", _("Transferred")),
        ("referred_out", _("Referred Out")),
        ("lost_contact", _("Lost Contact")),
        ("moved", _("Moved")),
        ("ineligible", _("Ineligible")),
        ("deceased", _("Deceased")),
        ("other", _("Other")),
    ]

    # --- Original fields (preserved) ---
    client_file = models.ForeignKey(ClientFile, on_delete=models.CASCADE, related_name="enrolments")
    program = models.ForeignKey("programs.Program", on_delete=models.CASCADE, related_name="client_enrolments")
    status = models.CharField(max_length=20, default="active", choices=STATUS_CHOICES)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    unenrolled_at = models.DateTimeField(null=True, blank=True)

    # --- New FHIR-informed fields ---
    status_reason = models.TextField(
        blank=True, default="",
        help_text=_("Why the status changed."),
    )
    episode_type = models.CharField(
        max_length=20, blank=True, default="",
        choices=EPISODE_TYPE_CHOICES,
        help_text=_("Auto-derived from enrolment history. Do not set manually."),
    )
    primary_worker = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="primary_episodes",
        help_text=_("Assigned case worker."),
    )
    referral_source = models.CharField(
        max_length=30, blank=True, default="",
        choices=REFERRAL_SOURCE_CHOICES,
    )
    started_at = models.DateTimeField(
        null=True, blank=True,
        help_text=_("When active service began."),
    )
    ended_at = models.DateTimeField(
        null=True, blank=True,
        help_text=_("When service ended."),
    )
    end_reason = models.CharField(
        max_length=30, blank=True, default="",
        choices=END_REASON_CHOICES,
    )

    class Meta:
        app_label = "clients"
        db_table = "client_program_enrolments"

    def __str__(self):
        return f"{self.client_file} → {self.program}"

    def derive_episode_type(self):
        """Auto-derive episode_type from enrolment history.

        Rules:
        - No prior episodes for this client × program → new_intake
        - Has a prior finished episode in this program → re_enrolment
        - Has a prior episode that ended with transferred from another program → transfer_in
        - crisis and short_term are set explicitly by admin (not auto-derived)
        """
        # Don't override admin-set types
        if self.episode_type in ("crisis", "short_term"):
            return self.episode_type

        prior_same_program = ServiceEpisode.objects.filter(
            client_file=self.client_file,
            program=self.program,
            status="finished",
        ).exclude(pk=self.pk)

        if prior_same_program.exists():
            return "re_enrolment"

        # Check for transfer_in: prior episode in ANY program ended with transferred
        prior_transferred = ServiceEpisode.objects.filter(
            client_file=self.client_file,
            end_reason="transferred",
            status="finished",
        ).exclude(program=self.program).exclude(pk=self.pk)

        if prior_transferred.exists():
            return "transfer_in"

        return "new_intake"

    def save(self, *args, **kwargs):
        # Auto-derive episode_type on first save if not explicitly set
        is_new = self.pk is None
        if is_new and not self.episode_type:
            self.episode_type = self.derive_episode_type()
        # Set started_at from enrolled_at if not set
        if is_new and not self.started_at:
            self.started_at = self.enrolled_at or timezone.now()
        super().save(*args, **kwargs)


# Backwards compatibility — all existing imports continue working
ClientProgramEnrolment = ServiceEpisode


class ServiceEpisodeStatusChange(models.Model):
    """Append-only history of status changes for a service episode.

    Every time ServiceEpisode.status changes, a row is appended here.
    Also written to AuditLog for the separate compliance trail.
    """

    episode = models.ForeignKey(
        ServiceEpisode, on_delete=models.CASCADE,
        related_name="status_changes",
    )
    status = models.CharField(
        max_length=20,
        help_text="The new status value.",
    )
    reason = models.TextField(
        blank=True, default="",
        help_text="Why the status changed.",
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL,
    )
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "clients"
        db_table = "service_episode_status_changes"
        ordering = ["changed_at"]
        indexes = [
            models.Index(fields=["episode", "changed_at"]),
        ]

    def __str__(self):
        return f"Episode #{self.episode_id} → {self.status}"


class ClientAccessBlock(models.Model):
    """Block a specific user from accessing a specific client's records.

    Used for conflict of interest, dual relationships, and DV safety.
    Checked FIRST in get_client_or_403 — overrides all other access.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="access_blocks",
    )
    client_file = models.ForeignKey(
        "ClientFile",
        on_delete=models.CASCADE,
        related_name="access_blocks",
    )
    reason = models.TextField(
        help_text="Why this block exists (e.g., conflict of interest, safety concern)",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_access_blocks",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = "clients"
        db_table = "client_access_blocks"
        unique_together = ("user", "client_file")
        verbose_name = "Client Access Block"
        verbose_name_plural = "Client Access Blocks"

    def __str__(self):
        return f"Block: {self.user} cannot access {self.client_file}"


class DvFlagRemovalRequest(models.Model):
    """Two-person-rule workflow for removing a DV safety flag.

    Step 1: A staff member recommends removal (requested_by + reason).
    Step 2: A program manager reviews and approves or rejects (reviewed_by).

    Until approved, is_dv_safe stays True on the ClientFile. If rejected,
    the request is closed and a new request can be made.
    """

    client_file = models.ForeignKey(
        ClientFile,
        on_delete=models.CASCADE,
        related_name="dv_removal_requests",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="+",
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(
        help_text=_("Explain why the DV safety flag should be removed."),
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    approved = models.BooleanField(
        null=True,
        blank=True,
        default=None,
        help_text="None = pending, True = approved (flag removed), False = rejected.",
    )
    review_note = models.TextField(
        default="",
        blank=True,
        help_text=_("Reviewer's note on approval or rejection."),
    )

    class Meta:
        app_label = "clients"
        db_table = "dv_flag_removal_requests"
        ordering = ["-requested_at"]

    def __str__(self):
        status = "pending" if self.approved is None else ("approved" if self.approved else "rejected")
        return f"DV removal request for {self.client_file} ({status})"

    @property
    def is_pending(self):
        return self.approved is None


class CustomFieldGroup(models.Model):
    """A group of custom fields (e.g., 'Contact Information', 'Demographics')."""

    title = models.CharField(max_length=255)
    sort_order = models.IntegerField(default=0)
    status = models.CharField(
        max_length=20, default="active",
        choices=[("active", "Active"), ("archived", "Archived")],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "clients"
        db_table = "custom_field_groups"
        ordering = ["sort_order"]

    def __str__(self):
        return self.title


class CustomFieldDefinition(models.Model):
    """A single custom field definition within a group."""

    INPUT_TYPE_CHOICES = [
        ("text", _("Text")),
        ("textarea", _("Text Area")),
        ("select", _("Dropdown")),
        ("select_other", _("Dropdown with Other option")),
        ("date", _("Date")),
        ("number", _("Number")),
    ]

    VALIDATION_TYPE_CHOICES = [
        ("none", _("None")),
        ("postal_code", _("Canadian Postal Code")),
        ("phone", _("Phone Number")),
        ("email", _("Email Address")),
    ]

    group = models.ForeignKey(CustomFieldGroup, on_delete=models.CASCADE, related_name="fields")
    name = models.CharField(max_length=255)
    input_type = models.CharField(max_length=20, choices=INPUT_TYPE_CHOICES, default="text")
    placeholder = models.CharField(max_length=255, default="", blank=True)
    is_required = models.BooleanField(default=False)
    is_sensitive = models.BooleanField(default=False, help_text="Encrypt this field's values.")
    front_desk_access = models.CharField(
        max_length=10,
        default="none",
        choices=[
            ("none", "Hidden"),
            ("view", "View only"),
            ("edit", "View and edit"),
        ],
        help_text="What access front desk staff have to this field.",
    )
    is_dv_sensitive = models.BooleanField(
        default=False,
        help_text=_(
            "When checked, this field is hidden from front desk staff "
            "for participants with a DV safety flag."
        ),
    )
    # Determines which validation and normalisation rules apply (I18N-FIX2).
    # Auto-detected from field name on first save if not explicitly set.
    validation_type = models.CharField(
        max_length=20,
        choices=VALIDATION_TYPE_CHOICES,
        default="none",
        help_text="Determines which validation and normalisation rules apply to this field.",
    )
    options_json = models.JSONField(default=list, blank=True, help_text="Options for select fields.")
    sort_order = models.IntegerField(default=0)
    status = models.CharField(
        max_length=20, default="active",
        choices=[("active", "Active"), ("archived", "Archived")],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "clients"
        db_table = "custom_field_definitions"
        ordering = ["sort_order"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Auto-detect validation type on first save if not explicitly set
        if not self.validation_type or self.validation_type == "none":
            from .validators import detect_validation_type
            detected = detect_validation_type(self.name)
            if detected != "none":
                self.validation_type = detected
        super().save(*args, **kwargs)


class ClientDetailValue(models.Model):
    """A custom field value for a specific client (EAV pattern)."""

    client_file = models.ForeignKey(ClientFile, on_delete=models.CASCADE, related_name="detail_values")
    field_def = models.ForeignKey(CustomFieldDefinition, on_delete=models.CASCADE)
    value = models.TextField(default="", blank=True)
    _value_encrypted = models.BinaryField(default=b"", blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "clients"
        db_table = "client_detail_values"
        unique_together = ["client_file", "field_def"]

    def get_value(self):
        """Return decrypted value if field is sensitive, plain value otherwise."""
        if self.field_def.is_sensitive:
            try:
                return decrypt_field(self._value_encrypted)
            except DecryptionError:
                return "[DECRYPTION ERROR]"
        return self.value

    def set_value(self, val):
        """Store encrypted or plain based on field sensitivity."""
        if self.field_def.is_sensitive:
            self._value_encrypted = encrypt_field(val)
            self.value = ""
        else:
            self.value = val
            self._value_encrypted = b""


class ErasureRequest(models.Model):
    """
    Tracks a client data erasure request through a multi-PM approval workflow.

    Workflow: PM requests → all program managers approve → data anonymised/erased.
    Survives after the ClientFile is deleted or anonymised (client_file SET_NULL on delete).
    Stores enough non-PII metadata to serve as a permanent audit record.
    """

    STATUS_CHOICES = [
        ("pending", _("Pending Approval")),
        ("anonymised", _("Approved — Data Anonymised")),
        ("scheduled", _("Scheduled — Awaiting Erasure")),
        ("approved", _("Approved — Data Erased")),
        ("rejected", _("Rejected")),
        ("cancelled", _("Cancelled")),
    ]

    TIER_CHOICES = [
        ("anonymise", _("Anonymise")),
        ("anonymise_purge", _("Anonymise + Purge Notes")),
        ("full_erasure", _("Full Erasure")),
    ]

    # Note: These labels use the default terminology ("Participant"). They are
    # class-level constants and cannot use request.get_term() dynamically. If an
    # agency overrides terminology, these dropdown labels won't change — this is
    # an accepted limitation (one dropdown in one form).
    REASON_CATEGORY_CHOICES = [
        ("client_requested", _("Participant Requested")),
        ("retention_expired", _("Retention Period Expired")),
        ("discharged", _("Participant Discharged")),
        ("other", _("Other")),
    ]

    # Link to the client (SET_NULL so this record survives deletion)
    client_file = models.ForeignKey(
        ClientFile, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="erasure_requests",
    )
    # Preserved identifiers (non-PII) for history after client is deleted
    client_pk = models.IntegerField(help_text="Original ClientFile PK for audit cross-reference.")
    client_record_id = models.CharField(max_length=100, default="", blank=True)

    # Data summary — snapshot of related record counts at request time (integers only, never PII)
    data_summary = models.JSONField(default=dict)

    # Request phase
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="erasure_requests_made",
    )
    requested_by_display = models.CharField(max_length=255, default="")
    requested_at = models.DateTimeField(auto_now_add=True)
    reason_category = models.CharField(
        max_length=30, choices=REASON_CATEGORY_CHOICES, default="other",
    )
    request_reason = models.TextField(
        help_text="Why this data should be erased. Do not include client names.",
    )

    # Erasure tier and tracking code
    erasure_tier = models.CharField(
        max_length=20, choices=TIER_CHOICES, default="anonymise",
        help_text="Level of data erasure: anonymise (default), purge notes, or full delete.",
    )
    erasure_code = models.CharField(
        max_length=20, unique=True, blank=True, default="",
        help_text="Auto-generated reference code, e.g. ER-2026-001.",
    )

    # Approval tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    completed_at = models.DateTimeField(null=True, blank=True)
    receipt_downloaded_at = models.DateTimeField(null=True, blank=True)
    scheduled_execution_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Tier 3 only: when the deferred erasure will execute (24h after approval).",
    )

    # Programs that need PM approval (snapshot of program PKs at request time)
    programs_required = models.JSONField(
        default=list,
        help_text="List of program PKs that need approval before erasure executes.",
    )

    class Meta:
        app_label = "clients"
        db_table = "erasure_requests"
        ordering = ["-requested_at"]

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

    def __str__(self):
        code = self.erasure_code or f"#{self.pk}"
        return f"Erasure {code} — Participant #{self.client_pk} ({self.get_status_display()})"


class ErasureApproval(models.Model):
    """
    Tracks an individual PM's approval for one program within an erasure request.

    When all required programs have an approval, the erasure auto-executes.
    """

    erasure_request = models.ForeignKey(
        ErasureRequest, on_delete=models.CASCADE, related_name="approvals",
    )
    program = models.ForeignKey(
        "programs.Program", on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="erasure_approvals_given",
    )
    approved_by_display = models.CharField(max_length=255, default="")
    approved_at = models.DateTimeField(auto_now_add=True)
    review_notes = models.TextField(default="", blank=True)

    class Meta:
        app_label = "clients"
        db_table = "erasure_approvals"
        unique_together = ["erasure_request", "program"]

    def __str__(self):
        program_name = self.program.name if self.program else _("Deleted program")
        return f"Approval for {program_name} by {self.approved_by_display}"


class FieldAccessConfig(models.Model):
    """Configures front desk access to core model fields.

    Only used at Tier 2+. At Tier 1, safe defaults apply automatically.
    Custom fields use CustomFieldDefinition.front_desk_access instead.

    This model covers core ClientFile fields (phone, email, birth_date, etc.)
    that an agency may want to grant or restrict for the receptionist role.
    """

    ACCESS_CHOICES = [
        ("none", _("Hidden")),
        ("view", _("View only")),
        ("edit", _("View and edit")),
    ]

    # Default access for core fields when no FieldAccessConfig row exists.
    # At Tier 1, these defaults are used without admin UI.
    # At Tier 2+, admin can override via the field access page.
    # Tier 3 uses tighter defaults (email: view only) for clinical safety.
    SAFE_DEFAULTS = {
        "phone": "edit",
        "email": "edit",
        "birth_date": "none",
        "preferred_name": "view",
    }

    SAFE_DEFAULTS_TIER3 = {
        "phone": "edit",
        "email": "view",
        "birth_date": "none",
        "preferred_name": "view",
    }

    # Fields that are always visible to front desk regardless of config.
    # These cannot be hidden because front desk needs them to identify clients.
    ALWAYS_VISIBLE = {"first_name", "last_name", "display_name", "record_id", "status"}

    field_name = models.CharField(max_length=100, unique=True)
    front_desk_access = models.CharField(
        max_length=10,
        choices=ACCESS_CHOICES,
        default="view",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "clients"
        db_table = "field_access_configs"
        ordering = ["field_name"]

    def __str__(self):
        return f"{self.field_name}: {self.get_front_desk_access_display()}"

    @classmethod
    def _get_defaults(cls):
        """Return the appropriate safe defaults for the current access tier.

        Tier 3 (clinical) uses tighter defaults — email is view-only
        instead of editable, since email addresses can be a safety
        concern in clinical and DV-serving agencies.
        """
        from apps.admin_settings.models import get_access_tier
        if get_access_tier() >= 3:
            return cls.SAFE_DEFAULTS_TIER3
        return cls.SAFE_DEFAULTS

    @classmethod
    def get_access(cls, field_name):
        """Return the front desk access level for a core field.

        Falls back to tier-sensitive safe defaults if no config row exists.
        """
        try:
            return cls.objects.get(field_name=field_name).front_desk_access
        except cls.DoesNotExist:
            return cls._get_defaults().get(field_name, "none")

    @classmethod
    def get_all_access(cls):
        """Return dict of field_name -> access level for all configurable fields."""
        result = dict(cls._get_defaults())  # Start with tier-sensitive defaults
        for config in cls.objects.all():
            result[config.field_name] = config.front_desk_access
        return result


class ClientMerge(models.Model):
    """Records that two client records were merged.

    The 'kept' client is the surviving record that receives all data.
    The 'archived' client is anonymised (PII stripped, status discharged).
    All related records (notes, events, plans, enrolments) transfer to 'kept'.
    """

    # Links to the two clients (SET_NULL so this record survives erasure)
    kept_client = models.ForeignKey(
        ClientFile, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="merges_kept",
    )
    archived_client = models.ForeignKey(
        ClientFile, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="merges_archived",
    )
    # Snapshot IDs survive FK nullification (e.g. after erasure)
    kept_client_pk = models.IntegerField()
    archived_client_pk = models.IntegerField()
    kept_record_id = models.CharField(max_length=100, default="", blank=True)
    archived_record_id = models.CharField(max_length=100, default="", blank=True)

    # Who and when
    merged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="merges_performed",
    )
    merged_by_display = models.CharField(max_length=255, default="")
    merged_at = models.DateTimeField(auto_now_add=True)

    # Audit data — field names only, never actual PII values
    transfer_summary = models.JSONField(
        default=dict,
        help_text="Counts of transferred records: {notes: 5, events: 2, ...}",
    )
    pii_choices = models.JSONField(
        default=dict,
        help_text="Which PII fields came from which client: {first_name: 'kept', phone: 'archived'}",
    )
    field_conflict_resolutions = models.JSONField(
        default=dict,
        help_text="Custom field conflict resolutions: {field_def_id: 'kept'/'archived'}",
    )

    class Meta:
        app_label = "clients"
        db_table = "client_merges"
        ordering = ["-merged_at"]

    def __str__(self):
        return (
            f"Merge #{self.pk}: Participant #{self.archived_client_pk} "
            f"→ Participant #{self.kept_client_pk}"
        )


class DataAccessRequest(models.Model):
    """Tracks a PIPEDA Section 8 data access request through a guided manual process.

    NOT an automated export — a checklist that tells staff what to gather,
    tracks the 30-day deadline, and logs completion to the audit trail.
    """

    REQUEST_METHOD_CHOICES = [
        ("verbal", _("Verbal")),
        ("written", _("Written")),
        ("email", _("Email")),
    ]

    DELIVERY_METHOD_CHOICES = [
        ("in_person", _("In person")),
        ("mail", _("Mail")),
        ("email", _("Email")),
    ]

    client_file = models.ForeignKey(
        ClientFile, on_delete=models.CASCADE, related_name="data_access_requests",
    )
    requested_at = models.DateField(
        help_text="Date the access request was received.",
    )
    request_method = models.CharField(
        max_length=20, choices=REQUEST_METHOD_CHOICES,
    )
    deadline = models.DateField(
        help_text="Auto-set to requested_at + 30 days.",
    )

    # Completion
    completed_at = models.DateField(null=True, blank=True)
    delivery_method = models.CharField(
        max_length=20, blank=True, choices=DELIVERY_METHOD_CHOICES,
    )
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="data_access_completions",
    )

    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name="data_access_requests_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "clients"
        db_table = "data_access_requests"
        ordering = ["-created_at"]

    def __str__(self):
        status = _("Complete") if self.completed_at else _("Pending")
        return f"Data Access #{self.pk} — {status}"

    @property
    def is_overdue(self):
        from datetime import date
        return not self.completed_at and self.deadline < date.today()

    @property
    def days_remaining(self):
        from datetime import date
        if self.completed_at:
            return None
        return (self.deadline - date.today()).days
