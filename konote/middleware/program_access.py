"""RBAC middleware enforcing program-scoped data access."""
import re

from django.shortcuts import redirect
from django.template.response import TemplateResponse


# URL patterns that require program-level access checks
# Maps URL regex to the URL kwarg containing the client ID
CLIENT_URL_PATTERNS = [
    (re.compile(r"^/clients/(?P<client_id>\d+)"), "client_id"),
    (re.compile(r"^/notes/client/(?P<client_id>\d+)"), "client_id"),
    (re.compile(r"^/reports/client/(?P<client_id>\d+)"), "client_id"),
]

# URL patterns for note-specific routes (look up client from note)
NOTE_URL_PATTERNS = [
    re.compile(r"^/notes/(?P<note_id>\d+)"),
]

# URLs that only admins can access
ADMIN_ONLY_PATTERNS = [
    re.compile(r"^/admin/"),
]


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

        # Admin-only routes (checked BEFORE program selection — admin routes
        # have their own access control and don't need program context)
        for pattern in ADMIN_ONLY_PATTERNS:
            if pattern.match(path):
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

        # Executive role: redirect to dashboard instead of client pages
        # Executives can see aggregate data only, not individual client records
        if self._is_executive_only(request.user):
            for pattern, _ in CLIENT_URL_PATTERNS:
                if pattern.match(path):
                    return redirect("clients:executive_dashboard")
            for pattern in NOTE_URL_PATTERNS:
                if pattern.match(path):
                    return redirect("clients:executive_dashboard")
            # Also redirect from client list
            if path == "/clients/" or path == "/clients":
                return redirect("clients:executive_dashboard")

        # Client-scoped routes — check program overlap (admins are NOT exempt)
        for pattern, id_param in CLIENT_URL_PATTERNS:
            match = pattern.match(path)
            if match:
                client_id = match.group("client_id")
                if not self._user_can_access_client(request.user, client_id):
                    if request.user.is_admin:
                        return self._forbidden_response(
                            request,
                            "Administrators cannot access individual client records. "
                            "Ask another admin to assign you a programme role if you need client access."
                        )
                    return self._forbidden_response(
                        request,
                        "Access denied. You are not assigned to this client's programme."
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
                    if not self._user_can_access_client(request.user, client_id):
                        if request.user.is_admin:
                            return self._forbidden_response(
                                request,
                                "Administrators cannot access individual client records. "
                                "Ask another admin to assign you a programme role if you need client access."
                            )
                        return self._forbidden_response(
                            request,
                            "Access denied. You are not assigned to this client's programme."
                        )
                    request.accessible_client_id = client_id
                    request.user_program_role = self._get_role_for_client(request.user, client_id)
                break

        return self.get_response(request)

    # Role hierarchy — higher number = more access (executive has highest rank but no client data access)
    ROLE_RANK = {"receptionist": 1, "staff": 2, "program_manager": 3, "executive": 4}

    def _is_executive_only(self, user):
        """Check if user's only/highest role is executive (no client data access)."""
        from apps.programs.models import UserProgramRole

        roles = set(
            UserProgramRole.objects.filter(user=user, status="active").values_list("role", flat=True)
        )
        if not roles:
            return False
        # Executive-only if they have executive role and no other roles that grant client access
        if "executive" in roles:
            client_access_roles = {"receptionist", "staff", "program_manager"}
            return not bool(roles & client_access_roles)
        return False

    def _user_can_access_client(self, user, client_id):
        """Check if user shares at least one program with the client."""
        from apps.clients.models import ClientProgramEnrolment
        from apps.programs.models import UserProgramRole

        user_program_ids = set(
            UserProgramRole.objects.filter(user=user, status="active").values_list("program_id", flat=True)
        )
        if not user_program_ids:
            return False

        client_program_ids = set(
            ClientProgramEnrolment.objects.filter(
                client_file_id=client_id, status="enrolled"
            ).values_list("program_id", flat=True)
        )
        return bool(user_program_ids & client_program_ids)

    def _get_role_for_client(self, user, client_id):
        """Return the user's highest role across programs shared with this client."""
        from apps.clients.models import ClientProgramEnrolment
        from apps.programs.models import UserProgramRole

        client_program_ids = set(
            ClientProgramEnrolment.objects.filter(
                client_file_id=client_id, status="enrolled"
            ).values_list("program_id", flat=True)
        )
        roles = UserProgramRole.objects.filter(
            user=user, status="active", program_id__in=client_program_ids,
        ).values_list("role", flat=True)

        if not roles:
            return None
        return max(roles, key=lambda r: self.ROLE_RANK.get(r, 0))

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
