"""Tests for the objective scoring module (QA-T10).

These are fast unit tests — no browser, no LLM, no database needed.
"""
from unittest import TestCase

from .objective_scorer import (
    compute_objective_scores,
    count_user_actions,
    get_persona_language,
    normalise_language_to_code,
    score_accessibility,
    score_efficiency,
    score_language,
)
from .state_capture import StepCapture


class TestCountUserActions(TestCase):
    """Test the user action counter."""

    def test_empty_actions(self):
        self.assertEqual(count_user_actions([]), 0)

    def test_counts_user_facing_actions(self):
        actions = [
            {"goto": "/clients/"},
            {"fill": ["#name", "Jane"]},
            {"click": "button[type='submit']"},
            {"press": "Tab"},
        ]
        self.assertEqual(count_user_actions(actions), 4)

    def test_ignores_infrastructure_actions(self):
        actions = [
            {"wait_for": "networkidle"},
            {"wait_htmx": True},
            {"wait": 500},
            {"set_viewport": {"width": 375}},
            {"set_network": "offline"},
            {"login_as": "staff"},
            {"emulate_touch": True},
            {"set_high_contrast": True},
            {"set_zoom": 150},
        ]
        self.assertEqual(count_user_actions(actions), 0)

    def test_mixed_actions(self):
        actions = [
            {"login_as": "staff"},
            {"goto": "/clients/"},
            {"wait_for": "networkidle"},
            {"fill": ["#search", "Jane"]},
            {"wait_htmx": True},
            {"click": ".result-link"},
        ]
        self.assertEqual(count_user_actions(actions), 3)

    def test_string_actions_ignored(self):
        actions = [
            "comment text",
            {"click": "#btn"},
        ]
        self.assertEqual(count_user_actions(actions), 1)

    def test_type_and_clear_counted(self):
        actions = [
            {"clear": "#field"},
            {"type": "new value"},
        ]
        self.assertEqual(count_user_actions(actions), 2)


class TestScoreAccessibility(TestCase):
    """Test axe-core violation scoring."""

    def test_no_violations(self):
        capture = StepCapture(
            scenario_id="test", step_id=1, actor_persona="DS1",
            axe_violations=[], axe_violation_count=0,
        )
        result = score_accessibility(capture)
        self.assertEqual(result.score, 5.0)
        self.assertEqual(result.dimension, "accessibility")

    def test_minor_violations(self):
        capture = StepCapture(
            scenario_id="test", step_id=1, actor_persona="DS1",
            axe_violations=[
                {"id": "color-contrast", "impact": "minor",
                 "description": "Colour contrast", "nodes_count": 2},
            ],
            axe_violation_count=1,
        )
        result = score_accessibility(capture)
        # 2 nodes * 0.5 weight = 1.0 -> score 4.0
        self.assertEqual(result.score, 4.0)

    def test_serious_violations(self):
        capture = StepCapture(
            scenario_id="test", step_id=1, actor_persona="DS1",
            axe_violations=[
                {"id": "label", "impact": "serious",
                 "description": "Missing label", "nodes_count": 3},
            ],
            axe_violation_count=1,
        )
        result = score_accessibility(capture)
        # 3 nodes * 2 weight = 6.0 -> score 2.0
        self.assertEqual(result.score, 2.0)

    def test_critical_violations(self):
        capture = StepCapture(
            scenario_id="test", step_id=1, actor_persona="DS1",
            axe_violations=[
                {"id": "image-alt", "impact": "critical",
                 "description": "Missing alt", "nodes_count": 5},
            ],
            axe_violation_count=1,
        )
        result = score_accessibility(capture)
        # 5 nodes * 3 weight = 15.0 -> score 1.0
        self.assertEqual(result.score, 1.0)


class TestScoreEfficiency(TestCase):
    """Test action count scoring."""

    def test_few_actions(self):
        result = score_efficiency(1)
        self.assertEqual(result.score, 5.0)

    def test_moderate_actions(self):
        result = score_efficiency(4)
        self.assertEqual(result.score, 4.0)

    def test_many_actions(self):
        result = score_efficiency(8)
        self.assertEqual(result.score, 2.0)

    def test_too_many_actions(self):
        result = score_efficiency(15)
        self.assertEqual(result.score, 1.0)


class TestScoreLanguage(TestCase):
    """Test document language scoring."""

    def test_exact_match(self):
        capture = StepCapture(
            scenario_id="test", step_id=1, actor_persona="DS1",
            document_lang="en",
        )
        result = score_language(capture, "en")
        self.assertEqual(result.score, 5.0)

    def test_base_language_match(self):
        capture = StepCapture(
            scenario_id="test", step_id=1, actor_persona="DS1",
            document_lang="fr",
        )
        result = score_language(capture, "fr-CA")
        self.assertEqual(result.score, 4.0)

    def test_lang_not_set(self):
        capture = StepCapture(
            scenario_id="test", step_id=1, actor_persona="DS1",
            document_lang="",
        )
        result = score_language(capture, "en")
        self.assertEqual(result.score, 3.0)

    def test_wrong_language(self):
        capture = StepCapture(
            scenario_id="test", step_id=1, actor_persona="DS2",
            document_lang="en",
        )
        result = score_language(capture, "fr")
        self.assertEqual(result.score, 1.0)

    def test_case_insensitive(self):
        capture = StepCapture(
            scenario_id="test", step_id=1, actor_persona="DS1",
            document_lang="EN-CA",
        )
        result = score_language(capture, "en-ca")
        self.assertEqual(result.score, 5.0)

    def test_defaults_to_english(self):
        capture = StepCapture(
            scenario_id="test", step_id=1, actor_persona="DS1",
            document_lang="en",
        )
        # No expected language — defaults to 'en'
        result = score_language(capture, "")
        self.assertEqual(result.score, 5.0)


class TestComputeObjectiveScores(TestCase):
    """Test the combined objective scoring function."""

    def test_all_dimensions(self):
        capture = StepCapture(
            scenario_id="test", step_id=1, actor_persona="DS1",
            axe_violations=[], axe_violation_count=0,
            document_lang="fr",
        )
        actions = [{"goto": "/"}, {"click": "#btn"}]
        scores = compute_objective_scores(
            capture=capture, actions=actions, expected_lang="fr",
        )
        self.assertIn("accessibility", scores)
        self.assertIn("efficiency", scores)
        self.assertIn("language", scores)
        self.assertEqual(scores["accessibility"].score, 5.0)
        self.assertEqual(scores["efficiency"].score, 5.0)
        self.assertEqual(scores["language"].score, 5.0)

    def test_no_actions_skips_efficiency(self):
        capture = StepCapture(
            scenario_id="test", step_id=1, actor_persona="DS1",
            axe_violations=[], axe_violation_count=0,
        )
        scores = compute_objective_scores(capture=capture)
        self.assertIn("accessibility", scores)
        self.assertNotIn("efficiency", scores)
        self.assertNotIn("language", scores)

    def test_no_lang_skips_language(self):
        capture = StepCapture(
            scenario_id="test", step_id=1, actor_persona="DS1",
            axe_violations=[], axe_violation_count=0,
        )
        actions = [{"click": "#btn"}]
        scores = compute_objective_scores(
            capture=capture, actions=actions, expected_lang=None,
        )
        self.assertIn("accessibility", scores)
        self.assertIn("efficiency", scores)
        self.assertNotIn("language", scores)


class TestNormaliseLanguageToCode(TestCase):
    """Test the persona language normalisation (fixes language scorer bug)."""

    def test_english_descriptive(self):
        self.assertEqual(normalise_language_to_code("English"), "en")

    def test_french_primary(self):
        self.assertEqual(
            normalise_language_to_code("French (primary), reads English"), "fr",
        )

    def test_french_functional(self):
        self.assertEqual(
            normalise_language_to_code(
                "French (primary), English (functional but prefers French interface)"
            ),
            "fr",
        )

    def test_english_and_somali(self):
        self.assertEqual(
            normalise_language_to_code("English and Somali"), "en",
        )

    def test_english_bilingual(self):
        self.assertEqual(
            normalise_language_to_code(
                "English and French (bilingual, prefers English interface)"
            ),
            "en",
        )

    def test_iso_code_passthrough(self):
        self.assertEqual(normalise_language_to_code("fr"), "fr")
        self.assertEqual(normalise_language_to_code("en"), "en")
        self.assertEqual(normalise_language_to_code("en-CA"), "en-ca")

    def test_english_some_romanian(self):
        self.assertEqual(
            normalise_language_to_code("English (some Romanian)"), "en",
        )


class TestGetPersonaLanguage(TestCase):
    """Test the persona language extraction with ISO normalisation."""

    def test_prefers_test_user_iso_code(self):
        persona = {
            "language": "French (primary), reads English",
            "test_user": {"language": "fr"},
        }
        self.assertEqual(get_persona_language(persona), "fr")

    def test_falls_back_to_descriptive(self):
        persona = {
            "language": "English",
            "test_user": {"username": "staff"},
        }
        self.assertEqual(get_persona_language(persona), "en")

    def test_empty_persona(self):
        self.assertEqual(get_persona_language(None), "en")
        self.assertEqual(get_persona_language({}), "en")


class TestStepEvaluationObjectiveOverride(TestCase):
    """Test that objective scores override LLM scores in StepEvaluation."""

    def test_effective_scores_use_objective_override(self):
        from .score_models import DimensionScore, StepEvaluation

        eval_result = StepEvaluation(
            scenario_id="test", step_id=1, persona_id="DS1",
            dimension_scores={
                "accessibility": DimensionScore("accessibility", 4.0, "LLM says ok"),
                "clarity": DimensionScore("clarity", 3.0, "LLM says meh"),
            },
            objective_scores={
                "accessibility": DimensionScore("accessibility", 2.0, "axe found issues"),
            },
        )
        effective = eval_result.effective_dimension_scores
        # Accessibility should use objective (2.0), not LLM (4.0)
        self.assertEqual(effective["accessibility"].score, 2.0)
        # Clarity should use LLM (3.0) since no objective score exists
        self.assertEqual(effective["clarity"].score, 3.0)

    def test_avg_uses_effective_scores(self):
        from .score_models import DimensionScore, StepEvaluation

        eval_result = StepEvaluation(
            scenario_id="test", step_id=1, persona_id="DS1",
            dimension_scores={
                "clarity": DimensionScore("clarity", 4.0, ""),
            },
            objective_scores={
                "accessibility": DimensionScore("accessibility", 2.0, ""),
            },
        )
        # avg of 4.0 (clarity) and 2.0 (accessibility) = 3.0
        self.assertAlmostEqual(eval_result.avg_dimension_score, 3.0)
