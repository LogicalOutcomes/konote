"""Tests for Phase 6: admin settings, terminology, features, users."""
from django.test import TestCase, Client, override_settings
from django.utils.translation import activate, deactivate
from cryptography.fernet import Fernet

from apps.admin_settings.models import (
    DEFAULT_TERMS, FeatureToggle, InstanceSetting, TerminologyOverride,
    get_default_terms_for_language,
)
from apps.auth_app.models import User
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


def build_terminology_form_data():
    """Build form data with default English values for all terms."""
    data = {}
    for key, defaults in DEFAULT_TERMS.items():
        default_en, _ = defaults
        data[key] = default_en
        data[f"{key}_fr"] = ""
    return data


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AdminSettingsDashboardTest(TestCase):
    def setUp(self):
        enc_module._fernet = None
        self.client = Client()
        self.admin = User.objects.create_user(username="admin", password="testpass123", is_admin=True)
        self.staff = User.objects.create_user(username="staff", password="testpass123", is_admin=False)

    def test_admin_can_view_dashboard(self):
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/admin/settings/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Terminology")

    def test_staff_cannot_view_dashboard(self):
        self.client.login(username="staff", password="testpass123")
        resp = self.client.get("/admin/settings/")
        self.assertEqual(resp.status_code, 403)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class TerminologyTest(TestCase):
    databases = ["default", "audit"]

    def setUp(self):
        enc_module._fernet = None
        self.client = Client()
        self.admin = User.objects.create_user(username="admin", password="testpass123", is_admin=True)

    def test_admin_can_view_terminology(self):
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/admin/settings/terminology/")
        self.assertEqual(resp.status_code, 200)
        # Check that both English and French columns are shown
        self.assertContains(resp, "English")
        self.assertContains(resp, "Français")

    def test_admin_can_update_terminology(self):
        self.client.login(username="admin", password="testpass123")
        data = build_terminology_form_data()
        data["client"] = "Beneficiary"
        resp = self.client.post("/admin/settings/terminology/", data)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            TerminologyOverride.objects.get(term_key="client").display_value,
            "Beneficiary",
        )

    def test_default_value_deletes_override(self):
        self.client.login(username="admin", password="testpass123")
        TerminologyOverride.objects.create(term_key="client", display_value="Participant")
        data = build_terminology_form_data()
        # Submit with default value — should remove override
        resp = self.client.post("/admin/settings/terminology/", data)
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(TerminologyOverride.objects.filter(term_key="client").exists())


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class BilingualTerminologyTest(TestCase):
    """Tests for bilingual (English/French) terminology support (I18N2)."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        from django.core.cache import cache
        cache.clear()

    def tearDown(self):
        deactivate()

    def test_get_default_terms_english(self):
        """Default terms in English use first value of tuple."""
        terms = get_default_terms_for_language("en")
        self.assertEqual(terms["client"], "Participant")
        self.assertEqual(terms["target"], "Target")
        self.assertEqual(terms["progress_note"], "Note")

    def test_get_default_terms_french(self):
        """Default terms in French use second value of tuple."""
        terms = get_default_terms_for_language("fr")
        self.assertEqual(terms["client"], "Participant(e)")
        self.assertEqual(terms["target"], "Objectif")
        self.assertEqual(terms["progress_note"], "Note de suivi")

    def test_get_all_terms_english_no_overrides(self):
        """get_all_terms returns English defaults when no overrides exist."""
        terms = TerminologyOverride.get_all_terms(lang="en")
        self.assertEqual(terms["client"], "Participant")
        self.assertEqual(terms["target"], "Target")

    def test_get_all_terms_french_no_overrides(self):
        """get_all_terms returns French defaults when no overrides exist."""
        terms = TerminologyOverride.get_all_terms(lang="fr")
        self.assertEqual(terms["target"], "Objectif")
        self.assertEqual(terms["metric"], "Indicateur")

    def test_get_all_terms_english_with_override(self):
        """English override is returned for English language."""
        TerminologyOverride.objects.create(
            term_key="client",
            display_value="Beneficiary",
            display_value_fr="",
        )
        terms = TerminologyOverride.get_all_terms(lang="en")
        self.assertEqual(terms["client"], "Beneficiary")

    def test_get_all_terms_french_with_french_override(self):
        """French override is returned when French language is requested."""
        TerminologyOverride.objects.create(
            term_key="client",
            display_value="Beneficiary",
            display_value_fr="Bénéficiaire",
        )
        terms = TerminologyOverride.get_all_terms(lang="fr")
        self.assertEqual(terms["client"], "Bénéficiaire")

    def test_get_all_terms_french_falls_back_to_english(self):
        """French falls back to English override when French is empty."""
        TerminologyOverride.objects.create(
            term_key="client",
            display_value="Beneficiary",
            display_value_fr="",  # Empty French
        )
        terms = TerminologyOverride.get_all_terms(lang="fr")
        self.assertEqual(terms["client"], "Beneficiary")

    def test_admin_can_set_french_terminology(self):
        """Admin can save both English and French terms."""
        self.client = Client()
        self.admin = User.objects.create_user(username="admin", password="testpass123", is_admin=True)
        self.client.login(username="admin", password="testpass123")

        data = build_terminology_form_data()
        data["client"] = "Beneficiary"
        data["client_fr"] = "Bénéficiaire"

        resp = self.client.post("/admin/settings/terminology/", data)
        self.assertEqual(resp.status_code, 302)

        override = TerminologyOverride.objects.get(term_key="client")
        self.assertEqual(override.display_value, "Beneficiary")
        self.assertEqual(override.display_value_fr, "Bénéficiaire")

    def test_french_language_prefix_detection(self):
        """Language codes like 'fr-ca' are treated as French."""
        TerminologyOverride.objects.create(
            term_key="client",
            display_value="Beneficiary",
            display_value_fr="Bénéficiaire",
        )
        # fr-ca (Canadian French) should use French terms
        terms = TerminologyOverride.get_all_terms(lang="fr-ca")
        self.assertEqual(terms["client"], "Bénéficiaire")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class FeatureToggleTest(TestCase):
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.client = Client()
        self.admin = User.objects.create_user(username="admin", password="testpass123", is_admin=True)

    def test_admin_can_view_features(self):
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/admin/settings/features/")
        self.assertEqual(resp.status_code, 200)

    def test_admin_can_enable_feature(self):
        self.client.login(username="admin", password="testpass123")
        resp = self.client.post("/admin/settings/features/", {
            "feature_key": "programs",
            "action": "enable",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(FeatureToggle.objects.get(feature_key="programs").is_enabled)

    def test_admin_can_disable_feature(self):
        self.client.login(username="admin", password="testpass123")
        FeatureToggle.objects.create(feature_key="programs", is_enabled=True)
        resp = self.client.post("/admin/settings/features/", {
            "feature_key": "programs",
            "action": "disable",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(FeatureToggle.objects.get(feature_key="programs").is_enabled)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class FeatureToggleConfirmTest(TestCase):
    """Tests for the HTMX feature toggle confirm and action views."""
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.client = Client()
        self.admin = User.objects.create_user(username="admin", password="testpass123", is_admin=True)
        self.staff = User.objects.create_user(username="staff", password="testpass123", is_admin=False)

    def test_confirm_returns_panel_for_valid_key(self):
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/admin/settings/features/programs/confirm/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Programs")
        self.assertContains(resp, "Yes,")

    def test_confirm_returns_error_for_invalid_key(self):
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/admin/settings/features/nonexistent/confirm/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Unknown feature")

    def test_confirm_requires_admin(self):
        self.client.login(username="staff", password="testpass123")
        resp = self.client.get("/admin/settings/features/programs/confirm/")
        self.assertEqual(resp.status_code, 403)

    def test_toggle_action_enables_feature(self):
        self.client.login(username="admin", password="testpass123")
        resp = self.client.post("/admin/settings/features/programs/toggle/")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(FeatureToggle.objects.get(feature_key="programs").is_enabled)

    def test_toggle_action_disables_feature(self):
        self.client.login(username="admin", password="testpass123")
        FeatureToggle.objects.create(feature_key="programs", is_enabled=True)
        resp = self.client.post("/admin/settings/features/programs/toggle/")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(FeatureToggle.objects.get(feature_key="programs").is_enabled)

    def test_toggle_action_rejects_get(self):
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/admin/settings/features/programs/toggle/")
        self.assertEqual(resp.status_code, 302)

    def test_toggle_action_invalid_key_redirects(self):
        self.client.login(username="admin", password="testpass123")
        resp = self.client.post("/admin/settings/features/nonexistent/toggle/")
        self.assertEqual(resp.status_code, 302)

    def test_toggle_action_requires_admin(self):
        self.client.login(username="staff", password="testpass123")
        resp = self.client.post("/admin/settings/features/programs/toggle/")
        self.assertEqual(resp.status_code, 403)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class InstanceSettingsTest(TestCase):
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.client = Client()
        self.admin = User.objects.create_user(username="admin", password="testpass123", is_admin=True)

    def test_admin_can_view_settings(self):
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/admin/settings/instance/")
        self.assertEqual(resp.status_code, 200)

    def test_admin_can_save_settings(self):
        self.client.login(username="admin", password="testpass123")
        resp = self.client.post("/admin/settings/instance/", {
            "product_name": "MyApp",
            "date_format": "Y-m-d",
            "session_timeout_minutes": "60",
            "document_storage_provider": "none",
            "meeting_time_start": "9",
            "meeting_time_end": "17",
            "meeting_time_step": "30",
            "access_tier": "1",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(InstanceSetting.get("product_name"), "MyApp")

    def test_admin_can_save_product_name_fr(self):
        self.client.login(username="admin", password="testpass123")
        resp = self.client.post("/admin/settings/instance/", {
            "product_name": "MyApp",
            "product_name_fr": "MonAppli",
            "date_format": "Y-m-d",
            "session_timeout_minutes": "60",
            "document_storage_provider": "none",
            "meeting_time_start": "9",
            "meeting_time_end": "17",
            "meeting_time_step": "30",
            "access_tier": "1",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(InstanceSetting.get("product_name_fr"), "MonAppli")

    def test_blank_product_name_fr_is_not_saved(self):
        self.client.login(username="admin", password="testpass123")
        InstanceSetting.objects.create(
            setting_key="product_name_fr", setting_value="OldFrench"
        )
        self.client.post("/admin/settings/instance/", {
            "product_name": "MyApp",
            "product_name_fr": "",
            "date_format": "Y-m-d",
            "session_timeout_minutes": "60",
            "document_storage_provider": "none",
            "meeting_time_start": "9",
            "meeting_time_end": "17",
            "meeting_time_step": "30",
            "access_tier": "1",
        })
        self.assertEqual(InstanceSetting.get("product_name_fr"), "")

    def test_context_processor_resolves_fr_product_name(self):
        from konote.context_processors import instance_settings
        from django.test import RequestFactory

        InstanceSetting.objects.create(
            setting_key="product_name", setting_value="MyAgency"
        )
        InstanceSetting.objects.create(
            setting_key="product_name_fr", setting_value="MonAgence"
        )
        factory = RequestFactory()
        request = factory.get("/")

        # English — should return English name
        activate("en")
        result = instance_settings(request)
        self.assertEqual(result["site"]["product_name"], "MyAgency")
        deactivate()

        # French — should return French name
        activate("fr")
        from django.core.cache import cache
        cache.delete("instance_settings")
        result = instance_settings(request)
        self.assertEqual(result["site"]["product_name"], "MonAgence")
        deactivate()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class BrandColourDerivationTest(TestCase):
    """Tests for the brand colour picker, hex validation, and CSS derivation."""

    def test_derive_brand_colours_known_blue(self):
        from apps.admin_settings.forms import _derive_brand_colours
        result = _derive_brand_colours("#3176aa")
        self.assertEqual(result["brand_color_hover"], "#296490")
        self.assertEqual(result["brand_color_focus"], "rgba(49, 118, 170, 0.25)")
        self.assertEqual(result["brand_color_subtle"], "rgba(49, 118, 170, 0.08)")
        self.assertEqual(result["brand_color_text"], "#ffffff")  # dark colour → white text
        # Light variant should be brighter than original
        self.assertTrue(result["brand_color_light"] > "#3176aa")

    def test_derive_brand_colours_light_colour_gets_dark_text(self):
        from apps.admin_settings.forms import _derive_brand_colours
        result = _derive_brand_colours("#ffd700")  # gold/yellow
        self.assertEqual(result["brand_color_text"], "#1a202c")

    def test_derive_brand_colours_dark_colour_gets_white_text(self):
        from apps.admin_settings.forms import _derive_brand_colours
        result = _derive_brand_colours("#1a202c")  # near-black
        self.assertEqual(result["brand_color_text"], "#ffffff")

    def test_derive_brand_colours_white_gets_dark_text(self):
        from apps.admin_settings.forms import _derive_brand_colours
        result = _derive_brand_colours("#ffffff")
        self.assertEqual(result["brand_color_text"], "#1a202c")

    def test_clean_brand_color_valid_hex(self):
        from apps.admin_settings.forms import InstanceSettingsForm
        form = InstanceSettingsForm(data={
            "brand_color": "#3176aa",
            "date_format": "Y-m-d",
            "session_timeout_minutes": "30",
            "document_storage_provider": "none",
            "meeting_time_start": "9",
            "meeting_time_end": "17",
            "meeting_time_step": "30",
            "access_tier": "1",
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["brand_color"], "#3176aa")

    def test_clean_brand_color_rejects_non_hex(self):
        from apps.admin_settings.forms import InstanceSettingsForm
        form = InstanceSettingsForm(data={
            "brand_color": "#}abcd",
            "date_format": "Y-m-d",
            "session_timeout_minutes": "30",
            "document_storage_provider": "none",
            "meeting_time_start": "9",
            "meeting_time_end": "17",
            "meeting_time_step": "30",
            "access_tier": "1",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("brand_color", form.errors)

    def test_clean_brand_color_rejects_named_colour(self):
        from apps.admin_settings.forms import InstanceSettingsForm
        form = InstanceSettingsForm(data={
            "brand_color": "red",
            "date_format": "Y-m-d",
            "session_timeout_minutes": "30",
            "document_storage_provider": "none",
            "meeting_time_start": "9",
            "meeting_time_end": "17",
            "meeting_time_step": "30",
            "access_tier": "1",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("brand_color", form.errors)

    def test_clean_brand_color_rejects_short_hex(self):
        from apps.admin_settings.forms import InstanceSettingsForm
        form = InstanceSettingsForm(data={
            "brand_color": "#123",
            "date_format": "Y-m-d",
            "session_timeout_minutes": "30",
            "document_storage_provider": "none",
            "meeting_time_start": "9",
            "meeting_time_end": "17",
            "meeting_time_step": "30",
            "access_tier": "1",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("brand_color", form.errors)

    def test_clean_brand_color_allows_empty(self):
        from apps.admin_settings.forms import InstanceSettingsForm
        form = InstanceSettingsForm(data={
            "brand_color": "",
            "date_format": "Y-m-d",
            "session_timeout_minutes": "30",
            "document_storage_provider": "none",
            "meeting_time_start": "9",
            "meeting_time_end": "17",
            "meeting_time_step": "30",
            "access_tier": "1",
        })
        self.assertTrue(form.is_valid(), form.errors)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class BrandColourSaveTest(TestCase):
    """Tests for saving brand colour and derived values via admin settings."""
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.client = Client()
        self.admin = User.objects.create_user(username="admin", password="testpass123", is_admin=True)

    def test_save_brand_colour_creates_derived_settings(self):
        self.client.login(username="admin", password="testpass123")
        self.client.post("/admin/settings/instance/", {
            "brand_color": "#3176aa",
            "date_format": "Y-m-d",
            "session_timeout_minutes": "30",
            "document_storage_provider": "none",
            "meeting_time_start": "9",
            "meeting_time_end": "17",
            "meeting_time_step": "30",
            "access_tier": "1",
        })
        self.assertEqual(InstanceSetting.get("brand_color"), "#3176aa")
        self.assertEqual(InstanceSetting.get("brand_color_hover"), "#296490")
        self.assertIn("rgba(49, 118, 170", InstanceSetting.get("brand_color_focus"))
        self.assertIsNotNone(InstanceSetting.get("brand_color_light"))
        self.assertIn(InstanceSetting.get("brand_color_text"), ("#ffffff", "#1a202c"))

    def test_clear_brand_colour_removes_derived_settings(self):
        self.client.login(username="admin", password="testpass123")
        # First set a colour
        self.client.post("/admin/settings/instance/", {
            "brand_color": "#ff0000",
            "date_format": "Y-m-d",
            "session_timeout_minutes": "30",
            "document_storage_provider": "none",
            "meeting_time_start": "9",
            "meeting_time_end": "17",
            "meeting_time_step": "30",
            "access_tier": "1",
        })
        self.assertIsNotNone(InstanceSetting.get("brand_color_hover"))
        # Then clear it
        self.client.post("/admin/settings/instance/", {
            "brand_color": "",
            "date_format": "Y-m-d",
            "session_timeout_minutes": "30",
            "document_storage_provider": "none",
            "meeting_time_start": "9",
            "meeting_time_end": "17",
            "meeting_time_step": "30",
            "access_tier": "1",
        })
        self.assertFalse(InstanceSetting.get("brand_color_hover"))
        self.assertFalse(InstanceSetting.get("brand_color_text"))

    def test_brand_colour_style_block_in_response(self):
        self.client.login(username="admin", password="testpass123")
        # Set a brand colour
        InstanceSetting.objects.update_or_create(
            setting_key="brand_color", defaults={"setting_value": "#ff5500"}
        )
        resp = self.client.get("/admin/settings/")
        self.assertContains(resp, "--kn-primary: #ff5500")
        self.assertContains(resp, "--kn-text-on-primary:")
        self.assertContains(resp, "--pico-primary-inverse:")
        self.assertContains(resp, "--kn-primary-active:")  # dark mode block

    def test_no_style_block_without_brand_colour(self):
        self.client.login(username="admin", password="testpass123")
        InstanceSetting.objects.filter(setting_key="brand_color").delete()
        resp = self.client.get("/admin/settings/")
        self.assertNotContains(resp, "--kn-primary:")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class UserManagementTest(TestCase):
    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.client = Client()
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True, display_name="Admin",
        )

    def test_admin_can_list_users(self):
        self.client.login(username="admin", password="testpass123")
        resp = self.client.get("/manage/users/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Admin")

    def test_admin_can_create_user(self):
        self.client.login(username="admin", password="testpass123")
        resp = self.client.post("/manage/users/new/", {
            "username": "newuser",
            "display_name": "New User",
            "password": "securepass1",
            "password_confirm": "securepass1",
            "is_admin": False,
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_password_mismatch_rejected(self):
        self.client.login(username="admin", password="testpass123")
        resp = self.client.post("/manage/users/new/", {
            "username": "newuser",
            "display_name": "New User",
            "password": "securepass1",
            "password_confirm": "differentpass",
            "is_admin": False,
        })
        self.assertEqual(resp.status_code, 200)  # Re-renders form
        self.assertFalse(User.objects.filter(username="newuser").exists())

    def test_admin_can_edit_user(self):
        self.client.login(username="admin", password="testpass123")
        user = User.objects.create_user(
            username="editme", password="testpass123", display_name="Edit Me",
        )
        resp = self.client.post(f"/manage/users/{user.pk}/edit/", {
            "display_name": "Edited Name",
            "is_admin": False,
            "is_active": True,
        })
        self.assertEqual(resp.status_code, 302)
        user.refresh_from_db()
        self.assertEqual(user.display_name, "Edited Name")

    def test_admin_can_deactivate_user(self):
        self.client.login(username="admin", password="testpass123")
        user = User.objects.create_user(
            username="deactivateme", password="testpass123", display_name="Deactivate Me",
        )
        resp = self.client.post(f"/manage/users/{user.pk}/deactivate/")
        self.assertEqual(resp.status_code, 302)
        user.refresh_from_db()
        self.assertFalse(user.is_active)

    def test_admin_cannot_deactivate_self(self):
        self.client.login(username="admin", password="testpass123")
        resp = self.client.post(f"/manage/users/{self.admin.pk}/deactivate/")
        self.assertEqual(resp.status_code, 302)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_staff_cannot_list_users(self):
        staff = User.objects.create_user(
            username="staff", password="testpass123", is_admin=False,
        )
        self.client.login(username="staff", password="testpass123")
        resp = self.client.get("/manage/users/")
        self.assertEqual(resp.status_code, 403)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class DocumentStorageSettingsTest(TestCase):
    """Tests for document storage configuration (DOC5)."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.client = Client()
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True
        )

    def test_admin_can_save_document_storage_settings(self):
        """Admin can configure SharePoint document storage."""
        self.client.login(username="admin", password="testpass123")
        resp = self.client.post("/admin/settings/instance/", {
            "product_name": "TestApp",
            "date_format": "Y-m-d",
            "session_timeout_minutes": "30",
            "document_storage_provider": "sharepoint",
            "meeting_time_start": "9",
            "meeting_time_end": "17",
            "meeting_time_step": "30",
            "document_storage_url_template": "https://contoso.sharepoint.com/sites/konote/Clients/{record_id}/",
            "access_tier": "1",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            InstanceSetting.get("document_storage_provider"),
            "sharepoint",
        )
        self.assertEqual(
            InstanceSetting.get("document_storage_url_template"),
            "https://contoso.sharepoint.com/sites/konote/Clients/{record_id}/",
        )

    def test_admin_can_configure_google_drive(self):
        """Admin can configure Google Drive document storage."""
        self.client.login(username="admin", password="testpass123")
        resp = self.client.post("/admin/settings/instance/", {
            "product_name": "TestApp",
            "date_format": "Y-m-d",
            "session_timeout_minutes": "30",
            "document_storage_provider": "google_drive",
            "document_storage_url_template": "https://drive.google.com/drive/search?q={record_id}",
            "meeting_time_start": "9",
            "meeting_time_end": "17",
            "meeting_time_step": "30",
            "access_tier": "1",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            InstanceSetting.get("document_storage_provider"),
            "google_drive",
        )

    def test_admin_can_disable_document_storage(self):
        """Admin can disable document storage by setting provider to 'none'."""
        self.client.login(username="admin", password="testpass123")
        # First enable
        InstanceSetting.objects.create(
            setting_key="document_storage_provider", setting_value="sharepoint"
        )
        # Then disable
        resp = self.client.post("/admin/settings/instance/", {
            "product_name": "TestApp",
            "date_format": "Y-m-d",
            "session_timeout_minutes": "30",
            "document_storage_provider": "none",
            "document_storage_url_template": "",
            "meeting_time_start": "9",
            "meeting_time_end": "17",
            "meeting_time_step": "30",
            "access_tier": "1",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            InstanceSetting.get("document_storage_provider"),
            "none",
        )


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class DocumentFolderUrlHelperTest(TestCase):
    """Tests for get_document_folder_url() helper function."""

    def setUp(self):
        enc_module._fernet = None
        from django.core.cache import cache
        cache.clear()

    def test_returns_none_when_not_configured(self):
        """Returns None when document storage is not configured."""
        from apps.clients.helpers import get_document_folder_url
        from apps.clients.models import ClientFile

        client = ClientFile.objects.create()
        client.first_name = "Jane"
        client.last_name = "Doe"
        client.record_id = "REC-2024-001"
        client.save()

        url = get_document_folder_url(client)
        self.assertIsNone(url)

    def test_returns_none_when_provider_is_none(self):
        """Returns None when provider is explicitly 'none'."""
        from apps.clients.helpers import get_document_folder_url
        from apps.clients.models import ClientFile
        from django.core.cache import cache

        InstanceSetting.objects.create(
            setting_key="document_storage_provider", setting_value="none"
        )
        cache.clear()

        client = ClientFile.objects.create()
        client.first_name = "Jane"
        client.last_name = "Doe"
        client.record_id = "REC-2024-001"
        client.save()

        url = get_document_folder_url(client)
        self.assertIsNone(url)

    def test_returns_url_with_record_id_substituted(self):
        """Returns URL with {record_id} replaced by client's record ID."""
        from apps.clients.helpers import get_document_folder_url
        from apps.clients.models import ClientFile
        from django.core.cache import cache

        InstanceSetting.objects.create(
            setting_key="document_storage_provider", setting_value="sharepoint"
        )
        InstanceSetting.objects.create(
            setting_key="document_storage_url_template",
            setting_value="https://contoso.sharepoint.com/sites/konote/Clients/{record_id}/",
        )
        cache.clear()

        client = ClientFile.objects.create()
        client.first_name = "Jane"
        client.last_name = "Doe"
        client.record_id = "REC-2024-042"
        client.save()

        url = get_document_folder_url(client)
        self.assertEqual(
            url,
            "https://contoso.sharepoint.com/sites/konote/Clients/REC-2024-042/",
        )

    def test_returns_none_when_client_has_no_record_id(self):
        """Returns None when client has no record ID."""
        from apps.clients.helpers import get_document_folder_url
        from apps.clients.models import ClientFile
        from django.core.cache import cache

        InstanceSetting.objects.create(
            setting_key="document_storage_provider", setting_value="sharepoint"
        )
        InstanceSetting.objects.create(
            setting_key="document_storage_url_template",
            setting_value="https://contoso.sharepoint.com/sites/konote/Clients/{record_id}/",
        )
        cache.clear()

        client = ClientFile.objects.create()
        client.first_name = "Jane"
        client.last_name = "Doe"
        client.record_id = ""  # No record ID
        client.save()

        url = get_document_folder_url(client)
        self.assertIsNone(url)

    def test_google_drive_search_url(self):
        """Google Drive URL uses search with record_id query."""
        from apps.clients.helpers import get_document_folder_url
        from apps.clients.models import ClientFile
        from django.core.cache import cache

        InstanceSetting.objects.create(
            setting_key="document_storage_provider", setting_value="google_drive"
        )
        InstanceSetting.objects.create(
            setting_key="document_storage_url_template",
            setting_value="https://drive.google.com/drive/search?q={record_id}",
        )
        cache.clear()

        client = ClientFile.objects.create()
        client.first_name = "Marcus"
        client.last_name = "Jones"
        client.record_id = "REC-2024-100"
        client.save()

        url = get_document_folder_url(client)
        self.assertEqual(
            url,
            "https://drive.google.com/drive/search?q=REC-2024-100",
        )
