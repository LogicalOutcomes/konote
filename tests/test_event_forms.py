"""Tests for event and alert form validation.

Covers:
- EventForm all_day logic (date-only vs. datetime mode)
- EventForm event_type queryset filtering (active only)
- AlertForm required content field
- AlertCancelForm required status_reason field

TEST-9 from code review.
"""
from cryptography.fernet import Fernet
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.events.forms import AlertCancelForm, AlertForm, EventForm
from apps.events.models import EventType
import konote.encryption as enc_module

TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class EventFormTest(TestCase):
    """Validate EventForm clean() logic for all_day and standard modes."""

    def setUp(self):
        enc_module._fernet = None
        self.event_type = EventType.objects.create(
            name="Intake", status="active",
        )

    def tearDown(self):
        enc_module._fernet = None

    # ------------------------------------------------------------------
    # All-day mode
    # ------------------------------------------------------------------

    def test_event_form_all_day_requires_start_date(self):
        """All-day event without start_date should be invalid."""
        form = EventForm(data={
            "title": "Orientation",
            "all_day": True,
            # no start_date
        })
        self.assertFalse(form.is_valid())
        self.assertIn("start_date", form.errors)

    def test_event_form_all_day_valid(self):
        """All-day event with start_date is valid and sets start_timestamp at midnight."""
        form = EventForm(data={
            "title": "Orientation",
            "all_day": True,
            "start_date": "2026-03-01",
        })
        self.assertTrue(form.is_valid(), form.errors)
        ts = form.cleaned_data["start_timestamp"]
        self.assertIsNotNone(ts)
        self.assertEqual(ts.hour, 0)
        self.assertEqual(ts.minute, 0)

    def test_event_form_all_day_with_end_date(self):
        """All-day event with both start and end dates populates both timestamps."""
        form = EventForm(data={
            "title": "Camp",
            "all_day": True,
            "start_date": "2026-03-01",
            "end_date": "2026-03-03",
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNotNone(form.cleaned_data["start_timestamp"])
        self.assertIsNotNone(form.cleaned_data["end_timestamp"])

    # ------------------------------------------------------------------
    # Standard (datetime) mode
    # ------------------------------------------------------------------

    def test_event_form_standard_requires_start_timestamp(self):
        """Non all-day event without start_timestamp should be invalid."""
        form = EventForm(data={
            "title": "Meeting",
            "all_day": False,
            # no start_timestamp
        })
        self.assertFalse(form.is_valid())
        self.assertIn("start_timestamp", form.errors)

    def test_event_form_standard_valid(self):
        """Non all-day event with start_timestamp should be valid."""
        form = EventForm(data={
            "title": "Meeting",
            "all_day": False,
            "start_timestamp": "2026-03-01T14:00",
        })
        self.assertTrue(form.is_valid(), form.errors)

    # ------------------------------------------------------------------
    # Queryset filtering
    # ------------------------------------------------------------------

    def test_event_form_event_type_queryset_only_active(self):
        """EventForm event_type queryset contains only active event types."""
        archived = EventType.objects.create(
            name="Deprecated", status="archived",
        )
        form = EventForm()
        qs = form.fields["event_type"].queryset
        self.assertIn(self.event_type, qs)
        self.assertNotIn(archived, qs)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AlertFormTest(TestCase):
    """Validate AlertForm and AlertCancelForm required fields."""

    def setUp(self):
        enc_module._fernet = None

    def tearDown(self):
        enc_module._fernet = None

    def test_alert_form_requires_content(self):
        """AlertForm with empty content should be invalid."""
        form = AlertForm(data={"content": ""})
        self.assertFalse(form.is_valid())
        self.assertIn("content", form.errors)

    def test_alert_cancel_form_requires_reason(self):
        """AlertCancelForm with empty status_reason should be invalid."""
        form = AlertCancelForm(data={"status_reason": ""})
        self.assertFalse(form.is_valid())
        self.assertIn("status_reason", form.errors)
