from unittest.mock import patch

from django.test import Client, TestCase
from django.urls import reverse

from apps.auth_app.models import User
from apps.events.models import CalendarFeedToken


class CalendarFeedSettingsTests(TestCase):
    databases = ["default", "audit"]

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="calendar_user",
            password="testpass123",
            display_name="Calendar User",
            is_admin=True,
        )

    def test_outlook_subscribe_url_uses_webcal_scheme(self):
        CalendarFeedToken.objects.create(user=self.user, token="abc123token")
        self.client.login(username="calendar_user", password="testpass123")

        response = self.client.get("/events/calendar/settings/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("feed_url", response.context)
        self.assertIn("outlook_subscribe_url", response.context)
        self.assertTrue(response.context["feed_url"].startswith("http"))
        self.assertTrue(response.context["outlook_subscribe_url"].startswith("webcal://"))

    def test_outlook_subscribe_url_absent_without_token(self):
        self.client.login(username="calendar_user", password="testpass123")

        response = self.client.get("/events/calendar/settings/")

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["feed_url"])
        self.assertIsNone(response.context["outlook_subscribe_url"])

    def test_generate_creates_token_and_redirects(self):
        """POST generate should create a token and redirect (POST-Redirect-GET)."""
        self.client.login(username="calendar_user", password="testpass123")

        response = self.client.post("/events/calendar/settings/", {"action": "generate"})

        # Should redirect, not render directly
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, "/events/calendar/settings/")
        # Token should now exist
        self.assertTrue(CalendarFeedToken.objects.filter(user=self.user).exists())

    def test_generate_shows_success_message(self):
        """After generate redirect, the GET response should contain a success message."""
        self.client.login(username="calendar_user", password="testpass123")

        self.client.post("/events/calendar/settings/", {"action": "generate"})
        response = self.client.get("/events/calendar/settings/")

        self.assertEqual(response.status_code, 200)
        messages = list(response.context["messages"])
        self.assertTrue(
            any("Calendar link created" in str(m) or "calendar link" in str(m).lower() for m in messages),
            f"Expected a success message about the calendar link, got: {[str(m) for m in messages]}",
        )

    def test_regenerate_updates_existing_token_and_redirects(self):
        """POST regenerate should update the token and redirect."""
        CalendarFeedToken.objects.create(user=self.user, token="old_token_value")
        self.client.login(username="calendar_user", password="testpass123")

        response = self.client.post("/events/calendar/settings/", {"action": "regenerate"})

        self.assertEqual(response.status_code, 302)
        # Token should have changed
        updated = CalendarFeedToken.objects.get(user=self.user)
        self.assertNotEqual(updated.token, "old_token_value")
        self.assertTrue(updated.is_active)

    def test_generate_shows_error_message_on_db_failure(self):
        """If token creation fails, an error message should be shown (not a silent 500)."""
        self.client.login(username="calendar_user", password="testpass123")

        with patch("apps.events.views.CalendarFeedToken.objects.create", side_effect=Exception("DB error")):
            response = self.client.post(
                "/events/calendar/settings/", {"action": "generate"}, follow=True
            )

        self.assertEqual(response.status_code, 200)
        messages = list(response.context["messages"])
        self.assertTrue(
            any("went wrong" in str(m).lower() or "error" in str(m).lower() for m in messages),
            f"Expected an error message, got: {[str(m) for m in messages]}",
        )

    def test_feed_url_is_valid_ical_format(self):
        """Generated feed URL should end in .ics and use http/https scheme."""
        CalendarFeedToken.objects.create(user=self.user, token="testtoken123")
        self.client.login(username="calendar_user", password="testpass123")

        response = self.client.get("/events/calendar/settings/")

        self.assertEqual(response.status_code, 200)
        feed_url = response.context["feed_url"]
        self.assertIsNotNone(feed_url)
        self.assertTrue(
            feed_url.startswith("http://") or feed_url.startswith("https://"),
            f"Feed URL should start with http(s)://, got: {feed_url}",
        )
        self.assertTrue(
            feed_url.endswith(".ics"),
            f"Feed URL should end in .ics, got: {feed_url}",
        )
