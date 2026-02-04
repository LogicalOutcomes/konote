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
        """Activate language with fallback on failure."""
        try:
            # Let Django's LocaleMiddleware do its thing
            super().process_request(request)

            # Test that translations actually work by calling gettext
            # This catches corrupted .mo files that load but fail on use
            current_lang = translation.get_language()
            if current_lang and current_lang.startswith("fr"):
                # Try a simple translation to verify the .mo file works
                translation.gettext("Sign In")

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
