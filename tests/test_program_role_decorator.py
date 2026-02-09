"""
Tests for program_role_required decorator.

This decorator fixes a security hole where users with different roles in different
programs could access resources based on their highest role across ALL programs,
not their role in the SPECIFIC program being accessed.
"""
from cryptography.fernet import Fernet
from django.test import TestCase, RequestFactory, override_settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

import konote.encryption as enc_module
from apps.auth_app.models import User
from apps.auth_app.decorators import program_role_required
from apps.programs.models import Program, UserProgramRole
from apps.groups.models import Group

TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class ProgramRoleRequiredDecoratorTest(TestCase):
    """Test program-specific role checking."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None

        # Create two programs
        self.program_a = Program.objects.create(name="Program A")
        self.program_b = Program.objects.create(name="Program B")

        # Create a user with different roles in each program
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            display_name="Test User",
        )

        # User is RECEPTIONIST in Program A
        UserProgramRole.objects.create(
            user=self.user,
            program=self.program_a,
            role="receptionist",
            status="active",
        )

        # User is STAFF in Program B
        UserProgramRole.objects.create(
            user=self.user,
            program=self.program_b,
            role="staff",
            status="active",
        )

        # Create groups in each program
        self.group_a = Group.objects.create(
            name="Group A",
            program=self.program_a,
            group_type="activity",
        )
        self.group_b = Group.objects.create(
            name="Group B",
            program=self.program_b,
            group_type="activity",
        )

        self.factory = RequestFactory()

    def test_allows_access_when_user_has_required_role_in_program(self):
        """User with staff role in Program B can access Program B resource."""

        @program_role_required("staff", lambda req, group_id: get_object_or_404(Group, pk=group_id).program)
        def test_view(request, group_id):
            return HttpResponse("OK")

        request = self.factory.get(f"/test/{self.group_b.id}/")
        request.user = self.user

        response = test_view(request, group_id=self.group_b.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"OK")

    def test_denies_access_when_user_lacks_required_role_in_program(self):
        """User with receptionist role in Program A cannot access staff-only resource in Program A."""

        @program_role_required("staff", lambda req, group_id: get_object_or_404(Group, pk=group_id).program)
        def test_view(request, group_id):
            return HttpResponse("OK")

        request = self.factory.get(f"/test/{self.group_a.id}/")
        request.user = self.user

        response = test_view(request, group_id=self.group_a.id)
        self.assertEqual(response.status_code, 403)
        # 403.html template is rendered, not the raw error message

    def test_denies_access_when_user_has_no_role_in_program(self):
        """User with no role in a program cannot access its resources."""
        program_c = Program.objects.create(name="Program C")
        group_c = Group.objects.create(
            name="Group C",
            program=program_c,
            group_type="activity",
        )

        @program_role_required("staff", lambda req, group_id: get_object_or_404(Group, pk=group_id).program)
        def test_view(request, group_id):
            return HttpResponse("OK")

        request = self.factory.get(f"/test/{group_c.id}/")
        request.user = self.user

        response = test_view(request, group_id=group_c.id)
        self.assertEqual(response.status_code, 403)
        # 403.html template is rendered, not the raw error message

    def test_security_fix_prevents_cross_program_privilege_escalation(self):
        """
        Security test: User with staff in Program B should NOT be able to
        access Program A resources just because they have staff somewhere.

        This is the security hole that program_role_required fixes.
        """

        @program_role_required("staff", lambda req, group_id: get_object_or_404(Group, pk=group_id).program)
        def test_view(request, group_id):
            return HttpResponse("OK")

        request = self.factory.get(f"/test/{self.group_a.id}/")
        request.user = self.user

        # User has staff in Program B, but only receptionist in Program A
        # They should be DENIED access to Program A's staff-only resource
        response = test_view(request, group_id=self.group_a.id)
        self.assertEqual(response.status_code, 403)

    def test_attaches_user_program_role_to_request(self):
        """Decorator attaches the user's role in this program to request object."""

        @program_role_required("staff", lambda req, group_id: get_object_or_404(Group, pk=group_id).program)
        def test_view(request, group_id):
            return HttpResponse(f"Role: {request.user_program_role}")

        request = self.factory.get(f"/test/{self.group_b.id}/")
        request.user = self.user

        response = test_view(request, group_id=self.group_b.id)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Role: staff", response.content)

    def test_denies_access_when_program_cannot_be_determined(self):
        """Decorator denies access if get_program_fn raises an exception."""

        def bad_program_getter(request, group_id):
            raise ValueError("Cannot determine program")

        @program_role_required("staff", bad_program_getter)
        def test_view(request, group_id):
            return HttpResponse("OK")

        request = self.factory.get("/test/999/")
        request.user = self.user

        response = test_view(request, group_id=999)
        self.assertEqual(response.status_code, 403)
        # 403.html template is rendered, not the raw error message

    def test_role_hierarchy_receptionist_less_than_staff(self):
        """Receptionist role is lower rank than staff."""

        @program_role_required("staff", lambda req, group_id: get_object_or_404(Group, pk=group_id).program)
        def test_view(request, group_id):
            return HttpResponse("OK")

        request = self.factory.get(f"/test/{self.group_a.id}/")
        request.user = self.user

        # User is receptionist in Program A, needs staff
        response = test_view(request, group_id=self.group_a.id)
        self.assertEqual(response.status_code, 403)

    def test_role_hierarchy_staff_meets_staff_requirement(self):
        """Staff role meets staff requirement."""

        @program_role_required("staff", lambda req, group_id: get_object_or_404(Group, pk=group_id).program)
        def test_view(request, group_id):
            return HttpResponse("OK")

        request = self.factory.get(f"/test/{self.group_b.id}/")
        request.user = self.user

        # User is staff in Program B, needs staff
        response = test_view(request, group_id=self.group_b.id)
        self.assertEqual(response.status_code, 200)

    def test_role_hierarchy_program_manager_exceeds_staff_requirement(self):
        """Program manager role exceeds staff requirement."""
        UserProgramRole.objects.filter(user=self.user, program=self.program_a).update(role="program_manager")

        @program_role_required("staff", lambda req, group_id: get_object_or_404(Group, pk=group_id).program)
        def test_view(request, group_id):
            return HttpResponse("OK")

        request = self.factory.get(f"/test/{self.group_a.id}/")
        request.user = self.user

        # User is program_manager in Program A, needs staff (program_manager > staff)
        response = test_view(request, group_id=self.group_a.id)
        self.assertEqual(response.status_code, 200)
