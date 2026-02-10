"""
Security tests for KoNote Web.

These tests verify that security properties hold across the application:
- PII fields are properly encrypted and not exposed
- RBAC controls cannot be bypassed
- Audit logging captures required events
- Document storage URLs are properly validated

Run with:
    python manage.py test tests.test_security
"""

from django.db import connection
from django.test import Client, TestCase, override_settings
from cryptography.fernet import Fernet

from apps.auth_app.models import User
from apps.programs.models import Program, UserProgramRole
from apps.clients.models import ClientFile, ClientProgramEnrolment
import konote.encryption as enc_module


TEST_KEY = Fernet.generate_key().decode()


# =============================================================================
# PII Exposure Tests
# =============================================================================


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class PIIExposureTest(TestCase):
    """Verify PII fields are never exposed in plaintext."""

    def setUp(self):
        enc_module._fernet = None

    def tearDown(self):
        enc_module._fernet = None

    def test_client_name_not_in_database_plaintext(self):
        """Raw database query should not find client names in cleartext."""
        # Create a client with a unique, searchable name
        test_name = "UniqueSecurityTestName12345"
        client = ClientFile.objects.create()
        client.first_name = test_name
        client.last_name = "TestLastName67890"
        client.save()

        # Query the raw database
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM client_files WHERE id = %s", [client.pk]
            )
            columns = [col[0] for col in cursor.description]
            row = cursor.fetchone()

            # Convert entire row to string for searching
            row_dict = dict(zip(columns, row))
            row_str = str(row_dict)

            # The plaintext name should NOT appear
            self.assertNotIn(test_name, row_str)
            self.assertNotIn("TestLastName67890", row_str)

    def test_encrypted_field_contains_ciphertext(self):
        """Encrypted fields should contain valid Fernet ciphertext, not plaintext."""
        client = ClientFile.objects.create()
        client.first_name = "Jane"
        client.save()

        # Refresh from database
        client.refresh_from_db()

        # The raw encrypted field should be bytes, not the plaintext
        raw = client._first_name_encrypted
        self.assertIsInstance(raw, (bytes, memoryview))

        # Convert memoryview if needed
        if isinstance(raw, memoryview):
            raw = bytes(raw)

        # Should not contain the plaintext
        self.assertNotIn(b"Jane", raw)

        # Should be valid base64-encoded Fernet ciphertext
        import base64
        decoded = base64.urlsafe_b64decode(raw)
        self.assertGreaterEqual(len(decoded), 57)  # Minimum Fernet size
        self.assertEqual(decoded[0], 0x80)  # Fernet version byte

    def test_property_accessor_decrypts_correctly(self):
        """Property accessor should return decrypted plaintext."""
        client = ClientFile.objects.create()
        client.first_name = "Encrypted"
        client.last_name = "Name"
        client.save()

        # Refresh and read via property
        client.refresh_from_db()
        self.assertEqual(client.first_name, "Encrypted")
        self.assertEqual(client.last_name, "Name")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class SensitiveCustomFieldTest(TestCase):
    """Verify sensitive custom fields use encryption."""

    def setUp(self):
        enc_module._fernet = None

    def tearDown(self):
        enc_module._fernet = None

    def test_sensitive_field_stores_encrypted(self):
        """Custom fields marked sensitive should store data encrypted."""
        from apps.clients.models import (
            ClientDetailValue,
            CustomFieldDefinition,
            CustomFieldGroup,
        )

        # Create a sensitive field definition
        group = CustomFieldGroup.objects.create(title="Test Group")
        field_def = CustomFieldDefinition.objects.create(
            group=group,
            name="Social Insurance Number",
            input_type="text",
            is_sensitive=True,
        )

        # Create a client and set the sensitive value
        client = ClientFile.objects.create()
        cdv = ClientDetailValue.objects.create(
            client_file=client,
            field_def=field_def,
        )
        cdv.set_value("123-456-789")
        cdv.save()

        # Refresh and verify storage
        cdv.refresh_from_db()

        # Plaintext field should be empty
        self.assertEqual(cdv.value, "")

        # Encrypted field should be populated
        self.assertTrue(cdv._value_encrypted)

        # Should decrypt correctly
        self.assertEqual(cdv.get_value(), "123-456-789")


# =============================================================================
# RBAC Bypass Tests
# =============================================================================


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class RBACBypassTest(TestCase):
    """Attempt to bypass RBAC controls."""

    def setUp(self):
        enc_module._fernet = None
        self.http_client = Client()

        # Create programs
        self.program_a = Program.objects.create(name="Program A")
        self.program_b = Program.objects.create(name="Program B")

        # Create users
        self.user_a = User.objects.create_user(
            username="user_a", password="testpass123", display_name="User A"
        )
        self.user_b = User.objects.create_user(
            username="user_b", password="testpass123", display_name="User B"
        )
        self.admin_only = User.objects.create_user(
            username="admin_only", password="testpass123", display_name="Admin Only"
        )
        self.admin_only.is_admin = True
        self.admin_only.save()

        # Assign users to programs
        UserProgramRole.objects.create(
            user=self.user_a, program=self.program_a, role="staff"
        )
        UserProgramRole.objects.create(
            user=self.user_b, program=self.program_b, role="staff"
        )

        # Create client in Program A only
        self.client_a = ClientFile.objects.create()
        self.client_a.first_name = "Client"
        self.client_a.last_name = "InProgramA"
        self.client_a.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.client_a, program=self.program_a
        )

        # Create client in Program B only
        self.client_b = ClientFile.objects.create()
        self.client_b.first_name = "Client"
        self.client_b.last_name = "InProgramB"
        self.client_b.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.client_b, program=self.program_b
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_direct_url_access_blocked(self):
        """User cannot access client by guessing URL if not in their program."""
        self.http_client.login(username="user_a", password="testpass123")

        # User A tries to access Client B's detail page
        response = self.http_client.get(f"/clients/{self.client_b.pk}/")

        # Should be forbidden
        self.assertEqual(response.status_code, 403)

    def test_htmx_partial_blocked(self):
        """HTMX partial requests also respect RBAC."""
        self.http_client.login(username="user_a", password="testpass123")

        # Try HTMX request to client in other program
        response = self.http_client.get(
            f"/clients/{self.client_b.pk}/",
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 403)

    def test_user_can_access_own_program_client(self):
        """User CAN access clients in their program."""
        self.http_client.login(username="user_a", password="testpass123")

        response = self.http_client.get(f"/clients/{self.client_a.pk}/")

        # Should succeed
        self.assertEqual(response.status_code, 200)

    def test_admin_without_program_role_blocked(self):
        """Admin-only users (no program roles) cannot access client data."""
        self.http_client.login(username="admin_only", password="testpass123")

        # Admin tries to access any client
        response = self.http_client.get(f"/clients/{self.client_a.pk}/")

        # Should be forbidden (admin role doesn't grant client access)
        self.assertEqual(response.status_code, 403)


# =============================================================================
# Audit Coverage Tests
# =============================================================================


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AuditCoverageTest(TestCase):
    """Verify audit logging covers required events."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http_client = Client()

        # Create program and user
        self.program = Program.objects.create(name="Audit Test Program")
        self.user = User.objects.create_user(
            username="auditor", password="testpass123", display_name="Auditor"
        )
        UserProgramRole.objects.create(
            user=self.user, program=self.program, role="staff"
        )

        # Create a client
        self.test_client = ClientFile.objects.create()
        self.test_client.first_name = "Audit"
        self.test_client.last_name = "TestClient"
        self.test_client.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.test_client, program=self.program
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_client_view_logged(self):
        """Viewing a client creates an audit entry."""
        from apps.audit.models import AuditLog

        initial_count = AuditLog.objects.using("audit").filter(action="view").count()

        self.http_client.login(username="auditor", password="testpass123")
        self.http_client.get(f"/clients/{self.test_client.pk}/")

        new_count = AuditLog.objects.using("audit").filter(action="view").count()

        # Should have at least one more view entry
        self.assertGreater(new_count, initial_count)


# =============================================================================
# Configuration Drift Tests
# =============================================================================


class ConfigurationDriftTest(TestCase):
    """Catch configuration drift that could weaken security."""

    def test_audit_middleware_enabled(self):
        """Ensure audit logging middleware is active."""
        from django.conf import settings

        self.assertIn(
            "konote.middleware.audit.AuditMiddleware",
            settings.MIDDLEWARE,
            "AuditMiddleware must be in MIDDLEWARE for audit logging",
        )

    def test_rbac_middleware_enabled(self):
        """Ensure RBAC middleware is active."""
        from django.conf import settings

        self.assertIn(
            "konote.middleware.program_access.ProgramAccessMiddleware",
            settings.MIDDLEWARE,
            "ProgramAccessMiddleware must be in MIDDLEWARE for RBAC",
        )

    def test_encryption_key_configured(self):
        """Ensure encryption key is configured."""
        from django.conf import settings

        key = getattr(settings, "FIELD_ENCRYPTION_KEY", None)
        self.assertIsNotNone(key, "FIELD_ENCRYPTION_KEY must be configured")
        self.assertTrue(len(key) > 0, "FIELD_ENCRYPTION_KEY must not be empty")
