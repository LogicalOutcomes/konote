# Phase 2: Report Artifact & Validation Pipeline — Agent Prompt

Build the non-PII artifact pipeline anchored to approved exports. Depends on Phase 1 (EvaluationFramework must exist).

## Context

KoNote's export flow: staff create a report → approve it → `SecureExportLink` is created with the file. This phase adds a layer on top: after approval, a `CanonicalReportArtifact` can be built from the approved export. This artifact is a stable, non-PII package that can be validated and later enriched (Phase 3).

Key constraint: **`CanonicalReportArtifact` must refuse to save if `contains_pii=True`** on the source `SecureExportLink`.

## Branch

Create branch `feat/report-artifact-validation` off `develop`.

## Prerequisites

Phase 1 must be merged (EvaluationFramework model exists in `apps/programs/models.py`).

## 1. Models — edit `apps/reports/models.py`

Add these three models at the bottom of the file (after `InsightSummary`):

### ReportValidationProfile

```python
class ReportValidationProfile(models.Model):
    """
    Partner-specific validation rule set.

    Defines what sections, metrics, and metadata a partner requires
    in their reports. Used for deterministic validation before AI enrichment.
    """

    name = models.CharField(max_length=255)
    partner = models.ForeignKey(
        Partner,
        null=True, blank=True,
        on_delete=models.CASCADE,
        related_name="validation_profiles",
    )
    report_template = models.ForeignKey(
        ReportTemplate,
        null=True, blank=True,
        on_delete=models.CASCADE,
        related_name="validation_profiles",
    )

    # Validation rules stored as JSON
    required_sections = models.JSONField(
        default=list, blank=True,
        help_text=_(
            "List of required section names. "
            "Schema: [str, ...]"
        ),
    )
    required_metrics = models.JSONField(
        default=list, blank=True,
        help_text=_(
            "List of required metric names or IDs. "
            "Schema: [str, ...]"
        ),
    )
    required_cids_classes = models.JSONField(
        default=list, blank=True,
        help_text=_(
            "CIDS classes that must be present in export. "
            "Schema: ['cids:Outcome', 'cids:Indicator', ...]"
        ),
    )
    min_taxonomy_coverage = models.FloatField(
        default=0.0,
        help_text=_("Minimum fraction of metrics with taxonomy mappings (0.0-1.0)."),
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        db_table = "report_validation_profiles"

    def __str__(self):
        return self.name
```

### CanonicalReportArtifact

```python
class CanonicalReportArtifact(models.Model):
    """
    Stable non-PII package built from an approved SecureExportLink.

    1:1 relationship with SecureExportLink. Created only when the export
    is approved and contains_pii=False.
    """

    ARTIFACT_STATES = [
        ("building", _("Building")),
        ("built", _("Built")),
        ("validated", _("Validated")),
        ("enriched", _("Enriched")),
        ("failed", _("Failed")),
    ]

    export_link = models.OneToOneField(
        SecureExportLink,
        on_delete=models.CASCADE,
        related_name="canonical_artifact",
    )
    state = models.CharField(
        max_length=20, choices=ARTIFACT_STATES, default="building",
    )

    # The non-PII aggregate payload
    aggregate_payload = models.JSONField(
        default=dict, blank=True,
        help_text=_(
            "Aggregate report data (metrics, demographics, narrative). "
            "Schema: {metrics: [...], demographics: [...], narrative_sections: [...]}"
        ),
    )

    # Reference to evaluation framework (if program has one)
    evaluation_framework = models.ForeignKey(
        "programs.EvaluationFramework",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="artifacts",
    )

    # Validation results
    validation_results = models.JSONField(
        default=dict, blank=True,
        help_text=_(
            "Results from deterministic validation. "
            "Schema: {passed: bool, checks: [{name, passed, message}], validated_at: iso}"
        ),
    )
    validation_profile = models.ForeignKey(
        ReportValidationProfile,
        null=True, blank=True,
        on_delete=models.SET_NULL,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        db_table = "canonical_report_artifacts"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Artifact for {self.export_link}"

    def save(self, *args, **kwargs):
        # Enforce: cannot create artifact from PII-containing export
        if self.export_link.contains_pii:
            from django.core.exceptions import ValidationError
            raise ValidationError(
                "Cannot create canonical artifact from an export that contains PII."
            )
        super().save(*args, **kwargs)
```

### EnrichmentRun

```python
class EnrichmentRun(models.Model):
    """
    Audit trail for validation/enrichment attempts on a canonical artifact.
    """

    RUN_TYPES = [
        ("deterministic", _("Deterministic Validation")),
        ("ai_enrichment", _("AI Enrichment")),
        ("shacl_validation", _("SHACL Validation")),
    ]

    STATUS_CHOICES = [
        ("running", _("Running")),
        ("completed", _("Completed")),
        ("failed", _("Failed")),
    ]

    artifact = models.ForeignKey(
        CanonicalReportArtifact,
        on_delete=models.CASCADE,
        related_name="enrichment_runs",
    )
    run_type = models.CharField(max_length=30, choices=RUN_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="running")

    # Configuration
    config = models.JSONField(
        default=dict, blank=True,
        help_text=_("Run configuration. Schema: {model_id, allow_external, auto_apply, ...}"),
    )

    # Results
    results_summary = models.JSONField(
        default=dict, blank=True,
        help_text=_("Summary of results. Schema varies by run_type."),
    )
    error_message = models.TextField(blank=True, default="")

    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        db_table = "enrichment_runs"
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.get_run_type_display()} — {self.get_status_display()}"
```

## 2. Migration

Create migration for `reports` app after adding models.

## 3. Services — create `apps/reports/artifact_service.py`

```python
"""Services for building and validating canonical report artifacts."""
from django.utils import timezone

from apps.reports.models import (
    CanonicalReportArtifact, EnrichmentRun, ReportValidationProfile,
    SecureExportLink,
)


def build_canonical_artifact(export_link, user=None):
    """
    Build a CanonicalReportArtifact from an approved, non-PII SecureExportLink.

    Returns the artifact or raises ValueError.
    """
    if export_link.contains_pii:
        raise ValueError("Cannot build artifact from PII-containing export.")

    if not export_link.approved_by:
        raise ValueError("Export must be approved before building artifact.")

    # Check for existing artifact
    existing = getattr(export_link, "canonical_artifact", None)
    if existing:
        return existing

    # Build aggregate payload from export data
    payload = _extract_aggregate_payload(export_link)

    # Find evaluation framework for the program (if any)
    framework = _find_evaluation_framework(export_link)

    artifact = CanonicalReportArtifact.objects.create(
        export_link=export_link,
        state="built",
        aggregate_payload=payload,
        evaluation_framework=framework,
        created_by=user,
    )

    return artifact


def _extract_aggregate_payload(export_link):
    """Extract aggregate data from the export file. Returns dict."""
    import json
    import os

    payload = {
        "export_type": export_link.export_type,
        "client_count": export_link.client_count,
        "filters": json.loads(export_link.filters_json or "{}"),
        "created_at": export_link.created_at.isoformat(),
        "metrics": [],
        "narrative_sections": [],
    }

    # If the export file is a CIDS JSON-LD, parse it
    if export_link.file_exists and export_link.filename.endswith(".jsonld"):
        try:
            with open(export_link.file_path, "r", encoding="utf-8") as f:
                cids_data = json.load(f)
            payload["cids_document"] = cids_data
        except (json.JSONDecodeError, OSError):
            pass

    return payload


def _find_evaluation_framework(export_link):
    """Find the EvaluationFramework for the export's program, if any."""
    from apps.programs.models import EvaluationFramework

    filters = {}
    try:
        import json
        filters = json.loads(export_link.filters_json or "{}")
    except (json.JSONDecodeError, ValueError):
        pass

    program_id = filters.get("program_id") or filters.get("program")
    if program_id:
        try:
            return EvaluationFramework.objects.get(program_id=program_id)
        except EvaluationFramework.DoesNotExist:
            pass
    return None


def run_deterministic_validation(artifact, profile=None):
    """
    Run deterministic validation checks on a canonical artifact.

    Uses ReportValidationProfile if provided, otherwise runs basic checks.
    Returns the EnrichmentRun record.
    """
    run = EnrichmentRun.objects.create(
        artifact=artifact,
        run_type="deterministic",
        triggered_by=artifact.created_by,
    )

    checks = []

    # Basic checks (always run)
    payload = artifact.aggregate_payload or {}

    # Check: has metrics
    has_metrics = bool(payload.get("metrics") or payload.get("cids_document"))
    checks.append({
        "name": "has_report_data",
        "passed": has_metrics,
        "message": "Report contains metric or CIDS data" if has_metrics else "No metric data found",
    })

    # Check: has evaluation framework
    has_fw = artifact.evaluation_framework is not None
    checks.append({
        "name": "has_evaluation_framework",
        "passed": has_fw,
        "message": "Evaluation framework linked" if has_fw else "No evaluation framework",
    })

    # Profile-specific checks
    if profile:
        artifact.validation_profile = profile

        # Required sections
        for section_name in (profile.required_sections or []):
            found = any(
                s.get("name") == section_name
                for s in payload.get("narrative_sections", [])
            )
            checks.append({
                "name": f"required_section:{section_name}",
                "passed": found,
                "message": f"Section '{section_name}' {'found' if found else 'missing'}",
            })

        # Required CIDS classes
        cids_doc = payload.get("cids_document", {})
        graph = cids_doc.get("@graph", [])
        present_types = {
            node.get("@type") for node in graph if isinstance(node, dict)
        }
        for cids_class in (profile.required_cids_classes or []):
            found = cids_class in present_types
            checks.append({
                "name": f"required_cids_class:{cids_class}",
                "passed": found,
                "message": f"CIDS class '{cids_class}' {'present' if found else 'missing'}",
            })

    all_passed = all(c["passed"] for c in checks)

    run.results_summary = {
        "passed": all_passed,
        "checks": checks,
        "validated_at": timezone.now().isoformat(),
    }
    run.status = "completed"
    run.completed_at = timezone.now()
    run.save()

    artifact.validation_results = run.results_summary
    if all_passed:
        artifact.state = "validated"
    artifact.save()

    return run
```

## 4. Views — edit `apps/reports/views.py`

Add at the bottom:

```python
@login_required
@admin_required
def export_metadata_status(request, export_id):
    """View metadata status for an export link."""
    export_link = get_object_or_404(SecureExportLink, pk=export_id)
    artifact = getattr(export_link, "canonical_artifact", None)
    runs = artifact.enrichment_runs.all() if artifact else []

    return render(request, "reports/export_metadata_status.html", {
        "export_link": export_link,
        "artifact": artifact,
        "runs": runs,
    })


@login_required
@admin_required
def build_artifact(request, export_id):
    """Build a canonical artifact from an approved export."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    export_link = get_object_or_404(SecureExportLink, pk=export_id)

    from apps.reports.artifact_service import build_canonical_artifact
    try:
        artifact = build_canonical_artifact(export_link, user=request.user)
        messages.success(request, _("Canonical artifact built successfully."))
    except ValueError as e:
        messages.error(request, str(e))

    return redirect("reports:export_metadata_status", export_id=export_id)


@login_required
@admin_required
def run_validation(request, export_id):
    """Run deterministic validation on a canonical artifact."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    export_link = get_object_or_404(SecureExportLink, pk=export_id)
    artifact = getattr(export_link, "canonical_artifact", None)
    if not artifact:
        messages.error(request, _("Build artifact first."))
        return redirect("reports:export_metadata_status", export_id=export_id)

    # Find validation profile
    from apps.reports.artifact_service import run_deterministic_validation
    profile_id = request.POST.get("profile_id")
    profile = None
    if profile_id:
        from apps.reports.models import ReportValidationProfile
        profile = ReportValidationProfile.objects.filter(pk=profile_id).first()

    run_deterministic_validation(artifact, profile=profile)
    messages.success(request, _("Validation complete."))
    return redirect("reports:export_metadata_status", export_id=export_id)
```

Add required imports at the top of views.py if not already present:
```python
from apps.auth_app.decorators import admin_required
```

## 5. URLs — edit `apps/reports/urls.py`

Add:
```python
# Export metadata & artifact pipeline
path("exports/<uuid:export_id>/metadata/",
     views.export_metadata_status,
     name="export_metadata_status"),
path("exports/<uuid:export_id>/metadata/build-artifact/",
     views.build_artifact,
     name="build_artifact"),
path("exports/<uuid:export_id>/metadata/validate/",
     views.run_validation,
     name="run_validation"),
```

## 6. Template — create `templates/reports/export_metadata_status.html`

```html
{% extends "base.html" %}
{% load i18n %}

{% block title %}{% trans "Export Metadata" %}{% endblock %}

{% block content %}
<h1>{% trans "Export Metadata Status" %}</h1>

<dl>
  <dt>{% trans "Export Type" %}</dt>
  <dd>{{ export_link.get_export_type_display }}</dd>
  <dt>{% trans "Created" %}</dt>
  <dd>{{ export_link.created_at|date:"Y-m-d H:i" }}</dd>
  <dt>{% trans "Contains PII" %}</dt>
  <dd>{{ export_link.contains_pii|yesno:"Yes,No" }}</dd>
  <dt>{% trans "Approved" %}</dt>
  <dd>{% if export_link.approved_by %}{{ export_link.approved_by.get_full_name }} — {{ export_link.approved_at|date:"Y-m-d" }}{% else %}{% trans "Not yet" %}{% endif %}</dd>
</dl>

{% if not artifact %}
  {% if not export_link.contains_pii and export_link.approved_by %}
  <form method="post" action="{% url 'reports:build_artifact' export_id=export_link.pk %}">
    {% csrf_token %}
    <button type="submit">{% trans "Build Canonical Artifact" %}</button>
  </form>
  {% else %}
  <p>{% trans "Export must be approved and non-PII before building artifact." %}</p>
  {% endif %}
{% else %}
  <h2>{% trans "Canonical Artifact" %}</h2>
  <dl>
    <dt>{% trans "State" %}</dt>
    <dd><mark>{{ artifact.get_state_display }}</mark></dd>
    <dt>{% trans "Evaluation Framework" %}</dt>
    <dd>{% if artifact.evaluation_framework %}
      <a href="{% url 'programs:evaluation_framework_detail' framework_id=artifact.evaluation_framework.pk %}">
        {{ artifact.evaluation_framework }}
      </a>
    {% else %}{% trans "None linked" %}{% endif %}</dd>
  </dl>

  {% if artifact.validation_results.checks %}
  <h3>{% trans "Validation Results" %}</h3>
  <table role="grid">
    <thead><tr><th>{% trans "Check" %}</th><th>{% trans "Result" %}</th><th>{% trans "Details" %}</th></tr></thead>
    <tbody>
      {% for check in artifact.validation_results.checks %}
      <tr>
        <td>{{ check.name }}</td>
        <td>{% if check.passed %}✓{% else %}✗{% endif %}</td>
        <td>{{ check.message }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
  {% endif %}

  <form method="post" action="{% url 'reports:run_validation' export_id=export_link.pk %}">
    {% csrf_token %}
    <button type="submit" class="secondary">{% trans "Run Validation" %}</button>
  </form>

  <h3>{% trans "Enrichment History" %}</h3>
  <table role="grid">
    <thead><tr><th>{% trans "Type" %}</th><th>{% trans "Status" %}</th><th>{% trans "Started" %}</th></tr></thead>
    <tbody>
      {% for run in runs %}
      <tr>
        <td>{{ run.get_run_type_display }}</td>
        <td>{{ run.get_status_display }}</td>
        <td>{{ run.started_at|date:"Y-m-d H:i" }}</td>
      </tr>
      {% empty %}
      <tr><td colspan="3">{% trans "No enrichment runs yet." %}</td></tr>
      {% endfor %}
    </tbody>
  </table>
{% endif %}
{% endblock %}
```

## 7. Tests — create `tests/test_report_artifacts.py`

```python
"""Tests for CanonicalReportArtifact, validation, and artifact service."""
import json
import uuid
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase, Client, override_settings
from django.utils import timezone
from cryptography.fernet import Fernet

from apps.auth_app.models import User
from apps.programs.models import Program, UserProgramRole, EvaluationFramework
from apps.reports.models import (
    CanonicalReportArtifact, EnrichmentRun,
    ReportValidationProfile, SecureExportLink,
)
from apps.reports.artifact_service import (
    build_canonical_artifact, run_deterministic_validation,
)

import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class CanonicalArtifactModelTest(TestCase):
    def setUp(self):
        enc_module._fernet = None
        self.user = User.objects.create_user(
            username="admin@test.ca", password="testpass123", is_admin=True,
        )
        self.program = Program.objects.create(name="Housing")

    def _make_export(self, contains_pii=False, approved=True):
        link = SecureExportLink.objects.create(
            created_by=self.user,
            expires_at=timezone.now() + timedelta(hours=24),
            export_type="standard_report",
            client_count=10,
            recipient="test",
            filename="report.csv",
            file_path="/tmp/test.csv",
            contains_pii=contains_pii,
            filters_json=json.dumps({"program_id": self.program.pk}),
        )
        if approved:
            link.approved_by = self.user
            link.approved_at = timezone.now()
            link.save()
        return link

    def test_artifact_blocked_when_pii(self):
        link = self._make_export(contains_pii=True)
        with self.assertRaises(ValidationError):
            CanonicalReportArtifact.objects.create(
                export_link=link, state="built",
            )

    def test_artifact_created_when_no_pii(self):
        link = self._make_export(contains_pii=False)
        artifact = CanonicalReportArtifact.objects.create(
            export_link=link, state="built",
        )
        self.assertEqual(artifact.state, "built")

    def test_service_blocks_unapproved(self):
        link = self._make_export(approved=False)
        with self.assertRaises(ValueError):
            build_canonical_artifact(link, user=self.user)

    def test_service_blocks_pii(self):
        link = self._make_export(contains_pii=True, approved=True)
        with self.assertRaises(ValueError):
            build_canonical_artifact(link, user=self.user)

    def test_service_builds_artifact(self):
        link = self._make_export()
        artifact = build_canonical_artifact(link, user=self.user)
        self.assertEqual(artifact.state, "built")
        self.assertEqual(artifact.export_link, link)

    def test_service_returns_existing(self):
        link = self._make_export()
        a1 = build_canonical_artifact(link, user=self.user)
        a2 = build_canonical_artifact(link, user=self.user)
        self.assertEqual(a1.pk, a2.pk)

    def test_validation_basic_checks(self):
        link = self._make_export()
        artifact = build_canonical_artifact(link, user=self.user)
        run = run_deterministic_validation(artifact)
        self.assertEqual(run.status, "completed")
        self.assertIn("checks", run.results_summary)

    def test_validation_with_profile(self):
        link = self._make_export()
        artifact = build_canonical_artifact(link, user=self.user)
        profile = ReportValidationProfile.objects.create(
            name="Test Profile",
            required_sections=["Executive Summary"],
            required_cids_classes=["cids:Outcome"],
        )
        run = run_deterministic_validation(artifact, profile=profile)
        # Should fail because sections are empty
        self.assertFalse(run.results_summary["passed"])


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ArtifactViewTest(TestCase):
    def setUp(self):
        enc_module._fernet = None
        self.user = User.objects.create_user(
            username="admin@test.ca", password="testpass123", is_admin=True,
        )
        self.client_http = Client()
        self.client_http.login(username="admin@test.ca", password="testpass123")
        self.program = Program.objects.create(name="Housing")

    def _make_export(self):
        return SecureExportLink.objects.create(
            created_by=self.user,
            expires_at=timezone.now() + timedelta(hours=24),
            export_type="standard_report",
            client_count=10,
            recipient="test",
            filename="report.csv",
            file_path="/tmp/test.csv",
            contains_pii=False,
            approved_by=self.user,
            approved_at=timezone.now(),
        )

    def test_metadata_status_page(self):
        link = self._make_export()
        response = self.client_http.get(f"/reports/exports/{link.pk}/metadata/")
        self.assertEqual(response.status_code, 200)

    def test_build_artifact_post(self):
        link = self._make_export()
        response = self.client_http.post(
            f"/reports/exports/{link.pk}/metadata/build-artifact/"
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            CanonicalReportArtifact.objects.filter(export_link=link).exists()
        )

    def test_non_admin_blocked(self):
        User.objects.create_user(
            username="staff@test.ca", password="testpass123", is_admin=False,
        )
        self.client_http.login(username="staff@test.ca", password="testpass123")
        link = self._make_export()
        response = self.client_http.get(f"/reports/exports/{link.pk}/metadata/")
        self.assertEqual(response.status_code, 403)
```

## Acceptance criteria

- [ ] 3 new models in `apps/reports/models.py` (ReportValidationProfile, CanonicalReportArtifact, EnrichmentRun)
- [ ] CanonicalReportArtifact.save() raises ValidationError when export contains PII
- [ ] Migration applies cleanly
- [ ] `artifact_service.py` with `build_canonical_artifact()` and `run_deterministic_validation()`
- [ ] Views: metadata status, build artifact, run validation (all admin-only)
- [ ] URLs registered under `/reports/exports/<uuid>/metadata/`
- [ ] Template with validation results table and enrichment history
- [ ] Tests: PII blocking, approval checking, idempotent build, validation with/without profile
- [ ] French translations added
