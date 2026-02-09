"""Django system checks for the participant portal.

These checks run at startup (and during ``manage.py check``) to warn about
configuration issues that could compromise portal security or expose
sensitive programme names to participants.

Run with:
    python manage.py check --deploy
"""
from django.core.checks import Warning, register


@register()
def check_session_cookie_domain(app_configs, **kwargs):
    """Warn if SESSION_COOKIE_DOMAIN could leak sessions between subdomains.

    When the portal runs on a subdomain (e.g. ``my.agency.org``) and the
    staff app on another (e.g. ``app.agency.org``), setting
    SESSION_COOKIE_DOMAIN to ``.agency.org`` would let session cookies
    travel between them. The safest default is ``None`` (current host only).
    """
    from django.conf import settings

    errors = []
    if getattr(settings, "SESSION_COOKIE_DOMAIN", None) is not None:
        errors.append(Warning(
            "SESSION_COOKIE_DOMAIN is set \u2014 portal sessions may leak between subdomains.",
            hint=(
                "Set SESSION_COOKIE_DOMAIN to None (the default) for proper "
                "portal/staff session isolation."
            ),
            id="portal.W001",
        ))
    return errors


@register()
def check_programme_portal_names(app_configs, **kwargs):
    """Warn if active programmes with sensitive names lack a portal alias.

    Programme names like "Substance Use Recovery" or "Mental Health Outreach"
    reveal clinical information when displayed in the participant portal.
    Agencies should set ``portal_display_name`` to a neutral alternative
    (e.g. "Wellness" or "Support Services").

    This check only runs when the ``participant_portal`` feature toggle is
    enabled. It silently passes if models are not yet migrated.
    """
    from django.conf import settings  # noqa: F811 — intentional re-import inside function

    errors = []
    try:
        from apps.admin_settings.models import FeatureToggle

        flags = FeatureToggle.get_all_flags()
        if not flags.get("participant_portal"):
            return errors  # Portal not enabled, skip check

        from apps.programs.models import Program

        # Keywords that may reveal clinical or sensitive context
        SENSITIVE_KEYWORDS = [
            "substance", "mental health", "hiv", "dv", "violence",
            "abuse", "addiction", "psychiatric",
        ]

        for program in Program.objects.filter(status="active"):
            if not program.portal_display_name:
                name_lower = program.name.lower()
                if any(kw in name_lower for kw in SENSITIVE_KEYWORDS):
                    errors.append(Warning(
                        f'Programme "{program.name}" may reveal clinical '
                        f"information in participant portal.",
                        hint=(
                            "Set portal_display_name on this programme to use "
                            "a neutral name in the portal."
                        ),
                        id="portal.W002",
                    ))
    except Exception:
        pass  # Don't break startup if models aren't migrated yet

    return errors
