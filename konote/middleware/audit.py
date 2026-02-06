"""Audit logging middleware — logs state-changing requests and client views."""
import logging
import re

from django.utils import timezone

logger = logging.getLogger(__name__)

# HTTP methods that change state
AUDITABLE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# URL patterns for client record views (GET requests to log for compliance)
# Includes both main app and Django admin paths.
CLIENT_VIEW_PATTERNS = [
    re.compile(r"^/clients/(\d+)/?$"),                          # /clients/123/
    re.compile(r"^/clients/(\d+)/"),                             # /clients/123/anything
    re.compile(r"^/django-admin/clients/clientfile/(\d+)/"),     # Django admin client view
]


class AuditMiddleware:
    """
    Automatically log HTTP requests to the audit database.

    Logs:
    - All state-changing requests (POST/PUT/PATCH/DELETE)
    - Client record views (GET /clients/<id>) for compliance
    - Failed access attempts (403) on client records — critical for DV audit trails

    Captures: user, action, path, IP address, timestamp, confidential context.
    Detailed field-level changes are logged via model signals in the audit app.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if not hasattr(request, "user") or not request.user.is_authenticated:
            return response

        # Log failed access attempts on client records (403) — DV audit signal
        if response.status_code == 403 and self._is_client_view(request.path):
            self._log_request(request, response, action="access_denied")
            return response

        # Skip other error responses
        if response.status_code >= 400:
            return response

        # Log state-changing requests
        if request.method in AUDITABLE_METHODS:
            self._log_request(request, response, action=request.method.lower())

        # Log client record views for compliance (PIPEDA, healthcare regs)
        elif request.method == "GET" and self._is_client_view(request.path):
            self._log_request(request, response, action="view")

        return response

    def _is_client_view(self, path):
        """Check if path is a client record view."""
        for pattern in CLIENT_VIEW_PATTERNS:
            if pattern.match(path):
                return True
        return False

    def _extract_client_id_from_path(self, path):
        """Extract client ID from a client view URL pattern."""
        for pattern in CLIENT_VIEW_PATTERNS:
            match = pattern.match(path)
            if match:
                return int(match.group(1))
        return None

    def _check_confidential_context(self, client_id):
        """Check if client is enrolled in any confidential program.

        Returns (is_confidential, program_id) tuple.
        """
        if client_id is None:
            return False, None
        try:
            from apps.clients.models import ClientProgramEnrolment
            enrolment = ClientProgramEnrolment.objects.filter(
                client_file_id=client_id,
                program__is_confidential=True,
                status="enrolled",
            ).select_related("program").first()
            if enrolment:
                return True, enrolment.program_id
        except Exception:
            pass
        return False, None

    def _get_user_role(self, user, client_id):
        """Get user's role for the client's program (for audit metadata)."""
        if client_id is None:
            return None
        try:
            from apps.clients.models import ClientProgramEnrolment
            from apps.programs.models import UserProgramRole

            # Get programs the client is enrolled in
            client_program_ids = ClientProgramEnrolment.objects.filter(
                client_file_id=client_id, status="enrolled",
            ).values_list("program_id", flat=True)

            # Get user's role in any of those programs
            role = UserProgramRole.objects.filter(
                user=user, program_id__in=client_program_ids, status="active",
            ).first()
            if role:
                return role.get_role_display()
        except Exception:
            pass
        return None

    def _log_request(self, request, response, action):
        """Write an audit log entry."""
        try:
            from apps.audit.models import AuditLog

            # Check confidential context for client views
            client_id = self._extract_client_id_from_path(request.path)
            is_confidential, conf_program_id = self._check_confidential_context(client_id)

            # Get user role for audit accountability
            user_role = self._get_user_role(request.user, client_id) if client_id else None

            metadata = {
                "path": request.path,
                "status_code": response.status_code,
            }
            if user_role:
                metadata["user_role"] = user_role

            AuditLog.objects.using("audit").create(
                event_timestamp=timezone.now(),
                user_id=request.user.id,
                user_display=request.user.get_display_name(),
                ip_address=self._get_client_ip(request),
                action=action,
                resource_type=self._extract_resource_type(request.path),
                resource_id=self._extract_resource_id(request.path),
                program_id=conf_program_id,
                is_demo_context=getattr(request.user, "is_demo", False),
                is_confidential_context=is_confidential,
                metadata=metadata,
            )
        except Exception as e:
            # Audit logging should never break the application, but log the failure
            logger.error("Audit logging failed for %s %s: %s", request.method, request.path, e)

    def _get_client_ip(self, request):
        """Get client IP, respecting X-Forwarded-For from reverse proxy."""
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")

    def _extract_resource_type(self, path):
        """Extract resource type from URL path (e.g., /clients/5/ -> client)."""
        parts = [p for p in path.strip("/").split("/") if p]
        return parts[0] if parts else "unknown"

    def _extract_resource_id(self, path):
        """Extract numeric resource ID from URL path if present."""
        parts = path.strip("/").split("/")
        for part in parts:
            if part.isdigit():
                return int(part)
        return None
