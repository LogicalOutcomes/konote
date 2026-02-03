"""Client CRUD views."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from apps.programs.models import Program, UserProgramRole

from .forms import ClientFileForm, CustomFieldDefinitionForm, CustomFieldGroupForm
from .models import ClientDetailValue, ClientFile, ClientProgramEnrolment, CustomFieldGroup


def _get_accessible_programs(user):
    """Return programs the user can access.

    Admins without program roles get no programs (they manage system config, not client data).
    """
    if user.is_admin:
        # Admins see programs for management; if they also have program roles, include those
        admin_program_ids = UserProgramRole.objects.filter(user=user, status="active").values_list("program_id", flat=True)
        if admin_program_ids:
            return Program.objects.filter(pk__in=admin_program_ids, status="active")
        return Program.objects.none()
    return Program.objects.filter(
        pk__in=UserProgramRole.objects.filter(user=user, status="active").values_list("program_id", flat=True),
        status="active",
    )


def _get_accessible_clients(user):
    """Return client queryset scoped to user's programs.

    Uses prefetch_related to avoid N+1 queries when displaying enrolments.
    Admins without program roles see no clients.
    """
    program_ids = UserProgramRole.objects.filter(user=user, status="active").values_list("program_id", flat=True)
    client_ids = ClientProgramEnrolment.objects.filter(
        program_id__in=program_ids, status="enrolled"
    ).values_list("client_file_id", flat=True)
    return ClientFile.objects.filter(pk__in=client_ids).prefetch_related("enrolments__program")


@login_required
def client_list(request):
    clients = _get_accessible_clients(request.user)
    # Decrypt names and build display list
    client_data = []
    for client in clients:
        programs = [e.program for e in client.enrolments.all() if e.status == "enrolled"]
        client_data.append({
            "client": client,
            "name": f"{client.first_name} {client.last_name}",
            "programs": programs,
        })
    # Sort by name
    client_data.sort(key=lambda c: c["name"].lower())
    paginator = Paginator(client_data, 25)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "clients/list.html", {"page": page})


@login_required
def client_create(request):
    available_programs = _get_accessible_programs(request.user)
    if request.method == "POST":
        form = ClientFileForm(request.POST, available_programs=available_programs)
        if form.is_valid():
            client = ClientFile()
            client.first_name = form.cleaned_data["first_name"]
            client.last_name = form.cleaned_data["last_name"]
            client.middle_name = form.cleaned_data["middle_name"] or ""
            client.birth_date = form.cleaned_data["birth_date"]
            client.record_id = form.cleaned_data["record_id"]
            client.status = form.cleaned_data["status"]
            client.save()
            # Enrol in selected programs
            for program in form.cleaned_data["programs"]:
                ClientProgramEnrolment.objects.create(client_file=client, program=program)
            messages.success(request, "Client file created.")
            return redirect("clients:client_detail", client_id=client.pk)
    else:
        form = ClientFileForm(available_programs=available_programs)
    return render(request, "clients/form.html", {"form": form, "editing": False})


@login_required
def client_edit(request, client_id):
    client = get_object_or_404(ClientFile, pk=client_id)
    available_programs = _get_accessible_programs(request.user)
    current_program_ids = list(
        ClientProgramEnrolment.objects.filter(client_file=client, status="enrolled").values_list("program_id", flat=True)
    )
    if request.method == "POST":
        form = ClientFileForm(request.POST, available_programs=available_programs)
        if form.is_valid():
            client.first_name = form.cleaned_data["first_name"]
            client.last_name = form.cleaned_data["last_name"]
            client.middle_name = form.cleaned_data["middle_name"] or ""
            client.birth_date = form.cleaned_data["birth_date"]
            client.record_id = form.cleaned_data["record_id"]
            client.status = form.cleaned_data["status"]
            client.save()
            # Sync enrolments
            selected_ids = set(p.pk for p in form.cleaned_data["programs"])
            # Unenrol removed programs
            for enrolment in ClientProgramEnrolment.objects.filter(client_file=client, status="enrolled"):
                if enrolment.program_id not in selected_ids:
                    enrolment.status = "unenrolled"
                    enrolment.save()
            # Enrol new programs
            for program_id in selected_ids:
                if program_id not in current_program_ids:
                    ClientProgramEnrolment.objects.update_or_create(
                        client_file=client, program_id=program_id,
                        defaults={"status": "enrolled"},
                    )
            messages.success(request, "Client file updated.")
            return redirect("clients:client_detail", client_id=client.pk)
    else:
        form = ClientFileForm(
            initial={
                "first_name": client.first_name,
                "last_name": client.last_name,
                "middle_name": client.middle_name,
                "birth_date": client.birth_date,
                "record_id": client.record_id,
                "status": client.status,
                "programs": current_program_ids,
            },
            available_programs=available_programs,
        )
    return render(request, "clients/form.html", {"form": form, "editing": True, "client": client})


@login_required
def client_detail(request, client_id):
    client = get_object_or_404(ClientFile, pk=client_id)
    # Track recently viewed clients in session (most recent first, max 10)
    recent = request.session.get("recent_clients", [])
    if client_id in recent:
        recent.remove(client_id)
    recent.insert(0, client_id)
    request.session["recent_clients"] = recent[:10]

    enrolments = ClientProgramEnrolment.objects.filter(client_file=client, status="enrolled").select_related("program")
    # Custom fields for Info tab
    groups = CustomFieldGroup.objects.filter(status="active").prefetch_related("fields")
    custom_data = []
    for group in groups:
        fields = group.fields.filter(status="active")
        field_values = []
        for field_def in fields:
            try:
                cdv = ClientDetailValue.objects.get(client_file=client, field_def=field_def)
                value = cdv.get_value()
            except ClientDetailValue.DoesNotExist:
                value = ""
            field_values.append({"field_def": field_def, "value": value})
        custom_data.append({"group": group, "fields": field_values})
    context = {
        "client": client,
        "enrolments": enrolments,
        "custom_data": custom_data,
        "active_tab": "info",
        "user_role": getattr(request, "user_program_role", None),
    }
    # HTMX tab switch — return only the tab content partial
    if request.headers.get("HX-Request"):
        return render(request, "clients/_tab_info.html", context)
    return render(request, "clients/detail.html", context)


@login_required
def client_save_custom_fields(request, client_id):
    """HTMX: save custom field values for a client."""
    client = get_object_or_404(ClientFile, pk=client_id)
    if request.method == "POST":
        groups = CustomFieldGroup.objects.filter(status="active").prefetch_related("fields")
        for group in groups:
            for field_def in group.fields.filter(status="active"):
                raw_value = request.POST.get(f"custom_{field_def.pk}", "")
                cdv, _ = ClientDetailValue.objects.get_or_create(
                    client_file=client, field_def=field_def,
                )
                cdv.set_value(raw_value)
                cdv.save()
        messages.success(request, "Custom fields saved.")
    return redirect("clients:client_detail", client_id=client.pk)


@login_required
def client_search(request):
    """HTMX: return search results partial.

    Encrypted fields cannot be searched in SQL — loads accessible clients
    into Python and filters in memory. Acceptable up to ~2,000 clients.
    """
    query = request.GET.get("q", "").strip().lower()
    if not query:
        return render(request, "clients/_search_results.html", {"results": [], "query": ""})

    clients = _get_accessible_clients(request.user)
    results = []
    for client in clients:
        name = f"{client.first_name} {client.last_name}".lower()
        record = (client.record_id or "").lower()
        if query in name or query in record:
            programs = [e.program for e in client.enrolments.all() if e.status == "enrolled"]
            results.append({
                "client": client,
                "name": f"{client.first_name} {client.last_name}",
                "programs": programs,
            })
    results.sort(key=lambda c: c["name"].lower())
    return render(request, "clients/_search_results.html", {"results": results[:50], "query": query})


# ---- Custom Field Admin (FIELD1) — admin only ----

@login_required
def custom_field_admin(request):
    if not request.user.is_admin:
        return HttpResponseForbidden("Access denied.")
    groups = CustomFieldGroup.objects.all().prefetch_related("fields")
    return render(request, "clients/custom_fields_admin.html", {"groups": groups})


@login_required
def custom_field_group_create(request):
    if not request.user.is_admin:
        return HttpResponseForbidden("Access denied.")
    if request.method == "POST":
        form = CustomFieldGroupForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Field group created.")
            return redirect("clients:custom_field_admin")
    else:
        form = CustomFieldGroupForm()
    return render(request, "clients/custom_field_form.html", {"form": form, "title": "New Field Group"})


@login_required
def custom_field_group_edit(request, group_id):
    if not request.user.is_admin:
        return HttpResponseForbidden("Access denied.")
    group = get_object_or_404(CustomFieldGroup, pk=group_id)
    if request.method == "POST":
        form = CustomFieldGroupForm(request.POST, instance=group)
        if form.is_valid():
            form.save()
            messages.success(request, "Field group updated.")
            return redirect("clients:custom_field_admin")
    else:
        form = CustomFieldGroupForm(instance=group)
    return render(request, "clients/custom_field_form.html", {"form": form, "title": f"Edit {group.title}"})


@login_required
def custom_field_def_create(request):
    if not request.user.is_admin:
        return HttpResponseForbidden("Access denied.")
    if request.method == "POST":
        form = CustomFieldDefinitionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Field created.")
            return redirect("clients:custom_field_admin")
    else:
        form = CustomFieldDefinitionForm()
    return render(request, "clients/custom_field_form.html", {"form": form, "title": "New Custom Field"})


@login_required
def custom_field_def_edit(request, field_id):
    if not request.user.is_admin:
        return HttpResponseForbidden("Access denied.")
    from .models import CustomFieldDefinition
    field_def = get_object_or_404(CustomFieldDefinition, pk=field_id)
    if request.method == "POST":
        form = CustomFieldDefinitionForm(request.POST, instance=field_def)
        if form.is_valid():
            form.save()
            messages.success(request, "Field updated.")
            return redirect("clients:custom_field_admin")
    else:
        form = CustomFieldDefinitionForm(instance=field_def)
    return render(request, "clients/custom_field_form.html", {"form": form, "title": f"Edit {field_def.name}"})
