"""Tests for Canadian localisation (I18N5, I18N5a, I18N5b, I18N5c, I18N-FIX2).

Covers:
- Postal code validation and normalisation (I18N5)
- Province/Territory field in seed data (I18N5a)
- Phone number validation and normalisation (I18N5b)
- Date and currency locale settings (I18N5c)
- validation_type field on CustomFieldDefinition (I18N-FIX2)
"""
from django.core.exceptions import ValidationError
from django.test import TestCase, Client, override_settings
from cryptography.fernet import Fernet

from apps.auth_app.models import User
from apps.clients.models import (
    ClientFile, ClientProgramEnrolment,
    CustomFieldGroup, CustomFieldDefinition, ClientDetailValue,
)
from apps.clients.validators import (
    validate_postal_code, normalize_postal_code,
    validate_phone_number, normalize_phone_number,
    is_postal_code_field, is_phone_field,
    detect_validation_type,
)
from apps.programs.models import Program, UserProgramRole
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


# ---------------------------------------------------------------------------
# I18N5: Postal Code Tests
# ---------------------------------------------------------------------------

class PostalCodeValidationTest(TestCase):
    """Unit tests for Canadian postal code validation."""

    def test_valid_with_space(self):
        """Standard format A1A 1A1 passes validation."""
        validate_postal_code("K1A 0B1")  # Parliament Hill

    def test_valid_without_space(self):
        """Compact format A1A1A1 passes validation."""
        validate_postal_code("K1A0B1")

    def test_valid_lowercase(self):
        """Lowercase letters pass validation."""
        validate_postal_code("k1a 0b1")

    def test_valid_mixed_case(self):
        """Mixed case passes validation."""
        validate_postal_code("k1A0b1")

    def test_invalid_format(self):
        """Invalid formats raise ValidationError."""
        invalid_codes = [
            "12345",         # US zip code
            "K1A0B",         # too short
            "K1A 0B1X",     # too long
            "111 222",       # all digits
            "ABC DEF",       # all letters
            "K1A  0B1",     # double space
            "",              # empty (should NOT raise — optional)
        ]
        for code in invalid_codes:
            if code == "":
                # Empty should pass (optional field)
                validate_postal_code(code)
                continue
            with self.assertRaises(ValidationError, msg=f"Should reject: '{code}'"):
                validate_postal_code(code)

    def test_empty_passes(self):
        """Empty string passes validation (field may be optional)."""
        validate_postal_code("")
        validate_postal_code(None)


class PostalCodeNormalisationTest(TestCase):
    """Unit tests for postal code normalisation."""

    def test_normalise_with_space(self):
        self.assertEqual(normalize_postal_code("k1a 0b1"), "K1A 0B1")

    def test_normalise_without_space(self):
        self.assertEqual(normalize_postal_code("k1a0b1"), "K1A 0B1")

    def test_normalise_uppercase(self):
        self.assertEqual(normalize_postal_code("K1A0B1"), "K1A 0B1")

    def test_normalise_with_extra_whitespace(self):
        self.assertEqual(normalize_postal_code("  k1a 0b1  "), "K1A 0B1")

    def test_normalise_empty(self):
        self.assertEqual(normalize_postal_code(""), "")
        self.assertEqual(normalize_postal_code(None), "")


# ---------------------------------------------------------------------------
# I18N5b: Phone Number Tests
# ---------------------------------------------------------------------------

class PhoneValidationTest(TestCase):
    """Unit tests for Canadian phone number validation."""

    def test_valid_formats(self):
        """All common Canadian phone formats should pass."""
        valid_numbers = [
            "(613) 555-1234",
            "613-555-1234",
            "6135551234",
            "613.555.1234",
            "+1 613 555 1234",
            "+16135551234",
            "1-613-555-1234",
            "1 (613) 555-1234",
            "(416) 555-0123",
        ]
        for num in valid_numbers:
            validate_phone_number(num)  # Should not raise

    def test_invalid_numbers(self):
        """Invalid phone numbers should raise ValidationError."""
        invalid_numbers = [
            "555-1234",       # only 7 digits
            "12345",          # too short
            "12345678901234", # too long
        ]
        for num in invalid_numbers:
            with self.assertRaises(ValidationError, msg=f"Should reject: '{num}'"):
                validate_phone_number(num)

    def test_empty_passes(self):
        """Empty string passes (phone may be optional)."""
        validate_phone_number("")
        validate_phone_number(None)


class PhoneNormalisationTest(TestCase):
    """Unit tests for phone number normalisation."""

    def test_normalise_parentheses_format(self):
        self.assertEqual(normalize_phone_number("(613) 555-1234"), "(613) 555-1234")

    def test_normalise_dashes(self):
        self.assertEqual(normalize_phone_number("613-555-1234"), "(613) 555-1234")

    def test_normalise_digits_only(self):
        self.assertEqual(normalize_phone_number("6135551234"), "(613) 555-1234")

    def test_normalise_dots(self):
        self.assertEqual(normalize_phone_number("613.555.1234"), "(613) 555-1234")

    def test_normalise_with_country_code(self):
        self.assertEqual(normalize_phone_number("+1 613 555 1234"), "(613) 555-1234")
        self.assertEqual(normalize_phone_number("+16135551234"), "(613) 555-1234")
        self.assertEqual(normalize_phone_number("1-613-555-1234"), "(613) 555-1234")

    def test_normalise_with_whitespace(self):
        self.assertEqual(normalize_phone_number("  (416) 555-0123  "), "(416) 555-0123")

    def test_normalise_empty(self):
        self.assertEqual(normalize_phone_number(""), "")
        self.assertEqual(normalize_phone_number(None), "")


# ---------------------------------------------------------------------------
# Field Name Matching Tests
# ---------------------------------------------------------------------------

class FieldNameMatchingTest(TestCase):
    """Tests for field name detection helpers (legacy) and detect_validation_type."""

    # Legacy helpers (deprecated but still functional)
    def test_postal_code_field_names(self):
        self.assertTrue(is_postal_code_field("Postal Code"))
        self.assertFalse(is_postal_code_field("Zip Code"))
        self.assertFalse(is_postal_code_field("Phone"))

    def test_phone_field_names(self):
        self.assertTrue(is_phone_field("Primary Phone"))
        self.assertTrue(is_phone_field("Secondary Phone"))
        self.assertTrue(is_phone_field("Emergency Contact Phone"))
        self.assertTrue(is_phone_field("Parent/Guardian Phone"))
        self.assertTrue(is_phone_field("Secondary Parent/Guardian Phone"))
        self.assertFalse(is_phone_field("Email"))
        self.assertFalse(is_phone_field("Preferred Contact Method"))

    # New detect_validation_type function (I18N-FIX2)
    def test_detect_postal_code(self):
        """detect_validation_type returns 'postal_code' for postal-related names."""
        self.assertEqual(detect_validation_type("Postal Code"), "postal_code")
        self.assertEqual(detect_validation_type("Code postal"), "postal_code")
        self.assertEqual(detect_validation_type("Zip Code"), "postal_code")  # contains "zip"

    def test_detect_phone(self):
        """detect_validation_type returns 'phone' for phone-related names."""
        self.assertEqual(detect_validation_type("Primary Phone"), "phone")
        self.assertEqual(detect_validation_type("Emergency Contact Phone"), "phone")
        self.assertEqual(detect_validation_type("Téléphone principal"), "phone")
        self.assertEqual(detect_validation_type("Home Tel"), "phone")

    def test_detect_none(self):
        """detect_validation_type returns 'none' for unrecognised names."""
        self.assertEqual(detect_validation_type("Email"), "none")
        self.assertEqual(detect_validation_type("Preferred Name"), "none")
        self.assertEqual(detect_validation_type("Pronouns"), "none")


# ---------------------------------------------------------------------------
# I18N-FIX2: validation_type Model Field Tests
# ---------------------------------------------------------------------------

@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ValidationTypeModelTest(TestCase):
    """Tests for the validation_type field on CustomFieldDefinition."""

    def setUp(self):
        enc_module._fernet = None
        self.group = CustomFieldGroup.objects.create(title="Test Group")

    def test_auto_detect_postal_code_on_save(self):
        """Field named 'Postal Code' auto-detects validation_type on save."""
        field_def = CustomFieldDefinition.objects.create(
            group=self.group, name="Postal Code", input_type="text",
        )
        self.assertEqual(field_def.validation_type, "postal_code")

    def test_auto_detect_phone_on_save(self):
        """Field named 'Primary Phone' auto-detects validation_type on save."""
        field_def = CustomFieldDefinition.objects.create(
            group=self.group, name="Primary Phone", input_type="text",
        )
        self.assertEqual(field_def.validation_type, "phone")

    def test_no_auto_detect_for_generic_field(self):
        """Generic field names keep validation_type='none'."""
        field_def = CustomFieldDefinition.objects.create(
            group=self.group, name="Email", input_type="text",
        )
        self.assertEqual(field_def.validation_type, "none")

    def test_explicit_validation_type_not_overridden(self):
        """Explicitly set validation_type is not overridden by auto-detection."""
        field_def = CustomFieldDefinition(
            group=self.group, name="Primary Phone", input_type="text",
            validation_type="postal_code",  # intentionally wrong — should be preserved
        )
        field_def.save()
        self.assertEqual(field_def.validation_type, "postal_code")

    def test_french_postal_code_auto_detected(self):
        """French field name 'Code postal' auto-detects as postal_code."""
        field_def = CustomFieldDefinition.objects.create(
            group=self.group, name="Code postal", input_type="text",
        )
        self.assertEqual(field_def.validation_type, "postal_code")


# ---------------------------------------------------------------------------
# I18N5 + I18N5b: Integration test — save custom field values view
# ---------------------------------------------------------------------------

@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class CustomFieldNormalisationIntegrationTest(TestCase):
    """Integration tests for postal code and phone normalisation on save."""

    def setUp(self):
        enc_module._fernet = None
        self.client = Client()
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True
        )
        self.program = Program.objects.create(name="Test Program", colour_hex="#10B981")
        UserProgramRole.objects.create(
            user=self.admin, program=self.program, role="program_manager"
        )
        self.group = CustomFieldGroup.objects.create(title="Contact Information")
        self.postal_field = CustomFieldDefinition.objects.create(
            group=self.group, name="Postal Code", input_type="text",
            is_sensitive=False, front_desk_access="edit",
        )
        self.phone_field = CustomFieldDefinition.objects.create(
            group=self.group, name="Primary Phone", input_type="text",
            is_sensitive=True, front_desk_access="edit",
        )
        self.cf = ClientFile()
        self.cf.first_name = "Jane"
        self.cf.last_name = "Doe"
        self.cf.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.cf, program=self.program
        )
        self.client.login(username="admin", password="testpass123")

    def test_postal_code_normalised_on_save(self):
        """Postal code is normalised to 'A1A 1A1' when saved."""
        resp = self.client.post(
            f"/clients/{self.cf.pk}/custom-fields/",
            {
                f"custom_{self.postal_field.pk}": "k1a0b1",
                f"custom_{self.phone_field.pk}": "",
            },
        )
        self.assertIn(resp.status_code, [200, 302])
        cdv = ClientDetailValue.objects.get(
            client_file=self.cf, field_def=self.postal_field
        )
        self.assertEqual(cdv.get_value(), "K1A 0B1")

    def test_phone_normalised_on_save(self):
        """Phone number is normalised to '(XXX) XXX-XXXX' when saved."""
        resp = self.client.post(
            f"/clients/{self.cf.pk}/custom-fields/",
            {
                f"custom_{self.postal_field.pk}": "",
                f"custom_{self.phone_field.pk}": "613-555-1234",
            },
        )
        self.assertIn(resp.status_code, [200, 302])
        cdv = ClientDetailValue.objects.get(
            client_file=self.cf, field_def=self.phone_field
        )
        self.assertEqual(cdv.get_value(), "(613) 555-1234")

    def test_phone_with_country_code_normalised(self):
        """Phone with +1 country code is normalised correctly."""
        resp = self.client.post(
            f"/clients/{self.cf.pk}/custom-fields/",
            {
                f"custom_{self.postal_field.pk}": "",
                f"custom_{self.phone_field.pk}": "+1 416 555 0123",
            },
        )
        self.assertIn(resp.status_code, [200, 302])
        cdv = ClientDetailValue.objects.get(
            client_file=self.cf, field_def=self.phone_field
        )
        self.assertEqual(cdv.get_value(), "(416) 555-0123")

    def test_invalid_postal_code_shows_error(self):
        """Invalid postal code shows an error message, does not save."""
        resp = self.client.post(
            f"/clients/{self.cf.pk}/custom-fields/",
            {
                f"custom_{self.postal_field.pk}": "12345",
                f"custom_{self.phone_field.pk}": "",
            },
        )
        self.assertIn(resp.status_code, [200, 302])
        # The postal code value should NOT have been saved
        exists = ClientDetailValue.objects.filter(
            client_file=self.cf, field_def=self.postal_field
        ).exists()
        self.assertFalse(exists)

    def test_invalid_phone_shows_error(self):
        """Invalid phone number shows an error message, does not save."""
        resp = self.client.post(
            f"/clients/{self.cf.pk}/custom-fields/",
            {
                f"custom_{self.postal_field.pk}": "",
                f"custom_{self.phone_field.pk}": "555",
            },
        )
        self.assertIn(resp.status_code, [200, 302])
        # The phone value should NOT have been saved
        exists = ClientDetailValue.objects.filter(
            client_file=self.cf, field_def=self.phone_field
        ).exists()
        self.assertFalse(exists)


# ---------------------------------------------------------------------------
# I18N5a: Province/Territory Seed Data Test
# ---------------------------------------------------------------------------

class ProvinceTerritorySeedTest(TestCase):
    """Test that Province or Territory field is included in seed data."""

    def test_province_field_in_seed_data(self):
        """The seed data should include a 'Province or Territory' field."""
        from apps.clients.management.commands.seed_intake_fields import INTAKE_FIELD_GROUPS

        province_field_found = False
        province_options = None
        for group_title, sort_order, fields in INTAKE_FIELD_GROUPS:
            for field_data in fields:
                name = field_data[0]
                if name == "Province or Territory":
                    province_field_found = True
                    province_options = field_data[6]  # options list
                    break
            if province_field_found:
                break

        self.assertTrue(province_field_found, "Province or Territory field missing from seed data")
        # Check that all 13 provinces and territories are listed
        self.assertEqual(len(province_options), 13, "Should have all 13 provinces and territories")
        self.assertIn("Ontario", province_options)
        self.assertIn("Quebec", province_options)
        self.assertIn("British Columbia", province_options)
        self.assertIn("Nunavut", province_options)
        self.assertIn("Yukon", province_options)

    def test_province_field_is_select_type(self):
        """Province or Territory should be a dropdown (select) field."""
        from apps.clients.management.commands.seed_intake_fields import INTAKE_FIELD_GROUPS

        for group_title, sort_order, fields in INTAKE_FIELD_GROUPS:
            for field_data in fields:
                if field_data[0] == "Province or Territory":
                    self.assertEqual(field_data[1], "select")
                    return
        self.fail("Province or Territory field not found")

    def test_province_in_contact_information_group(self):
        """Province or Territory should be in the Contact Information group."""
        from apps.clients.management.commands.seed_intake_fields import INTAKE_FIELD_GROUPS

        for group_title, sort_order, fields in INTAKE_FIELD_GROUPS:
            if group_title == "Contact Information":
                field_names = [f[0] for f in fields]
                self.assertIn("Province or Territory", field_names)
                return
        self.fail("Contact Information group not found")


# ---------------------------------------------------------------------------
# I18N5c: Date and Currency Locale Tests
# ---------------------------------------------------------------------------

class DateCurrencyLocaleTest(TestCase):
    """Tests for locale-aware date and currency formatting settings."""

    def test_format_module_path_configured(self):
        """FORMAT_MODULE_PATH should point to konote.formats."""
        from django.conf import settings
        self.assertIn("konote.formats", settings.FORMAT_MODULE_PATH)

    def test_use_l10n_enabled(self):
        """USE_L10N should be True for locale-aware formatting."""
        from django.conf import settings
        self.assertTrue(settings.USE_L10N)

    def test_english_date_format(self):
        """English format module should use human-readable date format."""
        from konote.formats.en.formats import DATE_FORMAT
        self.assertEqual(DATE_FORMAT, "N j, Y")

    def test_french_date_format(self):
        """French format module should use human-readable date format."""
        from konote.formats.fr.formats import DATE_FORMAT
        self.assertEqual(DATE_FORMAT, "j N Y")

    def test_english_number_format(self):
        """English format should use period as decimal separator."""
        from konote.formats.en.formats import DECIMAL_SEPARATOR, THOUSAND_SEPARATOR
        self.assertEqual(DECIMAL_SEPARATOR, ".")
        self.assertEqual(THOUSAND_SEPARATOR, ",")

    def test_french_number_format(self):
        """French format should use comma as decimal separator."""
        from konote.formats.fr.formats import DECIMAL_SEPARATOR
        self.assertEqual(DECIMAL_SEPARATOR, ",")

    def test_date_format_renders_correctly(self):
        """Django's date formatting should use our custom human-readable format."""
        from django.utils import formats, translation
        import datetime

        test_date = datetime.date(2026, 2, 5)

        with translation.override("en"):
            formatted = formats.date_format(test_date, "DATE_FORMAT")
            self.assertEqual(formatted, "Feb. 5, 2026")

        with translation.override("fr"):
            formatted = formats.date_format(test_date, "DATE_FORMAT")
            self.assertIn("5", formatted)  # Day
            self.assertIn("2026", formatted)  # Year
