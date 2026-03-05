from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("surveys", "0008_surveyresponse_consent_withdrawn_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="surveysection",
            name="skip_for_identified",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Hide this section when the survey is filled by or for "
                    "an identified participant (portal or staff-entered). "
                    "Use for demographics sections \u2014 that data is already "
                    "in the participant record."
                ),
            ),
        ),
    ]
