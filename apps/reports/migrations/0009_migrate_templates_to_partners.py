"""Data migration: create a Partner for each existing ReportTemplate.

For each existing template, a Partner is created with the template's name
and partner_type="funder" (safe default). The template's programs M2M is
copied to the partner's programs M2M, and the template is linked to the
new partner.
"""
from django.db import migrations


def forwards(apps, schema_editor):
    ReportTemplate = apps.get_model("reports", "ReportTemplate")
    Partner = apps.get_model("reports", "Partner")

    # Check if the report_templates table exists — on fresh databases where
    # FunderProfile was never created, the rename in 0006 may have been faked
    # and the M2M through table won't exist yet.
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'report_templates')"
        )
        if not cursor.fetchone()[0]:
            return

    for template in ReportTemplate.objects.all():
        partner = Partner.objects.create(
            name=template.name,
            partner_type="funder",
        )
        # Copy programs from template to partner
        partner.programs.set(template.programs.all())
        # Link template to partner
        template.partner = partner
        template.save(update_fields=["partner"])


def backwards(apps, schema_editor):
    # Reverse: copy partner.programs back to template.programs, unlink partner
    ReportTemplate = apps.get_model("reports", "ReportTemplate")
    Partner = apps.get_model("reports", "Partner")

    for template in ReportTemplate.objects.select_related("partner").all():
        if template.partner:
            template.programs.set(template.partner.programs.all())
            template.partner = None
            template.save(update_fields=["partner"])

    # Delete auto-created partners
    Partner.objects.filter(partner_type="funder").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("reports", "0008_partner_report_section_metric"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
