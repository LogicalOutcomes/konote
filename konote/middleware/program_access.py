"""RBAC middleware enforcing program-scoped data access."""
import re

from django.shortcuts import redirect
from django.template.response import TemplateResponse

from apps.auth_app.constants import ROLE_RANK
from apps.auth_app.permissions import DENY, can_access


# URL patterns that require program-level access checks
# Maps URL regex to the URL kwarg containing the client ID
CLIENT_URL_PATTERNS = [
    (re.compile(r"^/participants/(?P<client_id>\d+)"), "client_id"),
    (re.compile(r"^/notes/participant/(?P<client_id>\d+)"), "client_id"),
    (re.compile(r"^/reports/participant/(?P<client_id>\d+)"), "client_id"),
    (re.compile(r"^/plans/participant/(?P<client_id>\d+)"), "client_id"),
    (re.compile(r"^/events/participant/(?P<client_id>\d+)"), "client_id"),
    (re.compile(r"^/communications/participant/(?P<client_id>\d+)"), "client_id"),
]

# URL patterns for note-specific routes (look up client from note)
NOTE_URL_PATTERNS = [
    re.compile(r"^/notes/(?P<note_id>\d+)"),
]

# URLs that only admins can access. PM-accessible management pages now
# live under /manage/ so no exemption list is needed here.
ADMIN_ONLY_PREFIX = "/admin/"


class ProgramAccessMiddleware:
    """
    Check that the logged-in user has access to the requested resource
    based on their program assignments.

    - Admin-only users (no program roles) cannot access client data.
    - Other users can only access clients enrolled in their assigned programs.
    - /admin/* routes are restricted to admin users.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    # CONF9: Paths exempt from forced program selection redirect.
    # These either have their own access control or don't show client data.
    SELECTION_EXEMPT_PREFIXES = (
        "/programs/",
        "/auth/",
        "/i18n/",
        "/static/",
        "/merge/",
        "/audit/",
        "/admin/",
        "/manage/",
        "/erasure/",
        "/reports/export/",
    )

    def __call__(self, request):
        # Skip for unauthenticated users (login page handles that)
        if not hasattr(request, "user") or not request.user.is_authenticated:
            return self.get_response(request)

        path = request.path

        # CONF9: Stash active program IDs on request for views to use.
        # Guard against missing session (e.g., RequestFactory in tests).
        if hasattr(request, "session"):
            from apps.programs.context import get_active_program_ids
            request.active_program_ids = get_active_program_ids(request.user, request.session)
        else:
            request.active_program_ids = None

        # Admin-only routes: /admin/ now only contains admin settings.
        # PM-accessible management pages live under /manage/ instead.
        if path.startswith(ADMIN_ONLY_PREFIX):
            if not request.user.is_admin:
                return self._forbidden_response(
                    request,
                    "Access denied. Admin privileges are required to view this page."
                )
            return self.get_response(request)

        # CONF9: Force program selection for mixed-tier users without a selection.
        # Placed after admin-only check so admin routes aren't affected.
        # Stash needs_program_selector result on request for context processor (CONF9c).
        if hasattr(request, "session"):
            from apps.programs.context import needs_program_selection, needs_program_selector
            request._needs_program_selector = needs_program_selector(request.user)
            if request._needs_program_selector and needs_program_selection(request.user, request.session):
                if not any(path.startswith(p) for p in self.SELECTION_EXEMPT_PREFIXES):
                    return redirect("programs:select_program")

        # Redirect users whose role has no individual client-data permissions
        # to the executive dashboard. Reads from the permissions matrix so
        # changes there take effect automatically (e.g. granting an executive
        # client.view_name: ALLOW would stop the redirect).
        from apps.programs.models import UserProgramRole

        if self._all_client_permissions_denied(request.user):
            for pattern, _ in CLIENT_URL_PATTERNS:
                if pattern.match(path):
                    return redirect("clients:executive_dashboard")
            for pattern in NOTE_URL_PATTERNS:
                if pattern.match(path):
                    return redirect("clients:executive_dashboard")
            # Block access to group views (contain individual member names)
            if path.startswith("/groups/"):
                return redirect("clients:executive_dashboard")
            # Redirect from client list (home page handles executives inline)
            if path in ("/participants/", "/participants"):
                return redirect("clients:executive_dashboard")

        # Client-scoped routes — check program overlap (admins are NOT exempt)
        for pattern, id_param in CLIENT_URL_PATTERNS:
            match = pattern.match(path)
            if match:
                client_id = match.group("client_id")
                # BUG-7: Allow immediate access to a just-created client.
                # The enrollment may not be visible to the middleware query
                # on the redirect request due to connection timing.
                just_created = request.session.pop("_just_created_client_id", None)
                if just_created is not None and str(just_created) == client_id:
                    request.accessible_client_id = int(client_id)
                    request.user_program_role = self._get_role_for_client(
                        request.user, client_id,
                    )
                    break
                access = self._user_can_access_client(request.user, client_id)
                if access is None:
                    # Client doesn't exist — let the view's get_object_or_404 handle it
                    break
                if not access:
                    if request.user.is_admin:
                        return self._forbidden_response(
                            request,
                            "Administrators cannot access individual client records. "
                            "Ask another admin to assign you a program role if you need client access."
                        )
                    return self._forbidden_response(
                        request,
                        "Access denied. You are not assigned to this client's program."
                    )
                # Store for use in views
                request.accessible_client_id = int(client_id)
                # Store user's highest role for this client's programs
                request.user_program_role = self._get_role_for_client(request.user, client_id)
                break

        # Note-scoped routes (no client_id in URL) — look up client from note
        for pattern in NOTE_URL_PATTERNS:
            match = pattern.match(path)
            if match:
                note_id = match.group("note_id")
                client_id = self._get_client_id_from_note(note_id)
                if client_id:
                    access = self._user_can_access_client(request.user, client_id)
                    if access is None:
                        break  # Client doesn't exist — let the view handle 404
                    if not access:
                        if request.user.is_admin:
                            return self._forbidden_response(
                                request,
                                "Administrators cannot access individual client records. "
                                "Ask another admin to assign you a program role if you need client access."
                            )
                        return self._forbidden_response(
                            request,
                            "Access denied. You are not assigned to this client's program."
                        )
                    request.accessible_client_id = client_id
                    request.user_program_role = self._get_role_for_client(request.user, client_id)
                break

        return self.get_response(request)


    # Permission keys that represent individual client-scoped data access.
    # If ALL of these are DENY for a user's highest role, that user cannot
    # see individual client data and should be redirected to the exec dashboard.
    _CLIENT_SCOPED_KEYS = (
        "client.view_name", "client.view_contact", "client.view_safety",
        "client.view_clinical", "client.edit", "client.create",
        "note.view", "note.create", "note.edit",
        "plan.view", "plan.edit",
        "event.view", "event.create",
        "alert.view", "alert.create",
        "group.view_roster", "group.view_detail", "group.manage_members",
        "consent.view", "consent.manage",
        "intake.view", "intake.edit",
    )

    def _all_client_permissions_denied(self, user):
        """Check if the user's highest role has DENY for all client-scoped resources.

        Returns True only for users with program roles where every individual
        client-data permission is DENY (e.g. executive-only users by default).
        Users with no program roles return False (handled by admin-only check).
        """
        from apps.programs.models import UserProgramRole

        roles = set(
            UserProgramRole.objects.filter(
                user=user, status="active",
            ).values_list("role", flat=True)
        )
        if not roles:
            return False

        highest_role = max(roles, key=lambda r: ROLE_RANK.get(r, 0))
        return all(
            can_access(highest_role, key) == DENY
            for key in self._CLIENT_SCOPED_KEYS
        )

    def _user_can_access_client(self, user, client_id):
        """Check if user shares at least one program with the client.

        Returns:
            True  — user has program overlap with the client
            False — no overlap (user lacks access)
            None  — client does not exist (caller should 404, not 403)
        """
        from apps.clients.models import ClientFile, ClientProgramEnrolment
        from apps.programs.models import UserProgramRole

        # Check client exists before checking program overlap.
        # Without this, a non-existent client_id produces an empty
        # enrollment set → no overlap → misleading 403 instead of 404.
        if not ClientFile.objects.filter(pk=client_id).exists():
            return None

        user_program_ids = set(
            UserProgramRole.objects.filter(user=user, status="active").values_list("program_id", flat=True)
        )
        if not user_program_ids:
            return False

        client_program_ids = set(
            ClientProgramEnrolment.objects.filter(
                client_file_id=client_id, status="active"
            ).values_list("program_id", flat=True)
        )
        return bool(user_program_ids & client_program_ids)

    def _get_role_for_client(self, user, client_id):
        """Return the user's highest role across programs shared with this client."""
        from apps.clients.models import ClientProgramEnrolment
        from apps.programs.models import UserProgramRole

        client_program_ids = set(
            ClientProgramEnrolment.objects.filter(
                client_file_id=client_id, status="active"
            ).values_list("program_id", flat=True)
        )
        roles = UserProgramRole.objects.filter(
            user=user, status="active", program_id__in=client_program_ids,
        ).values_list("role", flat=True)

        if not roles:
            return None
        return max(roles, key=lambda r: ROLE_RANK.get(r, 0))

    def _get_client_id_from_note(self, note_id):
        """Return the client_file_id for a given progress note, or None if not found."""
        from apps.notes.models import ProgressNote

        try:
            return ProgressNote.objects.filter(pk=note_id).values_list(
                "client_file_id", flat=True
            ).first()
        except (ValueError, TypeError):
            return None

    def _forbidden_response(self, request, message):
        """Render a styled 403 error page with the given message."""
        response = TemplateResponse(
            request,
            "403.html",
            {"exception": message},
            status=403,
        )
        # Render immediately so context processors populate the template
        response.render()
        return response
