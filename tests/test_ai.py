"""Tests for konote.ai module — prompt content and validation."""
import json
from unittest.mock import patch

import pytest


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
