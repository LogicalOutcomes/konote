"""Authentication backend for the participant portal.

Participants log in with email + password. The email is never stored in
plaintext — we compute the HMAC-SHA-256 hash and look up by that. A
timing-equalisation step prevents enumeration of valid email addresses.
"""
import logging

from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone

from .models import ParticipantUser

logger = logging.getLogger(__name__)


class PortalAuthBackend:
    """Authenticates participants by email and password.

    This backend is separate from the staff authentication backends.
    It returns a ParticipantUser (not a staff User) on success.

    Security measures:
      - HMAC-SHA-256 email lookup (no plaintext email in the database)
      - Timing equalisation: if the email is not found, we still run a
        password hash to prevent timing-based account enumeration
      - Account lockout check before password verification
    """

    def authenticate(self, request, email=None, password=None, **kwargs):
        """Authenticate a participant by email and password.

        Args:
            request: The current HTTP request.
            email: Plaintext email address.
            password: Plaintext password.

        Returns:
            A ParticipantUser instance on success, or None on failure.
        """
        if email is None or password is None:
            return None

        email_hash = ParticipantUser.compute_email_hash(email)

        try:
            user = ParticipantUser.objects.get(email_hash=email_hash)
        except ParticipantUser.DoesNotExist:
            # Timing equalisation: run a password hash so that the response
            # time is similar whether or not the email exists. This prevents
            # attackers from measuring response times to enumerate accounts.
            make_password("dummy-timing-equalisation")
            return None

        # Check account lockout
        if user.locked_until and timezone.now() < user.locked_until:
            logger.warning(
                "Portal login attempt for locked account: %s",
                user.id,
            )
            return None

        # Check account is active
        if not user.is_active:
            logger.warning(
                "Portal login attempt for deactivated account: %s",
                user.id,
            )
            return None

        # Verify password
        if not user.check_password(password):
            # Increment failed login count (lockout policy enforced in views)
            user.failed_login_count += 1
            user.save(update_fields=["failed_login_count"])
            return None

        # Successful authentication — reset failed login count
        if user.failed_login_count > 0:
            user.failed_login_count = 0
            user.save(update_fields=["failed_login_count"])

        return user

    def get_user(self, user_id):
        """Return the ParticipantUser for the given primary key.

        Called by Django's session framework to load the authenticated
        user on subsequent requests. Not used for portal sessions (we
        use ``_portal_participant_id`` in the session instead), but
        required by the backend interface.
        """
        try:
            return ParticipantUser.objects.get(pk=user_id)
        except ParticipantUser.DoesNotExist:
            return None
