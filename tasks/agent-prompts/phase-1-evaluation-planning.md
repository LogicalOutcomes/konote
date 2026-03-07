# Phase 1: Evaluation Planning — Agent Prompt

Build the evaluation planning foundation: 3 models, forms, views, templates, and tests.

## Context

KoNote is achieving CIDS Full Tier compliance. Most CIDS Full Tier classes describe the *program model*, not individual participants. The `EvaluationFramework` and `EvaluationComponent` models map directly to CIDS Full Tier classes:

| component_type | CIDS Class |
|---|---|
| `participant_group` | `cids:Stakeholder` |
| `service` | `cids:Service` |
| `activity` | `cids:Activity` |
| `output` | `cids:Output` |
| `outcome` | `cids:StakeholderOutcome` |
| `risk` | `cids:ImpactRisk` |
| `counterfactual` | `cids:Counterfactual` |
| `input` | `cids:Input` |
| `impact_dimension` | `cids:ImpactDimension` |

## Branch

Create branch `feat/evaluation-planning` off `develop`.

## 1. Models — edit `apps/programs/models.py`

Add these three models at the bottom of the file (after `UserProgramRole`):

### EvaluationFramework

```python
class EvaluationFramework(models.Model):
    """
    Evaluation planning document for a program.

    Maps to CIDS Full Tier ImpactModel. One per program.
    Does NOT duplicate fields already on Program (description, cids_sector_code,
    population_served_codes) — the editor shows Program fields read-only.
    """

    QUALITY_STATES = [
        ("draft", _("Draft")),
        ("ai_generated", _("AI Generated")),
        ("human_reviewed", _("Human Reviewed")),
        ("confirmed", _("Confirmed")),
    ]

    program = models.OneToOneField(
        Program,
        on_delete=models.CASCADE,
        related_name="evaluation_framework",
    )
    # These fields add what Program doesn't have
    outcome_chain_summary = models.TextField(
        blank=True, default="",
        help_text=_("Theory of change / logic model narrative."),
    )
    risk_summary = models.TextField(
        blank=True, default="",
        help_text=_("Summary of impact risks and mitigations."),
    )
    counterfactual_summary = models.TextField(
        blank=True, default="",
        help_text=_("What would happen without this intervention."),
    )
    partner_requirements_summary = models.TextField(
        blank=True, default="",
        help_text=_("Funder/partner evaluation requirements."),
    )
    output_summary = models.TextField(
        blank=True, default="",
        help_text=_("Summary of intended outputs."),
    )
    source_documents_json = models.JSONField(
        default=list, blank=True,
        help_text=_("List of source document references. Schema: [{filename, uploaded_at, notes}]"),
    )
    quality_state = models.CharField(
        max_length=20, choices=QUALITY_STATES, default="draft",
    )

    # Evaluator attestation
    attested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="attested_frameworks",
    )
    attested_at = models.DateTimeField(null=True, blank=True)
    attestation_note = models.TextField(
        blank=True, default="",
        help_text=_("Evaluator's attestation statement."),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="created_frameworks",
    )

    class Meta:
        app_label = "programs"
        db_table = "evaluation_frameworks"

    def __str__(self):
        return f"Evaluation Framework: {self.program.name}"
```

### EvaluationComponent

```python
class EvaluationComponent(models.Model):
    """
    Structured child record under an EvaluationFramework.

    Each component maps to a CIDS Full Tier class via component_type.
    The structured_payload JSONField holds type-specific data validated in clean().
    """

    COMPONENT_TYPES = [
        ("participant_group", _("Participant Group")),
        ("service", _("Service")),
        ("activity", _("Activity")),
        ("output", _("Output")),
        ("outcome", _("Outcome")),
        ("risk", _("Impact Risk")),
        ("mitigation", _("Risk Mitigation")),
        ("counterfactual", _("Counterfactual")),
        ("assumption", _("Assumption")),
        ("input", _("Input")),
        ("impact_dimension", _("Impact Dimension")),
    ]

    # Maps component_type to CIDS Full Tier class URI
    CIDS_CLASS_MAP = {
        "participant_group": "cids:Stakeholder",
        "service": "cids:Service",
        "activity": "cids:Activity",
        "output": "cids:Output",
        "outcome": "cids:StakeholderOutcome",
        "risk": "cids:ImpactRisk",
        "mitigation": "cids:ImpactRisk",
        "counterfactual": "cids:Counterfactual",
        "assumption": None,  # metadata on ImpactModel
        "input": "cids:Input",
        "impact_dimension": "cids:ImpactDimension",
    }

    QUALITY_STATES = EvaluationFramework.QUALITY_STATES

    framework = models.ForeignKey(
        EvaluationFramework,
        on_delete=models.CASCADE,
        related_name="components",
    )
    component_type = models.CharField(max_length=30, choices=COMPONENT_TYPES)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    structured_payload = models.JSONField(
        default=dict, blank=True,
        help_text=_("Type-specific structured data. Schema varies by component_type."),
    )
    sort_order = models.PositiveIntegerField(default=0)
    quality_state = models.CharField(
        max_length=20, choices=QUALITY_STATES, default="draft",
    )

    # Optional link to existing KoNote entities
    linked_metric = models.ForeignKey(
        "plans.MetricDefinition",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="evaluation_components",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "programs"
        db_table = "evaluation_components"
        ordering = ["sort_order", "component_type"]

    def __str__(self):
        return f"{self.get_component_type_display()}: {self.title}"

    @property
    def cids_class(self):
        """Return the CIDS Full Tier class URI for this component type."""
        return self.CIDS_CLASS_MAP.get(self.component_type)

    def clean(self):
        """Validate structured_payload against per-type schema."""
        from django.core.exceptions import ValidationError
        payload = self.structured_payload or {}
        if not isinstance(payload, dict):
            raise ValidationError({"structured_payload": "Must be a JSON object."})

        # Type-specific validation
        validators = {
            "participant_group": self._validate_participant_group,
            "outcome": self._validate_outcome,
            "risk": self._validate_risk,
        }
        validator = validators.get(self.component_type)
        if validator:
            validator(payload)

    def _validate_participant_group(self, payload):
        """Schema: {demographics: str, estimated_size: int|null, geographic_scope: str}"""
        pass  # Accept any dict for now; tighten as schemas mature

    def _validate_outcome(self, payload):
        """Schema: {indicator_name: str, measurement_method: str, target_value: str, timeframe: str}"""
        pass

    def _validate_risk(self, payload):
        """Schema: {likelihood: str, severity: str, mitigation_strategy: str}"""
        pass
```

### EvaluationEvidenceLink

```python
class EvaluationEvidenceLink(models.Model):
    """
    Provenance tracking: links source material to framework content.
    """

    EVIDENCE_TYPES = [
        ("document", _("Document")),
        ("url", _("URL")),
        ("note", _("Staff Note")),
        ("ai_output", _("AI Output")),
    ]

    framework = models.ForeignKey(
        EvaluationFramework,
        on_delete=models.CASCADE,
        related_name="evidence_links",
    )
    component = models.ForeignKey(
        EvaluationComponent,
        null=True, blank=True,
        on_delete=models.CASCADE,
        related_name="evidence_links",
    )
    evidence_type = models.CharField(max_length=20, choices=EVIDENCE_TYPES)
    title = models.CharField(max_length=255)
    reference = models.TextField(
        blank=True, default="",
        help_text=_("URL, file path, or description of the source."),
    )
    excerpt = models.TextField(
        blank=True, default="",
        help_text=_("Relevant excerpt from the source."),
    )
    contains_pii = models.BooleanField(
        default=False,
        help_text=_("If True, this evidence cannot be sent to external AI."),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "programs"
        db_table = "evaluation_evidence_links"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_evidence_type_display()}: {self.title}"
```

## 2. Migration

After adding models, run:
```bash
ssh konote-vps "docker compose -f /opt/konote-dev/docker-compose.yml exec web python manage.py makemigrations programs"
```

Or create the migration file manually (preferred for this agent task — create the migration file locally and let the VPS apply it on deploy).

## 3. Forms — edit `apps/programs/forms.py`

Add at the bottom:

```python
class EvaluationFrameworkForm(forms.ModelForm):
    class Meta:
        model = EvaluationFramework
        fields = [
            "outcome_chain_summary", "risk_summary", "counterfactual_summary",
            "partner_requirements_summary", "output_summary", "quality_state",
        ]
        widgets = {
            "outcome_chain_summary": forms.Textarea(attrs={"rows": 4}),
            "risk_summary": forms.Textarea(attrs={"rows": 3}),
            "counterfactual_summary": forms.Textarea(attrs={"rows": 3}),
            "partner_requirements_summary": forms.Textarea(attrs={"rows": 3}),
            "output_summary": forms.Textarea(attrs={"rows": 3}),
        }


class EvaluationComponentForm(forms.ModelForm):
    class Meta:
        model = EvaluationComponent
        fields = [
            "component_type", "title", "description",
            "structured_payload", "sort_order", "quality_state",
            "linked_metric",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 2}),
            "structured_payload": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        self.framework = kwargs.pop("framework", None)
        super().__init__(*args, **kwargs)


# Formset for inline component editing
from django.forms import inlineformset_factory

EvaluationComponentFormSet = inlineformset_factory(
    EvaluationFramework,
    EvaluationComponent,
    form=EvaluationComponentForm,
    extra=1,
    can_delete=True,
)
```

Import `EvaluationFramework` and `EvaluationComponent` at the top of forms.py:
```python
from .models import Program, UserProgramRole, EvaluationFramework, EvaluationComponent
```

## 4. Views — edit `apps/programs/views.py`

Add these views at the bottom of the file:

```python
@login_required
@admin_required
def evaluation_framework_list(request):
    """List all evaluation frameworks across programs."""
    frameworks = EvaluationFramework.objects.select_related("program").all()
    return render(request, "programs/evaluation_framework_list.html", {
        "frameworks": frameworks,
    })


@login_required
@admin_required
def evaluation_framework_detail(request, framework_id):
    """View a single evaluation framework with its components."""
    framework = get_object_or_404(
        EvaluationFramework.objects.select_related("program"),
        pk=framework_id,
    )
    components = framework.components.all()
    evidence = framework.evidence_links.select_related("component").all()
    return render(request, "programs/evaluation_framework_detail.html", {
        "framework": framework,
        "components": components,
        "evidence": evidence,
    })


@login_required
@admin_required
def evaluation_framework_create(request, program_id):
    """Create an evaluation framework for a program."""
    from .forms import EvaluationFrameworkForm
    program = get_object_or_404(Program, pk=program_id)

    # Don't allow duplicate frameworks
    if hasattr(program, "evaluation_framework"):
        messages.info(request, _("This program already has an evaluation framework."))
        return redirect("programs:evaluation_framework_detail",
                        framework_id=program.evaluation_framework.pk)

    if request.method == "POST":
        form = EvaluationFrameworkForm(request.POST)
        if form.is_valid():
            framework = form.save(commit=False)
            framework.program = program
            framework.created_by = request.user
            framework.save()
            messages.success(request, _("Evaluation framework created."))
            return redirect("programs:evaluation_framework_detail",
                            framework_id=framework.pk)
    else:
        form = EvaluationFrameworkForm()

    return render(request, "programs/evaluation_framework_form.html", {
        "form": form,
        "program": program,
        "editing": False,
    })


@login_required
@admin_required
def evaluation_framework_edit(request, framework_id):
    """Edit an existing evaluation framework."""
    from .forms import EvaluationFrameworkForm, EvaluationComponentFormSet
    framework = get_object_or_404(
        EvaluationFramework.objects.select_related("program"),
        pk=framework_id,
    )

    if request.method == "POST":
        form = EvaluationFrameworkForm(request.POST, instance=framework)
        formset = EvaluationComponentFormSet(request.POST, instance=framework)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, _("Evaluation framework updated."))
            return redirect("programs:evaluation_framework_detail",
                            framework_id=framework.pk)
    else:
        form = EvaluationFrameworkForm(instance=framework)
        formset = EvaluationComponentFormSet(instance=framework)

    return render(request, "programs/evaluation_framework_form.html", {
        "form": form,
        "formset": formset,
        "framework": framework,
        "program": framework.program,
        "editing": True,
    })


@login_required
@admin_required
def evaluation_component_add(request, framework_id):
    """Add a single component to a framework (HTMX partial)."""
    from .forms import EvaluationComponentForm
    framework = get_object_or_404(EvaluationFramework, pk=framework_id)

    if request.method == "POST":
        form = EvaluationComponentForm(request.POST, framework=framework)
        if form.is_valid():
            component = form.save(commit=False)
            component.framework = framework
            component.save()
            if request.headers.get("HX-Request"):
                components = framework.components.all()
                return render(request, "programs/partials/component_table.html", {
                    "components": components,
                    "framework": framework,
                })
            messages.success(request, _("Component added."))
            return redirect("programs:evaluation_framework_detail",
                            framework_id=framework.pk)

    form = EvaluationComponentForm(framework=framework)
    return render(request, "programs/partials/component_form.html", {
        "form": form,
        "framework": framework,
    })
```

Add these imports at the top of views.py:
```python
from .models import Program, UserProgramRole, EvaluationFramework, EvaluationComponent
```

## 5. URLs — edit `apps/programs/urls.py`

Add these URL patterns inside `urlpatterns`:

```python
# Evaluation frameworks
path("evaluation-frameworks/",
     views.evaluation_framework_list,
     name="evaluation_framework_list"),
path("<int:program_id>/evaluation-framework/create/",
     views.evaluation_framework_create,
     name="evaluation_framework_create"),
path("evaluation-frameworks/<int:framework_id>/",
     views.evaluation_framework_detail,
     name="evaluation_framework_detail"),
path("evaluation-frameworks/<int:framework_id>/edit/",
     views.evaluation_framework_edit,
     name="evaluation_framework_edit"),
path("evaluation-frameworks/<int:framework_id>/components/add/",
     views.evaluation_component_add,
     name="evaluation_component_add"),
```

## 6. Templates

Create these files under `templates/programs/`:

### `evaluation_framework_list.html`
```html
{% extends "base.html" %}
{% load i18n %}

{% block title %}{% trans "Evaluation Frameworks" %}{% endblock %}

{% block content %}
<h1>{% trans "Evaluation Frameworks" %}</h1>
<p>{% trans "Evaluation frameworks map program models to CIDS Full Tier classes for impact reporting." %}</p>

<table role="grid">
  <thead>
    <tr>
      <th>{% trans "Program" %}</th>
      <th>{% trans "Quality" %}</th>
      <th>{% trans "Components" %}</th>
      <th>{% trans "Updated" %}</th>
      <th></th>
    </tr>
  </thead>
  <tbody>
    {% for fw in frameworks %}
    <tr>
      <td><a href="{% url 'programs:evaluation_framework_detail' framework_id=fw.pk %}">{{ fw.program.name }}</a></td>
      <td><mark>{{ fw.get_quality_state_display }}</mark></td>
      <td>{{ fw.components.count }}</td>
      <td>{{ fw.updated_at|date:"Y-m-d" }}</td>
      <td><a href="{% url 'programs:evaluation_framework_edit' framework_id=fw.pk %}">{% trans "Edit" %}</a></td>
    </tr>
    {% empty %}
    <tr>
      <td colspan="5">{% trans "No evaluation frameworks yet. Create one from a program's detail page." %}</td>
    </tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
```

### `evaluation_framework_detail.html`
```html
{% extends "base.html" %}
{% load i18n %}

{% block title %}{% trans "Evaluation Framework" %} — {{ framework.program.name }}{% endblock %}

{% block content %}
<nav aria-label="breadcrumb">
  <ul>
    <li><a href="{% url 'programs:evaluation_framework_list' %}">{% trans "Frameworks" %}</a></li>
    <li>{{ framework.program.name }}</li>
  </ul>
</nav>

<h1>{{ framework.program.name }}</h1>

<details open>
  <summary>{% trans "Program Details" %} <small>({% trans "read-only" %})</small></summary>
  <dl>
    <dt>{% trans "Description" %}</dt>
    <dd>{{ framework.program.description|default:"—" }}</dd>
    <dt>{% trans "CIDS Sector" %}</dt>
    <dd>{{ framework.program.cids_sector_code|default:"—" }}</dd>
    <dt>{% trans "Service Model" %}</dt>
    <dd>{{ framework.program.get_service_model_display }}</dd>
  </dl>
</details>

<h2>{% trans "Evaluation Narrative" %}</h2>
<dl>
  <dt>{% trans "Theory of Change" %}</dt>
  <dd>{{ framework.outcome_chain_summary|default:"—"|linebreaksbr }}</dd>
  <dt>{% trans "Risks" %}</dt>
  <dd>{{ framework.risk_summary|default:"—"|linebreaksbr }}</dd>
  <dt>{% trans "Counterfactual" %}</dt>
  <dd>{{ framework.counterfactual_summary|default:"—"|linebreaksbr }}</dd>
  <dt>{% trans "Outputs" %}</dt>
  <dd>{{ framework.output_summary|default:"—"|linebreaksbr }}</dd>
  <dt>{% trans "Partner Requirements" %}</dt>
  <dd>{{ framework.partner_requirements_summary|default:"—"|linebreaksbr }}</dd>
</dl>
<p><strong>{% trans "Quality" %}:</strong> <mark>{{ framework.get_quality_state_display }}</mark></p>

{% if framework.attested_by %}
<details>
  <summary>{% trans "Evaluator Attestation" %}</summary>
  <p>{% trans "Attested by" %} {{ framework.attested_by.get_full_name }} {% trans "on" %} {{ framework.attested_at|date:"Y-m-d H:i" }}</p>
  <blockquote>{{ framework.attestation_note }}</blockquote>
</details>
{% endif %}

<h2>{% trans "Components" %}</h2>
<table role="grid">
  <thead>
    <tr>
      <th>{% trans "Type" %}</th>
      <th>{% trans "CIDS Class" %}</th>
      <th>{% trans "Title" %}</th>
      <th>{% trans "Quality" %}</th>
    </tr>
  </thead>
  <tbody>
    {% for comp in components %}
    <tr>
      <td>{{ comp.get_component_type_display }}</td>
      <td><code>{{ comp.cids_class|default:"—" }}</code></td>
      <td>{{ comp.title }}</td>
      <td><mark>{{ comp.get_quality_state_display }}</mark></td>
    </tr>
    {% empty %}
    <tr><td colspan="4">{% trans "No components yet." %}</td></tr>
    {% endfor %}
  </tbody>
</table>

<a href="{% url 'programs:evaluation_framework_edit' framework_id=framework.pk %}" role="button">{% trans "Edit Framework" %}</a>
{% endblock %}
```

### `evaluation_framework_form.html`
```html
{% extends "base.html" %}
{% load i18n %}

{% block title %}{% if editing %}{% trans "Edit" %}{% else %}{% trans "Create" %}{% endif %} {% trans "Evaluation Framework" %}{% endblock %}

{% block content %}
<h1>{% if editing %}{% trans "Edit" %}{% else %}{% trans "Create" %}{% endif %} {% trans "Evaluation Framework" %}</h1>
<p>{{ program.name }}</p>

<form method="post">
  {% csrf_token %}

  <details open>
    <summary>{% trans "Program Details" %} <small>({% trans "read-only — edit on program page" %})</small></summary>
    <dl>
      <dt>{% trans "Description" %}</dt>
      <dd>{{ program.description|default:"—" }}</dd>
      <dt>{% trans "CIDS Sector" %}</dt>
      <dd>{{ program.cids_sector_code|default:"—" }}</dd>
    </dl>
  </details>

  <h2>{% trans "Evaluation Narrative" %}</h2>
  {% for field in form %}
  <label for="{{ field.id_for_label }}">{{ field.label }}</label>
  {{ field }}
  {% if field.help_text %}<small>{{ field.help_text }}</small>{% endif %}
  {% if field.errors %}<small class="error">{{ field.errors.0 }}</small>{% endif %}
  {% endfor %}

  {% if editing and formset %}
  <h2>{% trans "Components" %}</h2>
  {{ formset.management_form }}
  <table role="grid">
    <thead>
      <tr>
        <th>{% trans "Type" %}</th>
        <th>{% trans "Title" %}</th>
        <th>{% trans "Description" %}</th>
        <th>{% trans "Quality" %}</th>
        <th>{% trans "Delete" %}</th>
      </tr>
    </thead>
    <tbody>
      {% for cform in formset %}
      <tr>
        <td>{{ cform.component_type }}</td>
        <td>{{ cform.title }}</td>
        <td>{{ cform.description }}</td>
        <td>{{ cform.quality_state }}</td>
        <td>{{ cform.DELETE }}</td>
        {{ cform.structured_payload }}
        {{ cform.sort_order }}
        {{ cform.linked_metric }}
        {% for hidden in cform.hidden_fields %}{{ hidden }}{% endfor %}
      </tr>
      {% endfor %}
    </tbody>
  </table>
  {% endif %}

  <button type="submit">{% trans "Save" %}</button>
</form>
{% endblock %}
```

### `partials/component_table.html`
```html
{% load i18n %}
<table role="grid" id="component-table">
  <thead>
    <tr>
      <th>{% trans "Type" %}</th>
      <th>{% trans "CIDS Class" %}</th>
      <th>{% trans "Title" %}</th>
      <th>{% trans "Quality" %}</th>
    </tr>
  </thead>
  <tbody>
    {% for comp in components %}
    <tr>
      <td>{{ comp.get_component_type_display }}</td>
      <td><code>{{ comp.cids_class|default:"—" }}</code></td>
      <td>{{ comp.title }}</td>
      <td><mark>{{ comp.get_quality_state_display }}</mark></td>
    </tr>
    {% empty %}
    <tr><td colspan="4">{% trans "No components yet." %}</td></tr>
    {% endfor %}
  </tbody>
</table>
```

### `partials/component_form.html`
```html
{% load i18n %}
<form method="post" action="{% url 'programs:evaluation_component_add' framework_id=framework.pk %}"
      hx-post="{% url 'programs:evaluation_component_add' framework_id=framework.pk %}"
      hx-target="#component-table"
      hx-swap="outerHTML">
  {% csrf_token %}
  {% for field in form %}
  <label for="{{ field.id_for_label }}">{{ field.label }}</label>
  {{ field }}
  {% endfor %}
  <button type="submit">{% trans "Add Component" %}</button>
</form>
```

## 7. Tests — create `tests/test_evaluation_framework.py`

```python
"""Tests for EvaluationFramework, EvaluationComponent, and related views."""
import json
from unittest.mock import patch

from django.test import TestCase, Client, override_settings
from django.utils import timezone
from cryptography.fernet import Fernet

from apps.auth_app.models import User
from apps.programs.models import (
    Program, UserProgramRole, EvaluationFramework,
    EvaluationComponent, EvaluationEvidenceLink,
)

import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class EvaluationFrameworkModelTest(TestCase):
    def setUp(self):
        enc_module._fernet = None
        self.program = Program.objects.create(name="Youth Services")
        self.user = User.objects.create_user(
            username="admin@test.ca", password="testpass123",
            is_admin=True,
        )

    def test_create_framework(self):
        fw = EvaluationFramework.objects.create(
            program=self.program,
            outcome_chain_summary="Youth gain employment skills",
            quality_state="draft",
            created_by=self.user,
        )
        self.assertEqual(fw.program, self.program)
        self.assertEqual(str(fw), "Evaluation Framework: Youth Services")

    def test_one_framework_per_program(self):
        EvaluationFramework.objects.create(program=self.program)
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            EvaluationFramework.objects.create(program=self.program)

    def test_component_cids_class(self):
        fw = EvaluationFramework.objects.create(program=self.program)
        comp = EvaluationComponent.objects.create(
            framework=fw,
            component_type="participant_group",
            title="Youth aged 16-24",
        )
        self.assertEqual(comp.cids_class, "cids:Stakeholder")

    def test_component_types_all_mapped(self):
        """Every component_type should have a CIDS class mapping (or None for metadata)."""
        for type_code, _ in EvaluationComponent.COMPONENT_TYPES:
            self.assertIn(type_code, EvaluationComponent.CIDS_CLASS_MAP)

    def test_evidence_link_pii_flag(self):
        fw = EvaluationFramework.objects.create(program=self.program)
        link = EvaluationEvidenceLink.objects.create(
            framework=fw,
            evidence_type="document",
            title="Intake form template",
            contains_pii=True,
        )
        self.assertTrue(link.contains_pii)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class EvaluationFrameworkViewTest(TestCase):
    def setUp(self):
        enc_module._fernet = None
        self.user = User.objects.create_user(
            username="admin@test.ca", password="testpass123",
            is_admin=True,
        )
        self.program = Program.objects.create(name="Youth Services")
        UserProgramRole.objects.create(
            user=self.user, program=self.program, role="program_manager",
        )
        self.client = Client()
        self.client.login(username="admin@test.ca", password="testpass123")

    def test_list_view(self):
        response = self.client.get("/programs/evaluation-frameworks/")
        self.assertEqual(response.status_code, 200)

    def test_create_framework(self):
        response = self.client.post(
            f"/programs/{self.program.pk}/evaluation-framework/create/",
            {
                "outcome_chain_summary": "Youth gain skills",
                "quality_state": "draft",
                "risk_summary": "",
                "counterfactual_summary": "",
                "partner_requirements_summary": "",
                "output_summary": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            EvaluationFramework.objects.filter(program=self.program).exists()
        )

    def test_non_admin_blocked(self):
        non_admin = User.objects.create_user(
            username="staff@test.ca", password="testpass123",
            is_admin=False,
        )
        self.client.login(username="staff@test.ca", password="testpass123")
        response = self.client.get("/programs/evaluation-frameworks/")
        self.assertEqual(response.status_code, 403)

    def test_duplicate_framework_redirects(self):
        EvaluationFramework.objects.create(program=self.program)
        response = self.client.post(
            f"/programs/{self.program.pk}/evaluation-framework/create/",
            {"outcome_chain_summary": "Duplicate", "quality_state": "draft",
             "risk_summary": "", "counterfactual_summary": "",
             "partner_requirements_summary": "", "output_summary": ""},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(EvaluationFramework.objects.filter(program=self.program).count(), 1)
```

## 8. Translations

After creating templates with `{% trans %}` tags, run:
```bash
python manage.py translate_strings
```
Then fill in French translations in `locale/fr/LC_MESSAGES/django.po`.

## 9. Wire up to program detail page

Edit `templates/programs/detail.html` to add a link:
```html
{% if request.user.is_admin %}
<a href="{% url 'programs:evaluation_framework_create' program_id=program.pk %}"
   role="button" class="secondary">
  {% trans "Create Evaluation Framework" %}
</a>
{% endif %}
```

If the program already has a framework, show a link to view it instead.

## Acceptance criteria

- [ ] 3 new models created in `apps/programs/models.py`
- [ ] Migration file created and applies cleanly
- [ ] Forms with ModelForm validation (not raw POST)
- [ ] CRUD views for framework (list, detail, create, edit)
- [ ] Component add view with HTMX support
- [ ] All views admin-only (`@admin_required`)
- [ ] Templates extend `base.html`, use `{% trans %}` tags
- [ ] CIDS class badges shown on components
- [ ] Tests pass: model CRUD, view permissions, duplicate prevention
- [ ] No PII in any model field — all fields describe programs, not people
- [ ] French translations added
- [ ] Link from program detail page to framework
