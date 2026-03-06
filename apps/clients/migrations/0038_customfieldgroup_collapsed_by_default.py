from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("clients", "0037_customfielddefinition_show_on_create"),
    ]

    operations = [
        migrations.AddField(
            model_name="customfieldgroup",
            name="collapsed_by_default",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "When checked, this group is collapsed on the participant info tab. "
                    "Use for sensitive demographics that aren't needed for daily service delivery."
                ),
            ),
        ),
    ]
