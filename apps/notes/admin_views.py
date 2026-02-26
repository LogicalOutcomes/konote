"""Admin views for progress note templates.

Admins: full access to all note templates.
PMs with template.note.manage: PROGRAM: manage templates in their own programs,
read-only view of global (admin-created) templates.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.forms import inlineformset_factory
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from apps.auth_app.decorators import requires_permission
from apps.programs.models import UserProgramRole

from .forms import NoteTemplateForm, NoteTemplateSectionForm
from .models import ProgressNoteTemplate, ProgressNoteTemplateSection


SectionFormSet = inlineformset_factory(
    ProgressNoteTemplate,
    ProgressNoteTemplateSection,
    form=NoteTemplateSectionForm,
    extra=1,
    can_delete=True,
)


def _get_pm_program_ids(user):
    """Return set of program IDs where the user is an active PM."""
    return set(
        UserProgramRole.objects.filter(
            user=user, role="program_manager", status="active",
        ).values_list("program_id", flat=True)
    )


def _can_edit_template(user, template):
    """Check if the user can edit a note template."""
    if user.is_admin:
        return True
    if template.owning_program_id is None:
        return False
    return template.owning_program_id in _get_pm_program_ids(user)


@login_required
@requires_permission("template.note.manage", allow_admin=True)
def template_list(request):
    if request.user.is_admin:
        templates = ProgressNoteTemplate.objects.all()
    else:
        pm_program_ids = _get_pm_program_ids(request.user)
        templates = ProgressNoteTemplate.objects.filter(
            Q(owning_program_id__in=pm_program_ids) | Q(owning_program__isnull=True)
        )
    return render(request, "notes/admin/template_list.html", {
        "templates": templates,
        "is_admin": request.user.is_admin,
    })


@login_required
@requires_permission("template.note.manage", allow_admin=True)
def template_create(request):
    if request.method == "POST":
        form = NoteTemplateForm(request.POST, requesting_user=request.user)
        formset = SectionFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            template = form.save(commit=False)
            # Auto-assign program for single-program PMs
            if not request.user.is_admin and template.owning_program_id is None:
                pm_program_ids = _get_pm_program_ids(request.user)
                if len(pm_program_ids) == 1:
                    template.owning_program_id = next(iter(pm_program_ids))
            template.save()
            formset.instance = template
            formset.save()
            messages.success(request, _("Note template created."))
            return redirect("note_templates:template_list")
    else:
        form = NoteTemplateForm(requesting_user=request.user)
        formset = SectionFormSet()
    return render(request, "notes/admin/template_form.html", {
        "form": form,
        "formset": formset,
        "editing": False,
    })


@login_required
@requires_permission("template.note.manage", allow_admin=True)
def template_edit(request, pk):
    template = get_object_or_404(ProgressNoteTemplate, pk=pk)

    if not _can_edit_template(request.user, template):
        return HttpResponseForbidden(_("Access denied. You can only edit templates in your programs."))

    if request.method == "POST":
        form = NoteTemplateForm(request.POST, instance=template, requesting_user=request.user)
        formset = SectionFormSet(request.POST, instance=template)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, _("Note template updated."))
            return redirect("note_templates:template_list")
    else:
        form = NoteTemplateForm(instance=template, requesting_user=request.user)
        formset = SectionFormSet(instance=template)
    return render(request, "notes/admin/template_form.html", {
        "form": form,
        "formset": formset,
        "editing": True,
        "template": template,
    })
