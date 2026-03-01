"""
Tests that every KoNote model is covered by the export system.

This test suite ensures that adding a new model to any KoNote app
forces a deliberate decision: either export the model or explicitly
exclude it with a documented reason.
"""

from django.test import TestCase

from apps.reports.export_registry import (
    EXPORT_EXCLUDE,
    KONOTE_APPS,
    get_all_konote_models,
    get_excluded_models,
    get_exportable_models,
    get_uncovered_models,
)


class ExportCoverageTest(TestCase):
    def test_no_uncovered_models(self):
        """Every KoNote model must be exported or explicitly excluded."""
        uncovered = get_uncovered_models()
        if uncovered:
            names = [f"{m._meta.app_label}.{m.__name__}" for m in uncovered]
            self.fail(
                f"Models not covered by export: {', '.join(sorted(names))}. "
                f"Add to EXPORT_EXCLUDE in apps/reports/export_registry.py "
                f"or ensure the export command handles them."
            )

    def test_excluded_models_have_reasons(self):
        """Every excluded model entry should be well-formed."""
        for entry in EXPORT_EXCLUDE:
            self.assertEqual(
                len(entry), 2,
                f"EXPORT_EXCLUDE entry must be (app_label, model_name): {entry}",
            )

    def test_konote_apps_matches_installed(self):
        """KONOTE_APPS should match the actual installed KoNote apps."""
        from django.conf import settings

        installed_konote = {
            app.split(".")[-1]
            for app in settings.INSTALLED_APPS
            if app.startswith("apps.")
        }
        self.assertEqual(KONOTE_APPS, installed_konote)

    def test_exportable_and_excluded_are_disjoint(self):
        """A model cannot be both exportable and excluded."""
        exportable = get_exportable_models()
        excluded = get_excluded_models()
        overlap = exportable & excluded
        self.assertEqual(overlap, set())

    def test_exportable_models_not_empty(self):
        """Sanity check: there should be many exportable models."""
        exportable = get_exportable_models()
        self.assertGreater(len(exportable), 20)
