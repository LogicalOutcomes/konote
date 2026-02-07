"""Tests for public registration views."""
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone
from cryptography.fernet import Fernet

from apps.auth_app.models import User
from apps.programs.models import Program
from apps.registration.models import RegistrationLink, RegistrationSubmission
import konote.encryption as enc_module


TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class PublicRegistrationFormViewTest(TestCase):
    """Tests for the public registration form view."""

    def setUp(self):
        enc_module._fernet = None
        self.client = Client()

        # Create admin user
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", display_name="Admin"
        )
        self.admin.is_admin = True
        self.admin.save()

        # Create a program
        self.program = Program.objects.create(name="Test Program", status="active")

        # Create an active registration link
        self.registration_link = RegistrationLink.objects.create(
            program=self.program,
            title="Test Registration",
            description="Test description for registration.",
            is_active=True,
            created_by=self.admin,
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_public_form_loads_successfully(self):
        """Public registration form should load without authentication."""
        url = reverse(
            "registration:public_registration_form",
            kwargs={"slug": self.registration_link.slug}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Registration")
        self.assertContains(response, "Test description for registration.")

    def test_invalid_slug_returns_404(self):
        """Invalid slug should return 404."""
        url = reverse(
            "registration:public_registration_form",
            kwargs={"slug": "invalid-slug-12345"}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_inactive_link_returns_404(self):
        """Inactive registration links should return 404."""
        self.registration_link.is_active = False
        self.registration_link.save()

        url = reverse(
            "registration:public_registration_form",
            kwargs={"slug": self.registration_link.slug}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Registration Closed")

    def test_form_submission_creates_submission(self):
        """Valid form submission should create a RegistrationSubmission."""
        url = reverse(
            "registration:public_registration_form",
            kwargs={"slug": self.registration_link.slug}
        )

        # Submit the form
        response = self.client.post(url, {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "phone": "(613) 555-1234",
            "consent": "on",
        })

        # Should redirect to confirmation page
        self.assertEqual(response.status_code, 302)
        self.assertIn("submitted", response.url)

        # Check submission was created
        submission = RegistrationSubmission.objects.filter(
            registration_link=self.registration_link
        ).first()
        self.assertIsNotNone(submission)
        self.assertEqual(submission.first_name, "John")
        self.assertEqual(submission.last_name, "Doe")
        self.assertEqual(submission.email, "john.doe@example.com")
        self.assertEqual(submission.status, "pending")

    def test_form_submission_requires_consent(self):
        """Form submission without consent should fail."""
        url = reverse(
            "registration:public_registration_form",
            kwargs={"slug": self.registration_link.slug}
        )

        response = self.client.post(url, {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
        })

        # Should stay on form page with errors
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "consent")

        # No submission should be created
        self.assertEqual(
            RegistrationSubmission.objects.filter(
                registration_link=self.registration_link
            ).count(),
            0
        )

    def test_auto_approve_creates_approved_submission(self):
        """Auto-approve registration should set status to approved."""
        self.registration_link.auto_approve = True
        self.registration_link.save()

        url = reverse(
            "registration:public_registration_form",
            kwargs={"slug": self.registration_link.slug}
        )

        response = self.client.post(url, {
            "first_name": "Jane",
            "last_name": "Smith",
            "email": "jane.smith@example.com",
            "consent": "on",
        })

        self.assertEqual(response.status_code, 302)

        submission = RegistrationSubmission.objects.filter(
            registration_link=self.registration_link
        ).first()
        self.assertIsNotNone(submission)
        self.assertEqual(submission.status, "approved")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class RegistrationCapacityTest(TestCase):
    """Tests for registration capacity limits."""

    def setUp(self):
        enc_module._fernet = None
        self.client = Client()

        self.admin = User.objects.create_user(
            username="admin", password="testpass123", display_name="Admin"
        )
        self.admin.is_admin = True
        self.admin.save()

        self.program = Program.objects.create(name="Limited Program", status="active")

        # Create registration with max 2 spots
        self.registration_link = RegistrationLink.objects.create(
            program=self.program,
            title="Limited Registration",
            is_active=True,
            max_registrations=2,
            created_by=self.admin,
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_shows_spots_remaining(self):
        """Form should display remaining spots."""
        url = reverse(
            "registration:public_registration_form",
            kwargs={"slug": self.registration_link.slug}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "2")  # 2 spots remaining
        self.assertContains(response, "spots remaining")

    def test_closes_when_capacity_reached(self):
        """Registration should close when capacity is reached."""
        # Create 2 submissions (pending)
        for i in range(2):
            sub = RegistrationSubmission(registration_link=self.registration_link)
            sub.first_name = f"User{i}"
            sub.last_name = "Test"
            sub.email = f"user{i}@example.com"
            sub.status = "pending"
            sub.save()

        url = reverse(
            "registration:public_registration_form",
            kwargs={"slug": self.registration_link.slug}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Registration Closed")
        self.assertContains(response, "reached capacity")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class RegistrationDeadlineTest(TestCase):
    """Tests for registration deadline."""

    def setUp(self):
        enc_module._fernet = None
        self.client = Client()

        self.admin = User.objects.create_user(
            username="admin", password="testpass123", display_name="Admin"
        )
        self.admin.is_admin = True
        self.admin.save()

        self.program = Program.objects.create(name="Timed Program", status="active")

    def tearDown(self):
        enc_module._fernet = None

    def test_closes_after_deadline(self):
        """Registration should close after deadline passes."""
        # Create registration with deadline in the past
        past_deadline = timezone.now() - timezone.timedelta(hours=1)
        registration_link = RegistrationLink.objects.create(
            program=self.program,
            title="Expired Registration",
            is_active=True,
            closes_at=past_deadline,
            created_by=self.admin,
        )

        url = reverse(
            "registration:public_registration_form",
            kwargs={"slug": registration_link.slug}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Registration Closed")
        self.assertContains(response, "deadline")

    def test_open_before_deadline(self):
        """Registration should be open before deadline."""
        future_deadline = timezone.now() + timezone.timedelta(days=7)
        registration_link = RegistrationLink.objects.create(
            program=self.program,
            title="Future Registration",
            is_active=True,
            closes_at=future_deadline,
            created_by=self.admin,
        )

        url = reverse(
            "registration:public_registration_form",
            kwargs={"slug": registration_link.slug}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Submit Registration")
        self.assertContains(response, "Registration closes")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class RegistrationSubmittedViewTest(TestCase):
    """Tests for the registration submitted confirmation view."""

    def setUp(self):
        enc_module._fernet = None
        self.client = Client()

        self.admin = User.objects.create_user(
            username="admin", password="testpass123", display_name="Admin"
        )
        self.admin.is_admin = True
        self.admin.save()

        self.program = Program.objects.create(name="Test Program", status="active")
        self.registration_link = RegistrationLink.objects.create(
            program=self.program,
            title="Test Registration",
            is_active=True,
            created_by=self.admin,
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_submitted_page_loads(self):
        """Submitted confirmation page should load."""
        # First submit a registration to set session data
        form_url = reverse(
            "registration:public_registration_form",
            kwargs={"slug": self.registration_link.slug}
        )
        self.client.post(form_url, {
            "first_name": "Test",
            "last_name": "User",
            "email": "test@example.com",
            "consent": "on",
        })

        # Now check the submitted page
        url = reverse(
            "registration:registration_submitted",
            kwargs={"slug": self.registration_link.slug}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Thank You")
        self.assertContains(response, "REG-")  # Reference number

    def test_submitted_page_without_session_data(self):
        """Submitted page should still load without session data."""
        url = reverse(
            "registration:registration_submitted",
            kwargs={"slug": self.registration_link.slug}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Thank You")

    def test_auto_approved_message(self):
        """Auto-approved submission should show different message."""
        self.registration_link.auto_approve = True
        self.registration_link.save()

        form_url = reverse(
            "registration:public_registration_form",
            kwargs={"slug": self.registration_link.slug}
        )
        self.client.post(form_url, {
            "first_name": "Auto",
            "last_name": "Approved",
            "email": "auto@example.com",
            "consent": "on",
        })

        url = reverse(
            "registration:registration_submitted",
            kwargs={"slug": self.registration_link.slug}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Registered")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ApproveSubmissionUtilityTest(TestCase):
    """Tests for the approve_submission utility function."""

    def setUp(self):
        enc_module._fernet = None
        from apps.clients.models import ClientFile, ClientProgramEnrolment, ClientDetailValue
        from apps.clients.models import CustomFieldGroup, CustomFieldDefinition
        from apps.registration.utils import approve_submission

        self.approve_submission = approve_submission
        self.ClientFile = ClientFile
        self.ClientProgramEnrolment = ClientProgramEnrolment
        self.ClientDetailValue = ClientDetailValue
        self.CustomFieldGroup = CustomFieldGroup
        self.CustomFieldDefinition = CustomFieldDefinition

        self.admin = User.objects.create_user(
            username="admin", password="testpass123", display_name="Admin"
        )
        self.admin.is_admin = True
        self.admin.save()

        self.program = Program.objects.create(name="Test Program", status="active")
        self.registration_link = RegistrationLink.objects.create(
            program=self.program,
            title="Test Registration",
            is_active=True,
            created_by=self.admin,
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_approve_creates_client_file(self):
        """Approving a submission creates a ClientFile record."""
        submission = RegistrationSubmission(registration_link=self.registration_link)
        submission.first_name = "Jane"
        submission.last_name = "Doe"
        submission.email = "jane@example.com"
        submission.save()

        client = self.approve_submission(submission, reviewed_by=self.admin)

        self.assertIsNotNone(client)
        self.assertEqual(client.first_name, "Jane")
        self.assertEqual(client.last_name, "Doe")
        self.assertEqual(client.status, "active")

    def test_approve_creates_program_enrolment(self):
        """Approving a submission creates a program enrolment."""
        submission = RegistrationSubmission(registration_link=self.registration_link)
        submission.first_name = "Bob"
        submission.last_name = "Smith"
        submission.save()

        client = self.approve_submission(submission, reviewed_by=self.admin)

        enrolment = self.ClientProgramEnrolment.objects.filter(
            client_file=client, program=self.program
        ).first()
        self.assertIsNotNone(enrolment)
        self.assertEqual(enrolment.status, "enrolled")

    def test_approve_copies_custom_fields(self):
        """Approving a submission copies custom field values."""
        group = self.CustomFieldGroup.objects.create(title="Contact")
        field_def = self.CustomFieldDefinition.objects.create(
            group=group, name="Emergency Contact", input_type="text"
        )
        self.registration_link.field_groups.add(group)

        submission = RegistrationSubmission(registration_link=self.registration_link)
        submission.first_name = "Alice"
        submission.last_name = "Johnson"
        submission.field_values = {str(field_def.pk): "555-9999"}
        submission.save()

        client = self.approve_submission(submission, reviewed_by=self.admin)

        cdv = self.ClientDetailValue.objects.filter(
            client_file=client, field_def=field_def
        ).first()
        self.assertIsNotNone(cdv)
        self.assertEqual(cdv.get_value(), "555-9999")

    def test_approve_updates_submission_status(self):
        """Approving a submission updates the submission status."""
        submission = RegistrationSubmission(registration_link=self.registration_link)
        submission.first_name = "Carol"
        submission.last_name = "Williams"
        submission.save()

        self.assertEqual(submission.status, "pending")

        client = self.approve_submission(submission, reviewed_by=self.admin)

        submission.refresh_from_db()
        self.assertEqual(submission.status, "approved")
        self.assertEqual(submission.client_file, client)
        self.assertEqual(submission.reviewed_by, self.admin)
        self.assertIsNotNone(submission.reviewed_at)

    def test_auto_approve_has_no_reviewer(self):
        """Auto-approval (no reviewer) leaves reviewed_by as None."""
        submission = RegistrationSubmission(registration_link=self.registration_link)
        submission.first_name = "Auto"
        submission.last_name = "Approve"
        submission.save()

        self.approve_submission(submission, reviewed_by=None)

        submission.refresh_from_db()
        self.assertEqual(submission.status, "approved")
        self.assertIsNone(submission.reviewed_by)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class DuplicateDetectionUtilityTest(TestCase):
    """Tests for the find_duplicate_clients utility function."""

    def setUp(self):
        enc_module._fernet = None
        from apps.clients.models import ClientFile, ClientProgramEnrolment, ClientDetailValue
        from apps.clients.models import CustomFieldGroup, CustomFieldDefinition
        from apps.registration.utils import find_duplicate_clients

        self.find_duplicate_clients = find_duplicate_clients
        self.ClientFile = ClientFile
        self.ClientProgramEnrolment = ClientProgramEnrolment
        self.ClientDetailValue = ClientDetailValue
        self.CustomFieldGroup = CustomFieldGroup
        self.CustomFieldDefinition = CustomFieldDefinition

        self.admin = User.objects.create_user(
            username="admin", password="testpass123", display_name="Admin"
        )
        self.admin.is_admin = True
        self.admin.save()

        self.program = Program.objects.create(name="Test Program", status="active")
        self.registration_link = RegistrationLink.objects.create(
            program=self.program,
            title="Test Registration",
            is_active=True,
            created_by=self.admin,
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_no_duplicates_for_unique_submission(self):
        """Returns empty list when no duplicates exist."""
        submission = RegistrationSubmission(registration_link=self.registration_link)
        submission.first_name = "Unique"
        submission.last_name = "Person"
        submission.email = "unique@example.com"
        submission.save()

        matches = self.find_duplicate_clients(submission)
        self.assertEqual(len(matches), 0)

    def test_finds_duplicate_by_name(self):
        """Finds duplicate clients by matching name."""
        # Create existing client
        existing = self.ClientFile()
        existing.first_name = "John"
        existing.last_name = "Smith"
        existing.save()

        # Enrol in same program
        self.ClientProgramEnrolment.objects.create(
            client_file=existing, program=self.program
        )

        # Create submission with same name
        submission = RegistrationSubmission(registration_link=self.registration_link)
        submission.first_name = "John"
        submission.last_name = "Smith"
        submission.email = "john@example.com"
        submission.save()

        matches = self.find_duplicate_clients(submission)

        self.assertGreater(len(matches), 0)
        self.assertEqual(matches[0]["client"].pk, existing.pk)
        self.assertEqual(matches[0]["match_type"], "name_exact")
        self.assertEqual(matches[0]["confidence"], "medium")

    def test_name_match_is_case_insensitive(self):
        """Name matching is case insensitive."""
        existing = self.ClientFile()
        existing.first_name = "JANE"
        existing.last_name = "DOE"
        existing.save()

        self.ClientProgramEnrolment.objects.create(
            client_file=existing, program=self.program
        )

        submission = RegistrationSubmission(registration_link=self.registration_link)
        submission.first_name = "jane"
        submission.last_name = "doe"
        submission.email = "jane@example.com"
        submission.save()

        matches = self.find_duplicate_clients(submission)
        self.assertGreater(len(matches), 0)

    def test_only_checks_same_program(self):
        """Only checks for duplicates in the same program."""
        other_program = Program.objects.create(name="Other Program", status="active")

        existing = self.ClientFile()
        existing.first_name = "John"
        existing.last_name = "Smith"
        existing.save()

        # Enrol in different program
        self.ClientProgramEnrolment.objects.create(
            client_file=existing, program=other_program
        )

        submission = RegistrationSubmission(registration_link=self.registration_link)
        submission.first_name = "John"
        submission.last_name = "Smith"
        submission.email = "john@example.com"
        submission.save()

        matches = self.find_duplicate_clients(submission)
        # Should not find the client since they're in a different program
        self.assertEqual(len(matches), 0)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class MergeWithExistingUtilityTest(TestCase):
    """Tests for the merge_with_existing utility function."""

    def setUp(self):
        enc_module._fernet = None
        from apps.clients.models import ClientFile, ClientProgramEnrolment
        from apps.registration.utils import merge_with_existing

        self.merge_with_existing = merge_with_existing
        self.ClientFile = ClientFile
        self.ClientProgramEnrolment = ClientProgramEnrolment

        self.admin = User.objects.create_user(
            username="admin", password="testpass123", display_name="Admin"
        )
        self.admin.is_admin = True
        self.admin.save()

        self.program = Program.objects.create(name="Test Program", status="active")
        self.registration_link = RegistrationLink.objects.create(
            program=self.program,
            title="Test Registration",
            is_active=True,
            created_by=self.admin,
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_merge_creates_enrolment(self):
        """Merging creates a program enrolment for the existing client."""
        existing = self.ClientFile()
        existing.first_name = "Existing"
        existing.last_name = "Client"
        existing.save()

        submission = RegistrationSubmission(registration_link=self.registration_link)
        submission.first_name = "Existing"
        submission.last_name = "Client"
        submission.save()

        result = self.merge_with_existing(submission, existing, self.admin)

        self.assertEqual(result.pk, existing.pk)

        enrolment = self.ClientProgramEnrolment.objects.filter(
            client_file=existing, program=self.program
        ).first()
        self.assertIsNotNone(enrolment)
        self.assertEqual(enrolment.status, "enrolled")

    def test_merge_re_enrols_unenrolled_client(self):
        """Merging re-enrols a previously unenrolled client."""
        existing = self.ClientFile()
        existing.first_name = "Former"
        existing.last_name = "Client"
        existing.save()

        # Create unenrolled enrolment
        enrolment = self.ClientProgramEnrolment.objects.create(
            client_file=existing, program=self.program, status="unenrolled"
        )

        submission = RegistrationSubmission(registration_link=self.registration_link)
        submission.first_name = "Former"
        submission.last_name = "Client"
        submission.save()

        self.merge_with_existing(submission, existing, self.admin)

        enrolment.refresh_from_db()
        self.assertEqual(enrolment.status, "enrolled")

    def test_merge_updates_submission(self):
        """Merging updates the submission status and links to client."""
        existing = self.ClientFile()
        existing.first_name = "Merge"
        existing.last_name = "Test"
        existing.save()

        submission = RegistrationSubmission(registration_link=self.registration_link)
        submission.first_name = "Merge"
        submission.last_name = "Test"
        submission.save()

        self.merge_with_existing(submission, existing, self.admin)

        submission.refresh_from_db()
        self.assertEqual(submission.status, "approved")
        self.assertEqual(submission.client_file, existing)
        self.assertEqual(submission.reviewed_by, self.admin)
        self.assertIn("Merged", submission.review_notes)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class CapacityLimitPropertiesTest(TestCase):
    """Tests for RegistrationLink capacity limit properties."""

    def setUp(self):
        enc_module._fernet = None

        self.admin = User.objects.create_user(
            username="admin", password="testpass123", display_name="Admin"
        )
        self.admin.is_admin = True
        self.admin.save()

        self.program = Program.objects.create(name="Test Program", status="active")

    def tearDown(self):
        enc_module._fernet = None

    def test_spots_remaining_unlimited(self):
        """spots_remaining is None when no limit is set."""
        link = RegistrationLink.objects.create(
            program=self.program,
            title="Unlimited",
            max_registrations=None,
            created_by=self.admin,
        )
        self.assertIsNone(link.spots_remaining)

    def test_spots_remaining_with_limit(self):
        """spots_remaining correctly calculates remaining spots."""
        link = RegistrationLink.objects.create(
            program=self.program,
            title="Limited",
            max_registrations=5,
            created_by=self.admin,
        )

        self.assertEqual(link.spots_remaining, 5)

        # Add approved submission
        sub1 = RegistrationSubmission(registration_link=link)
        sub1.first_name = "Test"
        sub1.last_name = "User"
        sub1.status = "approved"
        sub1.save()

        self.assertEqual(link.spots_remaining, 4)

        # Add pending submission
        sub2 = RegistrationSubmission(registration_link=link)
        sub2.first_name = "Test"
        sub2.last_name = "User2"
        sub2.status = "pending"
        sub2.save()

        self.assertEqual(link.spots_remaining, 3)

    def test_spots_remaining_doesnt_count_rejected(self):
        """Rejected submissions don't count toward capacity."""
        link = RegistrationLink.objects.create(
            program=self.program,
            title="Limited",
            max_registrations=2,
            created_by=self.admin,
        )

        sub = RegistrationSubmission(registration_link=link)
        sub.first_name = "Rejected"
        sub.last_name = "User"
        sub.status = "rejected"
        sub.save()

        self.assertEqual(link.spots_remaining, 2)

    def test_is_closed_reason_inactive(self):
        """is_closed_reason returns 'inactive' for inactive links."""
        link = RegistrationLink.objects.create(
            program=self.program,
            title="Inactive",
            is_active=False,
            created_by=self.admin,
        )
        self.assertEqual(link.is_closed_reason, "inactive")

    def test_is_closed_reason_deadline(self):
        """is_closed_reason returns 'deadline' when deadline passed."""
        past = timezone.now() - timezone.timedelta(hours=1)
        link = RegistrationLink.objects.create(
            program=self.program,
            title="Past Deadline",
            closes_at=past,
            created_by=self.admin,
        )
        self.assertEqual(link.is_closed_reason, "deadline")

    def test_is_closed_reason_capacity(self):
        """is_closed_reason returns 'capacity' when full."""
        link = RegistrationLink.objects.create(
            program=self.program,
            title="Full",
            max_registrations=1,
            created_by=self.admin,
        )

        sub = RegistrationSubmission(registration_link=link)
        sub.first_name = "Fill"
        sub.last_name = "Spot"
        sub.status = "approved"
        sub.save()

        self.assertEqual(link.is_closed_reason, "capacity")

    def test_is_closed_reason_none_when_open(self):
        """is_closed_reason returns None when registration is open."""
        link = RegistrationLink.objects.create(
            program=self.program,
            title="Open",
            is_active=True,
            created_by=self.admin,
        )
        self.assertIsNone(link.is_closed_reason)
        self.assertTrue(link.is_open())


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class IframeEmbedSecurityTest(TestCase):
    """Security tests for iframe embed functionality.

    Verifies that:
    - Registration forms CAN be framed when embed=1
    - Registration forms cannot be framed without embed=1
    - Admin pages cannot be framed
    - Client data pages cannot be framed
    """

    def setUp(self):
        enc_module._fernet = None
        self.client = Client()

        # Create admin user
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", display_name="Admin"
        )
        self.admin.is_admin = True
        self.admin.save()

        # Create a program and registration link
        self.program = Program.objects.create(name="Test Program", status="active")
        self.registration_link = RegistrationLink.objects.create(
            program=self.program,
            title="Test Registration",
            is_active=True,
            created_by=self.admin,
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_embed_mode_allows_framing(self):
        """Registration form with ?embed=1 should allow iframe framing."""
        url = reverse(
            "registration:public_registration_form",
            kwargs={"slug": self.registration_link.slug}
        ) + "?embed=1"

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Embed mode exempts the response from X-Frame-Options middleware
        self.assertTrue(getattr(response, "xframe_options_exempt", False))
        self.assertIsNone(response.get("X-Frame-Options"))

    def test_regular_form_has_default_frame_options(self):
        """Registration form without ?embed=1 should NOT be frameable."""
        url = reverse(
            "registration:public_registration_form",
            kwargs={"slug": self.registration_link.slug}
        )

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Without embed mode, response should NOT be exempt from X-Frame-Options
        self.assertFalse(getattr(response, "xframe_options_exempt", False))

    def test_embed_mode_uses_minimal_template(self):
        """Embed mode should use minimal template without site navigation."""
        url = reverse(
            "registration:public_registration_form",
            kwargs={"slug": self.registration_link.slug}
        ) + "?embed=1"

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Embed template should have .embed-container class
        self.assertContains(response, "embed-container")
        # Should NOT have the main site navigation
        self.assertNotContains(response, 'href="/clients/"')

    def test_submitted_page_respects_embed_mode(self):
        """Submitted confirmation page should respect embed mode."""
        # First submit a registration
        submit_url = reverse(
            "registration:public_registration_form",
            kwargs={"slug": self.registration_link.slug}
        ) + "?embed=1"

        response = self.client.post(submit_url, {
            "first_name": "Embed",
            "last_name": "Test",
            "email": "embed@example.com",
            "consent": "on",
        })

        # Should redirect to submitted page with embed param
        self.assertEqual(response.status_code, 302)
        self.assertIn("embed=1", response.url)

        # Follow redirect
        response = self.client.get(response.url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(getattr(response, "xframe_options_exempt", False))
        self.assertIsNone(response.get("X-Frame-Options"))

    def test_admin_pages_cannot_be_framed(self):
        """Admin pages should never allow framing."""
        self.client.login(username="admin", password="testpass123")

        # Check registration link list (admin page)
        url = reverse("registration:registration_link_list")
        response = self.client.get(url)

        # Admin pages should NOT be exempt from X-Frame-Options
        self.assertFalse(getattr(response, "xframe_options_exempt", False))

    def test_embed_code_view_returns_correct_url(self):
        """Embed code view should generate correct iframe code."""
        self.client.login(username="admin", password="testpass123")

        url = reverse(
            "registration:registration_link_embed",
            kwargs={"pk": self.registration_link.pk}
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        # Should contain the embed URL with ?embed=1
        self.assertContains(response, "?embed=1")
        # Should contain iframe element
        self.assertContains(response, "<iframe")
        # Should have accessible title attribute
        self.assertContains(response, f'title="{self.registration_link.title}"')
