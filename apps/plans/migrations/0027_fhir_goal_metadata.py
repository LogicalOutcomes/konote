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
            name="target_date",
            field=models.DateField(
                blank=True,
                null=True,
                help_text="Target completion date. Auto-set from program default or AI extraction.",
            ),
        ),
        migrations.AddField(
            model_name="plantarget",
            name="continuous",
            field=models.BooleanField(
                default=False,
                help_text="Ongoing maintenance goal vs. time-bound achievement goal.",
            ),
        ),
        migrations.AddField(
            model_name="plantarget",
            name="metadata_sources",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Tracks how each auto-populated field was derived.",
            ),
        ),
        migrations.AlterField(
            model_name="plantarget",
            name="status",
            field=models.CharField(
                max_length=20,
                default="default",
                choices=[
                    ("default", "Active"),
                    ("on_hold", "On Hold"),
                    ("completed", "Completed"),
                    ("deactivated", "Deactivated"),
                ],
            ),
        ),
        migrations.AddField(
            model_name="plansection",
            name="period_start",
            field=models.DateField(
                blank=True,
                null=True,
                help_text="When this plan section became active. Auto-computed from target activity.",
            ),
        ),
        migrations.AddField(
            model_name="plansection",
            name="period_end",
            field=models.DateField(
                blank=True,
                null=True,
                help_text="When this plan section concluded. Auto-set when all targets complete.",
            ),
        ),
    ]
