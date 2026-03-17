from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0011_alter_evaluationcomponent_id_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="program",
            name="default_goal_review_days",
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                help_text="Default target date offset (days) for goals created in this program.",
            ),
        ),
    ]
