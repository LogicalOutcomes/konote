"""Safe locale middleware — gracefully handles translation failures.

If the French .mo file is corrupted or missing, this middleware catches
the error and falls back to English instead of crashing with a 500 error.
"""
import logging

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

            # BUG-9: Only validate .mo file when language came from cookie/header
            # (anonymous users or users without a saved preference). When the
            # user has an explicit preference, trust it — if translations are
            # missing, the page will show untranslated strings but the lang
            # attribute will correctly reflect the user's choice.
            if not user_has_preference:
                current_lang = translation.get_language()
                if current_lang and current_lang.startswith("fr"):
                    test_str = translation.gettext("Program Outcome Report")
                    if test_str == "Program Outcome Report":
                        logger.warning(
                            "French .mo catalog may be missing: "
                            "project string not translated."
                        )
                        translation.activate("en")
                        request.LANGUAGE_CODE = "en"

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
        """Process response with error handling."""
        try:
            return super().process_response(request, response)
        except Exception as e:
            logger.error("Translation error in response processing: %s", str(e))
            # Return response without translation patches
            return response
