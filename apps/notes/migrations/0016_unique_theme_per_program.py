"""Add unique constraint on SuggestionTheme(program, name).

Runs merge_duplicate_themes logic first to ensure no duplicates exist
before the constraint is applied. Safe to re-run.
"""
from collections import defaultdict

from django.db import migrations, models


def merge_duplicate_themes(apps, schema_editor):
    """Merge duplicate SuggestionTheme records before adding unique constraint."""
    SuggestionTheme = apps.get_model("notes", "SuggestionTheme")
    SuggestionLink = apps.get_model("notes", "SuggestionLink")

    groups = defaultdict(list)
    for theme in SuggestionTheme.objects.order_by("pk"):
        key = (theme.program_id, " ".join(theme.name.split()).lower())
        groups[key].append(theme)

    for (program_id, name_lower), themes in groups.items():
        if len(themes) < 2:
            continue

        # Pick the theme with the most links as primary (oldest as tiebreaker)
        link_counts = {
            t.pk: SuggestionLink.objects.filter(theme=t).count()
            for t in themes
        }
        themes.sort(key=lambda t: (-link_counts[t.pk], t.pk))
        primary = themes[0]

        for dupe in themes[1:]:
            # Move links from duplicate to primary
            for link in SuggestionLink.objects.filter(theme=dupe):
                if not SuggestionLink.objects.filter(
                    theme=primary, progress_note_id=link.progress_note_id
                ).exists():
                    link.theme = primary
                    link.save()

            # Keep longer description
            if len(dupe.description) > len(primary.description):
                primary.description = dupe.description

            # Merge keywords
            if dupe.keywords and not primary.keywords:
                primary.keywords = dupe.keywords

            dupe.delete()

        primary.save()


class Migration(migrations.Migration):

    dependencies = [
        ("notes", "0015_theme_automation_fields"),
    ]

    operations = [
        migrations.RunPython(
            merge_duplicate_themes,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AddConstraint(
            model_name="suggestiontheme",
            constraint=models.UniqueConstraint(
                fields=["program", "name"],
                name="unique_theme_per_program",
            ),
        ),
    ]
