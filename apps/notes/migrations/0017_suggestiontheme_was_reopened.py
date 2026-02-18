from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notes", "0016_unique_theme_per_program"),
    ]

    operations = [
        migrations.AddField(
            model_name="suggestiontheme",
            name="was_reopened",
            field=models.BooleanField(
                default=False,
                help_text="Set when an addressed theme is reopened by AI finding new suggestions.",
            ),
        ),
    ]
