"""Tests for Partner model, admin views, and form validation."""
from datetime import date

import pytest
from django.test import TestCase, Client

from apps.auth_app.models import User
from apps.programs.models import Program
from apps.reports.forms import PartnerForm
from apps.reports.models import Partner, ReportTemplate


# ─── Partner model tests ─────────────────────────────────────────────


class PartnerModelTest(TestCase):
    """Test Partner model behaviour, relationships, and cascading deletes."""

    def test_create_partner(self):
        """Create a Partner with all fields, verify __str__ and get_programs()."""
        program = Program.objects.create(name="Youth Mentorship", status="active")
        partner = Partner.objects.create(
            name="United Way",
            name_fr="Centraide",
            partner_type="funder",
            contact_name="Jane Doe",
            contact_email="jane@example.com",
            grant_number="UW-2026-001",
            grant_period_start=date(2026, 4, 1),
            grant_period_end=date(2027, 3, 31),
            is_active=True,
            notes="Annual grant for youth programs.",
        )
        partner.programs.add(program)

        assert str(partner) == "United Way"
        assert program in partner.get_programs()

    def test_get_programs_empty_returns_all_active(self):
        """Partner with no linked programs falls back to all active programs."""
        active_prog = Program.objects.create(name="Active Program", status="active")
        Program.objects.create(name="Inactive Program", status="inactive")
        partner = Partner.objects.create(name="Board of Directors", partner_type="board")

        result = partner.get_programs()
        assert active_prog in result
        assert result.filter(status="inactive").count() == 0

    def test_cascade_delete_removes_templates(self):
        """Deleting a partner cascades to its report templates."""
        partner = Partner.objects.create(name="Old Funder", partner_type="funder")
        ReportTemplate.objects.create(name="Quarterly Report", partner=partner)
        assert ReportTemplate.objects.filter(partner=partner).count() == 1

        partner.delete()
        assert ReportTemplate.objects.filter(name="Quarterly Report").count() == 0

    def test_partner_type_choices(self):
        """All 7 partner types should be valid choices."""
        valid_types = [choice[0] for choice in Partner.PARTNER_TYPES]
        expected = ["funder", "network", "board", "regulator", "accreditation", "donor", "other"]
        assert valid_types == expected
        assert len(valid_types) == 7


# ─── Partner admin view tests ────────────────────────────────────────


class PartnerViewTest(TestCase):
    """Test partner admin views — access control, CRUD operations, program linking."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username="admin", password="testpass123", is_admin=True,
        )
        self.staff_user = User.objects.create_user(
            username="staff", password="testpass123", is_admin=False,
        )
        self.program = Program.objects.create(name="Test Program", status="active")

    def test_partner_list_requires_admin(self):
        """Non-admin user gets 403 on partner list."""
        self.client.login(username="staff", password="testpass123")
        response = self.client.get("/admin/settings/partners/")
        assert response.status_code == 403

    def test_partner_list_shows_partners(self):
        """Admin sees partners in the list view."""
        Partner.objects.create(name="Visible Partner", partner_type="funder")
        self.client.login(username="admin", password="testpass123")
        response = self.client.get("/admin/settings/partners/")
        assert response.status_code == 200
        assert b"Visible Partner" in response.content

    def test_partner_create_happy_path(self):
        """POST valid data creates a partner and redirects."""
        self.client.login(username="admin", password="testpass123")
        data = {
            "name": "New Funder",
            "partner_type": "funder",
            "is_active": True,
        }
        response = self.client.post("/admin/settings/partners/create/", data)
        assert response.status_code == 302
        assert Partner.objects.filter(name="New Funder").exists()

    def test_partner_create_form_validation(self):
        """POST without required name field returns form with errors."""
        self.client.login(username="admin", password="testpass123")
        data = {
            "partner_type": "funder",
            "is_active": True,
        }
        response = self.client.post("/admin/settings/partners/create/", data)
        assert response.status_code == 200  # re-renders form, not redirect
        assert not Partner.objects.filter(partner_type="funder").exists()

    def test_partner_detail_shows_info(self):
        """GET partner detail page shows the partner name."""
        partner = Partner.objects.create(name="Detail Partner", partner_type="network")
        self.client.login(username="admin", password="testpass123")
        response = self.client.get(f"/admin/settings/partners/{partner.pk}/")
        assert response.status_code == 200
        assert b"Detail Partner" in response.content

    def test_partner_edit_happy_path(self):
        """POST updated name saves changes and redirects."""
        partner = Partner.objects.create(name="Old Name", partner_type="funder")
        self.client.login(username="admin", password="testpass123")
        data = {
            "name": "Updated Name",
            "partner_type": "funder",
            "is_active": True,
        }
        response = self.client.post(f"/admin/settings/partners/{partner.pk}/edit/", data)
        assert response.status_code == 302
        partner.refresh_from_db()
        assert partner.name == "Updated Name"

    def test_partner_edit_programs(self):
        """POST program_ids updates the partner's linked programs."""
        partner = Partner.objects.create(name="Program Partner", partner_type="funder")
        prog2 = Program.objects.create(name="Second Program", status="active")
        self.client.login(username="admin", password="testpass123")
        data = {
            "program_ids": [str(self.program.pk), str(prog2.pk)],
        }
        response = self.client.post(
            f"/admin/settings/partners/{partner.pk}/programs/", data,
        )
        assert response.status_code == 302
        assert set(partner.programs.values_list("pk", flat=True)) == {
            self.program.pk, prog2.pk,
        }

    def test_partner_delete_cascade_warning(self):
        """GET delete confirmation page shows the partner name."""
        partner = Partner.objects.create(name="Delete Me", partner_type="donor")
        self.client.login(username="admin", password="testpass123")
        response = self.client.get(f"/admin/settings/partners/{partner.pk}/delete/")
        assert response.status_code == 200
        assert b"Delete Me" in response.content

    def test_partner_delete_removes_partner(self):
        """POST delete removes the partner from the database."""
        partner = Partner.objects.create(name="Gone Partner", partner_type="other")
        self.client.login(username="admin", password="testpass123")
        response = self.client.post(f"/admin/settings/partners/{partner.pk}/delete/")
        assert response.status_code == 302
        assert not Partner.objects.filter(pk=partner.pk).exists()


# ─── Partner form tests ──────────────────────────────────────────────


class PartnerFormTest(TestCase):
    """Test PartnerForm validation rules."""

    def test_grant_period_validation(self):
        """Grant period start after end raises a validation error."""
        form = PartnerForm(data={
            "name": "Bad Dates Funder",
            "partner_type": "funder",
            "grant_period_start": "2027-01-01",
            "grant_period_end": "2026-01-01",
            "is_active": True,
        })
        assert not form.is_valid()
        assert "__all__" in form.errors or "grant_period_start" in form.errors

    def test_valid_form(self):
        """All valid data passes form validation."""
        form = PartnerForm(data={
            "name": "Good Funder",
            "partner_type": "funder",
            "contact_name": "Alex Smith",
            "contact_email": "alex@example.com",
            "grant_number": "GF-2026-100",
            "grant_period_start": "2026-04-01",
            "grant_period_end": "2027-03-31",
            "is_active": True,
            "notes": "Annual outcomes report required.",
        })
        assert form.is_valid(), f"Form errors: {form.errors}"
