# Phase 3: AI Enrichment & Review — Agent Prompt

Add AI-assisted enrichment on validated canonical artifacts and a metadata snapshot workflow. Depends on Phase 2 (CanonicalReportArtifact, EnrichmentRun must exist).

## Context

After a `CanonicalReportArtifact` is built and validated (Phase 2), an admin can optionally run AI enrichment to suggest:
- Missing narrative descriptions
- Outcome chain improvements
- Standards alignment metadata

**Taxonomy suggestions** (IRIS+, SDG, etc.) must route through the existing `apps/admin_settings/taxonomy_review.py` pipeline — they create `TaxonomyMapping` records, NOT `EnrichedMetadataItem` records. This avoids building a parallel taxonomy system.

`EnrichedMetadataItem` handles non-taxonomy items only: narrative suggestions, metric descriptions, risk assessments, etc.

## Branch

Create branch `feat/ai-enrichment-review` off `develop`.

## Prerequisites

Phase 2 must be merged (CanonicalReportArtifact, EnrichmentRun exist in `apps/reports/models.py`).

## 1. Models — edit `apps/reports/models.py`

Add these two models at the bottom:

### EnrichedMetadataItem

```python
class EnrichedMetadataItem(models.Model):
    """
    Field-level enrichment result from AI or deterministic analysis.

    For non-taxonomy items only. Taxonomy suggestions route through
    TaxonomyMapping via apps/admin_settings/taxonomy_review.py.
    """

    ITEM_TYPES = [
        ("narrative", _("Narrative Enhancement")),
        ("metric_description", _("Metric Description")),
        ("outcome_description", _("Outcome Description")),
        ("risk_assessment", _("Risk Assessment")),
        ("standards_alignment", _("Standards Alignment")),
        ("completeness_gap", _("Completeness Gap")),
    ]
    # NOTE: 'taxonomy_mapping' is deliberately NOT in ITEM_TYPES.
    # Taxonomy suggestions go through TaxonomyMapping model.

    REVIEW_STATES = [
        ("pending", _("Pending Review")),
        ("accepted", _("Accepted")),
        ("rejected", _("Rejected")),
        ("modified", _("Modified")),
    ]

    artifact = models.ForeignKey(
        CanonicalReportArtifact,
        on_delete=models.CASCADE,
        related_name="enriched_items",
    )
    enrichment_run = models.ForeignKey(
        EnrichmentRun,
        on_delete=models.CASCADE,
        related_name="items",
    )

    item_type = models.CharField(max_length=30, choices=ITEM_TYPES)
    field_path = models.CharField(
        max_length=255,
        help_text=_("Dot-notation path to the field being enriched, e.g. 'outcome_chain_summary'."),
    )
    original_value = models.TextField(blank=True, default="")
    suggested_value = models.TextField()
    confidence = models.FloatField(
        default=0.0,
        help_text=_("AI confidence score (0.0-1.0)."),
    )

    # Provenance
    model_id = models.CharField(
        max_length=100, blank=True, default="",
        help_text=_("Model used for generation, e.g. 'anthropic/claude-sonnet'."),
    )
    reasoning = models.TextField(
        blank=True, default="",
        help_text=_("AI's reasoning for the suggestion."),
    )

    # Review
    review_state = models.CharField(
        max_length=20, choices=REVIEW_STATES, default="pending",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_enrichments",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewer_note = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "enriched_metadata_items"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_item_type_display()}: {self.field_path}"
```

### ExportMetadataSnapshot

```python
class ExportMetadataSnapshot(models.Model):
    """
    Immutable accepted metadata package attached to an export.

    Created when an admin applies accepted enrichment items to an export.
    Once created, the snapshot is read-only — it represents the final
    metadata state for that export.
    """

    export_link = models.ForeignKey(
        SecureExportLink,
        on_delete=models.CASCADE,
        related_name="metadata_snapshots",
    )
    artifact = models.ForeignKey(
        CanonicalReportArtifact,
        on_delete=models.CASCADE,
        related_name="snapshots",
    )

    # The immutable snapshot payload
    snapshot_payload = models.JSONField(
        help_text=_(
            "Immutable metadata package. Schema: "
            "{accepted_items: [{field_path, value, item_type, confidence}], "
            "taxonomy_mappings: [{code, label, list_name, status}], "
            "evaluation_framework_id: int|null, "
            "applied_at: iso, applied_by: str}"
        ),
    )

    applied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "export_metadata_snapshots"
        ordering = ["-applied_at"]

    def __str__(self):
        return f"Snapshot for {self.export_link} at {self.applied_at}"
```

## 2. Migration

Create migration for `reports` app.

## 3. Enrichment service — create `apps/reports/enrichment_service.py`

```python
"""AI enrichment service for canonical report artifacts."""
import logging

from django.utils import timezone

from apps.reports.models import (
    CanonicalReportArtifact, EnrichedMetadataItem, EnrichmentRun,
    ExportMetadataSnapshot,
)
from konote import ai

logger = logging.getLogger(__name__)


def run_enrichment(artifact, user=None, allow_external=True):
    """
    Run AI enrichment on a canonical artifact.

    Creates an EnrichmentRun, calls AI for suggestions, persists
    EnrichedMetadataItem records for non-taxonomy items.

    Taxonomy suggestions route through taxonomy_review.py separately.
    """
    if not ai.is_ai_available():
        raise ValueError("AI is not configured. Set OPENROUTER_API_KEY.")

    run = EnrichmentRun.objects.create(
        artifact=artifact,
        run_type="ai_enrichment",
        config={
            "allow_external": allow_external,
            "model_id": getattr(ai, "DEFAULT_MODEL", ""),
        },
        triggered_by=user,
    )

    try:
        items = _generate_enrichment_suggestions(artifact, run)
        run.results_summary = {
            "items_created": len(items),
            "completed_at": timezone.now().isoformat(),
        }
        run.status = "completed"
        run.completed_at = timezone.now()
        run.save()

        if items:
            artifact.state = "enriched"
            artifact.save()

    except Exception as e:
        logger.exception("Enrichment failed for artifact %s", artifact.pk)
        run.status = "failed"
        run.error_message = str(e)
        run.completed_at = timezone.now()
        run.save()
        raise

    return run


def _generate_enrichment_suggestions(artifact, run):
    """Call AI to generate enrichment suggestions. Returns list of created items."""
    payload = artifact.aggregate_payload or {}
    framework = artifact.evaluation_framework

    # Build context for AI
    context_parts = []
    if framework:
        context_parts.append(f"Outcome chain: {framework.outcome_chain_summary}")
        context_parts.append(f"Risks: {framework.risk_summary}")
        context_parts.append(f"Counterfactual: {framework.counterfactual_summary}")
        context_parts.append(f"Outputs: {framework.output_summary}")

    context = "\n".join(context_parts) if context_parts else "No evaluation framework."

    prompt = (
        "You are reviewing an impact report for a nonprofit program. "
        "Suggest improvements to make this report more complete for CIDS Full Tier compliance.\n\n"
        f"Current evaluation context:\n{context}\n\n"
        "For each suggestion, provide:\n"
        "- field_path: which field to improve (e.g., 'outcome_chain_summary', 'risk_summary')\n"
        "- item_type: one of 'narrative', 'metric_description', 'outcome_description', "
        "'risk_assessment', 'standards_alignment', 'completeness_gap'\n"
        "- suggested_value: the improved text\n"
        "- confidence: 0.0-1.0\n"
        "- reasoning: why this improvement matters\n\n"
        "Return a JSON array of suggestions. Only suggest non-taxonomy improvements."
    )

    response_text = ai._call_openrouter(
        system_prompt="You are a nonprofit impact reporting specialist.",
        user_prompt=prompt,
        temperature=0.3,
    )

    suggestions = ai._extract_json_payload(response_text)
    if not suggestions or not isinstance(suggestions, list):
        return []

    items = []
    for s in suggestions:
        if not isinstance(s, dict):
            continue
        item_type = s.get("item_type", "narrative")
        valid_types = {t[0] for t in EnrichedMetadataItem.ITEM_TYPES}
        if item_type not in valid_types:
            item_type = "narrative"

        item = EnrichedMetadataItem.objects.create(
            artifact=artifact,
            enrichment_run=run,
            item_type=item_type,
            field_path=s.get("field_path", "unknown"),
            original_value=s.get("original_value", ""),
            suggested_value=s.get("suggested_value", ""),
            confidence=min(max(float(s.get("confidence", 0.5)), 0.0), 1.0),
            model_id=run.config.get("model_id", ""),
            reasoning=s.get("reasoning", ""),
        )
        items.append(item)

    return items


def run_taxonomy_enrichment(artifact, user=None):
    """
    Run taxonomy enrichment through the existing taxonomy_review pipeline.

    Creates TaxonomyMapping records (NOT EnrichedMetadataItem).
    """
    from apps.admin_settings.taxonomy_review import (
        generate_subject_suggestions,
        create_draft_suggestions,
    )

    framework = artifact.evaluation_framework
    if not framework:
        return []

    # Gather subjects for taxonomy suggestion
    subjects = []
    for comp in framework.components.all():
        subjects.append({
            "type": "evaluation_component",
            "name": comp.title,
            "description": comp.description,
            "subject_type": "metric",  # taxonomy_review expects this
            "subject_id": comp.pk,
        })

    if not subjects:
        return []

    # Use existing pipeline
    results = []
    for subject in subjects:
        suggestions = generate_subject_suggestions(
            subject_type=subject["subject_type"],
            subject_name=subject["name"],
            subject_description=subject["description"],
        )
        if suggestions:
            created = create_draft_suggestions(
                suggestions=suggestions,
                subject_type=subject["subject_type"],
                subject_id=subject["subject_id"],
                source="ai_suggested",
            )
            results.extend(created)

    return results


def apply_metadata_snapshot(export_link, accepted_item_ids, user=None):
    """
    Build an immutable metadata snapshot from accepted enrichment items.
    """
    artifact = export_link.canonical_artifact
    items = EnrichedMetadataItem.objects.filter(
        pk__in=accepted_item_ids,
        artifact=artifact,
        review_state="accepted",
    )

    # Gather accepted taxonomy mappings for this artifact's framework
    from apps.admin_settings.models import TaxonomyMapping
    taxonomy_mappings = []
    if artifact.evaluation_framework:
        comp_ids = list(
            artifact.evaluation_framework.components.values_list("pk", flat=True)
        )
        mappings = TaxonomyMapping.objects.filter(
            subject_id__in=[str(i) for i in comp_ids],
            review_status="approved",
        )
        taxonomy_mappings = [
            {
                "code": m.code_value,
                "label": m.code_label,
                "list_name": m.list_name,
                "status": m.review_status,
            }
            for m in mappings
        ]

    snapshot_payload = {
        "accepted_items": [
            {
                "field_path": item.field_path,
                "value": item.suggested_value,
                "item_type": item.item_type,
                "confidence": item.confidence,
            }
            for item in items
        ],
        "taxonomy_mappings": taxonomy_mappings,
        "evaluation_framework_id": (
            artifact.evaluation_framework.pk if artifact.evaluation_framework else None
        ),
        "applied_at": timezone.now().isoformat(),
        "applied_by": user.get_full_name() if user else "",
    }

    snapshot = ExportMetadataSnapshot.objects.create(
        export_link=export_link,
        artifact=artifact,
        snapshot_payload=snapshot_payload,
        applied_by=user,
    )

    return snapshot
```

## 4. Views — add to `apps/reports/views.py`

```python
@login_required
@admin_required
def run_enrichment_view(request, export_id):
    """Run AI enrichment on a canonical artifact."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    export_link = get_object_or_404(SecureExportLink, pk=export_id)
    artifact = getattr(export_link, "canonical_artifact", None)
    if not artifact:
        messages.error(request, _("Build artifact first."))
        return redirect("reports:export_metadata_status", export_id=export_id)

    from apps.reports.enrichment_service import run_enrichment
    try:
        run_enrichment(artifact, user=request.user)
        messages.success(request, _("AI enrichment complete."))
    except ValueError as e:
        messages.error(request, str(e))
    except Exception:
        messages.error(request, _("Enrichment failed. Check logs."))

    return redirect("reports:export_metadata_status", export_id=export_id)


@login_required
@admin_required
def review_enrichment_item(request, export_id, item_id):
    """Accept or reject an enrichment item."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    from apps.reports.models import EnrichedMetadataItem
    item = get_object_or_404(EnrichedMetadataItem, pk=item_id)

    action = request.POST.get("action")
    if action in ("accepted", "rejected"):
        item.review_state = action
        item.reviewed_by = request.user
        item.reviewed_at = timezone.now()
        item.reviewer_note = request.POST.get("note", "")
        item.save()

    if request.headers.get("HX-Request"):
        # Return just the updated row for HTMX
        return render(request, "reports/partials/enrichment_item_row.html", {
            "item": item,
            "export_link": item.artifact.export_link,
        })

    return redirect("reports:export_metadata_status", export_id=export_id)


@login_required
@admin_required
def apply_snapshot(request, export_id):
    """Apply accepted enrichment items as an immutable snapshot."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    export_link = get_object_or_404(SecureExportLink, pk=export_id)
    artifact = getattr(export_link, "canonical_artifact", None)
    if not artifact:
        messages.error(request, _("No artifact found."))
        return redirect("reports:export_metadata_status", export_id=export_id)

    accepted_ids = list(
        artifact.enriched_items.filter(review_state="accepted")
        .values_list("pk", flat=True)
    )

    from apps.reports.enrichment_service import apply_metadata_snapshot
    apply_metadata_snapshot(export_link, accepted_ids, user=request.user)
    messages.success(request, _("Metadata snapshot applied."))
    return redirect("reports:export_metadata_status", export_id=export_id)
```

## 5. URLs — add to `apps/reports/urls.py`

```python
path("exports/<uuid:export_id>/metadata/enrich/",
     views.run_enrichment_view,
     name="run_enrichment"),
path("exports/<uuid:export_id>/metadata/items/<int:item_id>/review/",
     views.review_enrichment_item,
     name="review_enrichment_item"),
path("exports/<uuid:export_id>/metadata/apply/",
     views.apply_snapshot,
     name="apply_snapshot"),
```

## 6. Template partial — create `templates/reports/partials/enrichment_item_row.html`

```html
{% load i18n %}
<tr id="item-{{ item.pk }}">
  <td>{{ item.get_item_type_display }}</td>
  <td><code>{{ item.field_path }}</code></td>
  <td>{{ item.suggested_value|truncatewords:20 }}</td>
  <td>{{ item.confidence|floatformat:2 }}</td>
  <td><mark>{{ item.get_review_state_display }}</mark></td>
  <td>
    {% if item.review_state == "pending" %}
    <form method="post"
          action="{% url 'reports:review_enrichment_item' export_id=export_link.pk item_id=item.pk %}"
          hx-post="{% url 'reports:review_enrichment_item' export_id=export_link.pk item_id=item.pk %}"
          hx-target="#item-{{ item.pk }}"
          hx-swap="outerHTML"
          style="display:inline">
      {% csrf_token %}
      <input type="hidden" name="action" value="accepted">
      <button type="submit" class="outline" style="padding:0.2em 0.5em">{% trans "Accept" %}</button>
    </form>
    <form method="post"
          action="{% url 'reports:review_enrichment_item' export_id=export_link.pk item_id=item.pk %}"
          hx-post="{% url 'reports:review_enrichment_item' export_id=export_link.pk item_id=item.pk %}"
          hx-target="#item-{{ item.pk }}"
          hx-swap="outerHTML"
          style="display:inline">
      {% csrf_token %}
      <input type="hidden" name="action" value="rejected">
      <button type="submit" class="outline secondary" style="padding:0.2em 0.5em">{% trans "Reject" %}</button>
    </form>
    {% endif %}
  </td>
</tr>
```

## 7. Update `export_metadata_status.html`

Add an enrichment section after the validation section (before `{% endif %}`):

```html
{% if artifact.state == "validated" or artifact.state == "enriched" %}
<h3>{% trans "AI Enrichment" %}</h3>
{% if artifact.state != "enriched" %}
<form method="post" action="{% url 'reports:run_enrichment' export_id=export_link.pk %}">
  {% csrf_token %}
  <button type="submit">{% trans "Run AI Enrichment" %}</button>
</form>
{% endif %}

{% with items=artifact.enriched_items.all %}
{% if items %}
<table role="grid">
  <thead>
    <tr>
      <th>{% trans "Type" %}</th>
      <th>{% trans "Field" %}</th>
      <th>{% trans "Suggestion" %}</th>
      <th>{% trans "Confidence" %}</th>
      <th>{% trans "Status" %}</th>
      <th></th>
    </tr>
  </thead>
  <tbody>
    {% for item in items %}
    {% include "reports/partials/enrichment_item_row.html" %}
    {% endfor %}
  </tbody>
</table>

{% if artifact.enriched_items.filter.review_state__eq_accepted %}
<form method="post" action="{% url 'reports:apply_snapshot' export_id=export_link.pk %}">
  {% csrf_token %}
  <button type="submit">{% trans "Apply Accepted Items as Snapshot" %}</button>
</form>
{% endif %}
{% endif %}
{% endwith %}
{% endif %}

{% with snapshots=export_link.metadata_snapshots.all %}
{% if snapshots %}
<h3>{% trans "Metadata Snapshots" %}</h3>
<table role="grid">
  <thead><tr><th>{% trans "Applied" %}</th><th>{% trans "By" %}</th><th>{% trans "Items" %}</th></tr></thead>
  <tbody>
    {% for snap in snapshots %}
    <tr>
      <td>{{ snap.applied_at|date:"Y-m-d H:i" }}</td>
      <td>{{ snap.applied_by.get_full_name }}</td>
      <td>{{ snap.snapshot_payload.accepted_items|length }}</td>
    </tr>
    {% endfor %}
  </tbody>
</table>
{% endif %}
{% endwith %}
```

Note: The template snippet `artifact.enriched_items.filter.review_state__eq_accepted` won't work in Django templates. Instead, add a simple check in the view to pass `has_accepted_items` as context, or use a template tag. The simplest approach: in the `export_metadata_status` view, add:

```python
has_accepted_items = artifact.enriched_items.filter(review_state="accepted").exists() if artifact else False
```

And pass it to the template context.

## 8. Tests — create `tests/test_enrichment.py`

```python
"""Tests for AI enrichment and metadata snapshot workflow."""
import json
from datetime import timedelta
from unittest.mock import patch, MagicMock

from django.test import TestCase, Client, override_settings
from django.utils import timezone
from cryptography.fernet import Fernet

from apps.auth_app.models import User
from apps.programs.models import Program, EvaluationFramework, EvaluationComponent
from apps.reports.models import (
    CanonicalReportArtifact, EnrichedMetadataItem, EnrichmentRun,
    ExportMetadataSnapshot, SecureExportLink,
)
from apps.reports.enrichment_service import (
    run_enrichment, apply_metadata_snapshot,
)

import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class EnrichmentServiceTest(TestCase):
    def setUp(self):
        enc_module._fernet = None
        self.user = User.objects.create_user(
            username="admin@test.ca", password="testpass123", is_admin=True,
        )
        self.program = Program.objects.create(name="Housing")
        self.framework = EvaluationFramework.objects.create(
            program=self.program,
            outcome_chain_summary="Participants gain stable housing",
            risk_summary="Market conditions",
        )
        self.link = SecureExportLink.objects.create(
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
            filters_json=json.dumps({"program_id": self.program.pk}),
        )
        self.artifact = CanonicalReportArtifact.objects.create(
            export_link=self.link,
            state="validated",
            evaluation_framework=self.framework,
        )

    @patch("konote.ai.is_ai_available", return_value=True)
    @patch("konote.ai._call_openrouter")
    def test_enrichment_creates_items(self, mock_call, mock_avail):
        mock_call.return_value = json.dumps([
            {
                "item_type": "narrative",
                "field_path": "outcome_chain_summary",
                "suggested_value": "Improved narrative",
                "confidence": 0.8,
                "reasoning": "More specific",
            }
        ])
        run = run_enrichment(self.artifact, user=self.user)
        self.assertEqual(run.status, "completed")
        self.assertEqual(EnrichedMetadataItem.objects.count(), 1)

    @patch("konote.ai.is_ai_available", return_value=False)
    def test_enrichment_fails_without_ai(self, mock_avail):
        with self.assertRaises(ValueError):
            run_enrichment(self.artifact, user=self.user)

    @patch("konote.ai.is_ai_available", return_value=True)
    @patch("konote.ai._call_openrouter")
    def test_enrichment_handles_bad_response(self, mock_call, mock_avail):
        mock_call.return_value = "not json"
        run = run_enrichment(self.artifact, user=self.user)
        self.assertEqual(run.status, "completed")
        self.assertEqual(EnrichedMetadataItem.objects.count(), 0)

    def test_apply_snapshot(self):
        run = EnrichmentRun.objects.create(
            artifact=self.artifact,
            run_type="ai_enrichment",
            status="completed",
        )
        item = EnrichedMetadataItem.objects.create(
            artifact=self.artifact,
            enrichment_run=run,
            item_type="narrative",
            field_path="outcome_chain_summary",
            suggested_value="Better text",
            confidence=0.9,
            review_state="accepted",
        )
        snapshot = apply_metadata_snapshot(
            self.link, [item.pk], user=self.user,
        )
        self.assertEqual(len(snapshot.snapshot_payload["accepted_items"]), 1)
        self.assertIsNotNone(snapshot.applied_at)

    def test_snapshot_excludes_rejected_items(self):
        run = EnrichmentRun.objects.create(
            artifact=self.artifact,
            run_type="ai_enrichment",
            status="completed",
        )
        item = EnrichedMetadataItem.objects.create(
            artifact=self.artifact,
            enrichment_run=run,
            item_type="narrative",
            field_path="risk_summary",
            suggested_value="Bad suggestion",
            review_state="rejected",
        )
        snapshot = apply_metadata_snapshot(
            self.link, [item.pk], user=self.user,
        )
        # Rejected item should not appear (filtered by review_state="accepted")
        self.assertEqual(len(snapshot.snapshot_payload["accepted_items"]), 0)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class EnrichmentReviewViewTest(TestCase):
    def setUp(self):
        enc_module._fernet = None
        self.user = User.objects.create_user(
            username="admin@test.ca", password="testpass123", is_admin=True,
        )
        self.client_http = Client()
        self.client_http.login(username="admin@test.ca", password="testpass123")
        self.program = Program.objects.create(name="Housing")
        self.link = SecureExportLink.objects.create(
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
        self.artifact = CanonicalReportArtifact.objects.create(
            export_link=self.link, state="enriched",
        )
        self.run = EnrichmentRun.objects.create(
            artifact=self.artifact, run_type="ai_enrichment", status="completed",
        )
        self.item = EnrichedMetadataItem.objects.create(
            artifact=self.artifact,
            enrichment_run=self.run,
            item_type="narrative",
            field_path="outcome_chain_summary",
            suggested_value="Better text",
        )

    def test_accept_item(self):
        response = self.client_http.post(
            f"/reports/exports/{self.link.pk}/metadata/items/{self.item.pk}/review/",
            {"action": "accepted"},
        )
        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        self.assertEqual(self.item.review_state, "accepted")

    def test_reject_item(self):
        response = self.client_http.post(
            f"/reports/exports/{self.link.pk}/metadata/items/{self.item.pk}/review/",
            {"action": "rejected"},
        )
        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        self.assertEqual(self.item.review_state, "rejected")
```

## Acceptance criteria

- [ ] 2 new models in `apps/reports/models.py` (EnrichedMetadataItem, ExportMetadataSnapshot)
- [ ] EnrichedMetadataItem.ITEM_TYPES does NOT include `taxonomy_mapping`
- [ ] Migration applies cleanly
- [ ] `enrichment_service.py` with `run_enrichment()`, `run_taxonomy_enrichment()`, `apply_metadata_snapshot()`
- [ ] Taxonomy enrichment routes through existing `taxonomy_review.py` (creates TaxonomyMapping, not EnrichedMetadataItem)
- [ ] Views: run enrichment, review item (with HTMX), apply snapshot (all admin-only)
- [ ] HTMX accept/reject buttons on enrichment items
- [ ] Tests: enrichment with mocked AI, bad response handling, snapshot with accepted/rejected filtering
- [ ] French translations added
