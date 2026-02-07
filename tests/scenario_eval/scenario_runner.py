"""Execute scenario steps using Playwright and capture state.

Extends BrowserTestBase from the existing UX walkthrough framework.
"""
from ..ux_walkthrough.browser_base import BrowserTestBase, TEST_PASSWORD

from .llm_evaluator import evaluate_step, format_persona_for_prompt
from .score_models import ScenarioResult, StepEvaluation
from .state_capture import capture_step_state, capture_to_evaluation_context


class ScenarioRunner(BrowserTestBase):
    """Execute scenario YAML files against a live test server.

    Inherits from BrowserTestBase for Playwright setup, test data,
    and helper methods (login, HTMX wait, axe-core).
    """

    # Set by subclass or test method
    scenario_data = None
    personas = None
    use_llm = True  # Set to False for dry-run (captures only, no API calls)

    def _create_test_data(self):
        """Extend base test data with extra users needed by scenarios."""
        super()._create_test_data()

        from apps.auth_app.models import User
        from apps.programs.models import UserProgramRole

        # DS1b: Casey's first week (new staff user)
        if not User.objects.filter(username="staff_new").exists():
            staff_new = User.objects.create_user(
                username="staff_new", password=TEST_PASSWORD,
                display_name="Casey New",
            )
            UserProgramRole.objects.create(
                user=staff_new, program=self.program_a, role="staff",
            )

        # DS2: Jean-Luc (French-speaking staff)
        if not User.objects.filter(username="staff_fr").exists():
            staff_fr = User.objects.create_user(
                username="staff_fr", password=TEST_PASSWORD,
                display_name="Jean-Luc Bergeron",
            )
            UserProgramRole.objects.create(
                user=staff_fr, program=self.program_a, role="staff",
            )

        # DS3: Amara (accessibility / keyboard-only staff)
        if not User.objects.filter(username="staff_a11y").exists():
            staff_a11y = User.objects.create_user(
                username="staff_a11y", password=TEST_PASSWORD,
                display_name="Amara Osei",
            )
            UserProgramRole.objects.create(
                user=staff_a11y, program=self.program_a, role="staff",
            )

    def run_scenario(self, scenario, personas=None, screenshot_dir=None):
        """Execute a full scenario and return a ScenarioResult.

        Args:
            scenario: Parsed scenario dict from YAML.
            personas: Dict of persona_id -> persona_data.
            screenshot_dir: Where to save screenshots (optional).

        Returns:
            ScenarioResult with all step evaluations.
        """
        personas = personas or self.personas or {}
        result = ScenarioResult(
            scenario_id=scenario["id"],
            title=scenario.get("title", ""),
        )

        steps = scenario.get("steps", [])
        current_user = None
        context_chain = []  # Accumulate context from previous steps

        for step in steps:
            step_id = step.get("id", 0)
            actor = step.get("actor", scenario.get("persona", ""))

            # Handle login / user switching
            actions = step.get("actions", [])
            for action in actions:
                if isinstance(action, dict) and "login_as" in action:
                    new_user = action["login_as"]
                    if new_user != current_user:
                        if current_user:
                            self.switch_user(new_user)
                        else:
                            self.login_via_browser(new_user)
                        current_user = new_user

            # Execute Playwright actions
            self._execute_actions(actions)

            # Capture page state
            capture = capture_step_state(
                page=self.page,
                scenario_id=scenario["id"],
                step_id=step_id,
                actor_persona=actor,
                screenshot_dir=screenshot_dir,
                run_axe_fn=self.run_axe if hasattr(self, "run_axe") else None,
            )

            # Build context chain for cross-step evaluation
            prev_context = step.get("context_from_previous", "")
            if not prev_context and context_chain:
                prev_context = " | ".join(context_chain[-3:])  # Last 3 steps

            # LLM evaluation (if enabled)
            if self.use_llm:
                persona_data = personas.get(actor, {})
                persona_desc = format_persona_for_prompt(persona_data)
                page_state_text = capture_to_evaluation_context(capture)

                evaluation = evaluate_step(
                    persona_desc=persona_desc,
                    step=step,
                    page_state_text=page_state_text,
                    context_from_previous=prev_context,
                )
                if evaluation:
                    evaluation.scenario_id = scenario["id"]
                    evaluation.persona_id = actor
                    result.step_evaluations.append(evaluation)
            else:
                # Dry-run mode — record capture info without LLM scoring
                placeholder = StepEvaluation(
                    scenario_id=scenario["id"],
                    step_id=step_id,
                    persona_id=actor,
                    one_line_summary=f"[DRY RUN] Captured: {capture.url}",
                )
                result.step_evaluations.append(placeholder)

            # Add to context chain
            intent = step.get("intent", "")
            context_chain.append(
                f"Step {step_id} ({actor}): {intent} -> {capture.url}"
            )

        return result

    def _execute_actions(self, actions):
        """Execute a list of Playwright actions from a scenario step.

        Actions are simple dicts like:
            - goto: "/clients/"
            - fill: ["#selector", "value"]
            - click: "button[type='submit']"
            - press: "Tab"
            - type: "some text"
            - clear: "#selector"
            - wait_for: "networkidle"
            - wait_htmx: true
        """
        for action in actions:
            if isinstance(action, str):
                # Simple string action — skip (e.g., comments)
                continue

            if not isinstance(action, dict):
                continue

            if "login_as" in action:
                # Handled above in run_scenario
                continue

            if "goto" in action:
                url = action["goto"]
                if url.startswith("/"):
                    url = self.live_url(url)
                self.page.goto(url)
                self.page.wait_for_load_state("networkidle")

            elif "fill" in action:
                selector, value = action["fill"]
                try:
                    self.page.fill(selector, value, timeout=5000)
                except Exception:
                    pass  # Field not found — the LLM evaluator will note the issue

            elif "clear" in action:
                selector = action["clear"]
                try:
                    self.page.fill(selector, "", timeout=5000)
                except Exception:
                    pass

            elif "click" in action:
                selector = action["click"]
                try:
                    self.page.click(selector, timeout=5000)
                except Exception:
                    pass  # Click failed — the LLM evaluator will note the issue

            elif "press" in action:
                key = action["press"]
                # Alt+ArrowLeft = browser back (use Playwright API for reliability)
                if key in ("Alt+ArrowLeft", "Alt+Left"):
                    self.page.go_back()
                else:
                    self.page.keyboard.press(key)

            elif "type" in action:
                text = action["type"]
                self.page.keyboard.type(text)

            elif "wait_for" in action:
                state = action["wait_for"]
                if state == "networkidle":
                    self.page.wait_for_load_state("networkidle")

            elif "wait_htmx" in action:
                if action["wait_htmx"]:
                    self.wait_for_htmx()

            # Small pause between actions for realism
            self.page.wait_for_timeout(100)
