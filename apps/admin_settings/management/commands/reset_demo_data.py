"""Restore the disposable demo instance to its seeded baseline.

Use this as the start command of a dedicated Railway cron service. The
schedule belongs to Railway, not this command.
"""

import io
import os
from time import monotonic

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from apps.clients.models import ClientFile
from apps.notes.models import ProgressNote
from apps.programs.models import Program
from apps.auth_app.models import EvaluationExportGrant, LTEExportGrant


LOCK_ID = 85122026


class Command(BaseCommand):
    help = "Reset a disposable demo instance to its seeded baseline."

    def handle(self, *args, **options):
        if not settings.DEMO_MODE:
            raise CommandError("DEMO_MODE must be enabled to reset demo data.")
        if connection.vendor != "postgresql":
            raise CommandError("Demo reset requires PostgreSQL for its concurrency lock.")
        if os.environ.get("PYTHONHASHSEED") != "0":
            raise CommandError("Set PYTHONHASHSEED=0 on the demo reset service.")

        started = monotonic()
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_try_advisory_lock(%s)", [LOCK_ID])
            if not cursor.fetchone()[0]:
                raise CommandError("Another demo reset is already running.")

        try:
            with transaction.atomic():
                # Both instances are disposable test instances. Remove all
                # participant, program, and account records, including ones
                # created by staff without the demo marker.
                ClientFile.objects.all().delete()
                Program.objects.all().delete()
                EvaluationExportGrant.objects.all().delete()
                LTEExportGrant.objects.all().delete()
                get_user_model().objects.all().delete()
                # Seed's narration contains demo names; cron logs need only
                # aggregate results and a bounded failure type.
                call_command("seed", strict_demo=True, stdout=io.StringIO(), stderr=io.StringIO())
                clients = ClientFile.objects.filter(is_demo=True, record_id__startswith="DEMO-").count()
                users = get_user_model().objects.filter(is_demo=True).count()
                notes = ProgressNote.objects.filter(client_file__is_demo=True).count()
                if clients < 15 or users < 6 or notes == 0:
                    raise CommandError(
                        "Demo reset incomplete: expected demo clients, users, and notes."
                    )
            self.stdout.write(self.style.SUCCESS(
                f"Demo reset complete: {clients} named clients, {users} demo users, "
                f"{notes} notes; {monotonic() - started:.1f}s."
            ))
        except Exception as exc:
            # Django prints uncaught exception values, which may contain a
            # participant name from a failed seed operation.
            raise CommandError(f"Demo reset failed ({type(exc).__name__}).") from None
        finally:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_unlock(%s)", [LOCK_ID])
