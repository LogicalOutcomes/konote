"""Management command to validate the permissions matrix and audit user roles.

Usage:
    python manage.py validate_permissions              # Matrix completeness only
    python manage.py validate_permissions --user casey  # Show one user's effective permissions
    python manage.py validate_permissions --all-users   # Audit every active user
    python manage.py validate_permissions --demo        # Validate demo users match expected roles
"""
from django.core.management.base import BaseCommand

from apps.auth_app.permissions import (
    ALLOW,
    DENY,
    GATED,
    PER_FIELD,
    PERMISSIONS,
    PROGRAM,
    permission_to_plain_english,
    validate_permissions,
)


# Expected demo user role assignments — single source of truth for tests and
# validation.  Format: username → list of (program_name, role).
EXPECTED_DEMO_ROLES = {
    "demo-frontdesk": [
        ("Supported Employment", "receptionist"),
        ("Housing Stability", "receptionist"),
        ("Youth Drop-In", "receptionist"),
        ("Newcomer Connections", "receptionist"),
        ("Community Kitchen", "receptionist"),
    ],
    "demo-worker-1": [
        ("Supported Employment", "program_manager"),
        ("Housing Stability", "staff"),
        ("Community Kitchen", "staff"),
    ],
    "demo-worker-2": [
        ("Youth Drop-In", "staff"),
        ("Newcomer Connections", "staff"),
        ("Community Kitchen", "staff"),
    ],
    "demo-manager": [
        ("Supported Employment", "program_manager"),
        ("Housing Stability", "program_manager"),
        ("Community Kitchen", "program_manager"),
    ],
    "demo-executive": [
        ("Supported Employment", "executive"),
        ("Housing Stability", "executive"),
        ("Youth Drop-In", "executive"),
        ("Newcomer Connections", "executive"),
        ("Community Kitchen", "executive"),
    ],
}


# Role display names for output
ROLE_DISPLAY = {
    "receptionist": "Front Desk",
    "staff": "Direct Service",
    "program_manager": "Program Manager",
    "executive": "Executive",
}

# Permission level display
LEVEL_DISPLAY = {
    ALLOW: "YES",
    PROGRAM: "SCOPED",
    GATED: "GATED",
    PER_FIELD: "PER FIELD",
    DENY: "—",
}


class Command(BaseCommand):
    help = "Validate permissions matrix and audit user role assignments."

    def add_arguments(self, parser):
        parser.add_argument(
            "--user",
            type=str,
            help="Show effective permissions for a specific username.",
        )
        parser.add_argument(
            "--all-users",
            action="store_true",
            help="Audit all active users and their effective permissions.",
        )
        parser.add_argument(
            "--demo",
            action="store_true",
            help="Validate demo user role assignments match expected configuration.",
        )

    def handle(self, *args, **options):
        """Run validation and optional user audits."""
        errors = []

        # Always validate matrix completeness
        matrix_errors = self._validate_matrix()
        errors.extend(matrix_errors)

        if options.get("demo"):
            demo_errors = self._validate_demo_users()
            errors.extend(demo_errors)

        if options.get("user"):
            self._show_user_permissions(options["user"])

        if options.get("all_users"):
            self._audit_all_users()

        if errors:
            self.stdout.write("")
            self.stdout.write(self.style.ERROR(f"[FAIL] {len(errors)} issue(s) found:"))
            for error in errors:
                self.stdout.write(self.style.ERROR(f"  - {error}"))
            return 1

        if not options.get("user") and not options.get("all_users"):
            self.stdout.write(self.style.SUCCESS("\n[OK] All validation checks passed."))
        return 0

    def _validate_matrix(self):
        """Check that all 4 roles have all permission keys defined."""
        is_valid, validation_errors = validate_permissions()
        errors = []

        if is_valid:
            total_keys = len(next(iter(PERMISSIONS.values())))
            self.stdout.write(
                self.style.SUCCESS(
                    f"[OK] Permissions matrix complete: "
                    f"4 roles x {total_keys} permission keys"
                )
            )

            # Print summary counts
            for role in ["receptionist", "staff", "program_manager", "executive"]:
                role_perms = PERMISSIONS[role]
                counts = {}
                for v in role_perms.values():
                    counts[v] = counts.get(v, 0) + 1
                parts = []
                for level in [ALLOW, PROGRAM, GATED, PER_FIELD, DENY]:
                    if counts.get(level, 0) > 0:
                        parts.append(f"{counts[level]} {LEVEL_DISPLAY[level]}")
                self.stdout.write(
                    f"  {ROLE_DISPLAY.get(role, role):20s} {', '.join(parts)}"
                )
        else:
            for e in validation_errors:
                errors.append(e)

        return errors

    def _validate_demo_users(self):
        """Check that demo users have exactly the expected role assignments."""
        from apps.auth_app.models import User
        from apps.programs.models import UserProgramRole

        self.stdout.write("")
        self.stdout.write("Demo User Role Validation")
        self.stdout.write("=" * 60)

        errors = []

        for username, expected_roles in EXPECTED_DEMO_ROLES.items():
            user = User.objects.filter(username=username, is_demo=True).first()
            if not user:
                errors.append(f"Demo user '{username}' not found")
                self.stdout.write(self.style.ERROR(f"  {username}: NOT FOUND"))
                continue

            # Get actual roles
            actual_roles = set(
                UserProgramRole.objects.filter(user=user, status="active")
                .values_list("program__name", "role")
            )
            expected_set = set(tuple(r) for r in expected_roles)

            missing = expected_set - actual_roles
            extra = actual_roles - expected_set

            if not missing and not extra:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  {username}: {len(actual_roles)} role(s) — all correct"
                    )
                )
            else:
                if missing:
                    for prog, role in sorted(missing):
                        errors.append(
                            f"{username}: missing role {ROLE_DISPLAY.get(role, role)} "
                            f"in {prog}"
                        )
                        self.stdout.write(
                            self.style.ERROR(
                                f"  {username}: MISSING {ROLE_DISPLAY.get(role, role)} "
                                f"in {prog}"
                            )
                        )
                if extra:
                    for prog, role in sorted(extra):
                        errors.append(
                            f"{username}: unexpected role {ROLE_DISPLAY.get(role, role)} "
                            f"in {prog}"
                        )
                        self.stdout.write(
                            self.style.WARNING(
                                f"  {username}: UNEXPECTED {ROLE_DISPLAY.get(role, role)} "
                                f"in {prog}"
                            )
                        )

        return errors

    def _show_user_permissions(self, username):
        """Print effective permissions for a specific user."""
        from apps.auth_app.models import User
        from apps.programs.models import UserProgramRole

        self.stdout.write("")
        user = User.objects.filter(username=username).first()
        if not user:
            self.stdout.write(self.style.ERROR(f"User '{username}' not found."))
            return

        self.stdout.write(f"Permissions for: {user.display_name} ({user.username})")
        self.stdout.write("=" * 60)

        if user.is_admin:
            self.stdout.write(
                self.style.WARNING("  [ADMIN] Has system configuration access")
            )

        roles = UserProgramRole.objects.filter(
            user=user, status="active"
        ).select_related("program").order_by("program__name")

        if not roles.exists():
            self.stdout.write("  No program roles assigned.")
            if user.is_admin:
                self.stdout.write(
                    "  Admin-only: can manage settings but cannot access "
                    "client data."
                )
            return

        # Show role assignments
        self.stdout.write("")
        self.stdout.write("  Role Assignments:")
        for role_obj in roles:
            self.stdout.write(
                f"    {role_obj.program.name:30s} "
                f"{ROLE_DISPLAY.get(role_obj.role, role_obj.role)}"
            )

        # Show effective permissions per program
        for role_obj in roles:
            self.stdout.write("")
            self.stdout.write(
                f"  In {role_obj.program.name} "
                f"({ROLE_DISPLAY.get(role_obj.role, role_obj.role)}):"
            )
            role_perms = PERMISSIONS.get(role_obj.role, {})

            # Group by category
            categories = {}
            for key, level in sorted(role_perms.items()):
                category = key.split(".")[0]
                if category not in categories:
                    categories[category] = []
                categories[category].append((key, level))

            for category, perms in sorted(categories.items()):
                allowed = [
                    (k, l) for k, l in perms if l != DENY
                ]
                if allowed:
                    for key, level in allowed:
                        label = LEVEL_DISPLAY.get(level, level)
                        desc = permission_to_plain_english(key, level)
                        self.stdout.write(f"    [{label:8s}] {desc}")

        # Show what they CAN'T do (summary)
        self.stdout.write("")
        self.stdout.write("  Key restrictions (across all programs):")
        # Use the user's highest role for a summary of denials
        from apps.auth_app.constants import ROLE_RANK
        all_roles = set(r.role for r in roles)
        highest = max(all_roles, key=lambda r: ROLE_RANK.get(r, 0))
        highest_perms = PERMISSIONS.get(highest, {})
        denied = [
            k for k, v in sorted(highest_perms.items()) if v == DENY
        ]
        if denied:
            for key in denied[:10]:  # Show first 10 to avoid overwhelming
                desc = permission_to_plain_english(key, DENY)
                self.stdout.write(f"    {desc}")
            if len(denied) > 10:
                self.stdout.write(f"    ... and {len(denied) - 10} more denied.")

    def _audit_all_users(self):
        """Print a summary table of all active users and their roles."""
        from apps.auth_app.models import User
        from apps.programs.models import UserProgramRole

        self.stdout.write("")
        self.stdout.write("All Active Users")
        self.stdout.write("=" * 60)

        users = User.objects.filter(is_active=True).order_by("username")

        for user in users:
            roles = UserProgramRole.objects.filter(
                user=user, status="active"
            ).select_related("program").order_by("program__name")

            flags = []
            if user.is_admin:
                flags.append("ADMIN")
            if user.is_demo:
                flags.append("DEMO")

            flag_str = f" [{', '.join(flags)}]" if flags else ""

            if roles.exists():
                role_strs = [
                    f"{ROLE_DISPLAY.get(r.role, r.role)} in {r.program.name}"
                    for r in roles
                ]
                self.stdout.write(
                    f"  {user.display_name} ({user.username}){flag_str}"
                )
                for rs in role_strs:
                    self.stdout.write(f"    - {rs}")
            else:
                suffix = " (system config only)" if user.is_admin else " (no access)"
                self.stdout.write(
                    f"  {user.display_name} ({user.username}){flag_str}{suffix}"
                )
