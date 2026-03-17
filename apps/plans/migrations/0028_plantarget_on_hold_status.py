from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("plans", "0027_fhir_goal_metadata"),
    ]

    operations = [
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
    ]
