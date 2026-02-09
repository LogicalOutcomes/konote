"""Middleware for the participant portal.

Two middleware classes:

1. **DomainEnforcementMiddleware** — ensures portal paths (``/my/``) are
   only accessible on the portal domain, and staff paths are only
   accessible on the staff domain. Does nothing when domains are not
   configured (graceful degradation for single-domain setups).

2. **PortalAuthMiddleware** — loads the authenticated ParticipantUser
   from the session and attaches it to ``request.participant_user``.
   Also verifies the participant's account is still active and their
   client file has not been discharged or erased.
"""
import logging

from django.conf import settings
from django.http import HttpResponse

from .models import ParticipantUser

logger = logging.getLogger(__name__)


class DomainEnforcementMiddleware:
    """Route enforcement: portal paths on portal domain, staff paths on staff domain.

    When ``PORTAL_DOMAIN`` and ``STAFF_DOMAIN`` are configured in settings,
    this middleware returns a 404 for:
      - Portal paths (``/my/``) accessed via the staff domain
      - Non-portal paths accessed via the portal domain

    When domains are not configured, this middleware does nothing —
    allowing the portal to work at ``/my/`` on the main domain.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(":")[0]
        portal_domain = getattr(settings, "PORTAL_DOMAIN", "")
        staff_domain = getattr(settings, "STAFF_DOMAIN", "")

        # Only enforce if domains are configured
        if portal_domain and host == portal_domain and not request.path.startswith("/my/"):
            return HttpResponse("Not Found", status=404, content_type="text/plain")

        if staff_domain and host == staff_domain and request.path.startswith("/my/"):
            return HttpResponse("Not Found", status=404, content_type="text/plain")

        return self.get_response(request)


class PortalAuthMiddleware:
    """Load the authenticated participant from the session.

    For requests to portal paths (``/my/``), this middleware reads the
    ``_portal_participant_id`` session key and loads the corresponding
    ParticipantUser. The loaded user is set on ``request.participant_user``.

    Additional checks:
      - Account must be active (``is_active=True``)
      - Linked ClientFile must not be discharged or erased

    If any check fails, the session key is cleared and
    ``request.participant_user`` is set to ``None``.

    For non-portal paths, ``request.participant_user`` is always ``None``.

    This middleware must run AFTER Django's ``AuthenticationMiddleware``
    so that the session is available.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/my/"):
            request.participant_user = self._load_participant(request)
        else:
            request.participant_user = None

        return self.get_response(request)

    def _load_participant(self, request):
        """Load and validate the participant from the session.

        Returns:
            A ParticipantUser instance if valid, or None.
        """
        participant_id = request.session.get("_portal_participant_id")
        if not participant_id:
            return None

        try:
            participant = ParticipantUser.objects.select_related(
                "client_file"
            ).get(pk=participant_id)
        except ParticipantUser.DoesNotExist:
            logger.warning(
                "Portal session references non-existent participant: %s",
                participant_id,
            )
            self._clear_session(request)
            return None

        # Check account is active
        if not participant.is_active:
            logger.info(
                "Portal session for deactivated account: %s",
                participant_id,
            )
            self._clear_session(request)
            return None

        # Check client file is not discharged or erased
        client = participant.client_file
        if client.status == "discharged":
            logger.info(
                "Portal session for discharged client: %s (participant %s)",
                client.pk,
                participant_id,
            )
            self._clear_session(request)
            return None

        if client.erasure_requested or client.erasure_completed_at:
            logger.info(
                "Portal session for erased client: %s (participant %s)",
                client.pk,
                participant_id,
            )
            self._clear_session(request)
            return None

        return participant

    def _clear_session(self, request):
        """Remove the portal participant ID from the session."""
        try:
            del request.session["_portal_participant_id"]
        except KeyError:
            pass
