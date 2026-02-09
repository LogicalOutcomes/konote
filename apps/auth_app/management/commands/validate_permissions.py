"""Management command to validate the central permissions matrix."""
from django.core.management.base import BaseCommand

from apps.auth_app.permissions import validate_permissions, PERMISSIONS


class Command(BaseCommand):
    help = "Validate that all roles have all permission keys defined"

    def handle(self, *args, **options):
        """Run validation and print results."""
        is_valid, errors = validate_permissions()

        if is_valid:
            self.stdout.write(self.style.SUCCESS("[OK] All 4 roles defined"))
            self.stdout.write(self.style.SUCCESS("[OK] All permission keys present for each role"))
            self.stdout.write(self.style.SUCCESS("[OK] No undefined permission levels"))
            self.stdout.write(self.style.SUCCESS("[OK] Permissions matrix complete"))

            # Print summary
            self.stdout.write("\n" + "=" * 60)
            self.stdout.write("Permissions Matrix Summary")
            self.stdout.write("=" * 60)

            for role in ["receptionist", "staff", "program_manager", "executive"]:
                role_perms = PERMISSIONS[role]
                allow_count = sum(1 for v in role_perms.values() if v == "allow")
                scoped_count = sum(1 for v in role_perms.values() if v == "scoped")
                deny_count = sum(1 for v in role_perms.values() if v == "deny")
                other_count = sum(1 for v in role_perms.values() if v not in ["allow", "scoped", "deny"])

                self.stdout.write(
                    f"\n{role.upper()}: "
                    f"{allow_count} ALLOW, "
                    f"{scoped_count} SCOPED, "
                    f"{deny_count} DENY, "
                    f"{other_count} OTHER"
                )

            return 0
        else:
            self.stdout.write(self.style.ERROR("[FAIL] Permissions validation failed"))
            for error in errors:
                self.stdout.write(self.style.ERROR(f"  - {error}"))
            return 1
