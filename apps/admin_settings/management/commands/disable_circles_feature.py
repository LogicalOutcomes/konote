from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Disable the circles feature toggle and remove demo circles."

    def add_arguments(self, parser):
        parser.add_argument(
            "--keep-demo-circles",
            action="store_true",
            help="Disable the feature toggle but leave demo circles in the database.",
        )

    def handle(self, *args, **options):
        from apps.admin_settings.models import FeatureToggle
        from apps.circles.models import Circle

        toggle, _ = FeatureToggle.objects.get_or_create(feature_key="circles")
        toggle.is_enabled = False
        toggle.save(update_fields=["is_enabled"])

        deleted_count = 0
        if not options["keep_demo_circles"]:
            deleted_count = Circle.objects.filter(is_demo=True).delete()[0]

        self.stdout.write(
            self.style.SUCCESS(
                f"Circles disabled. Demo circles removed: {deleted_count}."
            )
        )
