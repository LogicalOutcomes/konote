from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("notes", "0029_expand_metric_value_length"),
        ("clients", "0042_alter_customfieldgroup_collapsed_by_default"),
    ]

    operations = [
        migrations.AddField(
            model_name="progressnote",
            name="episode",
            field=models.ForeignKey(
                blank=True,
                help_text="Auto-linked service episode for this encounter.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="encounter_notes",
                to="clients.serviceepisode",
            ),
        ),
    ]
