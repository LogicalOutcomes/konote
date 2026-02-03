"""RBAC middleware enforcing program-scoped data access."""
import re

from django.http import HttpResponseForbidden


# URL patterns that require program-level access checks
# Maps URL regex to the URL kwarg containing the client ID
CLIENT_URL_PATTERNS = [
    (re.compile(r"^/clients/(?P<client_id>\d+)"), "client_id"),
    (re.compile(r"^/notes/client/(?P<client_id>\d+)"), "client_id"),
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

    def __call__(self, request):
        # Skip for unauthenticated users (login page handles that)
        if not hasattr(request, "user") or not request.user.is_authenticated:
            return self.get_response(request)

        path = request.path

        # Admin-only routes
        for pattern in ADMIN_ONLY_PATTERNS:
            if pattern.match(path):
                if not request.user.is_admin:
                    return HttpResponseForbidden("Access denied. Admin privileges required.")
                return self.get_response(request)

        # Client-scoped routes — check program overlap (admins are NOT exempt)
        for pattern, id_param in CLIENT_URL_PATTERNS:
            match = pattern.match(path)
            if match:
                client_id = match.group("client_id")
                if not self._user_can_access_client(request.user, client_id):
                    if request.user.is_admin:
                        return HttpResponseForbidden(
                            "Administrators cannot access individual client records. "
                            "Ask another admin to assign you a program role if you need client access."
                        )
                    return HttpResponseForbidden("Access denied. You are not assigned to this client's program.")
                # Store for use in views
                request.accessible_client_id = int(client_id)
                # Store user's highest role for this client's programs
                request.user_program_role = self._get_role_for_client(request.user, client_id)
                break

        return self.get_response(request)

    # Role hierarchy — higher number = more access
    ROLE_RANK = {"receptionist": 1, "staff": 2, "program_manager": 3}

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
