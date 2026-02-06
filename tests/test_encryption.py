"""Tests for PII field encryption (Fernet AES)."""
from django.test import TestCase, override_settings
from cryptography.fernet import Fernet

from konote.encryption import encrypt_field, decrypt_field, _get_fernet
import konote.encryption as enc_module


TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class EncryptionUtilsTest(TestCase):
    """Test encrypt_field / decrypt_field round-trip and edge cases."""

    def setUp(self):
        # Reset cached Fernet instance so test key is picked up
        enc_module._fernet = None

    def tearDown(self):
        enc_module._fernet = None

    def test_round_trip(self):
        """Encrypting then decrypting returns original text."""
        plaintext = "Jane Doe"
        ciphertext = encrypt_field(plaintext)
        self.assertIsInstance(ciphertext, bytes)
        self.assertNotEqual(ciphertext, plaintext.encode())
        self.assertEqual(decrypt_field(ciphertext), plaintext)

    def test_unicode_round_trip(self):
        """Unicode characters survive encryption round-trip."""
        plaintext = "Éloïse Côté-Tremblay"
        self.assertEqual(decrypt_field(encrypt_field(plaintext)), plaintext)

    def test_empty_string_returns_empty_bytes(self):
        self.assertEqual(encrypt_field(""), b"")
        self.assertEqual(decrypt_field(b""), "")

    def test_none_returns_empty_bytes(self):
        self.assertEqual(encrypt_field(None), b"")

    def test_invalid_ciphertext_returns_empty_string(self):
        """Corrupted data returns empty string, not an exception."""
        result = decrypt_field(b"not-valid-fernet-data")
        self.assertEqual(result, "")

    def test_memoryview_input(self):
        """BinaryField values come as memoryview — decryption handles this."""
        ciphertext = encrypt_field("Test")
        mv = memoryview(ciphertext)
        self.assertEqual(decrypt_field(mv), "Test")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ClientPIIEncryptionTest(TestCase):
    """Test that ClientFile model encrypts and decrypts PII via property accessors."""

    def setUp(self):
        enc_module._fernet = None

    def tearDown(self):
        enc_module._fernet = None

    def test_client_name_encryption(self):
        from apps.clients.models import ClientFile

        client = ClientFile()
        client.first_name = "Jane"
        client.last_name = "Doe"

        # Raw field should be encrypted bytes, not plaintext
        self.assertIsInstance(client._first_name_encrypted, bytes)
        self.assertNotIn(b"Jane", client._first_name_encrypted)

        # Property accessor returns plaintext
        self.assertEqual(client.first_name, "Jane")
        self.assertEqual(client.last_name, "Doe")

    def test_user_email_encryption(self):
        from apps.auth_app.models import User

        user = User(username="test", display_name="Test")
        user.email = "test@example.com"

        self.assertIsInstance(user._email_encrypted, bytes)
        self.assertEqual(user.email, "test@example.com")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ProgressNotePIIEncryptionTest(TestCase):
    """Test that ProgressNote model encrypts and decrypts PII via property accessors."""

    def setUp(self):
        enc_module._fernet = None

    def tearDown(self):
        enc_module._fernet = None

    def test_notes_text_encryption_on_write(self):
        """notes_text encrypts on write."""
        from apps.notes.models import ProgressNote

        note = ProgressNote()
        note.notes_text = "Client discussed housing concerns."

        # Raw field should be encrypted bytes, not plaintext
        self.assertIsInstance(note._notes_text_encrypted, bytes)
        self.assertNotEqual(note._notes_text_encrypted, b"")
        self.assertNotIn(b"Client", note._notes_text_encrypted)
        self.assertNotIn(b"housing", note._notes_text_encrypted)

    def test_notes_text_decryption_on_read(self):
        """notes_text decrypts correctly on read."""
        from apps.notes.models import ProgressNote

        original_text = "Client discussed housing concerns."
        note = ProgressNote()
        note.notes_text = original_text

        # Property accessor returns plaintext
        self.assertEqual(note.notes_text, original_text)

    def test_summary_encryption_on_write(self):
        """summary encrypts on write."""
        from apps.notes.models import ProgressNote

        note = ProgressNote()
        note.summary = "Good progress on goal #1."

        # Raw field should be encrypted bytes
        self.assertIsInstance(note._summary_encrypted, bytes)
        self.assertNotEqual(note._summary_encrypted, b"")
        self.assertNotIn(b"Good", note._summary_encrypted)
        self.assertNotIn(b"progress", note._summary_encrypted)

    def test_summary_decryption_on_read(self):
        """summary decrypts correctly on read."""
        from apps.notes.models import ProgressNote

        original_text = "Good progress on goal #1."
        note = ProgressNote()
        note.summary = original_text

        self.assertEqual(note.summary, original_text)

    def test_participant_reflection_encryption_on_write(self):
        """participant_reflection encrypts on write."""
        from apps.notes.models import ProgressNote

        note = ProgressNote()
        note.participant_reflection = "I feel more confident about my future."

        # Raw field should be encrypted bytes
        self.assertIsInstance(note._participant_reflection_encrypted, bytes)
        self.assertNotEqual(note._participant_reflection_encrypted, b"")
        self.assertNotIn(b"confident", note._participant_reflection_encrypted)
        self.assertNotIn(b"future", note._participant_reflection_encrypted)

    def test_participant_reflection_decryption_on_read(self):
        """participant_reflection decrypts correctly on read."""
        from apps.notes.models import ProgressNote

        original_text = "I feel more confident about my future."
        note = ProgressNote()
        note.participant_reflection = original_text

        self.assertEqual(note.participant_reflection, original_text)

    def test_empty_string_handling_notes_text(self):
        """Empty string for notes_text returns empty string on read."""
        from apps.notes.models import ProgressNote

        note = ProgressNote()
        note.notes_text = ""

        self.assertEqual(note._notes_text_encrypted, b"")
        self.assertEqual(note.notes_text, "")

    def test_empty_string_handling_summary(self):
        """Empty string for summary returns empty string on read."""
        from apps.notes.models import ProgressNote

        note = ProgressNote()
        note.summary = ""

        self.assertEqual(note._summary_encrypted, b"")
        self.assertEqual(note.summary, "")

    def test_empty_string_handling_participant_reflection(self):
        """Empty string for participant_reflection returns empty string on read."""
        from apps.notes.models import ProgressNote

        note = ProgressNote()
        note.participant_reflection = ""

        self.assertEqual(note._participant_reflection_encrypted, b"")
        self.assertEqual(note.participant_reflection, "")

    def test_none_value_handling(self):
        """Setting properties to None should be handled gracefully."""
        from apps.notes.models import ProgressNote

        note = ProgressNote()
        note.notes_text = None
        note.summary = None
        note.participant_reflection = None

        self.assertEqual(note._notes_text_encrypted, b"")
        self.assertEqual(note._summary_encrypted, b"")
        self.assertEqual(note._participant_reflection_encrypted, b"")
        self.assertEqual(note.notes_text, "")
        self.assertEqual(note.summary, "")
        self.assertEqual(note.participant_reflection, "")

    def test_unicode_content_round_trip(self):
        """Unicode characters survive encryption round-trip in progress notes."""
        from apps.notes.models import ProgressNote

        note = ProgressNote()
        note.notes_text = "Éloïse discussed concerns about her family — très bien!"
        note.summary = "Réunion avec le participant"
        note.participant_reflection = "Je me sens mieux aujourd'hui"

        self.assertEqual(note.notes_text, "Éloïse discussed concerns about her family — très bien!")
        self.assertEqual(note.summary, "Réunion avec le participant")
        self.assertEqual(note.participant_reflection, "Je me sens mieux aujourd'hui")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ProgressNoteTargetPIIEncryptionTest(TestCase):
    """Test that ProgressNoteTarget model encrypts and decrypts notes field."""

    def setUp(self):
        enc_module._fernet = None

    def tearDown(self):
        enc_module._fernet = None

    def test_notes_encryption_on_write(self):
        """ProgressNoteTarget notes field encrypts on write."""
        from apps.notes.models import ProgressNoteTarget

        target = ProgressNoteTarget()
        target.notes = "Client showed improvement in this area."

        # Raw field should be encrypted bytes, not plaintext
        self.assertIsInstance(target._notes_encrypted, bytes)
        self.assertNotEqual(target._notes_encrypted, b"")
        self.assertNotIn(b"Client", target._notes_encrypted)
        self.assertNotIn(b"improvement", target._notes_encrypted)

    def test_notes_decryption_on_read(self):
        """ProgressNoteTarget notes field decrypts correctly on read."""
        from apps.notes.models import ProgressNoteTarget

        original_text = "Client showed improvement in this area."
        target = ProgressNoteTarget()
        target.notes = original_text

        # Property accessor returns plaintext
        self.assertEqual(target.notes, original_text)

    def test_empty_string_handling(self):
        """Empty string for notes returns empty string on read."""
        from apps.notes.models import ProgressNoteTarget

        target = ProgressNoteTarget()
        target.notes = ""

        self.assertEqual(target._notes_encrypted, b"")
        self.assertEqual(target.notes, "")

    def test_none_value_handling(self):
        """Setting notes to None should be handled gracefully."""
        from apps.notes.models import ProgressNoteTarget

        target = ProgressNoteTarget()
        target.notes = None

        self.assertEqual(target._notes_encrypted, b"")
        self.assertEqual(target.notes, "")

    def test_unicode_content_round_trip(self):
        """Unicode characters survive encryption round-trip."""
        from apps.notes.models import ProgressNoteTarget

        target = ProgressNoteTarget()
        target.notes = "Le participant a montré des progrès — très encourageant!"

        self.assertEqual(target.notes, "Le participant a montré des progrès — très encourageant!")

    def test_raw_field_contains_bytes_not_plaintext(self):
        """Raw encrypted field must contain bytes, not plaintext string."""
        from apps.notes.models import ProgressNoteTarget

        target = ProgressNoteTarget()
        target.notes = "Sensitive client information here"

        # Must be bytes type
        self.assertIsInstance(target._notes_encrypted, bytes)
        # Must not be empty (indicates encryption happened)
        self.assertTrue(len(target._notes_encrypted) > 0)
        # Must not contain plaintext
        self.assertNotIn(b"Sensitive", target._notes_encrypted)
        self.assertNotIn(b"client", target._notes_encrypted)
        self.assertNotIn(b"information", target._notes_encrypted)


# --- MultiFernet key rotation tests ---

KEY_A = Fernet.generate_key().decode()
KEY_B = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=KEY_A)
class MultiFernetRotationTest(TestCase):
    """Test key rotation using comma-separated FIELD_ENCRYPTION_KEY."""

    def setUp(self):
        enc_module._fernet = None

    def tearDown(self):
        enc_module._fernet = None

    def test_single_key_still_works(self):
        """A single key (no comma) works exactly as before."""
        plaintext = "Single key test"
        ciphertext = encrypt_field(plaintext)
        self.assertEqual(decrypt_field(ciphertext), plaintext)

    @override_settings(FIELD_ENCRYPTION_KEY=f"{KEY_B},{KEY_A}")
    def test_data_encrypted_with_old_key_decrypts_with_new_primary(self):
        """Data encrypted with KEY_A can be decrypted when KEY_B is primary."""
        # Encrypt with KEY_A (single key)
        enc_module._fernet = None
        with self.settings(FIELD_ENCRYPTION_KEY=KEY_A):
            enc_module._fernet = None
            ciphertext = encrypt_field("Old key data")

        # Now switch to KEY_B as primary, KEY_A as secondary
        enc_module._fernet = None
        result = decrypt_field(ciphertext)
        self.assertEqual(result, "Old key data")

    @override_settings(FIELD_ENCRYPTION_KEY=f"{KEY_B},{KEY_A}")
    def test_new_encryption_uses_primary_key(self):
        """New data is encrypted with the first (primary) key."""
        enc_module._fernet = None
        ciphertext = encrypt_field("New data")

        # Should decrypt with KEY_B alone (the primary key)
        enc_module._fernet = None
        with self.settings(FIELD_ENCRYPTION_KEY=KEY_B):
            enc_module._fernet = None
            result = decrypt_field(ciphertext)
            self.assertEqual(result, "New data")

    @override_settings(FIELD_ENCRYPTION_KEY=f"{KEY_A},{KEY_B}")
    def test_multiple_keys_round_trip(self):
        """Encrypt/decrypt round-trip works with multiple keys."""
        enc_module._fernet = None
        plaintext = "Éloïse Côté-Tremblay — données personnelles"
        ciphertext = encrypt_field(plaintext)
        self.assertEqual(decrypt_field(ciphertext), plaintext)

    @override_settings(FIELD_ENCRYPTION_KEY=f" {KEY_A} , {KEY_B} ")
    def test_whitespace_in_key_string_is_trimmed(self):
        """Spaces around keys and commas are handled gracefully."""
        enc_module._fernet = None
        ciphertext = encrypt_field("Whitespace test")
        self.assertEqual(decrypt_field(ciphertext), "Whitespace test")


# --- PlanTarget encryption tests (SEC-FIX1) ---

@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class PlanTargetEncryptionTest(TestCase):
    """Test that PlanTarget name, description, status_reason are encrypted."""

    def setUp(self):
        enc_module._fernet = None

    def tearDown(self):
        enc_module._fernet = None

    def test_name_encryption_on_write(self):
        from apps.plans.models import PlanTarget

        target = PlanTarget()
        target.name = "Manage anxiety and panic attacks"

        self.assertIsInstance(target._name_encrypted, bytes)
        self.assertNotIn(b"anxiety", target._name_encrypted)

    def test_name_decryption_on_read(self):
        from apps.plans.models import PlanTarget

        target = PlanTarget()
        target.name = "Manage anxiety and panic attacks"
        self.assertEqual(target.name, "Manage anxiety and panic attacks")

    def test_description_encryption_on_write(self):
        from apps.plans.models import PlanTarget

        target = PlanTarget()
        target.description = "Work on breathing techniques and grounding exercises"

        self.assertIsInstance(target._description_encrypted, bytes)
        self.assertNotIn(b"breathing", target._description_encrypted)

    def test_description_decryption_on_read(self):
        from apps.plans.models import PlanTarget

        target = PlanTarget()
        target.description = "Work on breathing techniques and grounding exercises"
        self.assertEqual(target.description, "Work on breathing techniques and grounding exercises")

    def test_status_reason_encryption_on_write(self):
        from apps.plans.models import PlanTarget

        target = PlanTarget()
        target.status_reason = "Client requested to focus on employment first"

        self.assertIsInstance(target._status_reason_encrypted, bytes)
        self.assertNotIn(b"employment", target._status_reason_encrypted)

    def test_status_reason_decryption_on_read(self):
        from apps.plans.models import PlanTarget

        target = PlanTarget()
        target.status_reason = "Client requested to focus on employment first"
        self.assertEqual(target.status_reason, "Client requested to focus on employment first")

    def test_empty_and_none_handling(self):
        from apps.plans.models import PlanTarget

        target = PlanTarget()
        target.name = ""
        target.description = None
        target.status_reason = ""

        self.assertEqual(target._name_encrypted, b"")
        self.assertEqual(target._description_encrypted, b"")
        self.assertEqual(target._status_reason_encrypted, b"")
        self.assertEqual(target.name, "")
        self.assertEqual(target.description, "")
        self.assertEqual(target.status_reason, "")

    def test_unicode_round_trip(self):
        from apps.plans.models import PlanTarget

        target = PlanTarget()
        target.name = "Réduire la consommation d'alcool — objectif prioritaire"
        target.description = "Travailler avec l'équipe de soutien"

        self.assertEqual(target.name, "Réduire la consommation d'alcool — objectif prioritaire")
        self.assertEqual(target.description, "Travailler avec l'équipe de soutien")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class PlanTargetRevisionEncryptionTest(TestCase):
    """Test that PlanTargetRevision name, description, status_reason are encrypted."""

    def setUp(self):
        enc_module._fernet = None

    def tearDown(self):
        enc_module._fernet = None

    def test_name_encryption_on_write(self):
        from apps.plans.models import PlanTargetRevision

        rev = PlanTargetRevision()
        rev.name = "Original goal text"

        self.assertIsInstance(rev._name_encrypted, bytes)
        self.assertNotIn(b"Original", rev._name_encrypted)

    def test_name_decryption_on_read(self):
        from apps.plans.models import PlanTargetRevision

        rev = PlanTargetRevision()
        rev.name = "Original goal text"
        self.assertEqual(rev.name, "Original goal text")

    def test_description_round_trip(self):
        from apps.plans.models import PlanTargetRevision

        rev = PlanTargetRevision()
        rev.description = "Detailed plan for housing stability"
        self.assertEqual(rev.description, "Detailed plan for housing stability")
        self.assertNotIn(b"housing", rev._description_encrypted)

    def test_status_reason_round_trip(self):
        from apps.plans.models import PlanTargetRevision

        rev = PlanTargetRevision()
        rev.status_reason = "Target completed — client met all goals"
        self.assertEqual(rev.status_reason, "Target completed — client met all goals")
        self.assertNotIn(b"completed", rev._status_reason_encrypted)
