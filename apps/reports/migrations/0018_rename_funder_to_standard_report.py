"""Rename export_type 'funder_report' to 'standard_report' in SecureExportLink,
and report_type 'funder_report' to 'standard_report' in ReportDeadline."""
from django.db import migrations


def rename_funder_to_standard(apps, schema_editor):
    SecureExportLink = apps.get_model("reports", "SecureExportLink")
    SecureExportLink.objects.filter(export_type="funder_report").update(
        export_type="standard_report"
    )
    ReportDeadline = apps.get_model("reports", "ReportDeadline")
    ReportDeadline.objects.filter(report_type="funder_report").update(
        report_type="standard_report"
    )


def rename_standard_to_funder(apps, schema_editor):
    SecureExportLink = apps.get_model("reports", "SecureExportLink")
    SecureExportLink.objects.filter(export_type="standard_report").update(
        export_type="funder_report"
    )
    ReportDeadline = apps.get_model("reports", "ReportDeadline")
    ReportDeadline.objects.filter(report_type="standard_report").update(
        report_type="funder_report"
    )


class Migration(migrations.Migration):
    dependencies = [
        ("reports", "0017_reporttemplate_include_all_metrics"),
    ]

    operations = [
        migrations.RunPython(
            rename_funder_to_standard,
            rename_standard_to_funder,
        ),
    ]
