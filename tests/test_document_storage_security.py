"""Security tests for the document storage feature.

Covers URL template validation (S1), URL encoding (S2),
and domain allowlist enforcement. See tasks/document-access-security-tests.md.

Run with:
    pytest tests/test_document_storage_security.py -v
"""
from cryptography.fernet import Fernet
from django.core.cache import cache
from django.test import TestCase, override_settings

from apps.admin_settings.forms import ALLOWED_DOCUMENT_DOMAINS, InstanceSettingsForm
from apps.admin_settings.models import InstanceSetting
from apps.auth_app.models import User
from apps.clients.models import ClientFile
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


def _base_form_data(**overrides):
    """Build minimal valid form data for InstanceSettingsForm."""
    data = {
        "access_tier": "1",
        "product_name": "TestApp",
        "date_format": "Y-m-d",
        "session_timeout_minutes": "30",
        "document_storage_provider": "none",
        "document_storage_url_template": "",
        "meeting_time_start": "9",
        "meeting_time_end": "17",
        "meeting_time_step": "30",
    }
    data.update(overrides)
    return data


# ─── S1: URL Template Validation ─────────────────────────────────────────


class URLTemplateValidationTests(TestCase):
    """S1: Ensure malicious or invalid URL templates are rejected."""

    def test_rejects_http_urls(self):
        """HTTPS required — plain HTTP rejected."""
        form = InstanceSettingsForm(data=_base_form_data(
            document_storage_provider="sharepoint",
            document_storage_url_template="http://evil.com/{record_id}",
        ))
        self.assertFalse(form.is_valid())
        self.assertIn("document_storage_url_template", form.errors)

    def test_rejects_javascript_urls(self):
        """Block javascript: protocol."""
        form = InstanceSettingsForm(data=_base_form_data(
            document_storage_provider="sharepoint",
            document_storage_url_template="javascript:alert(1)",
        ))
        self.assertFalse(form.is_valid())
        self.assertIn("document_storage_url_template", form.errors)

    def test_rejects_data_urls(self):
        """Block data: protocol."""
        form = InstanceSettingsForm(data=_base_form_data(
            document_storage_provider="sharepoint",
            document_storage_url_template="data:text/html,<script>alert(1)</script>",
        ))
        self.assertFalse(form.is_valid())
        self.assertIn("document_storage_url_template", form.errors)

    def test_rejects_unauthorized_domains(self):
        """Only allow-listed domains accepted."""
        form = InstanceSettingsForm(data=_base_form_data(
            document_storage_provider="sharepoint",
            document_storage_url_template="https://evil-site.com/phish/{record_id}",
        ))
        self.assertFalse(form.is_valid())
        errors_str = str(form.errors)
        self.assertIn("must be one of", errors_str)

    def test_accepts_sharepoint_domain(self):
        """SharePoint URLs accepted."""
        form = InstanceSettingsForm(data=_base_form_data(
            document_storage_provider="sharepoint",
            document_storage_url_template=(
                "https://contoso.sharepoint.com/sites/KoNote/Clients/{record_id}/"
            ),
        ))
        self.assertTrue(form.is_valid(), form.errors)

    def test_accepts_google_drive_domain(self):
        """Google Drive URLs accepted."""
        form = InstanceSettingsForm(data=_base_form_data(
            document_storage_provider="google_drive",
            document_storage_url_template=(
                "https://drive.google.com/drive/search?q={record_id}"
            ),
        ))
        self.assertTrue(form.is_valid(), form.errors)

    def test_accepts_onedrive_domain(self):
        """OneDrive URLs accepted."""
        form = InstanceSettingsForm(data=_base_form_data(
            document_storage_provider="sharepoint",
            document_storage_url_template=(
                "https://onedrive.live.com/folder/{record_id}/"
            ),
        ))
        self.assertTrue(form.is_valid(), form.errors)

    def test_requires_record_id_placeholder(self):
        """Template must contain {record_id}."""
        form = InstanceSettingsForm(data=_base_form_data(
            document_storage_provider="sharepoint",
            document_storage_url_template=(
                "https://contoso.sharepoint.com/sites/KoNote/Clients/"
            ),
        ))
        self.assertFalse(form.is_valid())
        errors_str = str(form.errors)
        self.assertIn("record_id", errors_str)

    def test_requires_template_when_provider_selected(self):
        """URL template is required when provider is not 'none'."""
        form = InstanceSettingsForm(data=_base_form_data(
            document_storage_provider="sharepoint",
            document_storage_url_template="",
        ))
        self.assertFalse(form.is_valid())
        self.assertIn("document_storage_url_template", form.errors)

    def test_no_validation_when_provider_is_none(self):
        """No template validation when provider is 'none'."""
        form = InstanceSettingsForm(data=_base_form_data(
            document_storage_provider="none",
            document_storage_url_template="",
        ))
        self.assertTrue(form.is_valid(), form.errors)

    def test_rejects_subdomain_spoofing(self):
        """Reject domains like sharepoint.com.evil.com."""
        form = InstanceSettingsForm(data=_base_form_data(
            document_storage_provider="sharepoint",
            document_storage_url_template=(
                "https://sharepoint.com.evil.com/sites/{record_id}/"
            ),
        ))
        self.assertFalse(form.is_valid())
        self.assertIn("document_storage_url_template", form.errors)


# ─── S2: URL Encoding ─────────────────────────────────────────────────────


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class URLEncodingTests(TestCase):
    """S2: Ensure record IDs are properly URL-encoded."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        cache.clear()
        InstanceSetting.objects.create(
            setting_key="document_storage_provider", setting_value="sharepoint"
        )
        InstanceSetting.objects.create(
            setting_key="document_storage_url_template",
            setting_value="https://contoso.sharepoint.com/sites/konote/Clients/{record_id}/",
        )

    def _make_client(self, record_id):
        client = ClientFile.objects.create(record_id=record_id, status="active")
        client.first_name = "Test"
        client.last_name = "User"
        client.save()
        return client

    def test_normal_record_id(self):
        """Standard record ID works unchanged."""
        from apps.clients.helpers import get_document_folder_url

        client = self._make_client("REC-2024-042")
        url = get_document_folder_url(client)
        self.assertIn("REC-2024-042", url)

    def test_record_id_with_spaces_encoded(self):
        """Spaces are percent-encoded."""
        from apps.clients.helpers import get_document_folder_url

        client = self._make_client("REC 2024 042")
        url = get_document_folder_url(client)
        self.assertIn("REC%202024%20042", url)
        self.assertNotIn(" ", url)

    def test_record_id_with_slashes_encoded(self):
        """Slashes are encoded — prevents directory traversal."""
        from apps.clients.helpers import get_document_folder_url

        client = self._make_client("../../../etc/passwd")
        url = get_document_folder_url(client)
        self.assertNotIn("../", url)
        self.assertIn("%2F", url)

    def test_record_id_with_query_chars_encoded(self):
        """Question marks are encoded — can't inject parameters."""
        from apps.clients.helpers import get_document_folder_url

        client = self._make_client("REC-2024-042?admin=true")
        url = get_document_folder_url(client)
        self.assertNotIn("?admin", url)
        self.assertIn("%3F", url)

    def test_record_id_with_hash_encoded(self):
        """Hash is encoded — can't truncate URL."""
        from apps.clients.helpers import get_document_folder_url

        client = self._make_client("REC-2024-042#malicious")
        url = get_document_folder_url(client)
        self.assertNotIn("#malicious", url)
        self.assertIn("%23", url)


# ─── Domain Allowlist Integrity ────────────────────────────────────────────


class DomainAllowlistIntegrityTests(TestCase):
    """Ensure the domain allowlist hasn't been weakened."""

    def test_allowlist_contains_expected_domains(self):
        """Allowlist has exactly the expected domains."""
        expected = {"sharepoint.com", "drive.google.com", "onedrive.live.com"}
        self.assertEqual(set(ALLOWED_DOCUMENT_DOMAINS), expected)

    def test_no_wildcard_domains(self):
        """No wildcard patterns in allowlist."""
        for domain in ALLOWED_DOCUMENT_DOMAINS:
            self.assertNotIn("*", domain)
            self.assertFalse(domain.startswith("."))


# ─── Integration: Admin Saves Validated Settings ────────────────────────────


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class DocumentStorageAdminIntegrationTests(TestCase):
    """Integration tests: admin saves settings through the view."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        cache.clear()
        self.admin = User.objects.create_user(
            username="sec_admin", password="testpass123",
            display_name="Sec Admin", is_admin=True,
        )

    def test_valid_sharepoint_saves(self):
        """Valid SharePoint configuration saves successfully."""
        self.client.login(username="sec_admin", password="testpass123")
        resp = self.client.post("/admin/settings/instance/", _base_form_data(
            document_storage_provider="sharepoint",
            document_storage_url_template=(
                "https://contoso.sharepoint.com/sites/konote/Clients/{record_id}/"
            ),
        ))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            InstanceSetting.get("document_storage_provider"), "sharepoint"
        )

    def test_invalid_domain_rejected_by_view(self):
        """View rejects invalid domain and re-renders form with errors."""
        self.client.login(username="sec_admin", password="testpass123")
        resp = self.client.post("/admin/settings/instance/", _base_form_data(
            document_storage_provider="sharepoint",
            document_storage_url_template="https://evil.com/{record_id}/",
        ))
        self.assertEqual(resp.status_code, 200)  # Re-renders form, not redirect
        self.assertContains(resp, "must be one of")

    def test_http_rejected_by_view(self):
        """View rejects HTTP URL and re-renders form with errors."""
        self.client.login(username="sec_admin", password="testpass123")
        resp = self.client.post("/admin/settings/instance/", _base_form_data(
            document_storage_provider="sharepoint",
            document_storage_url_template="http://contoso.sharepoint.com/{record_id}/",
        ))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "HTTPS")

    def test_document_button_appears_on_client_page(self):
        """Documents button appears on client detail when configured."""
        from apps.programs.models import Program, UserProgramRole
        from apps.clients.models import ClientProgramEnrolment

        cache.clear()
        InstanceSetting.objects.create(
            setting_key="document_storage_provider", setting_value="sharepoint"
        )
        InstanceSetting.objects.create(
            setting_key="document_storage_url_template",
            setting_value="https://contoso.sharepoint.com/sites/konote/Clients/{record_id}/",
        )

        program = Program.objects.create(name="Test Prog")
        UserProgramRole.objects.create(
            user=self.admin, program=program, role="worker", status="active"
        )
        client_file = ClientFile.objects.create(
            record_id="REC-2024-042", status="active"
        )
        client_file.first_name = "Jane"
        client_file.last_name = "Doe"
        client_file.save()
        ClientProgramEnrolment.objects.create(
            client_file=client_file, program=program, status="enrolled"
        )

        self.client.login(username="sec_admin", password="testpass123")
        resp = self.client.get(f"/clients/{client_file.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Documents")
        self.assertContains(
            resp, "https://contoso.sharepoint.com/sites/konote/Clients/REC-2024-042/"
        )

    def test_document_button_hidden_when_not_configured(self):
        """Documents button not shown when provider is 'none'."""
        from apps.programs.models import Program, UserProgramRole
        from apps.clients.models import ClientProgramEnrolment

        cache.clear()

        program = Program.objects.create(name="Test Prog")
        UserProgramRole.objects.create(
            user=self.admin, program=program, role="worker", status="active"
        )
        client_file = ClientFile.objects.create(
            record_id="REC-2024-042", status="active"
        )
        client_file.first_name = "Jane"
        client_file.last_name = "Doe"
        client_file.save()
        ClientProgramEnrolment.objects.create(
            client_file=client_file, program=program, status="enrolled"
        )

        self.client.login(username="sec_admin", password="testpass123")
        resp = self.client.get(f"/clients/{client_file.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, 'rel="noopener noreferrer"')
