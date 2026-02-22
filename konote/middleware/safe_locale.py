"""Safe locale middleware — gracefully handles translation failures.

If the French .mo file is corrupted or missing, this middleware catches
the error and falls back to English instead of crashing with a 500 error.
"""
import logging

from django.conf import settings
from django.middleware.locale import LocaleMiddleware
from django.utils import translation

logger = logging.getLogger(__name__)


class SafeLocaleMiddleware(LocaleMiddleware):
    """
    Extends Django's LocaleMiddleware with error handling.

    If translation activation fails (e.g., corrupted .mo file),
    falls back to English and logs the error.
    """

    def process_request(self, request):
        """Activate language with fallback on failure.

        BUG-4: Override cookie-based language with user's saved preference.
        This middleware runs after AuthenticationMiddleware so request.user
        is available. Authenticated users always get their profile language,
        preventing language bleed on shared browsers.

        BUG-9: When a user has a saved preferred_language, skip the .mo
        validation check. The user's explicit preference is authoritative
        and must not be overridden by a gettext probe that can fail under
        threading or catalog-loading timing issues.
        """
        try:
            # Let Django's LocaleMiddleware set language from cookie/header
            super().process_request(request)

            # BUG-4: Override with user's saved preference if authenticated
            user_has_preference = False
            if hasattr(request, "user") and request.user.is_authenticated:
                pref = getattr(request.user, "preferred_language", "")
                if pref:
                    translation.activate(pref)
                    request.LANGUAGE_CODE = pref
                    user_has_preference = True
            # Portal participant language preference
            elif hasattr(request, "participant_user") and request.participant_user:
                pref = getattr(request.participant_user, "preferred_language", "")
                if pref:
                    translation.activate(pref)
                    request.LANGUAGE_CODE = pref
                    user_has_preference = True

            # BUG-14: Never revert language based on .mo validation. If the
            # user chose French (via preference, cookie, or header), honour
            # that choice. Missing translations show as English strings, but
            # the lang attribute must reflect the user's language choice for
            # WCAG 3.1.1 compliance. Log a warning for missing .mo files
            # so developers can add translations.
            if not user_has_preference:
                current_lang = translation.get_language()
                if current_lang and current_lang.startswith("fr"):
                    test_str = translation.gettext("Program Outcome Report")
                    if test_str == "Program Outcome Report":
                        logger.warning(
                            "French .mo catalog may be incomplete: "
                            "probe string 'Program Outcome Report' not "
                            "translated. lang attribute stays '%s' per "
                            "WCAG 3.1.1.", current_lang
                        )

        except Exception as e:
            # Log the error and fall back to English
            logger.error(
                "Translation error for language '%s': %s. Falling back to English.",
                translation.get_language(),
                str(e),
            )
            translation.activate("en")
            request.LANGUAGE_CODE = "en"

    def process_response(self, request, response):
        """Process response with error handling and cookie sync.

        BUG-1: Sync the language cookie to the user's preferred_language.
        If the cookie disagrees with the profile (e.g. stale cookie from a
        previous user or session), overwrite it.  This prevents language
        "bleed" when users share a browser or when cookies drift.
        """
        try:
            response = super().process_response(request, response)
        except Exception as e:
            logger.error("Translation error in response processing: %s", str(e))

        # Sync cookie → user.preferred_language (defense in depth)
        if hasattr(request, "user") and request.user.is_authenticated:
            pref = getattr(request.user, "preferred_language", "")
            if pref:
                cookie_lang = request.COOKIES.get(
                    settings.LANGUAGE_COOKIE_NAME, ""
                )
                if cookie_lang != pref:
                    response.set_cookie(
                        settings.LANGUAGE_COOKIE_NAME,
                        pref,
                        max_age=settings.LANGUAGE_COOKIE_AGE,
                        path=settings.LANGUAGE_COOKIE_PATH,
                        domain=settings.LANGUAGE_COOKIE_DOMAIN,
                        secure=settings.LANGUAGE_COOKIE_SECURE,
                        httponly=settings.LANGUAGE_COOKIE_HTTPONLY,
                        samesite=settings.LANGUAGE_COOKIE_SAMESITE,
                    )

        return response
