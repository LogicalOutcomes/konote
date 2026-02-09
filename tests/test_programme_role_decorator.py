"""
Tests for programme_role_required decorator.

This decorator fixes a security hole where users with different roles in different
programmes could access resources based on their highest role across ALL programmes,
not their role in the SPECIFIC programme being accessed.
"""
from cryptography.fernet import Fernet
from django.test import TestCase, RequestFactory, override_settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

import konote.encryption as enc_module
from apps.auth_app.models import User
from apps.auth_app.decorators import programme_role_required
from apps.programs.models import Program, UserProgramRole
from apps.groups.models import Group

TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ProgrammeRoleRequiredDecoratorTest(TestCase):
    """Test programme-specific role checking."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None

        # Create two programmes
        self.programme_a = Program.objects.create(name="Programme A")
        self.programme_b = Program.objects.create(name="Programme B")

        # Create a user with different roles in each programme
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            display_name="Test User",
        )

        # User is RECEPTIONIST in Programme A
        UserProgramRole.objects.create(
            user=self.user,
            program=self.programme_a,
            role="receptionist",
            status="active",
        )

        # User is STAFF in Programme B
        UserProgramRole.objects.create(
            user=self.user,
            program=self.programme_b,
            role="staff",
            status="active",
        )

        # Create groups in each programme
        self.group_a = Group.objects.create(
            name="Group A",
            program=self.programme_a,
            group_type="activity",
        )
        self.group_b = Group.objects.create(
            name="Group B",
            program=self.programme_b,
            group_type="activity",
        )

        self.factory = RequestFactory()

    def test_allows_access_when_user_has_required_role_in_programme(self):
        """User with staff role in Programme B can access Programme B resource."""

        @programme_role_required("staff", lambda req, group_id: get_object_or_404(Group, pk=group_id).program)
        def test_view(request, group_id):
            return HttpResponse("OK")

        request = self.factory.get(f"/test/{self.group_b.id}/")
        request.user = self.user

        response = test_view(request, group_id=self.group_b.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"OK")

    def test_denies_access_when_user_lacks_required_role_in_programme(self):
        """User with receptionist role in Programme A cannot access staff-only resource in Programme A."""

        @programme_role_required("staff", lambda req, group_id: get_object_or_404(Group, pk=group_id).program)
        def test_view(request, group_id):
            return HttpResponse("OK")

        request = self.factory.get(f"/test/{self.group_a.id}/")
        request.user = self.user

        response = test_view(request, group_id=self.group_a.id)
        self.assertEqual(response.status_code, 403)
        # 403.html template is rendered, not the raw error message

    def test_denies_access_when_user_has_no_role_in_programme(self):
        """User with no role in a programme cannot access its resources."""
        programme_c = Program.objects.create(name="Programme C")
        group_c = Group.objects.create(
            name="Group C",
            program=programme_c,
            group_type="activity",
        )

        @programme_role_required("staff", lambda req, group_id: get_object_or_404(Group, pk=group_id).program)
        def test_view(request, group_id):
            return HttpResponse("OK")

        request = self.factory.get(f"/test/{group_c.id}/")
        request.user = self.user

        response = test_view(request, group_id=group_c.id)
        self.assertEqual(response.status_code, 403)
        # 403.html template is rendered, not the raw error message

    def test_security_fix_prevents_cross_programme_privilege_escalation(self):
        """
        Security test: User with staff in Programme B should NOT be able to
        access Programme A resources just because they have staff somewhere.

        This is the security hole that programme_role_required fixes.
        """

        @programme_role_required("staff", lambda req, group_id: get_object_or_404(Group, pk=group_id).program)
        def test_view(request, group_id):
            return HttpResponse("OK")

        request = self.factory.get(f"/test/{self.group_a.id}/")
        request.user = self.user

        # User has staff in Programme B, but only receptionist in Programme A
        # They should be DENIED access to Programme A's staff-only resource
        response = test_view(request, group_id=self.group_a.id)
        self.assertEqual(response.status_code, 403)

    def test_attaches_user_programme_role_to_request(self):
        """Decorator attaches the user's role in this programme to request object."""

        @programme_role_required("staff", lambda req, group_id: get_object_or_404(Group, pk=group_id).program)
        def test_view(request, group_id):
            return HttpResponse(f"Role: {request.user_programme_role}")

        request = self.factory.get(f"/test/{self.group_b.id}/")
        request.user = self.user

        response = test_view(request, group_id=self.group_b.id)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Role: staff", response.content)

    def test_denies_access_when_programme_cannot_be_determined(self):
        """Decorator denies access if get_programme_fn raises an exception."""

        def bad_programme_getter(request, group_id):
            raise ValueError("Cannot determine programme")

        @programme_role_required("staff", bad_programme_getter)
        def test_view(request, group_id):
            return HttpResponse("OK")

        request = self.factory.get("/test/999/")
        request.user = self.user

        response = test_view(request, group_id=999)
        self.assertEqual(response.status_code, 403)
        # 403.html template is rendered, not the raw error message

    def test_role_hierarchy_receptionist_less_than_staff(self):
        """Receptionist role is lower rank than staff."""

        @programme_role_required("staff", lambda req, group_id: get_object_or_404(Group, pk=group_id).program)
        def test_view(request, group_id):
            return HttpResponse("OK")

        request = self.factory.get(f"/test/{self.group_a.id}/")
        request.user = self.user

        # User is receptionist in Programme A, needs staff
        response = test_view(request, group_id=self.group_a.id)
        self.assertEqual(response.status_code, 403)

    def test_role_hierarchy_staff_meets_staff_requirement(self):
        """Staff role meets staff requirement."""

        @programme_role_required("staff", lambda req, group_id: get_object_or_404(Group, pk=group_id).program)
        def test_view(request, group_id):
            return HttpResponse("OK")

        request = self.factory.get(f"/test/{self.group_b.id}/")
        request.user = self.user

        # User is staff in Programme B, needs staff
        response = test_view(request, group_id=self.group_b.id)
        self.assertEqual(response.status_code, 200)

    def test_role_hierarchy_program_manager_exceeds_staff_requirement(self):
        """Program manager role exceeds staff requirement."""
        UserProgramRole.objects.filter(user=self.user, program=self.programme_a).update(role="program_manager")

        @programme_role_required("staff", lambda req, group_id: get_object_or_404(Group, pk=group_id).program)
        def test_view(request, group_id):
            return HttpResponse("OK")

        request = self.factory.get(f"/test/{self.group_a.id}/")
        request.user = self.user

        # User is program_manager in Programme A, needs staff (program_manager > staff)
        response = test_view(request, group_id=self.group_a.id)
        self.assertEqual(response.status_code, 200)
