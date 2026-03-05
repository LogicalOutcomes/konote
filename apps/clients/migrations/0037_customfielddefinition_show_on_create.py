from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("clients", "0036_alter_consentevent_id_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="customfielddefinition",
            name="show_on_create",
            field=models.BooleanField(
                default=False,
                help_text="Show this field on the new participant creation form.",
            ),
        ),
    ]
