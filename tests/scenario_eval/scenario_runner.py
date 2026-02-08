"""Execute scenario steps using Playwright and capture state.

Extends BrowserTestBase from the existing UX walkthrough framework.

QA-ISO1: Fresh browser context per scenario, locale from persona,
         auto-login from persona data, prerequisite validation.
QA-T10:  Objective scoring for accessibility, efficiency, language.
"""
import logging

from ..ux_walkthrough.browser_base import BrowserTestBase, TEST_PASSWORD

from .llm_evaluator import evaluate_step, format_persona_for_prompt
from .objective_scorer import compute_objective_scores, count_user_actions
from .score_models import ScenarioResult, StepEvaluation
from .state_capture import capture_step_state, capture_to_evaluation_context

logger = logging.getLogger(__name__)


def _get_moment_action(moment):
    """Extract the 'what_X_does' text from a DITL moment.

    DITL moments use persona-specific keys like 'what_casey_does',
    'what_amara_does', etc. This finds whichever key matches.
    """
    for key, value in moment.items():
        if key.startswith("what_") and key.endswith("_does"):
            return value
    # Fall back to what_to_evaluate if no action key found
    evals = moment.get("what_to_evaluate", [])
    if evals:
        return "; ".join(evals)
    return ""


def _get_persona_language(persona_data):
    """Extract the expected language code from persona data.

    Checks persona.language, persona.test_user.language, and falls back
    to 'en' if not specified.

    Returns:
        Language code string, e.g. 'en', 'fr', 'en-CA', 'fr-CA'.
    """
    if not persona_data:
        return "en"
    # Direct language field
    lang = persona_data.get("language", "")
    if lang:
        return lang
    # From test_user config
    test_user = persona_data.get("test_user", {})
    lang = test_user.get("language", "")
    if lang:
        return lang
    return "en"


def _get_persona_username(persona_data):
    """Extract the test username from persona data.

    Returns:
        Username string, or None if not specified.
    """
    if not persona_data:
        return None
    test_user = persona_data.get("test_user", {})
    return test_user.get("username")


class ScenarioRunner(BrowserTestBase):
    """Execute scenario YAML files against a live test server.

    Inherits from BrowserTestBase for Playwright setup, test data,
    and helper methods (login, HTMX wait, axe-core).
    """

    # Set by subclass or test method
    scenario_data = None
    personas = None
    use_llm = True  # Set to False for dry-run (captures only, no API calls)

    # CDP session for network throttling (lazy-created)
    _cdp_session = None

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

        # R2: Omar (tech-savvy part-time receptionist)
        if not User.objects.filter(username="frontdesk2").exists():
            frontdesk2 = User.objects.create_user(
                username="frontdesk2", password=TEST_PASSWORD,
                display_name="Omar Hussain",
            )
            UserProgramRole.objects.create(
                user=frontdesk2, program=self.program_b, role="receptionist",
            )

        # Extra clients needed by specific scenarios
        from apps.clients.models import ClientFile, ClientProgramEnrolment

        # SCN-047 needs Aisha Mohamed in Youth Services
        # first_name is encrypted — can't filter in SQL, must check in Python
        if not any(c.first_name == "Aisha" for c in ClientFile.objects.all()):
            aisha = ClientFile.objects.create(is_demo=False)
            aisha.first_name = "Aisha"
            aisha.last_name = "Mohamed"
            aisha.status = "active"
            aisha.save()
            ClientProgramEnrolment.objects.create(
                client_file=aisha, program=self.program_b,
            )
            # Add phone number for the update-phone-number step
            from apps.clients.models import ClientDetailValue
            if hasattr(self, "phone_field"):
                ClientDetailValue.objects.create(
                    client_file=aisha, field_def=self.phone_field,
                    value="416-555-0199",
                )

        # SCN-048 needs James Thompson in Housing Support
        # first_name is encrypted — can't filter in SQL, must check in Python
        if not any(c.first_name == "James" for c in ClientFile.objects.all()):
            james = ClientFile.objects.create(is_demo=False)
            james.first_name = "James"
            james.last_name = "Thompson"
            james.status = "active"
            james.save()
            ClientProgramEnrolment.objects.create(
                client_file=james, program=self.program_a,
            )

    # ------------------------------------------------------------------
    # QA-ISO1: Fresh context per scenario with locale from persona
    # ------------------------------------------------------------------

    def _setup_context_for_scenario(self, scenario, personas=None):
        """Always create a fresh browser context for this scenario.

        QA-ISO1 fix: Previously only created a new context when there were
        device/a11y prerequisites. Now ALWAYS creates a fresh context to
        prevent cookie/session/language bleed between scenarios.

        Reads locale from persona data (not just prerequisites), and sets
        Accept-Language headers to match the persona's language.
        """
        prereqs = scenario.get("prerequisites", {})
        device = prereqs.get("device", {})
        personas = personas or self.personas or {}

        context_kwargs = {}

        # Viewport from device prerequisites
        viewport = device.get("viewport")
        if viewport:
            context_kwargs["viewport"] = {
                "width": viewport.get("width", 1280),
                "height": viewport.get("height", 720),
            }

        # Touch emulation
        if device.get("touch"):
            context_kwargs["has_touch"] = True

        # Forced colours (high contrast) for accessibility scenarios
        users = prereqs.get("users", [])
        for user in users:
            a11y = user.get("accessibility", {})
            if a11y.get("high_contrast"):
                context_kwargs["forced_colors"] = "active"

        # Locale from persona data (QA-ISO1: use persona as source of truth)
        persona_id = scenario.get("persona", "")
        persona_data = personas.get(persona_id, {})
        persona_lang = _get_persona_language(persona_data)

        # Also check prerequisites users for explicit language override
        for user in users:
            user_lang = user.get("language", "")
            if user_lang:
                persona_lang = user_lang

        # Set locale and Accept-Language header from persona language
        if persona_lang.startswith("fr"):
            locale_code = "fr-CA"
            accept_lang = "fr-CA,fr;q=0.9,en;q=0.1"
        else:
            locale_code = "en-CA"
            accept_lang = "en-CA,en;q=0.9"

        context_kwargs["locale"] = locale_code
        context_kwargs["extra_http_headers"] = {
            "Accept-Language": accept_lang,
        }

        # Always close existing context and create a fresh one
        self.page.close()
        self._context.close()
        self._context = self._browser.new_context(**context_kwargs)
        self.page = self._context.new_page()

    # ------------------------------------------------------------------
    # QA-ISO1: Auto-login from persona data
    # ------------------------------------------------------------------

    def _auto_login_for_scenario(self, scenario, personas=None):
        """Auto-login using the scenario's persona test_user.

        If the scenario has a top-level `persona` field and that persona
        has a `test_user.username`, log in automatically before steps.

        Returns:
            The username that was logged in, or None if no auto-login.
        """
        personas = personas or self.personas or {}
        persona_id = scenario.get("persona", "")
        if not persona_id:
            return None

        persona_data = personas.get(persona_id, {})
        username = _get_persona_username(persona_data)
        if not username:
            return None

        self.login_via_browser(username)
        return username

    # ------------------------------------------------------------------
    # QA-ISO1: Prerequisite validation
    # ------------------------------------------------------------------

    def _validate_prerequisites(self, scenario):
        """Check that required data exists before running a scenario.

        Reads prerequisites.data from the scenario YAML and verifies
        each requirement. Fails fast with a clear message if missing.
        """
        prereqs = scenario.get("prerequisites", {})
        required_data = prereqs.get("data", [])

        for requirement in required_data:
            req_type = requirement.get("type", "")
            req_name = requirement.get("name", "")

            if req_type == "client":
                from apps.clients.models import ClientFile
                # Encrypted field — must check in Python
                found = any(
                    c.first_name == req_name
                    for c in ClientFile.objects.all()
                )
                if not found:
                    self.fail(
                        f"PREREQUISITE MISSING: Client '{req_name}' not "
                        f"found. Seed demo data or run the setup scenario "
                        f"first. (Scenario: {scenario['id']})"
                    )

            elif req_type == "user":
                from apps.auth_app.models import User
                if not User.objects.filter(username=req_name).exists():
                    self.fail(
                        f"PREREQUISITE MISSING: User '{req_name}' not "
                        f"found. (Scenario: {scenario['id']})"
                    )

            elif req_type == "program":
                from apps.programs.models import Program
                if not Program.objects.filter(name=req_name).exists():
                    self.fail(
                        f"PREREQUISITE MISSING: Program '{req_name}' not "
                        f"found. (Scenario: {scenario['id']})"
                    )

    def _seed_bulk_clients(self, count=150):
        """Create many active clients for executive dashboard scenarios.

        DITL-E1 (Margaret) needs 140+ active clients to make the dashboard
        numbers realistic. This creates simple client records across both
        programs.
        """
        from apps.clients.models import ClientFile, ClientProgramEnrolment

        existing = ClientFile.objects.count()
        if existing >= count:
            return  # Already seeded

        needed = count - existing
        for i in range(needed):
            client = ClientFile.objects.create(is_demo=False)
            client.first_name = f"Client{i + existing}"
            client.last_name = f"Test{i + existing}"
            client.status = "active"
            client.save()
            # Alternate between programs
            program = self.program_a if i % 2 == 0 else self.program_b
            ClientProgramEnrolment.objects.create(
                client_file=client, program=program,
            )

    # ------------------------------------------------------------------
    # Scenario execution
    # ------------------------------------------------------------------

    def run_scenario(self, scenario, personas=None, screenshot_dir=None):
        """Execute a full scenario and return a ScenarioResult.

        QA-ISO1: Fresh context, auto-login, prerequisite validation.
        QA-T10: Objective scores computed alongside LLM evaluation.

        Args:
            scenario: Parsed scenario dict from YAML.
            personas: Dict of persona_id -> persona_data.
            screenshot_dir: Where to save screenshots (optional).

        Returns:
            ScenarioResult with all step evaluations.
        """
        personas = personas or self.personas or {}

        # QA-ISO1: Fresh browser context with locale from persona
        self._setup_context_for_scenario(scenario, personas)

        # QA-ISO1: Validate prerequisites before running
        self._validate_prerequisites(scenario)

        # QA-ISO1: Auto-login from persona data
        current_user = self._auto_login_for_scenario(scenario, personas)

        # Resolve expected language for objective scoring (QA-T10)
        persona_id = scenario.get("persona", "")
        persona_data = personas.get(persona_id, {})
        expected_lang = _get_persona_language(persona_data)

        result = ScenarioResult(
            scenario_id=scenario["id"],
            title=scenario.get("title", ""),
        )

        steps = scenario.get("steps", [])
        context_chain = []  # Accumulate context from previous steps

        for step in steps:
            step_id = step.get("id", 0)
            actor = step.get("actor", persona_id)

            # Resolve this step's actor persona language for scoring
            actor_data = personas.get(actor, persona_data)
            step_expected_lang = _get_persona_language(actor_data)

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

            # QA-T10: Compute objective scores
            objective_scores = compute_objective_scores(
                capture=capture,
                actions=actions,
                expected_lang=step_expected_lang,
            )

            # Build context chain for cross-step evaluation
            prev_context = step.get("context_from_previous", "")
            if not prev_context and context_chain:
                prev_context = " | ".join(context_chain[-3:])  # Last 3 steps

            # LLM evaluation (if enabled)
            if self.use_llm:
                persona_desc = format_persona_for_prompt(actor_data)
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
                    evaluation.objective_scores = objective_scores
                    result.step_evaluations.append(evaluation)
            else:
                # Dry-run mode — record objective scores without LLM
                placeholder = StepEvaluation(
                    scenario_id=scenario["id"],
                    step_id=step_id,
                    persona_id=actor,
                    one_line_summary=f"[DRY RUN] Captured: {capture.url}",
                    objective_scores=objective_scores,
                )
                result.step_evaluations.append(placeholder)

            # Add to context chain
            intent = step.get("intent", "")
            context_chain.append(
                f"Step {step_id} ({actor}): {intent} -> {capture.url}"
            )

        return result

    def run_narrative(self, scenario, personas=None, screenshot_dir=None):
        """Execute a day-in-the-life narrative scenario.

        DITL scenarios have 'moments' instead of 'steps'. They don't have
        explicit Playwright actions — instead, we capture key pages that
        correspond to each moment and send everything to the LLM for a
        holistic narrative assessment.

        The runner logs in as the persona, then visits key pages (dashboard,
        client list, client profile, note form) and captures state at each.
        The LLM gets the full narrative context plus the page captures.
        """
        personas = personas or self.personas or {}

        # QA-ISO1: Fresh context with locale from persona
        self._setup_context_for_scenario(scenario, personas)

        result = ScenarioResult(
            scenario_id=scenario["id"],
            title=scenario.get("title", ""),
        )

        persona_id = scenario.get("persona", "")
        moments = scenario.get("moments", [])
        if not moments:
            return result

        # Determine login user from persona data
        persona_data = personas.get(persona_id, {})
        test_user = persona_data.get("test_user", {})
        username = test_user.get("username", "staff")
        expected_lang = _get_persona_language(persona_data)

        self.login_via_browser(username)

        # Key pages to capture for narrative evaluation
        # Each moment maps to a page we can actually navigate to
        key_pages = [
            ("/", "dashboard"),
            ("/clients/", "client_list"),
        ]

        # Capture the dashboard and client list
        for page_url, label in key_pages:
            self.page.goto(self.live_url(page_url))
            self.page.wait_for_load_state("networkidle")

            capture = capture_step_state(
                page=self.page,
                scenario_id=scenario["id"],
                step_id=len(result.step_evaluations) + 1,
                actor_persona=persona_id,
                screenshot_dir=screenshot_dir,
                run_axe_fn=self.run_axe if hasattr(self, "run_axe") else None,
            )

            # QA-T10: Objective scores (no actions for narrative pages)
            objective_scores = compute_objective_scores(
                capture=capture,
                actions=None,
                expected_lang=expected_lang,
            )

            if self.use_llm:
                persona_desc = format_persona_for_prompt(persona_data)
                page_state_text = capture_to_evaluation_context(capture)

                # Build a combined prompt with narrative context
                narrative = scenario.get("narrative", "")
                moment_texts = "\n".join(
                    f"- {m.get('time', '')}: {m.get('event', '')} — "
                    f"{_get_moment_action(m)}"
                    for m in moments
                )
                eval_focus = "\n".join(
                    f"- {f}" for f in scenario.get("evaluation_focus", [])
                )

                # Create a synthetic step for the evaluator
                step = {
                    "id": len(result.step_evaluations) + 1,
                    "actor": persona_id,
                    "intent": f"Narrative: {label} — {narrative[:200]}",
                    "satisfaction_criteria": scenario.get("evaluation_focus", []),
                    "frustration_triggers": [],
                }

                context = (
                    f"NARRATIVE CONTEXT:\n{narrative}\n\n"
                    f"DAY'S MOMENTS:\n{moment_texts}\n\n"
                    f"EVALUATION FOCUS:\n{eval_focus}\n\n"
                    f"SCORING NOTE: {scenario.get('scoring_note', '')}"
                )

                evaluation = evaluate_step(
                    persona_desc=persona_desc,
                    step=step,
                    page_state_text=page_state_text,
                    context_from_previous=context,
                )
                if evaluation:
                    evaluation.scenario_id = scenario["id"]
                    evaluation.persona_id = persona_id
                    evaluation.objective_scores = objective_scores
                    result.step_evaluations.append(evaluation)
            else:
                placeholder = StepEvaluation(
                    scenario_id=scenario["id"],
                    step_id=len(result.step_evaluations) + 1,
                    persona_id=persona_id,
                    one_line_summary=f"[DRY RUN] DITL capture: {capture.url}",
                    objective_scores=objective_scores,
                )
                result.step_evaluations.append(placeholder)

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

            elif "wait" in action:
                # Timed wait in milliseconds (e.g., simulate idle period)
                # Cap at 30 seconds for test speed; real idle times are symbolic
                ms = min(action["wait"], 30000)
                self.page.wait_for_timeout(ms)

            elif "set_viewport" in action:
                vp = action["set_viewport"]
                self.page.set_viewport_size({
                    "width": vp.get("width", 1280),
                    "height": vp.get("height", 720),
                })

            elif "set_zoom" in action:
                zoom = action["set_zoom"]
                self.page.evaluate(
                    f"document.documentElement.style.zoom = '{zoom}%'"
                )

            elif "emulate_touch" in action:
                # Touch emulation is set at context creation via prerequisites.
                # This action is a no-op if the context was already created
                # with has_touch=True. Logged for clarity.
                pass

            elif "set_high_contrast" in action:
                # High contrast is set at context creation via prerequisites.
                # This action is a no-op if the context was already created
                # with forced_colors='active'.
                pass

            elif "set_network" in action:
                condition = action["set_network"]
                if condition == "offline":
                    self._context.set_offline(True)
                elif condition == "online":
                    self._context.set_offline(False)
                    # Close CDP throttle session if open
                    if self._cdp_session:
                        try:
                            self._cdp_session.send(
                                "Network.emulateNetworkConditions",
                                {
                                    "offline": False,
                                    "latency": 0,
                                    "downloadThroughput": -1,
                                    "uploadThroughput": -1,
                                },
                            )
                        except Exception:
                            pass
                elif condition == "Slow 3G":
                    # Use Chrome DevTools Protocol for throttling
                    try:
                        self._cdp_session = self._context.new_cdp_session(
                            self.page
                        )
                        self._cdp_session.send(
                            "Network.emulateNetworkConditions",
                            {
                                "offline": False,
                                "latency": 500,
                                "downloadThroughput": 50000,  # ~400kbps
                                "uploadThroughput": 50000,
                            },
                        )
                    except Exception:
                        pass  # CDP not available — proceed without throttle

            # Small pause between actions for realism
            self.page.wait_for_timeout(100)
