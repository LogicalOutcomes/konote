"""Tests for language switching — cookie persistence, login sync, and fallback."""
from cryptography.fernet import Fernet
from django.conf import settings
from django.test import TestCase, Client, override_settings

from apps.auth_app.models import User
import konote.encryption as enc_module


TEST_KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY, AUTH_MODE="local")
class SwitchLanguageViewTest(TestCase):
    """Test the custom switch_language view."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()
        self.user = User.objects.create_user(
            username="languser", password="testpass123", display_name="Lang User"
        )

    def tearDown(self):
        enc_module._fernet = None

    def test_switch_to_french_sets_cookie(self):
        resp = self.http.post("/i18n/switch/", {
            "language": "fr",
            "next": "/auth/login/",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.cookies[settings.LANGUAGE_COOKIE_NAME].value, "fr")

    def test_switch_to_english_sets_cookie(self):
        resp = self.http.post("/i18n/switch/", {
            "language": "en",
            "next": "/auth/login/",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.cookies[settings.LANGUAGE_COOKIE_NAME].value, "en")

    def test_invalid_language_falls_back_to_english(self):
        resp = self.http.post("/i18n/switch/", {
            "language": "xx",
            "next": "/",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.cookies[settings.LANGUAGE_COOKIE_NAME].value, "en")

    def test_get_request_not_allowed(self):
        resp = self.http.get("/i18n/switch/")
        self.assertEqual(resp.status_code, 405)

    def test_authenticated_user_preference_saved(self):
        self.http.login(username="languser", password="testpass123")
        self.http.post("/i18n/switch/", {
            "language": "fr",
            "next": "/",
        })
        self.user.refresh_from_db()
        self.assertEqual(self.user.preferred_language, "fr")

    def test_anonymous_user_no_db_error(self):
        resp = self.http.post("/i18n/switch/", {
            "language": "fr",
            "next": "/auth/login/",
        })
        self.assertEqual(resp.status_code, 302)

    def test_unsafe_next_url_redirects_to_home(self):
        resp = self.http.post("/i18n/switch/", {
            "language": "en",
            "next": "https://evil.example.com/",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, "/")

    def test_cookie_max_age_set(self):
        resp = self.http.post("/i18n/switch/", {
            "language": "fr",
            "next": "/",
        })
        cookie = resp.cookies[settings.LANGUAGE_COOKIE_NAME]
        self.assertEqual(cookie["max-age"], settings.LANGUAGE_COOKIE_AGE)


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY, AUTH_MODE="local", RATELIMIT_ENABLE=False)
class SyncLanguageOnLoginTest(TestCase):
    """Test the sync_language_on_login utility."""

    databases = {"default", "audit"}

    def setUp(self):
        from django.core.cache import cache

        enc_module._fernet = None
        cache.clear()
        self.http = Client()

    def tearDown(self):
        from django.core.cache import cache

        enc_module._fernet = None
        cache.clear()

    def test_login_saves_language_to_new_user(self):
        """First login with no preferred_language saves current lang to profile."""
        user = User.objects.create_user(
            username="newuser", password="testpass123", display_name="New"
        )
        self.assertEqual(user.preferred_language, "")
        resp = self.http.post("/auth/login/", {
            "username": "newuser",
            "password": "testpass123",
        })
        self.assertEqual(resp.status_code, 302)
        user.refresh_from_db()
        # Should have saved the default language
        self.assertIn(user.preferred_language, ["en", "fr"])

    def test_login_restores_saved_preference(self):
        """Login with preferred_language='fr' keeps preference on user."""
        user = User.objects.create_user(
            username="fruser", password="testpass123", display_name="FR User"
        )
        user.preferred_language = "fr"
        user.save(update_fields=["preferred_language"])

        resp = self.http.post("/auth/login/", {
            "username": "fruser",
            "password": "testpass123",
        })
        self.assertEqual(resp.status_code, 302)
        user.refresh_from_db()
        # Preference should still be French (not overwritten)
        self.assertEqual(user.preferred_language, "fr")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY, AUTH_MODE="local")
class BilingualLoginPageTest(TestCase):
    """Test the conditional bilingual hero on the login page."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()

    def tearDown(self):
        enc_module._fernet = None

    def test_first_visit_shows_bilingual_hero(self):
        """No language cookie → bilingual hero with English/Fran\u00e7ais buttons."""
        resp = self.http.get("/auth/login/")
        self.assertContains(resp, "Participant Outcome Management")
        self.assertContains(resp, "Gestion des r\u00e9sultats des participants")
        self.assertContains(resp, "lang-chooser")

    def test_return_visit_shows_language_link(self):
        """With language cookie → top-right language link, no bilingual hero."""
        self.http.cookies[settings.LANGUAGE_COOKIE_NAME] = "en"
        resp = self.http.get("/auth/login/")
        self.assertNotContains(resp, "lang-chooser")
        self.assertContains(resp, "lang-nav")
        # English page should show link to switch to French
        self.assertContains(resp, "Français")

    def test_french_cookie_shows_english_link(self):
        """French cookie → language link shows 'English' to switch back."""
        self.http.cookies[settings.LANGUAGE_COOKIE_NAME] = "fr"
        resp = self.http.get("/auth/login/")
        # The language link should offer English as the alternative
        self.assertContains(resp, 'lang="en"')
        self.assertContains(resp, "English")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY, AUTH_MODE="local", RATELIMIT_ENABLE=False)
class LogoutClearsCookieTest(TestCase):
    """Test that logout clears the language cookie."""

    databases = {"default", "audit"}

    def setUp(self):
        from django.core.cache import cache

        enc_module._fernet = None
        cache.clear()
        self.http = Client()
        self.user = User.objects.create_user(
            username="logoutuser", password="testpass123", display_name="Logout User"
        )

    def tearDown(self):
        from django.core.cache import cache

        enc_module._fernet = None
        cache.clear()

    def test_logout_deletes_language_cookie(self):
        """Logging out clears the language cookie so next user gets fresh state."""
        self.http.login(username="logoutuser", password="testpass123")
        # Switch to French (sets cookie)
        self.http.post("/i18n/switch/", {"language": "fr", "next": "/"})
        self.assertEqual(self.http.cookies[settings.LANGUAGE_COOKIE_NAME].value, "fr")

        # Log out
        resp = self.http.post("/auth/logout/")
        # Cookie should be cleared (max-age=0 means delete)
        cookie = resp.cookies[settings.LANGUAGE_COOKIE_NAME]
        self.assertEqual(cookie["max-age"], 0)

    def test_login_page_shows_bilingual_hero_after_logout(self):
        """After logout, the login page should show the bilingual hero (no cookie)."""
        self.http.login(username="logoutuser", password="testpass123")
        self.http.post("/i18n/switch/", {"language": "fr", "next": "/"})

        # Log out — clears cookie
        self.http.post("/auth/logout/")

        # Visit login page — should see bilingual hero since cookie was cleared
        resp = self.http.get("/auth/login/")
        self.assertContains(resp, "lang-chooser")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY, AUTH_MODE="local", RATELIMIT_ENABLE=False)
class LoginSetsCookieTest(TestCase):
    """Test that login sets the language cookie to the user's preference."""

    databases = {"default", "audit"}

    def setUp(self):
        from django.core.cache import cache

        enc_module._fernet = None
        cache.clear()
        self.http = Client()

    def tearDown(self):
        from django.core.cache import cache

        enc_module._fernet = None
        cache.clear()

    def test_login_sets_cookie_to_saved_preference(self):
        """User with preferred_language='fr' gets French cookie on login."""
        user = User.objects.create_user(
            username="frpref", password="testpass123", display_name="FR Pref"
        )
        user.preferred_language = "fr"
        user.save(update_fields=["preferred_language"])

        resp = self.http.post("/auth/login/", {
            "username": "frpref",
            "password": "testpass123",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.cookies[settings.LANGUAGE_COOKIE_NAME].value, "fr")

    def test_login_sets_cookie_for_new_user(self):
        """New user (no preference) gets a cookie matching the default language."""
        User.objects.create_user(
            username="newuser2", password="testpass123", display_name="New User"
        )
        resp = self.http.post("/auth/login/", {
            "username": "newuser2",
            "password": "testpass123",
        })
        self.assertEqual(resp.status_code, 302)
        # Should have a language cookie set (either "en" or "fr")
        self.assertIn(
            resp.cookies[settings.LANGUAGE_COOKIE_NAME].value, ["en", "fr"]
        )


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY, AUTH_MODE="local", RATELIMIT_ENABLE=False)
class SharedBrowserScenarioTest(TestCase):
    """Test that language doesn't bleed between users on the same browser."""

    databases = {"default", "audit"}

    def setUp(self):
        from django.core.cache import cache

        enc_module._fernet = None
        cache.clear()
        self.http = Client()
        # User A prefers French
        self.user_a = User.objects.create_user(
            username="user_a", password="testpass123", display_name="User A"
        )
        self.user_a.preferred_language = "fr"
        self.user_a.save(update_fields=["preferred_language"])
        # User B prefers English
        self.user_b = User.objects.create_user(
            username="user_b", password="testpass123", display_name="User B"
        )
        self.user_b.preferred_language = "en"
        self.user_b.save(update_fields=["preferred_language"])

    def tearDown(self):
        from django.core.cache import cache

        enc_module._fernet = None
        cache.clear()

    def test_user_b_not_affected_by_user_a_language(self):
        """User A (French) logs out → User B logs in → gets English, not French."""
        # User A logs in — gets French cookie
        resp = self.http.post("/auth/login/", {
            "username": "user_a",
            "password": "testpass123",
        })
        self.assertEqual(resp.cookies[settings.LANGUAGE_COOKIE_NAME].value, "fr")

        # User A logs out — cookie cleared
        self.http.post("/auth/logout/")

        # User B logs in — should get English cookie, not French
        resp = self.http.post("/auth/login/", {
            "username": "user_b",
            "password": "testpass123",
        })
        self.assertEqual(resp.cookies[settings.LANGUAGE_COOKIE_NAME].value, "en")

    def test_new_user_not_inheriting_stale_preference(self):
        """New user on shared browser doesn't inherit previous user's French."""
        new_user = User.objects.create_user(
            username="brand_new", password="testpass123", display_name="Brand New"
        )
        # Simulate: User A was using French, then logged out
        self.http.post("/auth/login/", {
            "username": "user_a",
            "password": "testpass123",
        })
        self.http.post("/auth/logout/")

        # New user logs in — no saved preference, should get default (en)
        resp = self.http.post("/auth/login/", {
            "username": "brand_new",
            "password": "testpass123",
        })
        new_user.refresh_from_db()
        # Should NOT have inherited French from User A
        self.assertEqual(new_user.preferred_language, "en")


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY, AUTH_MODE="local", RATELIMIT_ENABLE=False)
class LanguagePersistenceTest(TestCase):
    """BUG-1: Verify language persists across page navigation and POST requests."""

    databases = {"default", "audit"}

    def setUp(self):
        from django.core.cache import cache

        enc_module._fernet = None
        cache.clear()
        self.http = Client()

    def tearDown(self):
        from django.core.cache import cache

        enc_module._fernet = None
        cache.clear()

    def test_english_user_stays_english_across_navigation(self):
        """User with preferred_language='en' sees English on every page."""
        user = User.objects.create_user(
            username="en_persist", password="testpass123", display_name="EN User"
        )
        user.preferred_language = "en"
        user.save(update_fields=["preferred_language"])

        self.http.login(username="en_persist", password="testpass123")

        # Navigate to multiple pages — all should be English
        for url in ["/", "/participants/", "/programs/"]:
            resp = self.http.get(url)
            if resp.status_code == 200:
                self.assertEqual(
                    resp.get("Content-Language", "en"), "en",
                    f"Content-Language should be 'en' on {url}"
                )

    def test_french_user_stays_french_across_navigation(self):
        """User with preferred_language='fr' sees French on every page."""
        user = User.objects.create_user(
            username="fr_persist", password="testpass123", display_name="FR User"
        )
        user.preferred_language = "fr"
        user.save(update_fields=["preferred_language"])

        self.http.login(username="fr_persist", password="testpass123")

        for url in ["/", "/participants/", "/programs/"]:
            resp = self.http.get(url)
            if resp.status_code == 200:
                self.assertEqual(
                    resp.get("Content-Language", "en"), "fr",
                    f"Content-Language should be 'fr' on {url}"
                )

    def test_stale_cookie_overridden_by_profile(self):
        """Stale French cookie does not override English preferred_language."""
        user = User.objects.create_user(
            username="en_stale", password="testpass123", display_name="EN Stale"
        )
        user.preferred_language = "en"
        user.save(update_fields=["preferred_language"])

        self.http.login(username="en_stale", password="testpass123")

        # Inject a stale French cookie (as if left by a previous user)
        self.http.cookies[settings.LANGUAGE_COOKIE_NAME] = "fr"

        resp = self.http.get("/")
        if resp.status_code == 200:
            self.assertEqual(resp.get("Content-Language", "en"), "en")

    def test_stale_cookie_synced_on_response(self):
        """When cookie disagrees with profile, response corrects the cookie."""
        user = User.objects.create_user(
            username="sync_test", password="testpass123", display_name="Sync"
        )
        user.preferred_language = "en"
        user.save(update_fields=["preferred_language"])

        self.http.login(username="sync_test", password="testpass123")

        # Inject stale French cookie
        self.http.cookies[settings.LANGUAGE_COOKIE_NAME] = "fr"

        resp = self.http.get("/")
        # The response should include a Set-Cookie correcting to "en"
        cookie = resp.cookies.get(settings.LANGUAGE_COOKIE_NAME)
        self.assertIsNotNone(cookie, "Response should set a corrected cookie")
        self.assertEqual(cookie.value, "en")

    def test_language_persists_after_post(self):
        """Language stays consistent after a POST request (form submission)."""
        user = User.objects.create_user(
            username="post_persist", password="testpass123", display_name="Post"
        )
        user.preferred_language = "fr"
        user.save(update_fields=["preferred_language"])

        self.http.login(username="post_persist", password="testpass123")

        # POST to language switch to verify it stays French
        resp = self.http.post("/i18n/switch/", {
            "language": "fr",
            "next": "/",
        })
        self.assertEqual(resp.status_code, 302)

        # Follow redirect — should still be French
        resp = self.http.get("/")
        if resp.status_code == 200:
            self.assertEqual(resp.get("Content-Language", "en"), "fr")
