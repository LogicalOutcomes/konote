"""Replace case-sensitive unique constraint with case-insensitive version.

Uses Lower("name") so "Evening Availability" and "evening availability"
are treated as the same theme at the database level.
"""
from django.db import migrations, models
from django.db.models.functions import Lower


class Migration(migrations.Migration):

    dependencies = [
        ("notes", "0017_suggestiontheme_was_reopened"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="suggestiontheme",
            name="unique_theme_per_program",
        ),
        migrations.AddConstraint(
            model_name="suggestiontheme",
            constraint=models.UniqueConstraint(
                Lower("name"), "program",
                name="unique_theme_per_program",
            ),
        ),
    ]
