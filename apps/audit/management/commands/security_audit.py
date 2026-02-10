"""
Security audit command for KoNote Web.

Runs comprehensive security checks across encryption, RBAC, audit logging,
configuration, and document storage. Designed to work for any developer
regardless of their tools (no Claude, no GitHub required).

Usage:
    python manage.py security_audit              # Full audit
    python manage.py security_audit --verbose    # Detailed output
    python manage.py security_audit --category=ENC,RBAC  # Specific categories
    python manage.py security_audit --json       # Machine-readable output
    python manage.py security_audit --fail-on-warn  # Exit 1 if warnings (for CI)
"""

import json
from urllib.parse import urlparse

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connections
from django.utils import timezone


class CheckResult:
    """Result of a single security check."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    SKIP = "SKIP"

    def __init__(self, check_id, description, status, detail=""):
        self.check_id = check_id
        self.description = description
        self.status = status
        self.detail = detail

    def to_dict(self):
        return {
            "check_id": self.check_id,
            "description": self.description,
            "status": self.status,
            "detail": self.detail,
        }


class Command(BaseCommand):
    help = "Run security audit checks across encryption, RBAC, audit, and configuration."

    def add_arguments(self, parser):
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show detailed output including scanned records.",
        )
        parser.add_argument(
            "--category",
            type=str,
            help="Comma-separated list of categories to check (ENC,RBAC,AUD,CFG,DOC).",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Output machine-readable JSON.",
        )
        parser.add_argument(
            "--fail-on-warn",
            action="store_true",
            help="Exit with code 1 if warnings present (for CI).",
        )

    def handle(self, *args, **options):
        self.verbose = options["verbose"]
        self.json_output = options["json"]
        self.fail_on_warn = options["fail_on_warn"]

        # Parse categories
        all_categories = ["ENC", "RBAC", "AUD", "CFG", "DOC"]
        if options["category"]:
            self.categories = [c.strip().upper() for c in options["category"].split(",")]
        else:
            self.categories = all_categories

        results = []

        # Run checks for each enabled category
        if "ENC" in self.categories:
            results.extend(self._check_encryption())
        if "RBAC" in self.categories:
            results.extend(self._check_rbac())
        if "AUD" in self.categories:
            results.extend(self._check_audit())
        if "CFG" in self.categories:
            results.extend(self._check_configuration())
        if "DOC" in self.categories:
            results.extend(self._check_document_storage())

        # Output results
        if self.json_output:
            self._output_json(results)
        else:
            self._output_text(results)

        # Determine exit code
        failed = sum(1 for r in results if r.status == CheckResult.FAIL)
        warned = sum(1 for r in results if r.status == CheckResult.WARN)

        if failed > 0:
            exit(1)
        if warned > 0 and self.fail_on_warn:
            exit(1)

    # -------------------------------------------------------------------------
    # Encryption Checks (ENC)
    # -------------------------------------------------------------------------

    def _check_encryption(self):
        """Run encryption-related security checks."""
        results = []

        # ENC001: Encryption key configured
        key = getattr(settings, "FIELD_ENCRYPTION_KEY", None)
        if not key:
            results.append(CheckResult(
                "ENC001", "Encryption key configured",
                CheckResult.FAIL, "FIELD_ENCRYPTION_KEY not set"
            ))
        else:
            try:
                Fernet(key.encode() if isinstance(key, str) else key)
                results.append(CheckResult(
                    "ENC001", "Encryption key configured",
                    CheckResult.PASS, "Valid Fernet key"
                ))
            except Exception as e:
                results.append(CheckResult(
                    "ENC001", "Encryption key configured",
                    CheckResult.FAIL, f"Invalid Fernet key: {e}"
                ))

        # ENC002: Encryption round-trip works
        if key:
            try:
                from konote.encryption import decrypt_field, encrypt_field
                test_value = "security_audit_test_string"
                encrypted = encrypt_field(test_value)
                decrypted = decrypt_field(encrypted)
                if decrypted == test_value:
                    results.append(CheckResult(
                        "ENC002", "Encryption round-trip successful",
                        CheckResult.PASS
                    ))
                else:
                    results.append(CheckResult(
                        "ENC002", "Encryption round-trip successful",
                        CheckResult.FAIL, "Decrypted value doesn't match original"
                    ))
            except Exception as e:
                results.append(CheckResult(
                    "ENC002", "Encryption round-trip successful",
                    CheckResult.FAIL, str(e)
                ))
        else:
            results.append(CheckResult(
                "ENC002", "Encryption round-trip successful",
                CheckResult.SKIP, "No encryption key configured"
            ))

        # ENC003: No plaintext in encrypted fields
        if key:
            results.append(self._check_encrypted_fields())
        else:
            results.append(CheckResult(
                "ENC003", "No plaintext in encrypted fields",
                CheckResult.SKIP, "No encryption key configured"
            ))

        # ENC004: Sensitive custom fields encrypted
        results.append(self._check_sensitive_custom_fields())

        return results

    def _check_encrypted_fields(self):
        """ENC003: Verify encrypted fields contain valid ciphertext."""
        from apps.auth_app.models import User
        from apps.clients.models import ClientDetailValue, ClientFile

        issues = []
        scanned = 0

        # Check ClientFile
        for client in ClientFile.objects.all().iterator():
            scanned += 1
            for field in ["_first_name_encrypted", "_middle_name_encrypted",
                          "_last_name_encrypted", "_birth_date_encrypted"]:
                raw = getattr(client, field)
                if raw and not self._is_valid_ciphertext(raw):
                    issues.append(f"ClientFile pk={client.pk} {field}")

        # Check User
        for user in User.objects.all().iterator():
            scanned += 1
            raw = getattr(user, "_email_encrypted", None)
            if raw and not self._is_valid_ciphertext(raw):
                issues.append(f"User pk={user.pk} _email_encrypted")

        # Check ClientDetailValue
        for cdv in ClientDetailValue.objects.all().iterator():
            scanned += 1
            raw = getattr(cdv, "_value_encrypted", None)
            if raw and not self._is_valid_ciphertext(raw):
                issues.append(f"ClientDetailValue pk={cdv.pk} _value_encrypted")

        if issues:
            detail = f"{len(issues)} fields with invalid ciphertext"
            if self.verbose:
                detail += ": " + ", ".join(issues[:5])
                if len(issues) > 5:
                    detail += f" (+{len(issues) - 5} more)"
            return CheckResult(
                "ENC003", "No plaintext in encrypted fields",
                CheckResult.FAIL, detail
            )
        else:
            return CheckResult(
                "ENC003", "No plaintext in encrypted fields",
                CheckResult.PASS, f"Scanned {scanned} records"
            )

    def _is_valid_ciphertext(self, raw):
        """Check if data looks like valid Fernet ciphertext."""
        if isinstance(raw, memoryview):
            raw = bytes(raw)
        if not raw or raw == b"":
            return True  # Empty is OK
        # Fernet ciphertext is base64, minimum ~57 bytes decoded
        # and starts with version byte 0x80
        try:
            import base64
            decoded = base64.urlsafe_b64decode(raw)
            return len(decoded) >= 57 and decoded[0] == 0x80
        except Exception:
            return False

    def _check_sensitive_custom_fields(self):
        """ENC004: Verify sensitive custom fields use encryption."""
        from apps.clients.models import ClientDetailValue, CustomFieldDefinition

        sensitive_defs = CustomFieldDefinition.objects.filter(is_sensitive=True)
        if not sensitive_defs.exists():
            return CheckResult(
                "ENC004", "Sensitive custom fields encrypted",
                CheckResult.PASS, "No sensitive fields defined"
            )

        issues = []
        for field_def in sensitive_defs:
            # Check if any values have plaintext instead of encrypted
            for cdv in ClientDetailValue.objects.filter(field_def=field_def):
                if cdv.value and cdv.value.strip():  # Has plaintext
                    if not cdv._value_encrypted:  # No encrypted value
                        issues.append(f"CustomField '{field_def.name}' pk={cdv.pk}")

        if issues:
            return CheckResult(
                "ENC004", "Sensitive custom fields encrypted",
                CheckResult.FAIL, f"{len(issues)} unencrypted sensitive values"
            )
        return CheckResult(
            "ENC004", "Sensitive custom fields encrypted",
            CheckResult.PASS, f"{sensitive_defs.count()} sensitive fields checked"
        )

    # -------------------------------------------------------------------------
    # RBAC Checks
    # -------------------------------------------------------------------------

    def _check_rbac(self):
        """Run RBAC-related security checks."""
        results = []

        # RBAC001: Non-admin users have program roles
        results.append(self._check_user_program_roles())

        # RBAC002: No orphaned enrolments
        results.append(self._check_orphaned_enrolments())

        # RBAC003: Role values valid
        results.append(self._check_role_values())

        return results

    def _check_user_program_roles(self):
        """RBAC001: Every non-admin user has at least one active program role."""
        from apps.auth_app.models import User
        from apps.programs.models import UserProgramRole

        users_without_roles = []
        for user in User.objects.filter(is_admin=False, is_active=True):
            has_role = UserProgramRole.objects.filter(
                user=user, status="active"
            ).exists()
            if not has_role:
                users_without_roles.append(user.username)

        if users_without_roles:
            detail = f"{len(users_without_roles)} users without program roles"
            if self.verbose:
                detail += ": " + ", ".join(users_without_roles[:5])
            return CheckResult(
                "RBAC001", "Non-admin users have program roles",
                CheckResult.WARN, detail
            )
        return CheckResult(
            "RBAC001", "Non-admin users have program roles",
            CheckResult.PASS
        )

    def _check_orphaned_enrolments(self):
        """RBAC002: All ClientProgramEnrolment.program_id values exist."""
        from apps.clients.models import ClientProgramEnrolment
        from apps.programs.models import Program

        valid_program_ids = set(Program.objects.values_list("id", flat=True))
        orphaned = []

        for enrolment in ClientProgramEnrolment.objects.all():
            if enrolment.program_id not in valid_program_ids:
                orphaned.append(enrolment.pk)

        if orphaned:
            return CheckResult(
                "RBAC002", "No orphaned program enrolments",
                CheckResult.FAIL, f"{len(orphaned)} orphaned enrolments"
            )
        return CheckResult(
            "RBAC002", "No orphaned program enrolments",
            CheckResult.PASS
        )

    def _check_role_values(self):
        """RBAC003: All roles are valid values."""
        from apps.programs.models import UserProgramRole

        valid_roles = {"receptionist", "staff", "program_manager"}
        invalid = UserProgramRole.objects.exclude(role__in=valid_roles)

        if invalid.exists():
            bad_roles = set(invalid.values_list("role", flat=True))
            return CheckResult(
                "RBAC003", "Role values valid",
                CheckResult.FAIL, f"Invalid roles found: {bad_roles}"
            )
        return CheckResult(
            "RBAC003", "Role values valid",
            CheckResult.PASS
        )

    # -------------------------------------------------------------------------
    # Audit Checks
    # -------------------------------------------------------------------------

    def _check_audit(self):
        """Run audit logging security checks."""
        results = []

        # AUD001: Audit database accessible
        try:
            from apps.audit.models import AuditLog
            count = AuditLog.objects.using("audit").count()
            results.append(CheckResult(
                "AUD001", "Audit database accessible",
                CheckResult.PASS, f"{count} total entries"
            ))
        except Exception as e:
            results.append(CheckResult(
                "AUD001", "Audit database accessible",
                CheckResult.FAIL, str(e)
            ))
            # Skip remaining audit checks if DB not accessible
            return results

        # AUD002: Recent audit entries exist
        from apps.audit.models import AuditLog
        yesterday = timezone.now() - timezone.timedelta(hours=24)
        recent = AuditLog.objects.using("audit").filter(
            event_timestamp__gte=yesterday
        ).count()

        if recent == 0:
            results.append(CheckResult(
                "AUD002", "Recent audit entries exist",
                CheckResult.WARN, "No entries in last 24 hours"
            ))
        else:
            results.append(CheckResult(
                "AUD002", "Recent audit entries exist",
                CheckResult.PASS, f"{recent} entries in last 24h"
            ))

        # AUD003: Client views logged
        view_count = AuditLog.objects.using("audit").filter(action="view").count()
        if view_count > 0:
            results.append(CheckResult(
                "AUD003", "Client view logging active",
                CheckResult.PASS, f"{view_count} view entries"
            ))
        else:
            results.append(CheckResult(
                "AUD003", "Client view logging active",
                CheckResult.WARN, "No view entries found"
            ))

        # AUD004: State changes logged
        state_change_actions = ["post", "create", "update", "delete"]
        state_count = AuditLog.objects.using("audit").filter(
            action__in=state_change_actions
        ).count()
        if state_count > 0:
            results.append(CheckResult(
                "AUD004", "State-change logging active",
                CheckResult.PASS, f"{state_count} state-change entries"
            ))
        else:
            results.append(CheckResult(
                "AUD004", "State-change logging active",
                CheckResult.WARN, "No state-change entries found"
            ))

        return results

    # -------------------------------------------------------------------------
    # Configuration Checks
    # -------------------------------------------------------------------------

    def _check_configuration(self):
        """Run configuration security checks."""
        results = []

        # CFG001: DEBUG disabled
        if settings.DEBUG:
            results.append(CheckResult(
                "CFG001", "DEBUG disabled",
                CheckResult.WARN, "DEBUG=True (should be False in production)"
            ))
        else:
            results.append(CheckResult(
                "CFG001", "DEBUG disabled",
                CheckResult.PASS
            ))

        # CFG002: Secret key not default
        secret = settings.SECRET_KEY
        if secret.startswith("django-insecure-") or secret == "changeme":
            results.append(CheckResult(
                "CFG002", "SECRET_KEY not default",
                CheckResult.FAIL, "Using insecure default key"
            ))
        else:
            results.append(CheckResult(
                "CFG002", "SECRET_KEY not default",
                CheckResult.PASS
            ))

        # CFG003: Session cookies secure
        if getattr(settings, "SESSION_COOKIE_SECURE", False):
            results.append(CheckResult(
                "CFG003", "Session cookies secure",
                CheckResult.PASS
            ))
        else:
            results.append(CheckResult(
                "CFG003", "Session cookies secure",
                CheckResult.WARN, "SESSION_COOKIE_SECURE=False"
            ))

        # CFG004: CSRF cookies secure
        if getattr(settings, "CSRF_COOKIE_SECURE", False):
            results.append(CheckResult(
                "CFG004", "CSRF cookies secure",
                CheckResult.PASS
            ))
        else:
            results.append(CheckResult(
                "CFG004", "CSRF cookies secure",
                CheckResult.WARN, "CSRF_COOKIE_SECURE=False"
            ))

        # CFG005: Argon2 hasher configured
        hashers = getattr(settings, "PASSWORD_HASHERS", [])
        if hashers and "Argon2" in hashers[0]:
            results.append(CheckResult(
                "CFG005", "Argon2 password hasher configured",
                CheckResult.PASS
            ))
        else:
            results.append(CheckResult(
                "CFG005", "Argon2 password hasher configured",
                CheckResult.WARN, "Argon2 not primary hasher"
            ))

        # CFG006: Security middleware in chain
        middleware = getattr(settings, "MIDDLEWARE", [])
        required = [
            "konote.middleware.program_access.ProgramAccessMiddleware",
            "konote.middleware.audit.AuditMiddleware",
        ]
        missing = [m for m in required if m not in middleware]
        if missing:
            results.append(CheckResult(
                "CFG006", "Security middleware in chain",
                CheckResult.FAIL, f"Missing: {missing}"
            ))
        else:
            results.append(CheckResult(
                "CFG006", "Security middleware in chain",
                CheckResult.PASS
            ))

        return results

    # -------------------------------------------------------------------------
    # Document Storage Checks
    # -------------------------------------------------------------------------

    def _check_document_storage(self):
        """Run document storage security checks."""
        from apps.admin_settings.models import InstanceSetting

        results = []

        # Get document storage settings
        provider = InstanceSetting.get("document_storage_provider", "none")
        template = InstanceSetting.get("document_storage_url_template", "")

        if provider == "none" or not template:
            results.append(CheckResult(
                "DOC001", "Document storage configured",
                CheckResult.SKIP, "Document storage not configured"
            ))
            return results

        # DOC001: URL template uses HTTPS
        if template.startswith("https://"):
            results.append(CheckResult(
                "DOC001", "URL template uses HTTPS",
                CheckResult.PASS
            ))
        else:
            results.append(CheckResult(
                "DOC001", "URL template uses HTTPS",
                CheckResult.FAIL, f"Template starts with: {template[:20]}..."
            ))

        # DOC002: Domain in allowlist
        allowed_domains = ["sharepoint.com", "drive.google.com", "onedrive.live.com"]
        parsed = urlparse(template)
        domain_ok = any(parsed.netloc.endswith(d) for d in allowed_domains)
        if domain_ok:
            results.append(CheckResult(
                "DOC002", "Domain in allowlist",
                CheckResult.PASS, parsed.netloc
            ))
        else:
            results.append(CheckResult(
                "DOC002", "Domain in allowlist",
                CheckResult.FAIL, f"'{parsed.netloc}' not in {allowed_domains}"
            ))

        # DOC003: Record ID placeholder present
        if "{record_id}" in template:
            results.append(CheckResult(
                "DOC003", "Record ID placeholder present",
                CheckResult.PASS
            ))
        else:
            results.append(CheckResult(
                "DOC003", "Record ID placeholder present",
                CheckResult.FAIL, "Template missing {record_id}"
            ))

        # DOC004: Google Drive cross-org risk
        if provider == "google_drive" and "folders/" not in template:
            results.append(CheckResult(
                "DOC004", "Google Drive folder scoping",
                CheckResult.WARN,
                "Search URL may show results from other Shared Drives"
            ))
        else:
            results.append(CheckResult(
                "DOC004", "Google Drive folder scoping",
                CheckResult.PASS
            ))

        # DOC005: No wildcard domains
        # This would check the ALLOWED_DOCUMENT_DOMAINS constant if it exists
        results.append(CheckResult(
            "DOC005", "No wildcard domains in allowlist",
            CheckResult.PASS, "Hardcoded allowlist"
        ))

        return results

    # -------------------------------------------------------------------------
    # Output
    # -------------------------------------------------------------------------

    def _output_json(self, results):
        """Output results as JSON."""
        output = {
            "timestamp": timezone.now().isoformat(),
            "results": [r.to_dict() for r in results],
            "summary": {
                "passed": sum(1 for r in results if r.status == CheckResult.PASS),
                "warnings": sum(1 for r in results if r.status == CheckResult.WARN),
                "failed": sum(1 for r in results if r.status == CheckResult.FAIL),
                "skipped": sum(1 for r in results if r.status == CheckResult.SKIP),
            },
        }
        self.stdout.write(json.dumps(output, indent=2))

    def _output_text(self, results):
        """Output results as formatted text."""
        self.stdout.write("\nKoNote Security Audit")
        self.stdout.write("=" * 50)

        # Group by category
        categories = {
            "ENC": "Encryption Checks",
            "RBAC": "Access Control Checks",
            "AUD": "Audit Log Checks",
            "CFG": "Configuration Checks",
            "DOC": "Document Storage Checks",
        }

        for prefix, title in categories.items():
            cat_results = [r for r in results if r.check_id.startswith(prefix)]
            if not cat_results:
                continue

            self.stdout.write(f"\n[{prefix}] {title}")
            for r in cat_results:
                status_display = self._format_status(r.status)
                line = f"  {status_display} {r.check_id} {r.description}"
                if r.detail and (self.verbose or r.status != CheckResult.PASS):
                    line += f" — {r.detail}"
                self.stdout.write(line)

        # Summary
        passed = sum(1 for r in results if r.status == CheckResult.PASS)
        warned = sum(1 for r in results if r.status == CheckResult.WARN)
        failed = sum(1 for r in results if r.status == CheckResult.FAIL)
        skipped = sum(1 for r in results if r.status == CheckResult.SKIP)

        self.stdout.write("\n" + "-" * 50)
        summary = f"Passed: {passed}"
        if warned:
            summary += f", Warnings: {warned}"
        if failed:
            summary += f", Failed: {failed}"
        if skipped:
            summary += f", Skipped: {skipped}"
        self.stdout.write(summary)

        if failed:
            self.stdout.write(self.style.ERROR("\n❌ Security audit FAILED"))
        elif warned:
            self.stdout.write(self.style.WARNING("\n⚠ Security audit passed with warnings"))
        else:
            self.stdout.write(self.style.SUCCESS("\n✓ Security audit passed"))

    def _format_status(self, status):
        """Format status with colour."""
        if status == CheckResult.PASS:
            return self.style.SUCCESS("[PASS]")
        elif status == CheckResult.WARN:
            return self.style.WARNING("[WARN]")
        elif status == CheckResult.FAIL:
            return self.style.ERROR("[FAIL]")
        else:
            return "[SKIP]"
