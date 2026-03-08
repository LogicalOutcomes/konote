from pathlib import Path

from django.conf import settings
from django.template.loader import render_to_string
from django.test import SimpleTestCase
from django.utils.translation import override as translation_override


class StandaloneAccessibilityTemplateTests(SimpleTestCase):
    def test_500_template_uses_active_language_for_html_lang(self):
        with translation_override("fr"):
            content = render_to_string("500.html")

        self.assertIn('lang="fr"', content)
        self.assertIn('href="#main-content"', content)
        self.assertNotIn("Skip to main content", content)

    def test_offline_template_uses_active_language_for_html_lang(self):
        with translation_override("fr"):
            content = render_to_string("offline.html")

        self.assertIn('lang="fr"', content)
        self.assertIn('href="#main-content"', content)
        self.assertNotIn("Skip to main content", content)


class StaticOfflineFallbackTests(SimpleTestCase):
    def test_static_offline_page_has_skip_link_and_language_detection(self):
        content = (Path(settings.BASE_DIR) / "static" / "offline.html").read_text(encoding="utf-8")

        self.assertIn('href="#main-content"', content)
        self.assertIn('id="main-content"', content)
        self.assertIn("navigator.language", content)
        self.assertIn("document.documentElement.lang", content)