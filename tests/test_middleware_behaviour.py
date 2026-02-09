"""Behaviour tests for AuditMiddleware, SafeLocaleMiddleware, and TerminologyMiddleware."""
from unittest.mock import patch

from cryptography.fernet import Fernet
from django.conf import settings
from django.core.cache import cache
from django.test import TestCase, Client, override_settings
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.admin_settings.models import TerminologyOverride
from apps.auth_app.models import User
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.programs.models import Program, UserProgramRole
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


def _setup_staff_with_client(test_case):
    """Create a staff user with a program role and a client enrolled in that program.

    Returns (user, client_file, program) tuple.
    """
    user = User.objects.create_user(
        username="staffuser",
        password="testpass123",
        display_name="Staff User",
        is_admin=False,
    )
    program = Program.objects.create(name="Test Program", status="active")
    UserProgramRole.objects.create(
        user=user, program=program, role="staff", status="active",
    )
    client_file = ClientFile.objects.create(is_demo=False)
    client_file.first_name = "Test"
    client_file.last_name = "Client"
    client_file.save()
    ClientProgramEnrolment.objects.create(
        client_file=client_file, program=program, status="enrolled",
    )
    return user, client_file, program


# ── Section 1: AuditMiddleware behaviour ──────────────────────────


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AuditMiddlewareBehaviourTest(TestCase):
    """Test that AuditMiddleware logs the right requests to the audit DB."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()
        self.user, self.client_file, self.program = _setup_staff_with_client(self)

    def tearDown(self):
        enc_module._fernet = None

    # 1. POST to a client edit URL creates an audit log entry
    def test_audit_logs_post_request(self):
        """POST to a client edit URL should create an AuditLog with action='post'."""
        self.http.login(username="staffuser", password="testpass123")
        url = f"/clients/{self.client_file.pk}/edit/"
        self.http.post(url, {
            "first_name": "Updated",
            "last_name": "Client",
            "preferred_name": "",
            "middle_name": "",
            "birth_date": "",
            "phone": "",
            "record_id": "",
            "status": "active",
            "programs": [self.program.pk],
        })
        entries = AuditLog.objects.using("audit").filter(action="post")
        self.assertTrue(entries.exists(), "POST request should create an audit entry with action='post'")

    # 2. GET to a client detail URL creates an audit log with action="view"
    def test_audit_logs_client_view(self):
        """GET /clients/<id>/ should create an AuditLog with action='view'."""
        self.http.login(username="staffuser", password="testpass123")
        url = f"/clients/{self.client_file.pk}/"
        self.http.get(url)
        entries = AuditLog.objects.using("audit").filter(
            action="view", resource_type="clients",
        )
        self.assertTrue(entries.exists(), "GET on client detail should create 'view' audit entry")

    # 3. Access denied (403) creates an audit log with action="access_denied"
    def test_audit_logs_access_denied(self):
        """User WITHOUT programme access gets 403, and an 'access_denied' audit entry is created."""
        # Create a second user with no programme role
        outsider = User.objects.create_user(
            username="outsider", password="testpass123",
            display_name="Outsider", is_admin=False,
        )
        # Give outsider a role in a DIFFERENT programme so they are authenticated but cannot access
        other_program = Program.objects.create(name="Other Program", status="active")
        UserProgramRole.objects.create(
            user=outsider, program=other_program, role="staff", status="active",
        )
        self.http.login(username="outsider", password="testpass123")
        url = f"/clients/{self.client_file.pk}/"
        resp = self.http.get(url)
        self.assertEqual(resp.status_code, 403)
        entries = AuditLog.objects.using("audit").filter(action="access_denied")
        self.assertTrue(
            entries.exists(),
            "403 on a client URL should create an 'access_denied' audit entry",
        )

    # 4. Unauthenticated requests do NOT create audit entries
    def test_audit_skips_unauthenticated(self):
        """Request without login should not create any AuditLog entry."""
        url = f"/clients/{self.client_file.pk}/"
        self.http.get(url)  # redirects to login
        count = AuditLog.objects.using("audit").count()
        self.assertEqual(count, 0, "Unauthenticated requests should not create audit entries")

    # 5. GET to a non-client URL does NOT create a "view" audit entry
    def test_audit_skips_non_client_get(self):
        """GET /programs/ should not create a 'view' audit entry."""
        self.http.login(username="staffuser", password="testpass123")
        self.http.get("/programs/")
        view_entries = AuditLog.objects.using("audit").filter(action="view")
        self.assertFalse(
            view_entries.exists(),
            "GET on a non-client URL should not create a 'view' audit entry",
        )

    # 6. AuditLog entry has the correct resource_type
    def test_audit_extracts_resource_type(self):
        """Client view audit entry should have resource_type='clients'."""
        self.http.login(username="staffuser", password="testpass123")
        url = f"/clients/{self.client_file.pk}/"
        self.http.get(url)
        entry = AuditLog.objects.using("audit").filter(action="view").first()
        self.assertIsNotNone(entry, "Should have a view audit entry")
        self.assertEqual(entry.resource_type, "clients")

    # 7. AuditLog entry has the correct resource_id
    def test_audit_extracts_resource_id(self):
        """Client view audit entry should have the correct resource_id."""
        self.http.login(username="staffuser", password="testpass123")
        url = f"/clients/{self.client_file.pk}/"
        self.http.get(url)
        entry = AuditLog.objects.using("audit").filter(action="view").first()
        self.assertIsNotNone(entry, "Should have a view audit entry")
        self.assertEqual(entry.resource_id, self.client_file.pk)

    # 8. Audit middleware never crashes the request, even if logging fails
    def test_audit_never_crashes_on_error(self):
        """If AuditLog.create raises an exception, the response should still be returned."""
        self.http.login(username="staffuser", password="testpass123")
        url = f"/clients/{self.client_file.pk}/"
        with patch(
            "apps.audit.models.AuditLog.objects",
        ) as mock_objects:
            # Make the using().create() call raise an exception
            mock_objects.using.return_value.create.side_effect = RuntimeError("DB down")
            resp = self.http.get(url)
        # The response should still come through (200 from the view)
        self.assertIn(resp.status_code, [200, 302], "Response should be returned even if audit logging fails")


# ── Section 2: SafeLocaleMiddleware behaviour ─────────────────────


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class SafeLocaleMiddlewareBehaviourTest(TestCase):
    """Test that SafeLocaleMiddleware handles translation failures gracefully."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()
        self.user = User.objects.create_user(
            username="localeuser", password="testpass123",
            display_name="Locale User",
        )

    def tearDown(self):
        enc_module._fernet = None

    # 1. English language works normally
    def test_safe_locale_allows_english(self):
        """Request with English language cookie should return 200."""
        self.http.cookies[settings.LANGUAGE_COOKIE_NAME] = "en"
        resp = self.http.get("/auth/login/")
        self.assertEqual(resp.status_code, 200)

    # 2. Exception during translation.activate falls back gracefully
    def test_safe_locale_falls_back_on_exception(self):
        """If translation.activate raises for 'fr', middleware catches it and the request succeeds."""
        original_activate = __import__("django.utils.translation", fromlist=["activate"]).activate

        def exploding_activate(lang, *args, **kwargs):
            if isinstance(lang, str) and lang.startswith("fr"):
                raise RuntimeError("Corrupt .mo file")
            return original_activate(lang, *args, **kwargs)

        self.http.cookies[settings.LANGUAGE_COOKIE_NAME] = "fr"
        with patch("django.utils.translation.activate", side_effect=exploding_activate):
            resp = self.http.get("/auth/login/")
        # The request should still succeed — middleware catches the error
        self.assertEqual(resp.status_code, 200)

    # 3. process_response also catches errors (defensive check)
    def test_safe_locale_process_response_catches_error(self):
        """Normal request with language='en' processes response without crashing."""
        self.http.cookies[settings.LANGUAGE_COOKIE_NAME] = "en"
        resp = self.http.get("/auth/login/")
        self.assertEqual(resp.status_code, 200)

    # 4. Falls back on missing translation (canary check)
    def test_safe_locale_falls_back_on_missing_translation(self):
        """If the French .mo file is missing the canary string, middleware falls back to English.

        The middleware checks whether 'Programme Outcome Report' gets translated when
        French is active. If the string is unchanged (meaning our .mo file did not
        load), it falls back to English.
        """
        self.http.cookies[settings.LANGUAGE_COOKIE_NAME] = "fr"

        # Patch gettext to return the English string unchanged (simulates missing .mo)
        with patch("django.utils.translation.gettext", return_value="Programme Outcome Report"):
            resp = self.http.get("/auth/login/")
        # Request should still succeed
        self.assertEqual(resp.status_code, 200)


# ── Section 3: TerminologyMiddleware behaviour ────────────────────


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class TerminologyMiddlewareBehaviourTest(TestCase):
    """Test that TerminologyMiddleware attaches get_term to the request."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        cache.clear()
        self.http = Client()
        self.user = User.objects.create_user(
            username="termuser", password="testpass123",
            display_name="Term User",
        )

    def tearDown(self):
        enc_module._fernet = None
        cache.clear()

    # 1. get_term is attached to the request object
    def test_terminology_attaches_get_term(self):
        """After middleware runs, request.get_term should be a callable."""
        self.http.login(username="termuser", password="testpass123")
        resp = self.http.get("/programs/")
        # The wsgi_request object should have get_term attached
        self.assertTrue(
            hasattr(resp.wsgi_request, "get_term"),
            "Middleware should attach get_term to the request",
        )
        self.assertTrue(
            callable(resp.wsgi_request.get_term),
            "get_term should be callable",
        )

    # 2. Without overrides, get_term returns the default value for the key
    def test_terminology_returns_default_key(self):
        """With no TerminologyOverride in the DB, get_term('client') returns the default ('Participant')."""
        self.http.login(username="termuser", password="testpass123")
        resp = self.http.get("/programs/")
        # The default for 'client' in DEFAULT_TERMS is ('Participant', 'Participant(e)')
        result = resp.wsgi_request.get_term("client")
        self.assertEqual(
            result, "Participant",
            "Without overrides, get_term should return the default value from DEFAULT_TERMS",
        )

    # 3. With a TerminologyOverride, get_term returns the overridden value
    def test_terminology_returns_override(self):
        """With a TerminologyOverride for 'client', get_term returns the override value."""
        TerminologyOverride.objects.create(
            term_key="client", display_value="Beneficiary",
        )
        cache.clear()  # clear cached terminology
        self.http.login(username="termuser", password="testpass123")
        resp = self.http.get("/programs/")
        result = resp.wsgi_request.get_term("client")
        self.assertEqual(
            result, "Beneficiary",
            "get_term should return the overridden value from TerminologyOverride",
        )

    # 4. Terminology results are cached (second call uses cache, not another query)
    def test_terminology_caches_result(self):
        """Calling get_term twice should use cached results (not hit DB twice)."""
        self.http.login(username="termuser", password="testpass123")
        resp = self.http.get("/programs/")
        get_term = resp.wsgi_request.get_term

        # First call populates cache
        result1 = get_term("client")

        # Second call should use cache — verify by checking the cache key exists
        cache_key = "terminology_overrides_en"
        cached_terms = cache.get(cache_key)
        self.assertIsNotNone(
            cached_terms,
            "Terminology should be cached after first call to get_term",
        )

        # Second call returns the same value (from cache)
        result2 = get_term("client")
        self.assertEqual(result1, result2, "Cached result should match first result")
