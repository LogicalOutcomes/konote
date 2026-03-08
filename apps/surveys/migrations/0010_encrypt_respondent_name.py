import os

from django.db import migrations, models

from konote.encryption import DecryptionError, decrypt_field, encrypt_field


def encrypt_existing_respondent_names(apps, schema_editor):
    if not os.environ.get("FERNET_KEY"):
        # No encryption key available (CI/test). Skip — no real data to encrypt.
        return
    SurveyResponse = apps.get_model("surveys", "SurveyResponse")
    for response in SurveyResponse.objects.exclude(respondent_name_display="").iterator():
        response._respondent_name_encrypted = encrypt_field(
            response.respondent_name_display,
        )
        response.save(update_fields=["_respondent_name_encrypted"])


def decrypt_existing_respondent_names(apps, schema_editor):
    if not os.environ.get("FERNET_KEY"):
        return
    SurveyResponse = apps.get_model("surveys", "SurveyResponse")
    for response in SurveyResponse.objects.exclude(_respondent_name_encrypted=b"").iterator():
        try:
            response.respondent_name_display = decrypt_field(
                response._respondent_name_encrypted,
            )
        except DecryptionError:
            response.respondent_name_display = ""
        response.save(update_fields=["respondent_name_display"])


class Migration(migrations.Migration):

    dependencies = [
        ("surveys", "0009_surveysection_skip_for_identified"),
    ]

    operations = [
        migrations.AddField(
            model_name="surveyresponse",
            name="_respondent_name_encrypted",
            field=models.BinaryField(
                blank=True,
                default=b"",
                help_text="Optional encrypted respondent name for identified link responses.",
            ),
        ),
        migrations.RunPython(
            encrypt_existing_respondent_names,
            decrypt_existing_respondent_names,
        ),
        migrations.RemoveField(
            model_name="surveyresponse",
            name="respondent_name_display",
        ),
        migrations.AlterField(
            model_name="surveylink",
            name="collect_name",
            field=models.BooleanField(
                default=False,
                help_text="If true, ask respondent for their name on identified link responses only.",
            ),
        ),
    ]
