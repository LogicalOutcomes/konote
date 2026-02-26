"""Tests for the translate_strings management command — auto-translate feature.

Covers:
  - API translations applied to empty .po entries
  - --review flag marks translations as fuzzy
  - Error handling for bad JSON responses
  - Error handling for HTTP failures
  - Missing API key handling
  - Batch processing (multiple batches)
  - Markdown fence stripping from API responses
"""

import io
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import polib
from django.test import SimpleTestCase

from apps.admin_settings.management.commands.translate_strings import (
    Command,
    TRANSLATION_SYSTEM_PROMPT,
)


class AutoTranslateEmptyTest(SimpleTestCase):
    """Tests for Command._auto_translate_empty()."""

    def _make_po(self, entries):
        """Create a polib.POFile with the given (msgid, msgstr) pairs."""
        po = polib.POFile()
        po.metadata = {"Content-Type": "text/plain; charset=UTF-8"}
        for msgid, msgstr in entries:
            po.append(polib.POEntry(msgid=msgid, msgstr=msgstr))
        return po

    def _make_command(self):
        """Create a Command instance with captured stdout/stderr."""
        cmd = Command()
        cmd.stdout = io.StringIO()
        cmd.stderr = io.StringIO()
        # style is auto-initialised by BaseCommand.__init__; no override needed.
        return cmd

    def _mock_api_response(self, translations_dict):
        """Create a mock requests.Response returning the given translations."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": json.dumps(
                        translations_dict, ensure_ascii=False
                    )
                }
            }]
        }
        return mock_response

    # ------------------------------------------------------------------
    # Happy path: translations are applied
    # ------------------------------------------------------------------

    @patch.dict(os.environ, {"TRANSLATE_API_KEY": "test-key-123"})
    @patch("apps.admin_settings.management.commands.translate_strings.requests.post")
    def test_translations_applied_to_empty_entries(self, mock_post):
        """API translations are written into empty msgstr fields."""
        po = self._make_po([
            ("Hello", ""),
            ("Goodbye", ""),
            ("Already translated", "Deja traduit"),
        ])

        mock_post.return_value = self._mock_api_response({
            "0": "Bonjour",
            "1": "Au revoir",
        })

        cmd = self._make_command()
        count = cmd._auto_translate_empty(po, review=False)

        self.assertEqual(count, 2)
        self.assertEqual(po.find("Hello").msgstr, "Bonjour")
        self.assertEqual(po.find("Goodbye").msgstr, "Au revoir")
        # Pre-existing translation untouched.
        self.assertEqual(
            po.find("Already translated").msgstr, "Deja traduit"
        )

    # ------------------------------------------------------------------
    # --review flag marks entries as fuzzy
    # ------------------------------------------------------------------

    @patch.dict(os.environ, {"TRANSLATE_API_KEY": "test-key-123"})
    @patch("apps.admin_settings.management.commands.translate_strings.requests.post")
    def test_review_flag_marks_fuzzy(self, mock_post):
        """With review=True, translated entries get the 'fuzzy' flag."""
        po = self._make_po([
            ("Save", ""),
            ("Cancel", ""),
        ])

        mock_post.return_value = self._mock_api_response({
            "0": "Enregistrer",
            "1": "Annuler",
        })

        cmd = self._make_command()
        count = cmd._auto_translate_empty(po, review=True)

        self.assertEqual(count, 2)
        self.assertIn("fuzzy", po.find("Save").flags)
        self.assertIn("fuzzy", po.find("Cancel").flags)

    @patch.dict(os.environ, {"TRANSLATE_API_KEY": "test-key-123"})
    @patch("apps.admin_settings.management.commands.translate_strings.requests.post")
    def test_no_fuzzy_without_review(self, mock_post):
        """Without review=True, translated entries do NOT get 'fuzzy'."""
        po = self._make_po([("Save", "")])

        mock_post.return_value = self._mock_api_response({
            "0": "Enregistrer",
        })

        cmd = self._make_command()
        cmd._auto_translate_empty(po, review=False)

        self.assertNotIn("fuzzy", po.find("Save").flags)

    # ------------------------------------------------------------------
    # Error handling: bad JSON
    # ------------------------------------------------------------------

    @patch.dict(os.environ, {"TRANSLATE_API_KEY": "test-key-123"})
    @patch("apps.admin_settings.management.commands.translate_strings.requests.post")
    def test_bad_json_skips_batch(self, mock_post):
        """If the API returns invalid JSON, the batch is skipped."""
        po = self._make_po([("Hello", "")])

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {"content": "This is not valid JSON!!!"}
            }]
        }
        mock_post.return_value = mock_response

        cmd = self._make_command()
        count = cmd._auto_translate_empty(po, review=False)

        self.assertEqual(count, 0)
        self.assertEqual(po.find("Hello").msgstr, "")
        # Warning was written to stderr.
        self.assertIn("failed", cmd.stderr.getvalue().lower())

    # ------------------------------------------------------------------
    # Error handling: HTTP error
    # ------------------------------------------------------------------

    @patch.dict(os.environ, {"TRANSLATE_API_KEY": "test-key-123"})
    @patch("apps.admin_settings.management.commands.translate_strings.requests.post")
    def test_http_error_skips_batch(self, mock_post):
        """If the API returns an HTTP error, the batch is skipped."""
        import requests

        po = self._make_po([("Hello", "")])

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = (
            requests.exceptions.HTTPError("500 Server Error")
        )
        mock_post.return_value = mock_response

        cmd = self._make_command()
        count = cmd._auto_translate_empty(po, review=False)

        self.assertEqual(count, 0)
        self.assertEqual(po.find("Hello").msgstr, "")

    # ------------------------------------------------------------------
    # Error handling: timeout
    # ------------------------------------------------------------------

    @patch.dict(os.environ, {"TRANSLATE_API_KEY": "test-key-123"})
    @patch("apps.admin_settings.management.commands.translate_strings.requests.post")
    def test_timeout_skips_batch(self, mock_post):
        """If the API times out, the batch is skipped."""
        import requests

        po = self._make_po([("Hello", "")])

        mock_post.side_effect = requests.exceptions.Timeout("Request timed out")

        cmd = self._make_command()
        count = cmd._auto_translate_empty(po, review=False)

        self.assertEqual(count, 0)
        self.assertEqual(po.find("Hello").msgstr, "")

    # ------------------------------------------------------------------
    # Missing API key
    # ------------------------------------------------------------------

    @patch.dict(os.environ, {}, clear=False)
    def test_missing_api_key_returns_zero(self):
        """If TRANSLATE_API_KEY is not set, return 0 and print error."""
        # Ensure the key is not set.
        env = os.environ.copy()
        env.pop("TRANSLATE_API_KEY", None)

        with patch.dict(os.environ, env, clear=True):
            po = self._make_po([("Hello", "")])
            cmd = self._make_command()
            count = cmd._auto_translate_empty(po, review=False)

            self.assertEqual(count, 0)
            self.assertIn("TRANSLATE_API_KEY", cmd.stderr.getvalue())

    # ------------------------------------------------------------------
    # Batch processing
    # ------------------------------------------------------------------

    @patch.dict(os.environ, {"TRANSLATE_API_KEY": "test-key-123"})
    @patch("apps.admin_settings.management.commands.translate_strings.requests.post")
    def test_multiple_batches(self, mock_post):
        """Strings are processed in batches of TRANSLATE_BATCH_SIZE."""
        # Create 30 empty entries (should produce 2 batches with size 25).
        entries = [(f"String {i}", "") for i in range(30)]
        po = self._make_po(entries)

        # Respond differently for each batch so we can verify both.
        def side_effect(*args, **kwargs):
            payload = kwargs.get("json", {})
            user_msg = payload["messages"][1]["content"]
            source = json.loads(user_msg)
            translations = {k: f"FR-{v}" for k, v in source.items()}
            return self._mock_api_response(translations)

        mock_post.side_effect = side_effect

        cmd = self._make_command()
        # Use small batch size for testing.
        original_batch_size = cmd.TRANSLATE_BATCH_SIZE
        cmd.TRANSLATE_BATCH_SIZE = 25
        try:
            count = cmd._auto_translate_empty(po, review=False)
        finally:
            cmd.TRANSLATE_BATCH_SIZE = original_batch_size

        self.assertEqual(count, 30)
        self.assertEqual(mock_post.call_count, 2)
        # Check a sample from each batch.
        self.assertEqual(po.find("String 0").msgstr, "FR-String 0")
        self.assertEqual(po.find("String 29").msgstr, "FR-String 29")

    # ------------------------------------------------------------------
    # No empty entries
    # ------------------------------------------------------------------

    @patch.dict(os.environ, {"TRANSLATE_API_KEY": "test-key-123"})
    def test_no_empty_entries_returns_zero(self):
        """If all entries are already translated, return 0 immediately."""
        po = self._make_po([
            ("Hello", "Bonjour"),
            ("Goodbye", "Au revoir"),
        ])

        cmd = self._make_command()
        count = cmd._auto_translate_empty(po, review=False)

        self.assertEqual(count, 0)

    # ------------------------------------------------------------------
    # Markdown fence stripping
    # ------------------------------------------------------------------

    @patch.dict(os.environ, {"TRANSLATE_API_KEY": "test-key-123"})
    @patch("apps.admin_settings.management.commands.translate_strings.requests.post")
    def test_markdown_fences_stripped(self, mock_post):
        """API responses wrapped in ```json fences are handled correctly."""
        po = self._make_po([("Hello", "")])

        fenced_content = '```json\n{"0": "Bonjour"}\n```'
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {"content": fenced_content}
            }]
        }
        mock_post.return_value = mock_response

        cmd = self._make_command()
        count = cmd._auto_translate_empty(po, review=False)

        self.assertEqual(count, 1)
        self.assertEqual(po.find("Hello").msgstr, "Bonjour")

    # ------------------------------------------------------------------
    # API response that is not a dict
    # ------------------------------------------------------------------

    @patch.dict(os.environ, {"TRANSLATE_API_KEY": "test-key-123"})
    @patch("apps.admin_settings.management.commands.translate_strings.requests.post")
    def test_non_dict_response_skips_batch(self, mock_post):
        """If the API returns a list instead of a dict, batch is skipped."""
        po = self._make_po([("Hello", "")])

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {"content": '["Bonjour"]'}
            }]
        }
        mock_post.return_value = mock_response

        cmd = self._make_command()
        count = cmd._auto_translate_empty(po, review=False)

        self.assertEqual(count, 0)
        self.assertEqual(po.find("Hello").msgstr, "")

    # ------------------------------------------------------------------
    # Partial batch: some keys missing in response
    # ------------------------------------------------------------------

    @patch.dict(os.environ, {"TRANSLATE_API_KEY": "test-key-123"})
    @patch("apps.admin_settings.management.commands.translate_strings.requests.post")
    def test_partial_response_applies_available(self, mock_post):
        """If the API omits some keys, only available translations apply."""
        po = self._make_po([
            ("Hello", ""),
            ("Goodbye", ""),
            ("Thanks", ""),
        ])

        # Only translate keys 0 and 2; key 1 is missing.
        mock_post.return_value = self._mock_api_response({
            "0": "Bonjour",
            "2": "Merci",
        })

        cmd = self._make_command()
        count = cmd._auto_translate_empty(po, review=False)

        self.assertEqual(count, 2)
        self.assertEqual(po.find("Hello").msgstr, "Bonjour")
        self.assertEqual(po.find("Goodbye").msgstr, "")
        self.assertEqual(po.find("Thanks").msgstr, "Merci")


class CallTranslationApiTest(SimpleTestCase):
    """Tests for Command._call_translation_api()."""

    def _make_command(self):
        cmd = Command()
        cmd.stdout = io.StringIO()
        cmd.stderr = io.StringIO()
        # style is auto-initialised by BaseCommand.__init__; no override needed.
        return cmd

    @patch("apps.admin_settings.management.commands.translate_strings.requests.post")
    def test_sends_correct_payload(self, mock_post):
        """Verify the API request payload structure."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {"content": '{"0": "Bonjour"}'}
            }]
        }
        mock_post.return_value = mock_response

        cmd = self._make_command()
        source_map = {"0": "Hello"}
        cmd._call_translation_api(
            "https://api.example.com/v1/chat/completions",
            "test-key",
            "gpt-4o-mini",
            source_map,
        )

        # Verify the call was made with correct structure.
        call_kwargs = mock_post.call_args
        self.assertEqual(
            call_kwargs.kwargs["headers"]["Authorization"],
            "Bearer test-key",
        )
        payload = call_kwargs.kwargs["json"]
        self.assertEqual(payload["model"], "gpt-4o-mini")
        self.assertEqual(payload["messages"][0]["role"], "system")
        self.assertEqual(
            payload["messages"][0]["content"], TRANSLATION_SYSTEM_PROMPT
        )
        self.assertEqual(payload["messages"][1]["role"], "user")
        # User message is the JSON-encoded source map.
        self.assertEqual(
            json.loads(payload["messages"][1]["content"]),
            {"0": "Hello"},
        )

    @patch("apps.admin_settings.management.commands.translate_strings.requests.post")
    def test_env_var_defaults(self, mock_post):
        """Verify default API base URL and model from env vars."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {"content": '{"0": "Bonjour"}'}
            }]
        }
        mock_post.return_value = mock_response

        cmd = self._make_command()

        # When env vars are not set, defaults should apply.
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("TRANSLATE_API_BASE", None)
            os.environ.pop("TRANSLATE_MODEL", None)
            os.environ["TRANSLATE_API_KEY"] = "key-123"

            po = self._make_po_for_env_test(cmd)

        # The URL used should be the default.
        call_args = mock_post.call_args
        self.assertTrue(
            call_args.args[0].startswith("https://api.openai.com/v1")
            or call_args.kwargs.get("url", "").startswith(
                "https://api.openai.com/v1"
            )
        )

    def _make_po_for_env_test(self, cmd):
        """Helper to run _auto_translate_empty for env var tests."""
        po = polib.POFile()
        po.metadata = {"Content-Type": "text/plain; charset=UTF-8"}
        po.append(polib.POEntry(msgid="Hello", msgstr=""))
        cmd._auto_translate_empty(po, review=False)
        return po


class SystemPromptTest(SimpleTestCase):
    """Verify the system prompt contains required context."""

    def test_prompt_mentions_canadian_french(self):
        self.assertIn("Canadian French", TRANSLATION_SYSTEM_PROMPT)

    def test_prompt_requires_vous(self):
        self.assertIn("vous", TRANSLATION_SYSTEM_PROMPT)

    def test_prompt_mentions_placeholders(self):
        self.assertIn("%(name)s", TRANSLATION_SYSTEM_PROMPT)
        self.assertIn("{{ var }}", TRANSLATION_SYSTEM_PROMPT)

    def test_prompt_mentions_html_tags(self):
        self.assertIn("<strong>", TRANSLATION_SYSTEM_PROMPT)

    def test_prompt_mentions_guillemets(self):
        self.assertIn("guillemets", TRANSLATION_SYSTEM_PROMPT)

    def test_prompt_mentions_courriel(self):
        self.assertIn("courriel", TRANSLATION_SYSTEM_PROMPT)

    def test_prompt_requests_json(self):
        self.assertIn("JSON object", TRANSLATION_SYSTEM_PROMPT)
