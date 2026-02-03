"""
Test document folder URL generation.

This command tests that document folder URLs are generated correctly and safely.
Useful for debugging URL configuration after setting up document storage.

Usage:
    python manage.py test_document_url
    python manage.py test_document_url --record-id "REC-2024-042"
    python manage.py test_document_url --check-reachable
"""

from urllib.parse import quote, urlparse

from django.core.management.base import BaseCommand

from apps.admin_settings.models import InstanceSetting


class Command(BaseCommand):
    help = "Test document folder URL generation with a sample record ID."

    def add_arguments(self, parser):
        parser.add_argument(
            "--record-id",
            default="REC-2024-001",
            help="Sample record ID to test (default: REC-2024-001)",
        )
        parser.add_argument(
            "--check-reachable",
            action="store_true",
            help="Actually ping the URL to verify reachability (requires network access)",
        )

    def handle(self, *args, **options):
        record_id = options["record_id"]
        check_reachable = options["check_reachable"]

        # Get document storage configuration
        provider = InstanceSetting.get("document_storage_provider", "none")
        template = InstanceSetting.get("document_storage_url_template", "")

        if provider == "none" or not template:
            self.stdout.write(
                self.style.WARNING("Document storage not configured — nothing to test.")
            )
            self.stdout.write(
                "Configure document_storage_provider and document_storage_url_template "
                "in Instance Settings to enable this feature."
            )
            return

        self.stdout.write(f"Provider: {provider}")
        self.stdout.write(f"Template: {template}")
        self.stdout.write(f"Record ID: {record_id}")
        self.stdout.write("")

        # Generate URL with proper encoding
        encoded_record_id = quote(record_id, safe="")
        url = template.replace("{record_id}", encoded_record_id)

        self.stdout.write(f"Generated URL: {url}")
        self.stdout.write("")

        # Validate URL structure
        errors = []
        warnings = []

        parsed = urlparse(url)
        if not parsed.scheme:
            errors.append("URL has no scheme (missing https://)")
        elif parsed.scheme != "https":
            errors.append(f"URL uses {parsed.scheme}:// instead of https://")

        if not parsed.netloc:
            errors.append("URL has no host/domain")

        # Check for unencoded dangerous characters
        dangerous_chars = [" ", "<", ">", '"', "'", "\\"]
        for char in dangerous_chars:
            if char in url:
                errors.append(f"URL contains unencoded character: {repr(char)}")

        # Check for directory traversal
        if "../" in url or "..\\" in url:
            errors.append("URL contains directory traversal pattern (../)")

        # Check for query injection
        if record_id in url and "?" in record_id:
            # The ? should be encoded
            if "?" + record_id.split("?")[1] in url:
                errors.append("Query characters not properly encoded")

        # Domain validation
        allowed_domains = ["sharepoint.com", "drive.google.com", "onedrive.live.com"]
        if parsed.netloc:
            domain_ok = any(parsed.netloc.endswith(d) for d in allowed_domains)
            if not domain_ok:
                warnings.append(
                    f"Domain '{parsed.netloc}' is not in the standard allowlist: {allowed_domains}"
                )

        # Output validation results
        if errors:
            self.stdout.write(self.style.ERROR("Validation errors:"))
            for e in errors:
                self.stdout.write(self.style.ERROR(f"  ✗ {e}"))
            exit(1)

        if warnings:
            self.stdout.write(self.style.WARNING("Warnings:"))
            for w in warnings:
                self.stdout.write(self.style.WARNING(f"  ⚠ {w}"))

        self.stdout.write(self.style.SUCCESS("✓ URL structure is valid"))

        # Optional: check reachability
        if check_reachable:
            self._check_reachability(url)

    def _check_reachability(self, url):
        """Attempt to reach the URL and report status."""
        self.stdout.write("")
        self.stdout.write("Checking reachability...")

        try:
            import requests
        except ImportError:
            self.stdout.write(
                self.style.WARNING(
                    "requests library not installed — cannot check reachability. "
                    "Install with: pip install requests"
                )
            )
            return

        try:
            # Use HEAD request to avoid downloading content
            # Short timeout, don't follow redirects
            response = requests.head(url, allow_redirects=False, timeout=10)

            self.stdout.write(f"Response status: {response.status_code}")

            if response.status_code in [200, 301, 302]:
                self.stdout.write(
                    self.style.SUCCESS("✓ URL is reachable (authentication may be required)")
                )
            elif response.status_code in [401, 403]:
                self.stdout.write(
                    self.style.SUCCESS(
                        "✓ URL is reachable but requires authentication (expected)"
                    )
                )
            elif response.status_code == 404:
                self.stdout.write(
                    self.style.WARNING(
                        "⚠ URL returns 404 — folder may not exist yet for this record ID"
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"⚠ Unexpected status code: {response.status_code}")
                )

        except requests.exceptions.Timeout:
            self.stdout.write(self.style.WARNING("⚠ Request timed out"))
        except requests.exceptions.ConnectionError as e:
            self.stdout.write(self.style.ERROR(f"✗ Connection error: {e}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Error: {e}"))
