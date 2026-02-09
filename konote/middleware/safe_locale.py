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
        """
        try:
            # Let Django's LocaleMiddleware set language from cookie/header
            super().process_request(request)

            # BUG-4: Override with user's saved preference if authenticated
            if hasattr(request, "user") and request.user.is_authenticated:
                pref = getattr(request.user, "preferred_language", "")
                if pref:
                    translation.activate(pref)
                    request.LANGUAGE_CODE = pref
            # Portal participant language preference
            elif hasattr(request, "participant_user") and request.participant_user:
                pref = getattr(request.participant_user, "preferred_language", "")
                if pref:
                    translation.activate(pref)
                    request.LANGUAGE_CODE = pref

            # Test that translations actually work by calling gettext
            # This catches corrupted .mo files that load but fail on use
            current_lang = translation.get_language()
            if current_lang and current_lang.startswith("fr"):
                # Try a project-specific translation to verify our .mo file works.
                # We use a KoNote-only string (not a Django built-in) so this
                # fails if our .mo catalog is missing, even if Django's is loaded.
                test_str = translation.gettext("Programme Outcome Report")
                if test_str == "Programme Outcome Report":
                    # Our project .mo file didn't load — French string was not translated
                    logger.warning(
                        "French .mo catalog may be missing: project string not translated."
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
