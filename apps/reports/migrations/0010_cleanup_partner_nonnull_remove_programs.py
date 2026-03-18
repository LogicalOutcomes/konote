"""Cleanup migration: make partner non-nullable, remove programs M2M from ReportTemplate.

The data migration (0009) already ensured every existing ReportTemplate has a
Partner assigned, so the AlterField to non-nullable is safe.

Programs are now managed on the Partner entity, not the ReportTemplate.
"""
import django.db.models.deletion
from django.db import connection, migrations, models


def _table_exists(table_name):
    with connection.cursor() as cursor:
        if connection.vendor == "sqlite":
            cursor.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=%s",
                [table_name],
            )
            return cursor.fetchone()[0] > 0
        cursor.execute(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = %s)",
            [table_name],
        )
        return cursor.fetchone()[0]


def _column_exists(table_name, column_name):
    with connection.cursor() as cursor:
        if connection.vendor == "sqlite":
            cursor.execute("PRAGMA table_info(%s)" % table_name)
            columns = [row[1] for row in cursor.fetchall()]
            return column_name in columns
        cursor.execute(
            "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
            "WHERE table_name = %s AND column_name = %s)",
            [table_name, column_name],
        )
        return cursor.fetchone()[0]


def forwards(apps, schema_editor):
    """Apply schema changes only if the tables/columns actually exist.

    On fresh databases where FunderProfile was never created, the
    report_templates table and its programs M2M may not exist yet.
    """
    # Make partner FK non-nullable (only if the column exists and is nullable)
    if _table_exists("report_templates") and _column_exists("report_templates", "partner_id"):
        if connection.vendor != "sqlite":
            schema_editor.execute(
                'ALTER TABLE "report_templates" ALTER COLUMN "partner_id" SET NOT NULL'
            )
        # SQLite doesn't support ALTER COLUMN; Django handles NOT NULL via
        # table recreation which SeparateDatabaseAndState's state_operations cover.

    # Drop the programs M2M through table (only if it exists)
    if _table_exists("report_templates_programs"):
        schema_editor.execute('DROP TABLE IF EXISTS "report_templates_programs"')


class Migration(migrations.Migration):

    dependencies = [
        ("reports", "0009_migrate_templates_to_partners"),
    ]

    operations = [
        # Use SeparateDatabaseAndState so Django's state tracker knows the
        # field changes happened, but the actual SQL is conditional.
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name="reporttemplate",
                    name="partner",
                    field=models.ForeignKey(
                        help_text="The partner this report template belongs to.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="report_templates",
                        to="reports.partner",
                    ),
                ),
                migrations.RemoveField(
                    model_name="reporttemplate",
                    name="programs",
                ),
            ],
            database_operations=[
                migrations.RunPython(forwards, migrations.RunPython.noop),
            ],
        ),
    ]
