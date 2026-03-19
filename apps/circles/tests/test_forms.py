"""Tests for Circles forms."""
from unittest.mock import patch

from django import forms
from django.template import Context, Template
from django.test import SimpleTestCase

from apps.circles.forms import CircleMembershipForm, get_circle_relationship_choices


class CircleMembershipRelationshipFormTests(SimpleTestCase):
    """Protect the opt-in relationship dropdown behaviour for Circles."""

    @patch("apps.circles.forms.InstanceSetting.get", return_value="")
    def test_relationship_field_defaults_to_free_text_when_unconfigured(self, _mock_setting):
        form = CircleMembershipForm()

        relationship_field = form.fields["relationship_label"]
        self.assertIsInstance(relationship_field, forms.CharField)
        self.assertIsInstance(relationship_field.widget, forms.TextInput)
        self.assertEqual(
            relationship_field.help_text,
            "Optional — describes this person's role in the circle.",
        )

    @patch(
        "apps.circles.forms.InstanceSetting.get",
        return_value="Parent/Guardian\nPartner\nChild\nGrandparent\nSupport Person",
    )
    def test_relationship_field_switches_to_dropdown_when_choices_are_configured(self, _mock_setting):
        form = CircleMembershipForm()

        relationship_field = form.fields["relationship_label"]
        self.assertIsInstance(relationship_field, forms.ChoiceField)
        self.assertIsInstance(relationship_field.widget, forms.Select)
        self.assertEqual(
            list(relationship_field.choices),
            [
                ("", "— Select —"),
                ("Parent/Guardian", "Parent/Guardian"),
                ("Partner", "Partner"),
                ("Child", "Child"),
                ("Grandparent", "Grandparent"),
                ("Support Person", "Support Person"),
            ],
        )

    @patch(
        "apps.circles.forms.InstanceSetting.get",
        return_value="['Parent/Guardian', 'Partner', 'Child']",
    )
    def test_relationship_setting_accepts_list_like_values(self, _mock_setting):
        self.assertEqual(
            get_circle_relationship_choices(),
            ["Parent/Guardian", "Partner", "Child"],
        )

    @patch(
        "apps.circles.forms.InstanceSetting.get",
        return_value="Parent/Guardian\nPartner\nChild",
    )
    def test_dropdown_rejects_free_text_outside_configured_choices(self, _mock_setting):
        form = CircleMembershipForm(
            data={
                "member_name": "Alex Example",
                "relationship_label": "Cousin",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("relationship_label", form.errors)

    @patch(
        "apps.circles.forms.InstanceSetting.get",
        return_value="Parent/Guardian\nPartner\nChild",
    )
    def test_dropdown_accepts_configured_choice(self, _mock_setting):
        form = CircleMembershipForm(
            data={
                "member_name": "Alex Example",
                "relationship_label": "Partner",
            }
        )

        self.assertTrue(form.is_valid())

    @patch(
        "apps.circles.forms.InstanceSetting.get",
        return_value="Parent/Guardian\nPartner\nChild",
    )
    def test_relationship_field_renders_select_when_configured(self, _mock_setting):
        form = CircleMembershipForm()

        html = Template("{{ form.relationship_label }}").render(Context({"form": form}))

        self.assertIn("<select", html)
        self.assertIn("Parent/Guardian", html)