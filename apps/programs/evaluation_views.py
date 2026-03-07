"""Evaluation planning views — admin-only CRUD for CIDS Full Tier frameworks."""
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from apps.auth_app.decorators import admin_required

from .evaluation_forms import (
    EvaluationComponentForm,
    EvaluationEvidenceLinkForm,
    EvaluationFrameworkForm,
    EvaluatorAttestationForm,
)
from .models import (
    EvaluationComponent,
    EvaluationEvidenceLink,
    EvaluationFramework,
    Program,
)

logger = logging.getLogger(__name__)


@login_required
@admin_required
def framework_list(request):
    """List all evaluation frameworks, filterable by program."""
    program_id = request.GET.get("program")
    frameworks = EvaluationFramework.objects.select_related("program", "created_by")
    if program_id:
        frameworks = frameworks.filter(program_id=program_id)

    programs = Program.objects.filter(status="active")
    return render(request, "programs/evaluation/framework_list.html", {
        "frameworks": frameworks,
        "programs": programs,
        "selected_program_id": int(program_id) if program_id else None,
    })


@login_required
@admin_required
def framework_create(request, program_id):
    """Create an evaluation framework for a program."""
    program = get_object_or_404(Program, pk=program_id)
    if request.method == "POST":
        form = EvaluationFrameworkForm(request.POST)
        if form.is_valid():
            fw = form.save(commit=False)
            fw.program = program
            fw.created_by = request.user
            fw.updated_by = request.user
            fw.save()
            messages.success(request, _("Evaluation framework created."))
            return redirect("programs:framework_detail", framework_id=fw.pk)
    else:
        form = EvaluationFrameworkForm(initial={"name": f"{program.name} evaluation framework"})

    return render(request, "programs/evaluation/framework_form.html", {
        "form": form,
        "program": program,
        "is_create": True,
    })


@login_required
@admin_required
def framework_detail(request, framework_id):
    """View an evaluation framework with its components and evidence."""
    fw = get_object_or_404(
        EvaluationFramework.objects.select_related("program", "evaluator_attestation_by"),
        pk=framework_id,
    )
    components = fw.components.filter(is_active=True)
    evidence = fw.evidence_links.all()

    component_groups = {}
    for comp in components:
        group = comp.get_component_type_display()
        component_groups.setdefault(group, []).append(comp)

    cids_coverage = fw.cids_class_coverage
    total_cids_classes = 8  # Service, Activity, Output, Stakeholder, StakeholderOutcome, ImpactRisk, Counterfactual, ImpactDimension
    coverage_pct = round(len(cids_coverage) / total_cids_classes * 100) if total_cids_classes else 0

    return render(request, "programs/evaluation/framework_detail.html", {
        "framework": fw,
        "component_groups": component_groups,
        "evidence": evidence,
        "cids_coverage": cids_coverage,
        "coverage_pct": coverage_pct,
        "total_cids_classes": total_cids_classes,
    })


@login_required
@admin_required
def framework_edit(request, framework_id):
    """Edit an evaluation framework."""
    fw = get_object_or_404(EvaluationFramework, pk=framework_id)
    if request.method == "POST":
        form = EvaluationFrameworkForm(request.POST, instance=fw)
        if form.is_valid():
            fw = form.save(commit=False)
            fw.updated_by = request.user
            fw.save()
            messages.success(request, _("Evaluation framework updated."))
            return redirect("programs:framework_detail", framework_id=fw.pk)
    else:
        form = EvaluationFrameworkForm(instance=fw)

    return render(request, "programs/evaluation/framework_form.html", {
        "form": form,
        "program": fw.program,
        "framework": fw,
        "is_create": False,
    })


@login_required
@admin_required
def component_add(request, framework_id):
    """Add a component to a framework."""
    fw = get_object_or_404(EvaluationFramework, pk=framework_id)
    if request.method == "POST":
        form = EvaluationComponentForm(request.POST, framework=fw)
        if form.is_valid():
            comp = form.save(commit=False)
            comp.framework = fw
            comp.save()
            messages.success(request, _("Component added."))
            return redirect("programs:framework_detail", framework_id=fw.pk)
    else:
        form = EvaluationComponentForm(framework=fw)

    return render(request, "programs/evaluation/component_form.html", {
        "form": form,
        "framework": fw,
        "is_create": True,
    })


@login_required
@admin_required
def component_edit(request, framework_id, component_id):
    """Edit a component."""
    fw = get_object_or_404(EvaluationFramework, pk=framework_id)
    comp = get_object_or_404(EvaluationComponent, pk=component_id, framework=fw)
    if request.method == "POST":
        form = EvaluationComponentForm(request.POST, instance=comp, framework=fw)
        if form.is_valid():
            form.save()
            messages.success(request, _("Component updated."))
            return redirect("programs:framework_detail", framework_id=fw.pk)
    else:
        form = EvaluationComponentForm(instance=comp, framework=fw)

    return render(request, "programs/evaluation/component_form.html", {
        "form": form,
        "framework": fw,
        "component": comp,
        "is_create": False,
    })


@login_required
@admin_required
@require_POST
def component_deactivate(request, framework_id, component_id):
    """Deactivate a component (soft delete)."""
    fw = get_object_or_404(EvaluationFramework, pk=framework_id)
    comp = get_object_or_404(EvaluationComponent, pk=component_id, framework=fw)
    comp.is_active = False
    comp.save(update_fields=["is_active", "updated_at"])
    messages.success(request, _("Component removed."))
    return redirect("programs:framework_detail", framework_id=fw.pk)


@login_required
@admin_required
def evidence_add(request, framework_id):
    """Add an evidence link to a framework."""
    fw = get_object_or_404(EvaluationFramework, pk=framework_id)
    if request.method == "POST":
        form = EvaluationEvidenceLinkForm(request.POST)
        if form.is_valid():
            link = form.save(commit=False)
            link.framework = fw
            link.save()
            messages.success(request, _("Evidence link added."))
            return redirect("programs:framework_detail", framework_id=fw.pk)
    else:
        form = EvaluationEvidenceLinkForm()

    return render(request, "programs/evaluation/evidence_form.html", {
        "form": form,
        "framework": fw,
    })


@login_required
@admin_required
@require_POST
def evidence_delete(request, framework_id, evidence_id):
    """Delete an evidence link."""
    fw = get_object_or_404(EvaluationFramework, pk=framework_id)
    link = get_object_or_404(EvaluationEvidenceLink, pk=evidence_id, framework=fw)
    link.delete()
    messages.success(request, _("Evidence link removed."))
    return redirect("programs:framework_detail", framework_id=fw.pk)


@login_required
@admin_required
def framework_attest(request, framework_id):
    """Record evaluator attestation on a framework."""
    fw = get_object_or_404(EvaluationFramework, pk=framework_id)
    if request.method == "POST":
        form = EvaluatorAttestationForm(request.POST)
        if form.is_valid():
            fw.evaluator_attestation_by = request.user
            fw.evaluator_attestation_at = timezone.now()
            fw.evaluator_attestation_scope = form.cleaned_data["scope"]
            fw.evaluator_attestation_text = form.cleaned_data["attestation_text"]
            fw.save(update_fields=[
                "evaluator_attestation_by",
                "evaluator_attestation_at",
                "evaluator_attestation_scope",
                "evaluator_attestation_text",
                "updated_at",
            ])
            messages.success(request, _("Attestation recorded."))
            return redirect("programs:framework_detail", framework_id=fw.pk)
    else:
        form = EvaluatorAttestationForm()

    return render(request, "programs/evaluation/attest_form.html", {
        "form": form,
        "framework": fw,
    })
