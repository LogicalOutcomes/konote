"""Admin views for plan template CRUD (PLAN4) and apply-to-client (PLAN5)."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from apps.auth_app.decorators import admin_required
from apps.clients.models import ClientFile
from apps.clients.views import get_client_queryset
from apps.plans.admin_forms import (
    PlanTemplateForm,
    PlanTemplateSectionForm,
    PlanTemplateTargetForm,
)
from apps.plans.models import (
    PlanSection,
    PlanTarget,
    PlanTemplate,
    PlanTemplateSection,
    PlanTemplateTarget,
)


# ---------------------------------------------------------------------------
# PLAN4 — Template CRUD
# ---------------------------------------------------------------------------

@login_required
@admin_required
def template_list(request):
    """List all plan templates."""
    templates = PlanTemplate.objects.prefetch_related("sections").all()
    return render(request, "plans/template_list.html", {"templates": templates})


@login_required
@admin_required
def template_create(request):
    """Create a new plan template."""
    if request.method == "POST":
        form = PlanTemplateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("Template created."))
            return redirect("plan_templates:template_list")
    else:
        form = PlanTemplateForm()

    return render(request, "plans/template_form.html", {
        "form": form,
        "is_edit": False,
    })


@login_required
@admin_required
def template_edit(request, template_id):
    """Edit an existing plan template."""
    template = get_object_or_404(PlanTemplate, pk=template_id)

    if request.method == "POST":
        form = PlanTemplateForm(request.POST, instance=template)
        if form.is_valid():
            form.save()
            messages.success(request, _("Template updated."))
            return redirect("plan_templates:template_detail", template_id=template.pk)
    else:
        form = PlanTemplateForm(instance=template)

    return render(request, "plans/template_form.html", {
        "form": form,
        "template": template,
        "is_edit": True,
    })


@login_required
@admin_required
def template_detail(request, template_id):
    """Show a template with its sections and targets."""
    template = get_object_or_404(
        PlanTemplate.objects.prefetch_related("sections__targets"),
        pk=template_id,
    )
    return render(request, "plans/template_detail.html", {"template": template})


# --- Template sections ---

@login_required
@admin_required
def template_section_create(request, template_id):
    """Add a section to a template."""
    template = get_object_or_404(PlanTemplate, pk=template_id)

    if request.method == "POST":
        form = PlanTemplateSectionForm(request.POST)
        if form.is_valid():
            section = form.save(commit=False)
            section.plan_template = template
            section.save()
            messages.success(request, _("Section added."))
            return redirect("plan_templates:template_detail", template_id=template.pk)
    else:
        form = PlanTemplateSectionForm()

    return render(request, "plans/template_section_form.html", {
        "form": form,
        "template": template,
        "is_edit": False,
    })


@login_required
@admin_required
def template_section_edit(request, section_id):
    """Edit a template section."""
    section = get_object_or_404(PlanTemplateSection, pk=section_id)
    template = section.plan_template

    if request.method == "POST":
        form = PlanTemplateSectionForm(request.POST, instance=section)
        if form.is_valid():
            form.save()
            messages.success(request, _("Section updated."))
            return redirect("plan_templates:template_detail", template_id=template.pk)
    else:
        form = PlanTemplateSectionForm(instance=section)

    return render(request, "plans/template_section_form.html", {
        "form": form,
        "template": template,
        "section": section,
        "is_edit": True,
    })


@login_required
@admin_required
def template_section_delete(request, section_id):
    """Delete a template section after POST confirmation."""
    section = get_object_or_404(PlanTemplateSection, pk=section_id)
    template = section.plan_template

    if request.method == "POST":
        section.delete()
        messages.success(request, _("Section deleted."))
        return redirect("plan_templates:template_detail", template_id=template.pk)

    # GET — show confirmation page
    return render(request, "plans/template_section_delete_confirm.html", {
        "section": section,
        "template": template,
    })


# --- Template targets ---

@login_required
@admin_required
def template_target_create(request, section_id):
    """Add a target to a template section."""
    section = get_object_or_404(PlanTemplateSection, pk=section_id)
    template = section.plan_template

    if request.method == "POST":
        form = PlanTemplateTargetForm(request.POST)
        if form.is_valid():
            target = form.save(commit=False)
            target.template_section = section
            target.save()
            messages.success(request, _("Target added."))
            return redirect("plan_templates:template_detail", template_id=template.pk)
    else:
        form = PlanTemplateTargetForm()

    return render(request, "plans/template_target_form.html", {
        "form": form,
        "template": template,
        "section": section,
        "is_edit": False,
    })


@login_required
@admin_required
def template_target_edit(request, target_id):
    """Edit a template target."""
    target = get_object_or_404(PlanTemplateTarget, pk=target_id)
    section = target.template_section
    template = section.plan_template

    if request.method == "POST":
        form = PlanTemplateTargetForm(request.POST, instance=target)
        if form.is_valid():
            form.save()
            messages.success(request, _("Target updated."))
            return redirect("plan_templates:template_detail", template_id=template.pk)
    else:
        form = PlanTemplateTargetForm(instance=target)

    return render(request, "plans/template_target_form.html", {
        "form": form,
        "template": template,
        "section": section,
        "target": target,
        "is_edit": True,
    })


@login_required
@admin_required
def template_target_delete(request, target_id):
    """Delete a template target after POST confirmation."""
    target = get_object_or_404(PlanTemplateTarget, pk=target_id)
    section = target.template_section
    template = section.plan_template

    if request.method == "POST":
        target.delete()
        messages.success(request, _("Target deleted."))
        return redirect("plan_templates:template_detail", template_id=template.pk)

    return render(request, "plans/template_target_delete_confirm.html", {
        "target": target,
        "section": section,
        "template": template,
    })


# ---------------------------------------------------------------------------
# PLAN5 — Apply template to a client
# ---------------------------------------------------------------------------

@login_required
@admin_required
def template_apply_list(request, client_id):
    """Show active templates that can be applied to a client."""
    base_queryset = get_client_queryset(request.user)
    client_file = get_object_or_404(base_queryset, pk=client_id)
    templates = PlanTemplate.objects.filter(status="active").prefetch_related("sections__targets")

    return render(request, "plans/template_apply.html", {
        "client_file": client_file,
        "templates": templates,
    })


@login_required
@admin_required
def template_apply(request, client_id, template_id):
    """Apply a template to a client — copies sections and targets."""
    if request.method != "POST":
        return redirect("plan_templates:template_apply_list", client_id=client_id)

    base_queryset = get_client_queryset(request.user)
    client_file = get_object_or_404(base_queryset, pk=client_id)
    template = get_object_or_404(
        PlanTemplate.objects.prefetch_related("sections__targets"),
        pk=template_id,
        status="active",
    )

    with transaction.atomic():
        for tmpl_section in template.sections.all():
            plan_section = PlanSection.objects.create(
                client_file=client_file,
                name=tmpl_section.name,
                program=tmpl_section.program,
                sort_order=tmpl_section.sort_order,
            )
            for tmpl_target in tmpl_section.targets.all():
                PlanTarget.objects.create(
                    plan_section=plan_section,
                    client_file=client_file,
                    name=tmpl_target.name,
                    description=tmpl_target.description,
                    sort_order=tmpl_target.sort_order,
                )

    messages.success(request, _('Template "%(name)s" applied successfully.') % {"name": template.name})
    return redirect("plans:plan_view", client_id=client_file.pk)
