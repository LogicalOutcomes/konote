from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("clients", "0042_alter_customfieldgroup_collapsed_by_default"),
    ]

    operations = [
        migrations.AddField(
            model_name="customfieldgroup",
            name="is_evaluation_exportable",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "When enabled, fields in this group can be selected as "
                    "demographic columns in evaluation exports. Only non-sensitive "
                    "groups should be marked exportable."
                ),
            ),
        ),
    ]
