"""
Startup security check for KoNote Web.

Runs critical security checks before the application starts. Behaviour depends
on KONOTE_MODE environment variable:

- production (default): Block startup if critical checks fail
- demo: Warn loudly but allow startup for evaluation purposes

This command is called automatically by entrypoint.sh. It does NOT replace the
full security_audit command, which should still be run periodically.

Usage:
    python manage.py startup_check  # Uses KONOTE_MODE from environment
"""

import os
import sys

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run critical security checks before application startup."

    # Checks that MUST pass in production (will block startup)
    CRITICAL_CHECKS = [
        "database_urls",
        "encryption_key",
        "secret_key",
        "security_middleware",
    ]

    # Checks that generate warnings (logged but don't block)
    WARNING_CHECKS = [
        "debug_mode",
        "secure_cookies",
    ]

    def handle(self, *args, **options):
        mode = os.environ.get("KONOTE_MODE", "production").lower()

        if mode not in ("production", "demo"):
            self.stderr.write(
                f"Invalid KONOTE_MODE: '{mode}'. Must be 'production' or 'demo'."
            )
            sys.exit(1)

        self.stdout.write(f"\nKoNote Startup Security Check (mode: {mode})")
        self.stdout.write("=" * 55)

        critical_failures = []
        warnings = []

        # Run critical checks
        for check_name in self.CRITICAL_CHECKS:
            check_method = getattr(self, f"_check_{check_name}")
            passed, message = check_method()
            if passed:
                self.stdout.write(self.style.SUCCESS(f"  [PASS] {message}"))
            else:
                self.stdout.write(self.style.ERROR(f"  [FAIL] {message}"))
                critical_failures.append(message)

        # Run warning checks
        for check_name in self.WARNING_CHECKS:
            check_method = getattr(self, f"_check_{check_name}")
            passed, message = check_method()
            if passed:
                self.stdout.write(self.style.SUCCESS(f"  [PASS] {message}"))
            else:
                self.stdout.write(self.style.WARNING(f"  [WARN] {message}"))
                warnings.append(message)

        self.stdout.write("")

        # Handle results based on mode
        if mode == "demo":
            self._handle_demo_mode(critical_failures, warnings)
        else:
            self._handle_production_mode(critical_failures, warnings)

    def _handle_demo_mode(self, critical_failures, warnings):
        """In demo mode: warn loudly but allow startup."""
        all_issues = critical_failures + warnings

        if all_issues:
            self.stdout.write(self.style.WARNING(
                "\n" + "=" * 55 +
                "\n  KoNote IS RUNNING IN DEMO MODE" +
                "\n" + "=" * 55
            ))
            self.stdout.write(self.style.WARNING(
                f"\n  Security checks found {len(all_issues)} issue(s):\n"
            ))
            for issue in all_issues:
                self.stdout.write(self.style.WARNING(f"    - {issue}"))

            self.stdout.write(self.style.WARNING(
                "\n  DO NOT use this instance for real client data."
                "\n  Set KoNote_MODE=production when ready for production use."
                "\n"
            ))
            self.stdout.write("=" * 55 + "\n")
        else:
            self.stdout.write(self.style.SUCCESS(
                "All security checks passed. Demo mode active.\n"
            ))

        # Always allow startup in demo mode
        sys.exit(0)

    def _handle_production_mode(self, critical_failures, warnings):
        """In production mode: block startup if critical checks fail."""
        if critical_failures:
            self.stdout.write(self.style.ERROR(
                "\n" + "=" * 55 +
                "\n  STARTUP BLOCKED - CRITICAL SECURITY FAILURES" +
                "\n" + "=" * 55
            ))
            self.stdout.write(self.style.ERROR(
                f"\n  {len(critical_failures)} critical check(s) failed:\n"
            ))
            for failure in critical_failures:
                self.stdout.write(self.style.ERROR(f"    - {failure}"))

            self.stdout.write(self.style.ERROR(
                "\n  Fix these issues before starting KoNote in production."
                "\n  For evaluation/demo, set KoNote_MODE=demo"
                "\n"
            ))
            self.stdout.write("=" * 55 + "\n")
            sys.exit(1)

        if warnings:
            self.stdout.write(self.style.WARNING(
                f"\n  {len(warnings)} warning(s) - review recommended:\n"
            ))
            for warning in warnings:
                self.stdout.write(self.style.WARNING(f"    - {warning}"))
            self.stdout.write("")

        self.stdout.write(self.style.SUCCESS(
            "Security checks passed. Starting KoNote in production mode.\n"
        ))
        sys.exit(0)

    # -------------------------------------------------------------------------
    # Critical Checks
    # -------------------------------------------------------------------------

    def _check_database_urls(self):
        """Verify DATABASE_URL and AUDIT_DATABASE_URL are configured."""
        missing = []

        db_url = os.environ.get("DATABASE_URL", "")
        audit_url = os.environ.get("AUDIT_DATABASE_URL", "")

        if not db_url or db_url.startswith("sqlite:///dummy"):
            missing.append("DATABASE_URL")

        if not audit_url or audit_url.startswith("sqlite:///dummy"):
            missing.append("AUDIT_DATABASE_URL")

        if missing:
            hint = self._get_platform_hint()
            return False, f"Missing database configuration: {', '.join(missing)}{hint}"

        return True, "Database URLs configured"

    def _get_platform_hint(self):
        """Return platform-specific hint for configuring DATABASE_URL."""
        if os.environ.get("RAILWAY_ENVIRONMENT"):
            return " (Railway: use ${{ServiceName.DATABASE_URL}} syntax)"
        if os.environ.get("WEBSITE_SITE_NAME"):
            return " (Azure: configure in App Service > Configuration)"
        if os.environ.get("ELESTIO_VM_NAME"):
            return " (Elestio: configure in service environment variables)"
        return " (Docker: set in docker-compose.yml or -e flag)"

    def _check_encryption_key(self):
        """Verify FIELD_ENCRYPTION_KEY is set and valid."""
        key = getattr(settings, "FIELD_ENCRYPTION_KEY", None)

        if not key:
            return False, "Encryption key not configured (FIELD_ENCRYPTION_KEY)"

        # Check for known insecure default keys
        insecure_keys = [
            "ly6OqAlMm32VVf08PoPJigrLCIxGd_tW1-kfWhXxXj8=",  # dev default
        ]
        if key in insecure_keys:
            return False, "Using default encryption key (not safe for real data)"

        # Verify it's a valid Fernet key
        try:
            from cryptography.fernet import Fernet
            Fernet(key.encode() if isinstance(key, str) else key)
            return True, "Encryption key configured and valid"
        except Exception as e:
            return False, f"Invalid encryption key: {e}"

    def _check_secret_key(self):
        """Verify SECRET_KEY is not a known insecure default."""
        secret = settings.SECRET_KEY

        insecure_patterns = [
            "django-insecure-",
            "changeme",
            "insecure-dev-key",
        ]

        for pattern in insecure_patterns:
            if pattern in secret:
                return False, "Using insecure default SECRET_KEY"

        return True, "SECRET_KEY is configured"

    def _check_security_middleware(self):
        """Verify required security middleware is in the chain."""
        middleware = getattr(settings, "MIDDLEWARE", [])

        required = [
            ("konote.middleware.program_access.ProgramAccessMiddleware", "RBAC"),
            ("konote.middleware.audit.AuditMiddleware", "Audit logging"),
        ]

        missing = []
        for mw_path, name in required:
            if mw_path not in middleware:
                missing.append(name)

        if missing:
            return False, f"Missing security middleware: {', '.join(missing)}"

        return True, "Security middleware configured"

    # -------------------------------------------------------------------------
    # Warning Checks
    # -------------------------------------------------------------------------

    def _check_debug_mode(self):
        """Check if DEBUG is disabled."""
        if settings.DEBUG:
            return False, "DEBUG=True (should be False in production)"
        return True, "DEBUG mode disabled"

    def _check_secure_cookies(self):
        """Check if session cookies are configured securely."""
        issues = []

        if not getattr(settings, "SESSION_COOKIE_SECURE", False):
            issues.append("SESSION_COOKIE_SECURE=False")

        if not getattr(settings, "CSRF_COOKIE_SECURE", False):
            issues.append("CSRF_COOKIE_SECURE=False")

        if issues:
            return False, f"Insecure cookie settings: {', '.join(issues)}"

        return True, "Cookie security configured"
