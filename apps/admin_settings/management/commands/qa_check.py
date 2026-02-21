"""
Quick Check: Run interaction tests and report results.

Wraps pytest to run the 15 Playwright interaction tests from
tests/scenario_eval/test_interactions.py and produce a traffic-light
summary.

Usage:
    python manage.py qa_check
    python manage.py qa_check --verbose
    python manage.py qa_check --failfast
"""
import subprocess
import sys

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run QA Quick Check — 15 interaction tests with traffic-light output."

    def add_arguments(self, parser):
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show full pytest output",
        )
        parser.add_argument(
            "--failfast", "-x",
            action="store_true",
            help="Stop on first failure",
        )

    def handle(self, *args, **options):
        self.stdout.write("")
        self.stdout.write("QA Quick Check")
        self.stdout.write("=" * 55)
        self.stdout.write("")

        cmd = [
            sys.executable, "-m", "pytest",
            "tests/scenario_eval/test_interactions.py",
            "-m", "scenario_eval",
            "--tb=short",
        ]

        if options["verbose"]:
            cmd.append("-v")
        else:
            cmd.append("-q")

        if options["failfast"]:
            cmd.append("-x")

        result = subprocess.run(cmd, capture_output=not options["verbose"])

        if options["verbose"]:
            # Output already shown
            pass
        else:
            output = result.stdout.decode("utf-8", errors="replace")
            self.stdout.write(output)
            if result.stderr:
                self.stderr.write(result.stderr.decode("utf-8", errors="replace"))

        # Traffic-light summary
        self.stdout.write("")
        if result.returncode == 0:
            self.stdout.write(self.style.SUCCESS("QA Quick Check — GREEN"))
            self.stdout.write("All interaction tests passed.")
        elif result.returncode == 1:
            self.stdout.write(self.style.WARNING("QA Quick Check — YELLOW"))
            self.stdout.write("Some tests failed — review output above.")
        else:
            self.stdout.write(self.style.ERROR("QA Quick Check — RED"))
            self.stdout.write("Tests could not run — check environment.")

        sys.exit(result.returncode)
