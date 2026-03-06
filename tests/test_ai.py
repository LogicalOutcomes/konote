"""Tests for konote.ai module — prompt content and validation."""
import json
from unittest.mock import Mock, patch

import pytest

from konote.ai import _call_insights_api, _validate_suggest_target_response


@pytest.mark.django_db
def test_suggest_target_prompt_includes_validation_criteria():
    """The suggest_target prompt should include all 8 validation criteria."""
    with patch("konote.ai._call_openrouter") as mock_call:
        mock_call.return_value = json.dumps({
            "name": "Test",
            "description": "Test description",
            "client_goal": "Test goal",
            "suggested_section": "Test",
            "metrics": [],
            "custom_metric": None,
        })
        from konote.ai import suggest_target
        suggest_target("test words", "Test Program", [], [])

        # Check the system prompt (first arg to _call_openrouter)
        system_prompt = mock_call.call_args[0][0]
        assert "Observable behaviour" in system_prompt
        assert "Time-bound" in system_prompt
        assert "Causally linked" in system_prompt
        assert "Participant-meaningful" in system_prompt
        assert "custom_metric" in system_prompt.lower() or "target-specific metric" in system_prompt.lower()


def _make_valid_response(**overrides):
    """Build a minimal valid suggest_target response dict."""
    base = {
        "name": "Test target",
        "description": "Test description",
        "client_goal": "Test goal",
        "suggested_section": "Housing",
        "metrics": [],
        "custom_metric": None,
    }
    base.update(overrides)
    return base


@pytest.mark.parametrize("bad_section", [
    None,
    "",
    "   ",
    123,
], ids=["none", "empty", "whitespace", "non-string"])
def test_validate_suggest_target_defaults_missing_section_to_general(bad_section):
    """Missing/empty/non-string suggested_section should default to 'General'."""
    response = _make_valid_response(suggested_section=bad_section)
    result = _validate_suggest_target_response(response, [])
    assert result is not None
    assert result["suggested_section"] == "General"


def test_validate_suggest_target_preserves_valid_section():
    """A valid suggested_section string should pass through unchanged."""
    response = _make_valid_response(suggested_section="Employment")
    result = _validate_suggest_target_response(response, [])
    assert result["suggested_section"] == "Employment"


@pytest.mark.django_db
def test_call_insights_api_rejects_remote_http_provider(settings):
    settings.OPENROUTER_API_KEY = "test-key"
    settings.INSIGHTS_API_BASE = "http://example.com/v1"

    with patch("konote.ai.requests.post") as mock_post:
        with patch("konote.ai.logger.error") as mock_error:
            result = _call_insights_api("system", "user")

    assert result is None
    mock_post.assert_not_called()
    mock_error.assert_called_once()
    assert "must use HTTPS" in mock_error.call_args[0][0]


@pytest.mark.django_db
def test_call_insights_api_allows_local_http_provider(settings):
    settings.OPENROUTER_API_KEY = "test-key"
    settings.INSIGHTS_API_BASE = "http://localhost:11434/v1"

    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "ok"}}],
    }

    with patch("konote.ai.requests.post", return_value=mock_response) as mock_post:
        result = _call_insights_api("system", "user")

    assert result == "ok"
    mock_post.assert_called_once()


@pytest.mark.django_db
def test_call_insights_api_rejects_unapproved_remote_host(settings):
    settings.OPENROUTER_API_KEY = "test-key"
    settings.INSIGHTS_API_BASE = "https://example.com/v1"
    settings.INSIGHTS_ALLOWED_HOSTS = ["approved.example.com"]

    with patch("konote.ai.requests.post") as mock_post:
        with patch("konote.ai.logger.error") as mock_error:
            result = _call_insights_api("system", "user")

    assert result is None
    mock_post.assert_not_called()
    mock_error.assert_called_once()
    assert "INSIGHTS_ALLOWED_HOSTS" in mock_error.call_args[0][0]


@pytest.mark.django_db
def test_call_insights_api_allows_approved_remote_host(settings):
    settings.OPENROUTER_API_KEY = "test-key"
    settings.INSIGHTS_API_BASE = "https://sub.ai.agency.ca/v1"
    settings.INSIGHTS_ALLOWED_HOSTS = ["*.agency.ca"]

    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "ok"}}],
    }

    with patch("konote.ai.requests.post", return_value=mock_response) as mock_post:
        result = _call_insights_api("system", "user")

    assert result == "ok"
    mock_post.assert_called_once()
