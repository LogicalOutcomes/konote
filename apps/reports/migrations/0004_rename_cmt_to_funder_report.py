"""Rename export_type 'cmt' to 'funder_report' in SecureExportLink."""
from django.db import migrations


def rename_cmt_to_funder_report(apps, schema_editor):
    SecureExportLink = apps.get_model("reports", "SecureExportLink")
    SecureExportLink.objects.filter(export_type="cmt").update(export_type="funder_report")


def rename_funder_report_to_cmt(apps, schema_editor):
    SecureExportLink = apps.get_model("reports", "SecureExportLink")
    SecureExportLink.objects.filter(export_type="funder_report").update(export_type="cmt")


class Migration(migrations.Migration):
    dependencies = [
        ("reports", "0003_add_contains_pii_to_secureexportlink"),
    ]

    operations = [
        migrations.RunPython(
            rename_cmt_to_funder_report,
            rename_funder_report_to_cmt,
        ),
    ]
