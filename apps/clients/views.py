"""Client CRUD views."""
import unicodedata
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.auth_app.decorators import admin_required, requires_permission
from apps.auth_app.permissions import DENY, PERMISSIONS, can_access
from apps.notes.models import ProgressNote
from apps.programs.models import Program, UserProgramRole

from .forms import ClientContactForm, ClientFileForm, ClientTransferForm, ConsentRecordForm, CustomFieldDefinitionForm, CustomFieldGroupForm, CustomFieldValuesForm
from .helpers import get_client_tab_counts, get_document_folder_url
from .models import ClientDetailValue, ClientFile, ClientProgramEnrolment, CustomFieldGroup
from .validators import (
    normalize_phone_number, normalize_postal_code,
    validate_phone_number, validate_postal_code,
)


def _strip_accents(text):
    """Remove accent marks for accent-insensitive search (BUG-13)."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def get_client_queryset(user):
    """Return filtered ClientFile queryset based on user's demo status.

    Security requirement: is_demo is read ONLY from request.user.is_demo.
    Never read from query params, form data, or cookies.
    """
    if user.is_demo:
        return ClientFile.objects.demo()
    return ClientFile.objects.real()


# Shared program access helpers — canonical implementations in apps/programs/access
from apps.programs.access import (
    get_user_program_ids as _get_user_program_ids,
    get_accessible_programs as _get_accessible_programs,
    get_program_from_client as _get_program_from_client,
    should_share_across_programs,
    _resolve_viewing_program,
)
from django.db.models import Q


def _get_accessible_clients(user, active_program_ids=None):
    """Return client queryset scoped to user's programs and demo status.

    Uses prefetch_related to avoid N+1 queries when displaying enrolments.
    Admins without program roles see no clients.

    Security: Filters by user.is_demo to enforce demo/real data separation.
    Demo users only see demo clients; real users only see real clients.

    If active_program_ids is provided (CONF9), narrows to those programs only.
    """
    if active_program_ids:
        program_ids = active_program_ids
    else:
        program_ids = UserProgramRole.objects.filter(user=user, status="active").values_list("program_id", flat=True)
    client_ids = ClientProgramEnrolment.objects.filter(
        program_id__in=program_ids, status="enrolled"
    ).values_list("client_file_id", flat=True)
    # Filter by demo status using the helper function
    base_queryset = get_client_queryset(user)
    return base_queryset.filter(pk__in=client_ids).prefetch_related("enrolments__program")


def _get_last_contact_dates(client_ids):
    """Batch-query last contact dates for a list of clients.

    Returns dict: {client_id: datetime or None}

    Performance: 3 aggregate queries instead of 3N individual queries.
    """
    from django.db.models import Max
    from apps.communications.models import Communication
    from apps.events.models import Meeting

    if not client_ids:
        return {}

    # Query 1: Last note date per client
    note_dates = dict(
        ProgressNote.objects.filter(
            client_file_id__in=client_ids,
            status="default",
        ).values("client_file_id").annotate(
            last_date=Max("created_at")
        ).values_list("client_file_id", "last_date")
    )

    # Query 2: Last communication date per client
    comm_dates = dict(
        Communication.objects.filter(
            client_file_id__in=client_ids,
        ).values("client_file_id").annotate(
            last_date=Max("created_at")
        ).values_list("client_file_id", "last_date")
    )

    # Query 3: Last meeting date per client (Meeting -> Event -> client_file)
    meeting_dates = dict(
        Meeting.objects.filter(
            event__client_file_id__in=client_ids,
        ).values("event__client_file_id").annotate(
            last_date=Max("event__start_timestamp")
        ).values_list("event__client_file_id", "last_date")
    )

    # Merge: find max date across all three sources per client
    result = {}
    for client_id in client_ids:
        dates = [
            note_dates.get(client_id),
            comm_dates.get(client_id),
            meeting_dates.get(client_id),
        ]
        valid_dates = [d for d in dates if d is not None]
        result[client_id] = max(valid_dates) if valid_dates else None

    return result


def _find_clients_with_matching_notes(client_ids, query_lower, user,
                                      active_program_ids=None):
    """Return set of client IDs whose progress notes contain the search query.

    Encrypted fields can't be searched in SQL, so we decrypt each note's text
    fields in memory and check for a case- and accent-insensitive substring match.
    Stops checking a client as soon as one matching note is found.

    PHIPA (PHIPA-SEARCH1): Filters notes by program access and consent
    settings to prevent side-channel disclosure through search results.
    A search for sensitive clinical terms must not reveal that a restricted-
    program note contains that term.
    """
    from apps.clients.dashboard_views import _get_feature_flags

    user_program_ids = _get_user_program_ids(user, active_program_ids)

    # Step 1: Filter notes to user's accessible programs (basic access control)
    notes = (
        ProgressNote.objects.filter(client_file_id__in=client_ids)
        .filter(
            Q(author_program_id__in=user_program_ids)
            | Q(author_program__isnull=True)
        )
        .select_related("author_program")
        .prefetch_related("target_entries")
    )

    # Step 2: Check agency sharing flag once
    flags = _get_feature_flags()
    agency_shares = flags.get("cross_program_note_sharing", True)

    # Step 3: Pre-load per-client consent overrides for efficient filtering.
    # Load client objects for those that need per-client checking.
    # - Agency ON:  most clients (default) get all accessible notes.
    #               Only filter for clients with cross_program_sharing="restrict".
    # - Agency OFF: most clients (default) get only viewing-program notes.
    #               Clients with cross_program_sharing="consent" get all accessible notes.
    client_sharing_map = dict(
        ClientFile.objects.filter(pk__in=client_ids)
        .values_list("pk", "cross_program_sharing")
    )

    # Pre-compute the viewing program for clients that need per-client filtering.
    # Resolving viewing program is expensive, so only do it when needed.
    viewing_program_cache = {}  # client_id -> viewing_program or None

    def _get_viewing_program_for_client(client_id):
        if client_id not in viewing_program_cache:
            client_obj = ClientFile.objects.get(pk=client_id)
            viewing_program_cache[client_id] = _resolve_viewing_program(
                user, client_obj, active_program_ids
            )
        return viewing_program_cache[client_id]

    def _note_passes_consent(note):
        """Check if a note passes PHIPA consent filtering for its client."""
        cid = note.client_file_id
        sharing = client_sharing_map.get(cid, "default")

        # Determine if this client shares across programs
        if sharing == "consent":
            return True  # Client explicitly consents — all accessible notes OK
        if sharing == "restrict":
            # Client restricts — only viewing program notes
            if note.author_program is None:
                return True  # Legacy notes always visible
            vp = _get_viewing_program_for_client(cid)
            if vp is None:
                return False  # Fail-closed (DRR decision #9)
            return note.author_program_id == vp.pk

        # sharing == "default" — follow agency toggle
        if agency_shares:
            return True  # Agency shares by default, client uses default
        # Agency does NOT share, client uses default — restrict to viewing program
        if note.author_program is None:
            return True  # Legacy notes always visible
        vp = _get_viewing_program_for_client(cid)
        if vp is None:
            return False  # Fail-closed
        return note.author_program_id == vp.pk

    matched = set()
    for note in notes:
        cid = note.client_file_id
        if cid in matched:
            continue  # already found a match for this client

        # PHIPA consent check before revealing search match
        if not _note_passes_consent(note):
            continue

        for text in [note.notes_text or "", note.summary or "", note.participant_reflection or ""]:
            if query_lower in _strip_accents(text.lower()):
                matched.add(cid)
                break
        else:
            for entry in note.target_entries.all():
                if query_lower in _strip_accents((entry.notes or "").lower()):
                    matched.add(cid)
                    break
    return matched


@login_required
def client_list(request):
    # CONF9: Use active program context from middleware if available
    active_ids = getattr(request, "active_program_ids", None)
    clients = _get_accessible_clients(request.user, active_program_ids=active_ids)
    accessible_programs = _get_accessible_programs(request.user, active_program_ids=active_ids)
    user_program_ids = _get_user_program_ids(request.user, active_program_ids=active_ids)

    # Compute program IDs where user can edit plans.
    # Uses PERMISSIONS.keys() so any future roles are automatically included.
    plan_edit_program_ids = set(
        UserProgramRole.objects.filter(user=request.user, status="active")
        .exclude(role__in=[
            r for r in PERMISSIONS.keys()
            if can_access(r, "plan.edit") == DENY
        ])
        .values_list("program_id", flat=True)
    )

    # Get filter values from query params
    status_filter = request.GET.get("status", "")
    program_filter = request.GET.get("program", "")
    editable_filter = request.GET.get("editable", "")
    search_query = _strip_accents(request.GET.get("q", "").strip().lower())
    sort_by = request.GET.get("sort", "name")

    # Batch-query last contact dates (3 aggregate queries total — not 3N).
    # Queries all accessible client IDs, not just the current page, because
    # sort-by-last-contact needs the full list before pagination. Acceptable
    # up to ~2,000 clients (same ceiling as the encrypted-field search loop).
    all_client_ids = list(clients.values_list("pk", flat=True))
    last_contact_map = _get_last_contact_dates(all_client_ids)

    # Decrypt names and build display list — two passes when searching:
    # 1. Apply status/program filters, match by name/record ID
    # 2. For unmatched clients, also search progress note content
    client_data = []
    unmatched = {}  # client.pk → item dict, for the note-search pass
    for client in clients:
        # Apply status filter (in Python because we're already iterating)
        if status_filter and client.status != status_filter:
            continue

        # Only show enrolments in programs the user has access to.
        # Prevents leaking confidential program names.
        programs = [
            e.program for e in client.enrolments.all()
            if e.status == "enrolled" and e.program_id in user_program_ids
        ]

        # Apply program filter
        if program_filter:
            program_ids = [p.pk for p in programs]
            if int(program_filter) not in program_ids:
                continue

        name = f"{client.display_name} {client.last_name}"
        # Check if user can edit plans for this participant
        enrolled_prog_ids = {p.pk for p in programs}
        can_edit_plan = bool(plan_edit_program_ids & enrolled_prog_ids)
        item = {"client": client, "name": name, "programs": programs, "last_contact": last_contact_map.get(client.pk), "can_edit_plan": can_edit_plan}

        # Apply editable plans filter
        if editable_filter and not can_edit_plan:
            continue

        # Apply text search (name, record ID, or — via second pass — note content)
        # BUG-13: accent-insensitive — strip accents from name/record before comparing
        if search_query:
            record = (client.record_id or "").lower()
            if search_query in _strip_accents(name.lower()) or search_query in _strip_accents(record):
                client_data.append(item)
            else:
                unmatched[client.pk] = item
        else:
            client_data.append(item)

    # Second pass: search progress notes for clients not matched by name/ID
    # PHIPA-SEARCH1: pass user + active_program_ids for consent filtering
    if search_query and unmatched:
        note_matched_ids = _find_clients_with_matching_notes(
            unmatched.keys(), search_query,
            user=request.user, active_program_ids=active_ids,
        )
        for cid in note_matched_ids:
            client_data.append(unmatched[cid])

    # Sort by name or last contact
    if sort_by == "last_contact":
        from datetime import datetime as dt
        epoch = dt(2000, 1, 1, 0, 0)
        min_dt = timezone.make_aware(epoch) if timezone.is_aware(timezone.now()) else epoch
        client_data.sort(
            key=lambda c: c["last_contact"] or min_dt,
            reverse=True,
        )
    else:
        client_data.sort(key=lambda c: c["name"].lower())
    paginator = Paginator(client_data, 25)
    page = paginator.get_page(request.GET.get("page"))

    # Show create button if user's role grants client.create permission
    from apps.auth_app.decorators import _get_user_highest_role
    from apps.auth_app.permissions import DENY, PERMISSIONS
    user_role = _get_user_highest_role(request.user)
    can_create = PERMISSIONS.get(user_role, {}).get("client.create", DENY) != DENY

    context = {
        "page": page,
        "accessible_programs": accessible_programs,
        "status_filter": status_filter,
        "program_filter": program_filter,
        "editable_filter": editable_filter,
        "has_plan_edit_programs": bool(plan_edit_program_ids),
        "search_query": request.GET.get("q", ""),
        "sort_by": sort_by,
        "can_create": can_create,
    }

    # HTMX request — return only the table partial
    if request.headers.get("HX-Request"):
        return render(request, "clients/_client_list_table.html", context)

    return render(request, "clients/list.html", context)


@login_required
@requires_permission("client.create")
def client_create(request):
    available_programs = _get_accessible_programs(request.user)

    # Circle integration — only when feature is enabled
    circle_choices = None
    from apps.admin_settings.models import FeatureToggle
    if FeatureToggle.get_all_flags().get("circles", False):
        from apps.circles.helpers import get_visible_circles
        visible = get_visible_circles(request.user)
        circle_choices = [(c.pk, c.name) for c in visible]

    if request.method == "POST":
        form = ClientFileForm(request.POST, available_programs=available_programs, circle_choices=circle_choices)
        if form.is_valid():
            # BUG-7: Wrap in transaction so client + enrollments commit
            # atomically. Prevents a half-created client if enrollment
            # creation fails, and ensures the redirect sees all data.
            with transaction.atomic():
                client = ClientFile()
                client.first_name = form.cleaned_data["first_name"]
                client.last_name = form.cleaned_data["last_name"]
                client.preferred_name = form.cleaned_data["preferred_name"] or ""
                client.middle_name = form.cleaned_data["middle_name"] or ""
                client.birth_date = form.cleaned_data["birth_date"]
                client.phone = form.cleaned_data.get("phone", "")
                client.email = form.cleaned_data.get("email", "")
                client.record_id = form.cleaned_data["record_id"]
                client.status = form.cleaned_data["status"]
                client.preferred_language = form.cleaned_data.get("preferred_language", "en")
                # CASL consent — record date automatically on consent
                client.sms_consent = form.cleaned_data.get("sms_consent", False)
                if client.sms_consent:
                    client.sms_consent_date = date.today()
                client.email_consent = form.cleaned_data.get("email_consent", False)
                if client.email_consent:
                    client.email_consent_date = date.today()
                # Auto-set preferred_contact_method from consent
                if client.sms_consent:
                    client.preferred_contact_method = "sms"
                elif client.email_consent:
                    client.preferred_contact_method = "email"
                # Set is_demo based on the creating user's status
                # Security: is_demo is immutable after creation
                client.is_demo = request.user.is_demo
                client.save()
                # Enrol in selected programs
                for program in form.cleaned_data["programs"]:
                    ClientProgramEnrolment.objects.create(
                        client_file=client, program=program, status="enrolled",
                    )
                # Circle linking/creation (when circles feature is on)
                existing_circle_id = form.cleaned_data.get("existing_circle", "")
                new_circle_name = form.cleaned_data.get("new_circle_name", "").strip()
                if existing_circle_id or new_circle_name:
                    from apps.circles.models import Circle, CircleMembership
                    from apps.circles.helpers import get_visible_circles
                    if existing_circle_id:
                        circle = get_visible_circles(request.user).filter(pk=existing_circle_id).first()
                    else:
                        circle = Circle(is_demo=request.user.is_demo)
                        circle.name = new_circle_name
                        circle.created_by = request.user
                        circle.save()
                    if circle:
                        # Set as primary contact if first participant member
                        has_participant = CircleMembership.objects.filter(
                            circle=circle, client_file__isnull=False, status="active",
                        ).exists()
                        CircleMembership.objects.create(
                            circle=circle,
                            client_file=client,
                            is_primary_contact=not has_participant,
                        )
            # Allow immediate access on redirect — the RBAC middleware may
            # not yet see the new enrollment depending on connection timing.
            request.session["_just_created_client_id"] = client.pk
            display_name = f"{client.display_name} {client.last_name}"
            messages.success(
                request,
                _("%(name)s's %(term)s file created successfully.") % {
                    "name": display_name,
                    "term": request.get_term("client").lower(),
                },
            )
            return redirect("clients:client_detail", client_id=client.pk)
    else:
        form = ClientFileForm(available_programs=available_programs, circle_choices=circle_choices)
    return render(request, "clients/form.html", {"form": form, "editing": False})


@login_required
@requires_permission("client.edit", _get_program_from_client)
def client_edit(request, client_id):
    # Security: Only fetch clients matching user's demo status
    base_queryset = get_client_queryset(request.user)
    client = get_object_or_404(base_queryset, pk=client_id)
    if request.method == "POST":
        form = ClientFileForm(request.POST)
        if form.is_valid():
            client.first_name = form.cleaned_data["first_name"]
            client.last_name = form.cleaned_data["last_name"]
            client.preferred_name = form.cleaned_data["preferred_name"] or ""
            client.middle_name = form.cleaned_data["middle_name"] or ""
            client.birth_date = form.cleaned_data["birth_date"]
            client.phone = form.cleaned_data.get("phone", "")
            client.email = form.cleaned_data.get("email", "")
            client.record_id = form.cleaned_data["record_id"]
            client.status = form.cleaned_data["status"]
            client.preferred_language = form.cleaned_data.get("preferred_language", "en")
            # CASL consent — record/clear dates based on checkbox changes
            consent_changes = []
            new_sms = form.cleaned_data.get("sms_consent", False)
            if new_sms and not client.sms_consent:
                client.sms_consent_date = date.today()
                consent_changes.append({"field": "sms_consent", "action": "granted"})
            elif not new_sms and client.sms_consent:
                client.sms_consent_withdrawn_date = date.today()
                consent_changes.append({"field": "sms_consent", "action": "withdrawn"})
            client.sms_consent = new_sms
            new_email_consent = form.cleaned_data.get("email_consent", False)
            if new_email_consent and not client.email_consent:
                client.email_consent_date = date.today()
                consent_changes.append({"field": "email_consent", "action": "granted"})
            elif not new_email_consent and client.email_consent:
                client.email_consent_withdrawn_date = date.today()
                consent_changes.append({"field": "email_consent", "action": "withdrawn"})
            client.email_consent = new_email_consent
            # Auto-set preferred_contact_method from consent
            if new_sms:
                client.preferred_contact_method = "sms"
            elif new_email_consent:
                client.preferred_contact_method = "email"
            client.save()
            # Audit log for consent changes (CASL compliance)
            if consent_changes:
                from apps.audit.models import AuditLog
                user = request.user
                AuditLog.objects.using("audit").create(
                    event_timestamp=timezone.now(),
                    user_id=user.pk,
                    user_display=user.display_name if hasattr(user, "display_name") else str(user),
                    action="update",
                    resource_type="clients",
                    resource_id=client.pk,
                    is_demo_context=getattr(user, "is_demo", False),
                    metadata={"consent_changes": consent_changes},
                )
            messages.success(request, _("%(term)s file updated.") % {"term": request.get_term("client")})
            return redirect("clients:client_detail", client_id=client.pk)
    else:
        form = ClientFileForm(
            initial={
                "first_name": client.first_name,
                "last_name": client.last_name,
                "preferred_name": client.preferred_name,
                "middle_name": client.middle_name,
                "phone": client.phone,
                "email": client.email,
                "birth_date": client.birth_date,
                "record_id": client.record_id,
                "status": client.status,
                "preferred_language": client.preferred_language,
                "sms_consent": client.sms_consent,
                "email_consent": client.email_consent,
            },
        )
    # Breadcrumbs: Participants > [Name] > Edit
    breadcrumbs = [
        {"url": reverse("clients:client_list"), "label": request.get_term("client_plural")},
        {"url": reverse("clients:client_detail", kwargs={"client_id": client.pk}), "label": f"{client.display_name} {client.last_name}"},
        {"url": "", "label": _("Edit")},
    ]
    return render(request, "clients/form.html", {"form": form, "editing": True, "client": client, "breadcrumbs": breadcrumbs})


@login_required
@requires_permission("client.transfer", _get_program_from_client)
def client_transfer(request, client_id):
    """Transfer a client between programs (enrol/unenrol).

    Separated from client_edit so transfers have their own permission key
    (client.transfer) and audit trail. Only touches programs the user has
    access to — confidential program enrolments are preserved.
    """
    base_queryset = get_client_queryset(request.user)
    client = get_object_or_404(base_queryset, pk=client_id)
    available_programs = _get_accessible_programs(request.user)
    current_program_ids = set(
        ClientProgramEnrolment.objects.filter(
            client_file=client, status="enrolled",
        ).values_list("program_id", flat=True)
    )
    if request.method == "POST":
        form = ClientTransferForm(request.POST, available_programs=available_programs)
        if form.is_valid():
            accessible_program_ids = _get_user_program_ids(request.user)
            selected_ids = set(p.pk for p in form.cleaned_data["programs"])
            added = []
            removed = []
            # Unenrol removed programs (only within user's accessible programs)
            for enrolment in ClientProgramEnrolment.objects.filter(
                client_file=client, status="enrolled",
                program_id__in=accessible_program_ids,
            ):
                if enrolment.program_id not in selected_ids:
                    enrolment.status = "unenrolled"
                    enrolment.unenrolled_at = timezone.now()
                    enrolment.save()
                    removed.append(enrolment.program_id)
            # Enrol in new programs
            for program_id in selected_ids:
                if program_id not in current_program_ids:
                    ClientProgramEnrolment.objects.update_or_create(
                        client_file=client, program_id=program_id,
                        defaults={"status": "enrolled", "unenrolled_at": None},
                    )
                    added.append(program_id)
            # Update cross-program sharing preference
            client.cross_program_sharing = form.cleaned_data.get(
                "cross_program_sharing", "default"
            )
            client.save()
            # Audit log for transfer (always log, even if no changes)
            if added or removed:
                from apps.audit.models import AuditLog
                AuditLog.objects.using("audit").create(
                    event_timestamp=timezone.now(),
                    user_id=request.user.pk,
                    user_display=(
                        request.user.display_name
                        if hasattr(request.user, "display_name")
                        else str(request.user)
                    ),
                    action="update",
                    resource_type="enrolment",
                    resource_id=client.pk,
                    is_demo_context=getattr(request.user, "is_demo", False),
                    metadata={
                        "transfer": True,
                        "programs_added": added,
                        "programs_removed": removed,
                        "reason": form.cleaned_data.get("transfer_reason", ""),
                    },
                )
            messages.success(
                request,
                _("%(term)s program enrolment updated.")
                % {"term": request.get_term("client")},
            )
            return redirect("clients:client_detail", client_id=client.pk)
    else:
        form = ClientTransferForm(
            initial={
                "programs": list(current_program_ids),
                "cross_program_sharing": client.cross_program_sharing,
            },
            available_programs=available_programs,
        )
    breadcrumbs = [
        {"url": reverse("clients:client_list"), "label": request.get_term("client_plural")},
        {"url": reverse("clients:client_detail", kwargs={"client_id": client.pk}), "label": f"{client.display_name} {client.last_name}"},
        {"url": "", "label": _("Transfer")},
    ]
    return render(request, "clients/transfer.html", {
        "form": form,
        "client": client,
        "breadcrumbs": breadcrumbs,
        "current_enrolments": ClientProgramEnrolment.objects.filter(
            client_file=client, status="enrolled",
        ).select_related("program"),
    })


@login_required
@requires_permission("client.edit_contact", _get_program_from_client)
def client_contact_edit(request, client_id):
    """Edit client phone number only — narrow scope for front desk.

    Front desk can update phone (client.edit_contact: ALLOW).
    Does NOT include address or emergency contact (DV safety implications).
    Replace with PER_FIELD form in Phase 2.
    """
    base_queryset = get_client_queryset(request.user)
    client = get_object_or_404(base_queryset, pk=client_id)
    if request.method == "POST":
        form = ClientContactForm(request.POST)
        if form.is_valid():
            client.phone = form.cleaned_data["phone"]
            client.save()
            messages.success(request, _("Contact information updated."))
            return redirect("clients:client_detail", client_id=client.pk)
    else:
        form = ClientContactForm(initial={"phone": client.phone})
    breadcrumbs = [
        {"url": reverse("clients:client_list"), "label": request.get_term("client_plural")},
        {"url": reverse("clients:client_detail", kwargs={"client_id": client.pk}), "label": f"{client.display_name} {client.last_name}"},
        {"url": "", "label": _("Edit Contact")},
    ]
    return render(request, "clients/contact_edit.html", {
        "form": form,
        "client": client,
        "breadcrumbs": breadcrumbs,
    })


@login_required
@requires_permission("client.edit_contact", _get_program_from_client)
def client_confirm_phone(request, client_id):
    """Mark a client's phone number as verified today.

    Sets phone_last_confirmed to today's date for staleness tracking.
    Only accessible via POST (form submission from client detail page).
    """
    if request.method != "POST":
        return redirect("clients:client_detail", client_id=client_id)

    from apps.programs.access import get_client_or_403
    client = get_client_or_403(request, client_id)
    if client is None:
        return HttpResponseForbidden("You do not have access to this client.")
    client.phone_last_confirmed = date.today()
    client.save()

    # Audit log
    from apps.audit.models import AuditLog
    user = request.user
    AuditLog.objects.using("audit").create(
        event_timestamp=timezone.now(),
        user_id=user.pk,
        user_display=user.display_name if hasattr(user, "display_name") else str(user),
        action="update",
        resource_type="clients",
        resource_id=client.pk,
        is_demo_context=getattr(user, "is_demo", False),
        metadata={"field": "phone_last_confirmed", "value": str(date.today())},
    )

    messages.success(request, _("Phone number marked as verified."))
    return redirect("clients:client_detail", client_id=client.pk)


@login_required
def client_detail(request, client_id):
    # Security: Only fetch clients matching user's demo status
    base_queryset = get_client_queryset(request.user)
    client = get_object_or_404(base_queryset, pk=client_id)
    # Track recently viewed clients in session (most recent first, max 10)
    recent = request.session.get("recent_clients", [])
    if client_id in recent:
        recent.remove(client_id)
    recent.insert(0, client_id)
    request.session["recent_clients"] = recent[:10]

    user_role = getattr(request, "user_program_role", None)
    is_receptionist = user_role == "receptionist"

    # Only show enrolments in programs the user has access to.
    # Prevents leaking confidential program names.
    user_program_ids = _get_user_program_ids(request.user)
    enrolments = ClientProgramEnrolment.objects.filter(
        client_file=client, status="enrolled", program_id__in=user_program_ids,
    ).select_related("program")
    # IMPROVE-5: Check if client has programs hidden from this user
    all_enrolled_count = ClientProgramEnrolment.objects.filter(
        client_file=client, status="enrolled",
    ).count()
    visible_count = enrolments.count()
    has_hidden_programs = all_enrolled_count > visible_count

    # Custom fields for Info tab — uses shared helper with hide_empty=True (display mode)
    custom_fields_ctx = _get_custom_fields_context(client, user_role, hide_empty=True)
    custom_data = custom_fields_ctx["custom_data"]
    has_editable_fields = custom_fields_ctx["has_editable_fields"]
    # Breadcrumbs: Participants > [Name]
    breadcrumbs = [
        {"url": reverse("clients:client_list"), "label": request.get_term("client_plural")},
        {"url": "", "label": f"{client.display_name} {client.last_name}"},
    ]
    # Tab counts for badges (only for non-front-desk roles, only for full page loads)
    tab_counts = {} if is_receptionist else get_client_tab_counts(client)

    # Check for pending erasure request (ERASE8)
    from .models import ErasureRequest
    pending_erasure = ErasureRequest.objects.filter(
        client_file=client, status="pending",
    ).exists()

    is_pm_or_admin = user_role in ("program_manager", "executive") or getattr(request.user, "is_admin", False)

    # Circles sidebar (only when feature toggle is on and user is not front desk)
    client_circles = []
    from apps.admin_settings.models import FeatureToggle
    circles_enabled = FeatureToggle.get_all_flags().get("circles", False)
    if circles_enabled and not is_receptionist:
        from apps.circles.models import CircleMembership
        from apps.circles.helpers import get_visible_circles
        from apps.circles.helpers import get_accessible_client_ids, get_blocked_client_ids
        visible_circle_ids = set(get_visible_circles(request.user).values_list("pk", flat=True))
        accessible_client_ids = get_accessible_client_ids(request.user)
        blocked_client_ids = get_blocked_client_ids(request.user)
        accessible_client_ids -= blocked_client_ids
        memberships = (
            CircleMembership.objects.filter(
                client_file=client, status="active", circle_id__in=visible_circle_ids,
            )
            .select_related("circle")
            .prefetch_related("circle__memberships__client_file")
        )
        for m in memberships:
            # Build "other members" string — only show names the user can access
            others = []
            hidden_count = 0
            for om in m.circle.memberships.all():
                if om.status != "active" or om.pk == m.pk:
                    continue
                # Non-participant members (no client_file) are always shown
                if om.client_file_id is None:
                    others.append(om.display_name)
                elif om.client_file_id in accessible_client_ids:
                    others.append(om.display_name)
                else:
                    hidden_count += 1
            display = ", ".join(others[:5])
            if len(others) > 5:
                display += f" (+{len(others) - 5})"
            if hidden_count:
                display += f" (+{hidden_count} other)" if hidden_count == 1 else f" (+{hidden_count} others)"
            m.other_members = display
            client_circles.append(m)

    # PERM-S3: Field-level visibility based on role.
    # Determines which core model fields (e.g. birth_date) the user can see.
    # Custom fields use their own front_desk_access setting instead.
    from apps.auth_app.decorators import _get_user_highest_role
    effective_role = user_role or _get_user_highest_role(request.user)
    visible_fields = client.get_visible_fields(effective_role) if effective_role else client.get_visible_fields("receptionist")

    context = {
        "client": client,
        "enrolments": enrolments,
        "custom_data": custom_data,
        "has_editable_fields": has_editable_fields,
        "active_tab": "info",
        "user_role": user_role,
        "is_receptionist": is_receptionist,
        "is_pm_or_admin": is_pm_or_admin,
        "pending_erasure": pending_erasure,
        "visible_fields": visible_fields,
        "document_folder_url": get_document_folder_url(client),
        "has_hidden_programs": has_hidden_programs,
        "client_circles": client_circles,
        "breadcrumbs": breadcrumbs,
        **tab_counts,  # notes_count, events_count, targets_count
    }
    # HTMX tab switch — return only the tab content partial
    if request.headers.get("HX-Request"):
        return render(request, "clients/_tab_info.html", context)
    return render(request, "clients/detail.html", context)


def _get_custom_fields_context(client, user_role, hide_empty=False):
    """Build custom fields context for display/edit templates.

    Args:
        client: ClientFile instance
        user_role: User's role (front desk, direct service, etc.)
        hide_empty: If True, exclude fields without values (for display mode).
                   If False, include all fields (for edit mode).

    Returns a dict with custom_data, has_editable_fields, client, and is_receptionist (front desk flag).
    """
    is_receptionist = user_role == "receptionist"
    groups = CustomFieldGroup.objects.filter(status="active").prefetch_related("fields")
    custom_data = []
    has_editable_fields = False

    for group in groups:
        if is_receptionist:
            fields = group.fields.filter(status="active", front_desk_access__in=["view", "edit"])
        else:
            fields = group.fields.filter(status="active")
        field_values = []
        for field_def in fields:
            try:
                cdv = ClientDetailValue.objects.get(client_file=client, field_def=field_def)
                value = cdv.get_value()
            except ClientDetailValue.DoesNotExist:
                value = ""
            is_editable = not is_receptionist or field_def.front_desk_access == "edit"
            if is_editable:
                has_editable_fields = True
            # In display mode (hide_empty=True), skip fields without values
            if hide_empty and not value:
                continue
            # For select_other fields, detect if stored value is a custom "Other" entry
            is_other_value = False
            if field_def.input_type == "select_other" and value and field_def.options_json:
                is_other_value = value not in field_def.options_json
            field_values.append({
                "field_def": field_def, "value": value,
                "is_editable": is_editable, "is_other_value": is_other_value,
            })
        # Only include groups that have visible fields
        if field_values:
            custom_data.append({"group": group, "fields": field_values})

    return {
        "client": client,
        "custom_data": custom_data,
        "has_editable_fields": has_editable_fields,
        "is_receptionist": is_receptionist,
    }


@login_required
def client_custom_fields_display(request, client_id):
    """HTMX: Return read-only custom fields partial."""
    base_queryset = get_client_queryset(request.user)
    client = get_object_or_404(base_queryset, pk=client_id)
    user_role = getattr(request, "user_program_role", None)
    context = _get_custom_fields_context(client, user_role, hide_empty=True)
    return render(request, "clients/_custom_fields_display.html", context)


@login_required
def client_custom_fields_edit(request, client_id):
    """HTMX: Return editable custom fields form partial."""
    base_queryset = get_client_queryset(request.user)
    client = get_object_or_404(base_queryset, pk=client_id)
    user_role = getattr(request, "user_program_role", None)
    context = _get_custom_fields_context(client, user_role)

    # Only allow edit mode if user has editable fields
    if not context["has_editable_fields"]:
        return HttpResponseForbidden("You do not have permission to edit any fields.")

    return render(request, "clients/_custom_fields_edit.html", context)


@login_required
def client_save_custom_fields(request, client_id):
    """Save custom field values for a client.

    Security: Only fetch clients matching user's demo status.
    Front desk staff can only save fields with front_desk_access='edit'.
    Direct service staff and managers can save all fields.
    Returns the read-only display partial for HTMX, or redirects for non-HTMX.
    """
    # Security: Only fetch clients matching user's demo status
    base_queryset = get_client_queryset(request.user)
    client = get_object_or_404(base_queryset, pk=client_id)
    user_role = getattr(request, "user_program_role", None)
    is_receptionist = user_role == "receptionist"

    if request.method == "POST":
        groups = CustomFieldGroup.objects.filter(status="active").prefetch_related("fields")

        # Get field definitions the user can edit
        if is_receptionist:
            editable_field_defs = [
                fd for group in groups
                for fd in group.fields.filter(status="active", front_desk_access="edit")
            ]
        else:
            editable_field_defs = [
                fd for group in groups
                for fd in group.fields.filter(status="active")
            ]

        # Block if no editable fields
        if not editable_field_defs:
            return HttpResponseForbidden("You do not have permission to edit any fields.")

        form = CustomFieldValuesForm(request.POST, field_definitions=editable_field_defs)
        if form.is_valid():
            # Validate and normalise Canadian-specific fields (I18N5, I18N5b)
            validation_errors = []
            for field_def in editable_field_defs:
                raw_value = form.cleaned_data.get(f"custom_{field_def.pk}", "")
                # For select_other: if "Other" was chosen, use the free-text value
                if field_def.input_type == "select_other" and raw_value == "__other__":
                    raw_value = form.cleaned_data.get(f"custom_{field_def.pk}_other", "").strip()
                # Validate and normalise based on field's validation_type (I18N-FIX2)
                if field_def.validation_type == "postal_code" and raw_value:
                    try:
                        validate_postal_code(raw_value)
                        raw_value = normalize_postal_code(raw_value)
                    except Exception as e:
                        validation_errors.append(f"{field_def.name}: {e.message}")
                        continue
                if field_def.validation_type == "phone" and raw_value:
                    try:
                        validate_phone_number(raw_value)
                        raw_value = normalize_phone_number(raw_value)
                    except Exception as e:
                        validation_errors.append(f"{field_def.name}: {e.message}")
                        continue
                cdv, _created = ClientDetailValue.objects.get_or_create(
                    client_file=client, field_def=field_def,
                )
                cdv.set_value(raw_value)
                cdv.save()
            if validation_errors:
                for err in validation_errors:
                    messages.error(request, err)
            else:
                messages.success(request, _("Saved."))
        else:
            messages.error(request, _("Please correct the errors."))

    # For HTMX requests, return the read-only display partial
    if request.headers.get("HX-Request"):
        context = _get_custom_fields_context(client, user_role, hide_empty=True)
        return render(request, "clients/_custom_fields_display.html", context)

    return redirect("clients:client_detail", client_id=client.pk)


# ---- Consent Recording (PRIV1) ----

@login_required
def client_consent_display(request, client_id):
    """HTMX: Return read-only consent status partial."""
    base_queryset = get_client_queryset(request.user)
    client = get_object_or_404(base_queryset, pk=client_id)
    user_role = getattr(request, "user_program_role", None)
    is_receptionist = user_role == "receptionist"
    return render(request, "clients/_consent_display.html", {
        "client": client,
        "is_receptionist": is_receptionist,
    })


@login_required
@requires_permission("consent.manage")
def client_consent_edit(request, client_id):
    """HTMX: Return consent recording form partial."""
    from django.utils import timezone

    base_queryset = get_client_queryset(request.user)
    client = get_object_or_404(base_queryset, pk=client_id)
    initial = {}
    if client.consent_given_at:
        initial["consent_date"] = client.consent_given_at.date()
        initial["consent_type"] = client.consent_type or "written"
    else:
        initial["consent_date"] = timezone.now().date()
    form = ConsentRecordForm(initial=initial)
    return render(request, "clients/_consent_edit.html", {
        "client": client,
        "form": form,
    })


@login_required
@requires_permission("consent.manage")
def client_consent_save(request, client_id):
    """Save consent record for a client.

    Returns the read-only display partial for HTMX, or redirects for non-HTMX.
    """
    from django.utils import timezone

    base_queryset = get_client_queryset(request.user)
    client = get_object_or_404(base_queryset, pk=client_id)
    user_role = getattr(request, "user_program_role", None)
    is_receptionist = user_role == "receptionist"

    if request.method == "POST":
        form = ConsentRecordForm(request.POST)
        if form.is_valid():
            # Immutability: consent records can't be edited after creation.
            # To change consent, withdraw first (set consent_given_at=None)
            # then re-record. This prevents accidental overwrites.
            if client.consent_given_at is not None:
                messages.error(request, _(
                    "Consent has already been recorded. To update, withdraw "
                    "existing consent first, then record new consent."
                ))
                if request.headers.get("HX-Request"):
                    return render(request, "clients/_consent_display.html", {
                        "client": client,
                        "is_receptionist": is_receptionist,
                    })
                return redirect("clients:client_detail", client_id=client.pk)

            # Combine date with current time for the timestamp
            consent_date = form.cleaned_data["consent_date"]
            client.consent_given_at = timezone.make_aware(
                timezone.datetime.combine(consent_date, timezone.datetime.min.time())
            )
            client.consent_type = form.cleaned_data["consent_type"]
            client.save(update_fields=["consent_given_at", "consent_type"])
            messages.success(request, _("Consent recorded."))
        else:
            messages.error(request, _("Please correct the errors."))
            # Return to edit form on error
            if request.headers.get("HX-Request"):
                return render(request, "clients/_consent_edit.html", {
                    "client": client,
                    "form": form,
                })

    # For HTMX requests, return the read-only display partial
    if request.headers.get("HX-Request"):
        return render(request, "clients/_consent_display.html", {
            "client": client,
            "is_receptionist": is_receptionist,
        })

    return redirect("clients:client_detail", client_id=client.pk)


@login_required
def client_search(request):
    """HTMX: return search results partial.

    Encrypted fields cannot be searched in SQL — loads accessible clients
    into Python and filters in memory. Acceptable up to ~2,000 clients.

    Supports optional filters:
    - status: filter by client status (active/inactive/discharged)
    - program: filter by enrolled program ID
    - date_from: filter clients created on or after this date
    - date_to: filter clients created on or before this date
    """
    from datetime import datetime

    query = _strip_accents(request.GET.get("q", "").strip().lower())
    status_filter = request.GET.get("status", "").strip()
    program_filter = request.GET.get("program", "").strip()
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()

    # Check if any filters are active (show results even without search query)
    has_filters = any([status_filter, program_filter, date_from, date_to])

    if not query and not has_filters:
        context = {"results": [], "query": ""}
        if request.headers.get("HX-Request"):
            return render(request, "clients/_search_results.html", context)
        return render(request, "clients/search.html", context)

    clients = _get_accessible_clients(request.user)

    # Parse date filters
    date_from_parsed = None
    date_to_parsed = None
    if date_from:
        try:
            date_from_parsed = datetime.strptime(date_from, "%Y-%m-%d").date()
        except ValueError:
            pass
    if date_to:
        try:
            date_to_parsed = datetime.strptime(date_to, "%Y-%m-%d").date()
        except ValueError:
            pass

    results = []
    unmatched = {}  # client.pk → item dict, for the note-search pass
    for client in clients:
        # Apply status filter
        if status_filter and client.status != status_filter:
            continue

        # Apply date filters
        if date_from_parsed and client.created_at.date() < date_from_parsed:
            continue
        if date_to_parsed and client.created_at.date() > date_to_parsed:
            continue

        programs = [e.program for e in client.enrolments.all() if e.status == "enrolled"]

        # Apply program filter
        if program_filter:
            program_ids = [p.pk for p in programs]
            try:
                if int(program_filter) not in program_ids:
                    continue
            except ValueError:
                pass

        name = f"{client.display_name} {client.last_name}"
        item = {"client": client, "name": name, "programs": programs}

        # Apply text search (name, record ID, or — via second pass — note content)
        # BUG-13: accent-insensitive — strip accents from name/record before comparing
        if query:
            record = (client.record_id or "").lower()
            if query in _strip_accents(name.lower()) or query in _strip_accents(record):
                results.append(item)
            else:
                unmatched[client.pk] = item
        else:
            results.append(item)

    # Second pass: search progress notes for clients not matched by name/ID
    if query and unmatched:
        note_matched_ids = _find_clients_with_matching_notes(
            unmatched.keys(), query
        )
        for cid in note_matched_ids:
            results.append(unmatched[cid])

    results.sort(key=lambda c: c["name"].lower())

    # IMPROVE-2: pass can_create so search results can show "Create New" prompt
    from apps.auth_app.decorators import _get_user_highest_role
    from apps.auth_app.permissions import DENY, PERMISSIONS
    user_role = _get_user_highest_role(request.user)
    can_create = PERMISSIONS.get(user_role, {}).get("client.create", DENY) != DENY

    context = {"results": results[:50], "query": query, "can_create": can_create}

    # HTMX request — return only the partial
    if request.headers.get("HX-Request"):
        return render(request, "clients/_search_results.html", context)

    # Full page request — wrap in base template
    return render(request, "clients/search.html", context)


# ---- Custom Field Admin (FIELD1) — admin only ----

@login_required
@admin_required
def custom_field_admin(request):
    groups = CustomFieldGroup.objects.all().prefetch_related("fields")
    return render(request, "clients/custom_fields_admin.html", {"groups": groups})


@login_required
@admin_required
def custom_field_group_create(request):
    if request.method == "POST":
        form = CustomFieldGroupForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("Field group created."))
            return redirect("clients:custom_field_admin")
    else:
        form = CustomFieldGroupForm()
    return render(request, "clients/custom_field_form.html", {"form": form, "title": "New Field Group"})


@login_required
@admin_required
def custom_field_group_edit(request, group_id):
    group = get_object_or_404(CustomFieldGroup, pk=group_id)
    if request.method == "POST":
        form = CustomFieldGroupForm(request.POST, instance=group)
        if form.is_valid():
            form.save()
            messages.success(request, _("Field group updated."))
            return redirect("clients:custom_field_admin")
    else:
        form = CustomFieldGroupForm(instance=group)
    return render(request, "clients/custom_field_form.html", {"form": form, "title": f"Edit {group.title}"})


@login_required
@admin_required
def custom_field_def_create(request):
    if request.method == "POST":
        form = CustomFieldDefinitionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("Field created."))
            return redirect("clients:custom_field_admin")
    else:
        form = CustomFieldDefinitionForm()
    return render(request, "clients/custom_field_form.html", {"form": form, "title": "New Custom Field"})


@login_required
@admin_required
def custom_field_def_edit(request, field_id):
    from .models import CustomFieldDefinition
    field_def = get_object_or_404(CustomFieldDefinition, pk=field_id)
    if request.method == "POST":
        form = CustomFieldDefinitionForm(request.POST, instance=field_def)
        if form.is_valid():
            form.save()
            messages.success(request, _("Field updated."))
            return redirect("clients:custom_field_admin")
    else:
        form = CustomFieldDefinitionForm(instance=field_def)
    return render(request, "clients/custom_field_form.html", {"form": form, "title": f"Edit {field_def.name}"})


@login_required
@requires_permission("client.create")
def check_duplicate(request):
    """HTMX endpoint: check for duplicate clients.

    Tries phone matching first (strong signal). Falls back to
    name + DOB matching when phone is unavailable or has no match.
    Returns the _duplicate_banner.html partial with any matches,
    or an empty response if no matches.
    """
    phone = request.GET.get("phone", "").strip()
    first_name = request.GET.get("first_name", "").strip()
    birth_date = request.GET.get("birth_date", "").strip()
    exclude_id = request.GET.get("exclude", "")

    from .matching import find_duplicate_matches
    matches, match_type = find_duplicate_matches(
        phone, first_name, birth_date, request.user,
        exclude_client_id=int(exclude_id) if exclude_id.isdigit() else None,
    )
    return render(request, "clients/_duplicate_banner.html", {
        "matches": matches,
        "match_type": match_type,
    })
