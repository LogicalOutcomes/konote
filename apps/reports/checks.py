"""
Django system check for export coverage completeness.

Check ID: KoNote.W020 — Export coverage gap detected
"""

from django.core.checks import Warning, register


@register()
def check_export_coverage(app_configs, **kwargs):
    """W020: Warn if any KoNote model is neither exported nor excluded."""
    from apps.reports.export_registry import get_uncovered_models

    uncovered = get_uncovered_models()
    if uncovered:
        model_names = ", ".join(
            sorted(f"{m._meta.app_label}.{m.__name__}" for m in uncovered)
        )
        return [
            Warning(
                f"Export coverage gap: {len(uncovered)} model(s) not covered "
                f"by export or exclusion list: {model_names}",
                hint="Add to EXPORT_EXCLUDE in apps/reports/export_registry.py "
                     "or ensure the export command handles them.",
                id="KoNote.W020",
            )
        ]
    return []
