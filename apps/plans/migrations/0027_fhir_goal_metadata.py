from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("plans", "0026_metricdefinition_dqv_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="plantarget",
            name="goal_source",
            field=models.CharField(
                blank=True,
                default="",
                max_length=20,
                choices=[
                    ("participant", "Participant-initiated"),
                    ("worker", "Worker-initiated"),
                    ("joint", "Jointly developed"),
                    ("funder_required", "Funder-required"),
                ],
                help_text="Who established this goal. Auto-classified from content.",
            ),
        ),
        migrations.AddField(
            model_name="plantarget",
            name="goal_source_method",
            field=models.CharField(
                blank=True,
                default="",
                max_length=20,
                help_text="How goal_source was derived (e.g. heuristic, manual, ai_inferred).",
            ),
        ),
        migrations.AddField(
            model_name="plantarget",
            name="target_date",
            field=models.DateField(
                blank=True,
                null=True,
                help_text="Target completion date. Auto-set from program default or AI extraction.",
            ),
        ),
    ]
