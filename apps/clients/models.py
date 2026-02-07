"""Client file and custom field models."""
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from konote.encryption import decrypt_field, encrypt_field


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

    def __str__(self):
        if self.is_anonymised:
            return _("[ANONYMISED]")
        return f"{self.first_name} {self.last_name}" if self.first_name else f"Client #{self.pk}"

    # Encrypted property accessors
    @property
    def first_name(self):
        return decrypt_field(self._first_name_encrypted)

    @first_name.setter
    def first_name(self, value):
        self._first_name_encrypted = encrypt_field(value)

    @property
    def middle_name(self):
        return decrypt_field(self._middle_name_encrypted)

    @middle_name.setter
    def middle_name(self, value):
        self._middle_name_encrypted = encrypt_field(value)

    @property
    def last_name(self):
        return decrypt_field(self._last_name_encrypted)

    @last_name.setter
    def last_name(self, value):
        self._last_name_encrypted = encrypt_field(value)

    @property
    def birth_date(self):
        val = decrypt_field(self._birth_date_encrypted)
        return val if val else None

    @birth_date.setter
    def birth_date(self, value):
        self._birth_date_encrypted = encrypt_field(str(value) if value else "")

    @property
    def phone(self):
        return decrypt_field(self._phone_encrypted)

    @phone.setter
    def phone(self, value):
        self._phone_encrypted = encrypt_field(value)


class ClientProgramEnrolment(models.Model):
    """Links a client to a program."""

    STATUS_CHOICES = [
        ("enrolled", _("Enrolled")),
        ("unenrolled", _("Unenrolled")),
    ]

    client_file = models.ForeignKey(ClientFile, on_delete=models.CASCADE, related_name="enrolments")
    program = models.ForeignKey("programs.Program", on_delete=models.CASCADE, related_name="client_enrolments")
    status = models.CharField(max_length=20, default="enrolled", choices=STATUS_CHOICES)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    unenrolled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "clients"
        db_table = "client_program_enrolments"

    def __str__(self):
        return f"{self.client_file} → {self.program}"


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
            return decrypt_field(self._value_encrypted)
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
        ("approved", _("Approved — Data Erased")),
        ("rejected", _("Rejected")),
        ("cancelled", _("Cancelled")),
    ]

    TIER_CHOICES = [
        ("anonymise", _("Anonymise")),
        ("anonymise_purge", _("Anonymise + Purge Notes")),
        ("full_erasure", _("Full Erasure")),
    ]

    REASON_CATEGORY_CHOICES = [
        ("client_requested", _("Client Requested")),
        ("retention_expired", _("Retention Period Expired")),
        ("discharged", _("Client Discharged")),
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
        return f"Erasure {code} — Client #{self.client_pk} ({self.get_status_display()})"


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
            f"Merge #{self.pk}: Client #{self.archived_client_pk} "
            f"→ Client #{self.kept_client_pk}"
        )
