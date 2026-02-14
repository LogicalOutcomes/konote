from django.test import Client, TestCase

from apps.auth_app.models import User
from apps.events.models import CalendarFeedToken


class CalendarFeedSettingsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="calendar_user",
            password="testpass123",
            display_name="Calendar User",
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
