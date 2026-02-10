# Document Access Feature — Security Tests

**Related to:** [document-access-plan.md](document-access-plan.md)
**Purpose:** Automated tests to catch security issues during development and deployment

---

## Overview

These tests address the security findings from the expert panel review:

| Issue | Description | Test Coverage |
|-------|-------------|---------------|
| **S1** | URL template injection | Unit tests + deployment validation |
| **S2** | Record ID not URL-encoded | Unit tests |
| **S3** | No audit logging | Unit + integration tests |
| **S4** | Google Drive cross-org disclosure | Deployment warning |

---

## 1. Unit Tests (Run on Every Commit)

Add to `tests/test_document_access_security.py`:

### URL Template Validation Tests (S1)

```python
from django.test import TestCase
from django.core.exceptions import ValidationError
from apps.admin_settings.forms import InstanceSettingsForm
from apps.clients.helpers import get_document_folder_url
from apps.clients.models import Client


class URLTemplateValidationTests(TestCase):
    """S1: Ensure malicious URL templates are rejected."""

    def test_rejects_http_urls(self):
        """HTTPS required — no plain HTTP."""
        form = InstanceSettingsForm(data={
            'document_storage_provider': 'sharepoint',
            'document_storage_url_template': 'http://evil.com/{record_id}'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('document_storage_url_template', form.errors)

    def test_rejects_javascript_urls(self):
        """Block javascript: protocol."""
        form = InstanceSettingsForm(data={
            'document_storage_provider': 'sharepoint',
            'document_storage_url_template': 'javascript:alert(1)'
        })
        self.assertFalse(form.is_valid())

    def test_rejects_data_urls(self):
        """Block data: protocol."""
        form = InstanceSettingsForm(data={
            'document_storage_provider': 'sharepoint',
            'document_storage_url_template': 'data:text/html,<script>alert(1)</script>'
        })
        self.assertFalse(form.is_valid())

    def test_rejects_unauthorized_domains(self):
        """Only allow-listed domains accepted."""
        form = InstanceSettingsForm(data={
            'document_storage_provider': 'sharepoint',
            'document_storage_url_template': 'https://evil-site.com/phish/{record_id}'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('must be one of', str(form.errors))

    def test_accepts_sharepoint_domain(self):
        """SharePoint URLs accepted."""
        form = InstanceSettingsForm(data={
            'document_storage_provider': 'sharepoint',
            'document_storage_url_template': 'https://contoso.sharepoint.com/sites/KoNote/Clients/{record_id}/'
        })
        self.assertTrue(form.is_valid())

    def test_accepts_google_drive_domain(self):
        """Google Drive URLs accepted."""
        form = InstanceSettingsForm(data={
            'document_storage_provider': 'google_drive',
            'document_storage_url_template': 'https://drive.google.com/drive/search?q={record_id}'
        })
        self.assertTrue(form.is_valid())

    def test_requires_record_id_placeholder(self):
        """Template must contain {record_id}."""
        form = InstanceSettingsForm(data={
            'document_storage_provider': 'sharepoint',
            'document_storage_url_template': 'https://contoso.sharepoint.com/sites/KoNote/Clients/'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('record_id', str(form.errors))
```

### URL Encoding Tests (S2)

```python
class URLEncodingTests(TestCase):
    """S2: Ensure record IDs are properly URL-encoded."""

    def setUp(self):
        self.client_obj = Client.objects.create(
            record_id='REC-2024-042',
            # ... other required fields
        )

    def test_normal_record_id_encoded(self):
        """Standard record ID works."""
        url = get_document_folder_url(self.client_obj)
        self.assertIn('REC-2024-042', url)

    def test_record_id_with_spaces_encoded(self):
        """Spaces are percent-encoded."""
        self.client_obj.record_id = 'REC 2024 042'
        url = get_document_folder_url(self.client_obj)
        self.assertIn('REC%202024%20042', url)
        self.assertNotIn(' ', url)

    def test_record_id_with_slashes_encoded(self):
        """Slashes can't escape path — prevents directory traversal."""
        self.client_obj.record_id = '../../../etc/passwd'
        url = get_document_folder_url(self.client_obj)
        self.assertNotIn('../', url)
        self.assertIn('%2F', url)  # Encoded slash

    def test_record_id_with_query_chars_encoded(self):
        """Query characters can't inject parameters."""
        self.client_obj.record_id = 'REC-2024-042?admin=true'
        url = get_document_folder_url(self.client_obj)
        self.assertNotIn('?admin', url)
        self.assertIn('%3F', url)  # Encoded question mark

    def test_record_id_with_hash_encoded(self):
        """Hash can't truncate URL."""
        self.client_obj.record_id = 'REC-2024-042#malicious'
        url = get_document_folder_url(self.client_obj)
        self.assertNotIn('#malicious', url)
        self.assertIn('%23', url)  # Encoded hash
```

### Audit Logging Tests (S3)

```python
class AuditLoggingTests(TestCase):
    """S3: Ensure document access is logged."""

    def setUp(self):
        self.user = User.objects.create_user('counsellor', password='test')
        self.client_obj = Client.objects.create(record_id='REC-2024-042')

    def test_document_folder_click_logged(self):
        """Clicking document folder button creates audit entry."""
        self.client.login(username='counsellor', password='test')

        # Simulate clicking the document folder button
        response = self.client.get(
            f'/clients/{self.client_obj.pk}/?open_docs=1',
            follow=False  # Don't follow redirect to external site
        )

        # Check audit log entry created
        from apps.audit.models import AuditLog
        log = AuditLog.objects.using('audit').filter(
            action='document_folder_access',
            user=self.user
        ).first()

        self.assertIsNotNone(log)
        self.assertEqual(log.record_id, 'REC-2024-042')

    def test_audit_log_excludes_pii(self):
        """Audit log contains record_id but not client name."""
        self.client.login(username='counsellor', password='test')
        self.client.get(f'/clients/{self.client_obj.pk}/?open_docs=1', follow=False)

        log = AuditLog.objects.using('audit').latest('created_at')
        log_str = str(log.details)

        self.assertIn('REC-2024-042', log_str)
        self.assertNotIn('Jane', log_str)   # Client's first name
        self.assertNotIn('Smith', log_str)  # Client's last name
```

---

## 2. Deployment Validation Command

Create `apps/admin_settings/management/commands/validate_document_storage.py`:

```python
from django.core.management.base import BaseCommand
from urllib.parse import urlparse


class Command(BaseCommand):
    help = 'Validate document storage configuration for security issues'

    def handle(self, *args, **options):
        from apps.admin_settings.models import InstanceSetting
        settings = InstanceSetting.objects.first()

        errors = []
        warnings = []

        if settings.document_storage_provider == 'none':
            self.stdout.write('Document storage not configured — skipping validation.')
            return

        template = settings.document_storage_url_template

        # Security checks
        if not template.startswith('https://'):
            errors.append('ERROR: URL template must use HTTPS')

        if '{record_id}' not in template:
            errors.append('ERROR: URL template missing {record_id} placeholder')

        parsed = urlparse(template)
        allowed_domains = ['sharepoint.com', 'drive.google.com', 'onedrive.live.com']
        if not any(parsed.netloc.endswith(d) for d in allowed_domains):
            errors.append(f'ERROR: Domain "{parsed.netloc}" not in allow-list: {allowed_domains}')

        # Warning checks
        if settings.document_storage_provider == 'google_drive':
            if 'folders/' not in template:
                warnings.append(
                    'WARNING: Google Drive search URL may show results from other Shared Drives. '
                    'Consider adding specific folder ID for better security.'
                )

        if not template.endswith('/') and 'search' not in template:
            warnings.append(
                'WARNING: SharePoint folder URLs typically end with /. '
                'Missing trailing slash may cause redirect.'
            )

        # Output results
        if errors:
            for e in errors:
                self.stdout.write(self.style.ERROR(e))
            self.stdout.write(self.style.ERROR('\n❌ Configuration FAILED security validation'))
            exit(1)

        if warnings:
            for w in warnings:
                self.stdout.write(self.style.WARNING(w))

        self.stdout.write(self.style.SUCCESS('\n✓ Configuration passed security validation'))
```

**Usage:** After configuring document storage, run:

```bash
python manage.py validate_document_storage
```

---

## 3. URL Generation Test Command

Create `apps/admin_settings/management/commands/test_document_url.py`:

```python
from django.core.management.base import BaseCommand
from apps.clients.helpers import get_document_folder_url
from urllib.parse import urlparse
import requests


class Command(BaseCommand):
    help = 'Test document folder URL generation with a sample record ID'

    def add_arguments(self, parser):
        parser.add_argument(
            '--record-id',
            default='REC-2024-001',
            help='Sample record ID to test'
        )
        parser.add_argument(
            '--check-reachable',
            action='store_true',
            help='Actually ping the URL (requires network access)'
        )

    def handle(self, *args, **options):
        # Create a mock client object
        class MockClient:
            def __init__(self, record_id):
                self.record_id = record_id

        mock_client = MockClient(options['record_id'])
        url = get_document_folder_url(mock_client)

        if not url:
            self.stdout.write(self.style.WARNING('Document storage not configured'))
            return

        self.stdout.write(f'Generated URL: {url}')

        # Validate URL structure
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            self.stdout.write(self.style.ERROR('ERROR: Malformed URL'))
            exit(1)

        # Check for unencoded dangerous characters
        dangerous_chars = [' ', '<', '>', '"', "'", '\\']
        for char in dangerous_chars:
            if char in url:
                self.stdout.write(
                    self.style.ERROR(f'ERROR: URL contains unencoded character: {repr(char)}')
                )
                exit(1)

        # Optional: check if URL is reachable
        if options['check_reachable']:
            try:
                response = requests.head(url, allow_redirects=False, timeout=5)
                self.stdout.write(f'Response status: {response.status_code}')
                if response.status_code in [200, 301, 302, 401, 403]:
                    self.stdout.write(
                        self.style.SUCCESS('✓ URL is reachable (auth may be required)')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'Unexpected status code: {response.status_code}')
                    )
            except requests.RequestException as e:
                self.stdout.write(self.style.ERROR(f'Could not reach URL: {e}'))

        self.stdout.write(self.style.SUCCESS('\n✓ URL generation test passed'))
```

**Usage:**

```bash
# Basic test
python manage.py test_document_url

# Test with specific record ID
python manage.py test_document_url --record-id "REC-2024-042"

# Test and verify URL is reachable
python manage.py test_document_url --check-reachable
```

---

## 4. Security Monitoring Tests

Add to `tests/test_security_monitoring.py` for periodic checks:

```python
class DocumentAccessSecurityMonitoringTests(TestCase):
    """Run these periodically to catch configuration drift."""

    def test_domain_allowlist_not_expanded(self):
        """Ensure allow-list hasn't been weakened."""
        from apps.admin_settings.forms import ALLOWED_DOCUMENT_DOMAINS

        expected = {'sharepoint.com', 'drive.google.com', 'onedrive.live.com'}
        self.assertEqual(set(ALLOWED_DOCUMENT_DOMAINS), expected)

    def test_audit_logging_enabled(self):
        """Ensure audit logging middleware is active."""
        from django.conf import settings
        self.assertIn(
            'konote.middleware.audit.AuditMiddleware',
            settings.MIDDLEWARE
        )

    def test_no_wildcard_domains(self):
        """Ensure no one added wildcard patterns to allow-list."""
        from apps.admin_settings.forms import ALLOWED_DOCUMENT_DOMAINS

        for domain in ALLOWED_DOCUMENT_DOMAINS:
            self.assertNotIn('*', domain)
            self.assertFalse(domain.startswith('.'))
```

---

## Test Coverage Summary

| Security Issue | Test Type | When Run | File |
|----------------|-----------|----------|------|
| **S1** URL injection | Unit tests | Every commit | `tests/test_document_access_security.py` |
| **S1** Domain allow-list | Unit + deployment | Commit + config change | Same + `validate_document_storage` |
| **S2** URL encoding | Unit tests | Every commit | `tests/test_document_access_security.py` |
| **S3** Audit logging | Unit tests | Every commit | `tests/test_document_access_security.py` |
| **S4** Google Drive cross-org | Deployment warning | Config change | `validate_document_storage` |
| URL structure | Deployment | Config change | `test_document_url` |
| Configuration drift | Monitoring | Periodic/CI | `tests/test_security_monitoring.py` |

---

## Deployment Checklist

When deploying with document storage configured:

```bash
# 1. Run security validation
python manage.py validate_document_storage

# 2. Test URL generation
python manage.py test_document_url --record-id "REC-2024-001"

# 3. (Optional) Verify URL is reachable
python manage.py test_document_url --record-id "REC-2024-001" --check-reachable

# 4. Run full test suite
python manage.py test tests.test_document_access_security
```

---

## Adding to CI Pipeline

Add to your CI configuration (e.g., GitHub Actions):

```yaml
- name: Run security tests
  run: |
    python manage.py test tests.test_document_access_security
    python manage.py test tests.test_security_monitoring
```

For staging/production deployments:

```yaml
- name: Validate document storage config
  run: python manage.py validate_document_storage
```
