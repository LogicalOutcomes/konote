"""Tests for cross-program permission leakage — users must not access data
from programs they aren't assigned to by manipulating URL IDs.

Covers group views (membership_remove, milestone_create/edit, outcome_create)
and plans views (target_history).
"""
from django.test import TestCase, override_settings
from django.utils import timezone
from cryptography.fernet import Fernet

from apps.auth_app.models import User
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.groups.models import (
    Group,
    GroupMembership,
    ProjectMilestone,
    ProjectOutcome,
)
from apps.plans.models import PlanSection, PlanTarget, PlanTargetRevision
from apps.programs.models import Program, UserProgramRole
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class CrossProgramSecurityTest(TestCase):
    """Verify that staff in Program A cannot access Program B data."""

    databases = {"default", "audit"}

    @classmethod
    def setUpTestData(cls):
        enc_module._fernet = None

        # Programs
        cls.program_a = Program.objects.create(name="Housing Support", status="active")
        cls.program_b = Program.objects.create(name="Youth Services", status="active")

        # Staff user — access to Program A only
        cls.staff = User.objects.create_user(
            username="casey", password="testpass123", display_name="Casey Worker",
        )
        UserProgramRole.objects.create(
            user=cls.staff, program=cls.program_a, role="staff",
        )

        # Group in Program A (accessible)
        cls.group_a = Group.objects.create(
            name="Housing Workshop", program=cls.program_a, group_type="project",
        )

        # Group in Program B (should be blocked)
        cls.group_b = Group.objects.create(
            name="Youth Coding Club", program=cls.program_b, group_type="project",
        )
        cls.membership_b = GroupMembership.objects.create(
            group=cls.group_b, member_name="Test Member",
        )
        cls.milestone_b = ProjectMilestone.objects.create(
            group=cls.group_b, title="Launch Day",
        )

        # Client in Program B with plan data (should be blocked)
        cls.client_b = ClientFile.objects.create(is_demo=False, status="active")
        ClientProgramEnrolment.objects.create(
            client_file=cls.client_b, program=cls.program_b,
        )
        section_b = PlanSection.objects.create(
            client_file=cls.client_b, name="Youth Goals", program=cls.program_b,
        )
        cls.target_b = PlanTarget.objects.create(
            plan_section=section_b, client_file=cls.client_b,
            name="Complete coding course",
        )
        PlanTargetRevision.objects.create(
            plan_target=cls.target_b,
            name="Complete coding course",
            status="active",
            changed_by=cls.staff,
        )

    def setUp(self):
        enc_module._fernet = None
        self.client.login(username="casey", password="testpass123")

    def tearDown(self):
        enc_module._fernet = None

    # --- Cross-program access should be blocked ---

    def test_membership_remove_blocked_cross_program(self):
        """Staff in Program A cannot remove a member from Program B's group."""
        resp = self.client.post(
            f"/groups/member/{self.membership_b.pk}/remove/",
        )
        self.assertEqual(resp.status_code, 403)
        # Membership should still be active
        self.membership_b.refresh_from_db()
        self.assertEqual(self.membership_b.status, "active")

    def test_milestone_create_blocked_cross_program(self):
        """Staff in Program A cannot create a milestone in Program B's group."""
        resp = self.client.post(
            f"/groups/{self.group_b.pk}/milestone/",
            {"title": "Hacked Milestone", "status": "not_started"},
        )
        self.assertEqual(resp.status_code, 403)

    def test_milestone_edit_blocked_cross_program(self):
        """Staff in Program A cannot edit a milestone in Program B's group."""
        resp = self.client.get(
            f"/groups/milestone/{self.milestone_b.pk}/edit/",
        )
        self.assertEqual(resp.status_code, 403)

    def test_outcome_create_blocked_cross_program(self):
        """Staff in Program A cannot record an outcome in Program B's group."""
        resp = self.client.post(
            f"/groups/{self.group_b.pk}/outcome/",
            {
                "outcome_date": "2026-01-15",
                "description": "Hacked outcome",
            },
        )
        self.assertEqual(resp.status_code, 403)

    def test_target_history_blocked_cross_program(self):
        """Staff in Program A cannot view target history for Program B client."""
        resp = self.client.get(
            f"/plans/targets/{self.target_b.pk}/history/",
        )
        self.assertEqual(resp.status_code, 403)

    # --- Own program access still works ---

    def test_own_program_group_accessible(self):
        """Staff in Program A can still access their own program's group."""
        resp = self.client.get(f"/groups/{self.group_a.pk}/")
        self.assertEqual(resp.status_code, 200)
