"""Execute scenario steps using Playwright and capture state.

Extends BrowserTestBase from the existing UX walkthrough framework.

QA-ISO1: Fresh browser context per scenario, locale from persona,
         auto-login from persona data, prerequisite validation.
QA-T10:  Objective scoring for accessibility, efficiency, language.
QA-W4:   Action verification — retry fill/click/login_as on failure.
QA-W5:   DITL key_moments screenshot coverage.
"""
import logging
import os
import re

from django.utils import timezone

from ..ux_walkthrough.browser_base import BrowserTestBase, TEST_PASSWORD

from .llm_evaluator import evaluate_step, format_persona_for_prompt
from .objective_scorer import compute_objective_scores, count_user_actions
from .score_models import ScenarioResult, StepEvaluation
from .state_capture import capture_step_state, capture_to_evaluation_context

logger = logging.getLogger(__name__)


def _slugify(text, max_length=40):
    """Create a filesystem-safe slug from text.

    Converts to lowercase, replaces non-alphanumeric characters with
    hyphens, and truncates to max_length.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:max_length].rstrip("-")


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
    eval_model = None  # Override LLM model for evaluation (None = default)
    eval_temperature = None  # Override LLM temperature (None = API default)

    # CDP session for network throttling (lazy-created)
    _cdp_session = None

    # Timeout (ms) for networkidle waits — pages with HTMX polling or timers
    # may never reach idle, so we cap the wait and fall back to domcontentloaded.
    _networkidle_timeout = 10000

    def _wait_for_idle(self):
        """Wait for network idle, falling back to domcontentloaded on timeout.

        Pages with HTMX polling, timers, or long-running fetches may never
        reach 'networkidle'. Rather than hang forever, cap the wait and
        continue — the page is usable once DOM content has loaded.
        """
        try:
            self.page.wait_for_load_state(
                "networkidle", timeout=self._networkidle_timeout
            )
        except Exception:
            self.page.wait_for_load_state("domcontentloaded")

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
                preferred_language="fr",
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

        # DS1c: Casey with ADHD (cognitive accessibility profile)
        if not User.objects.filter(username="staff_adhd").exists():
            staff_adhd = User.objects.create_user(
                username="staff_adhd", password=TEST_PASSWORD,
                display_name="Casey Parker",
            )
            UserProgramRole.objects.create(
                user=staff_adhd, program=self.program_a, role="staff",
            )

        # DS4: Riley Chen (voice navigation / Dragon user)
        if not User.objects.filter(username="staff_voice").exists():
            staff_voice = User.objects.create_user(
                username="staff_voice", password=TEST_PASSWORD,
                display_name="Riley Chen",
            )
            UserProgramRole.objects.create(
                user=staff_voice, program=self.program_a, role="staff",
            )

        # PM1: Morgan Tremblay (program manager, cross-program)
        if not User.objects.filter(username="program_mgr").exists():
            program_mgr = User.objects.create_user(
                username="program_mgr", password=TEST_PASSWORD,
                display_name="Morgan Tremblay",
            )
            UserProgramRole.objects.create(
                user=program_mgr, program=self.program_a,
                role="program_manager",
            )
            UserProgramRole.objects.create(
                user=program_mgr, program=self.program_b,
                role="program_manager",
            )

        # E2: Kwame Asante (second admin)
        if not User.objects.filter(username="admin2").exists():
            admin2 = User.objects.create_user(
                username="admin2", password=TEST_PASSWORD,
                display_name="Kwame Asante",
            )
            admin2.is_admin = True
            admin2.save()
            UserProgramRole.objects.create(
                user=admin2, program=self.program_a, role="executive",
            )
            UserProgramRole.objects.create(
                user=admin2, program=self.program_b, role="executive",
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

        # Helper: check if a client already exists by first name
        # (encrypted field — can't filter in SQL)
        all_clients = list(ClientFile.objects.all())

        def _client_exists(first):
            return any(c.first_name == first for c in all_clients)

        from apps.clients.models import ClientDetailValue
        from apps.notes.models import ProgressNote
        staff = User.objects.filter(username="staff").first()

        # SCN-040: Benoit Tremblay (French-accented name for bilingual intake)
        if not _client_exists("Benoit"):
            benoit = ClientFile.objects.create(is_demo=False)
            benoit.first_name = "Benoit"
            benoit.last_name = "Tremblay"
            benoit.status = "active"
            benoit.save()
            ClientProgramEnrolment.objects.create(
                client_file=benoit, program=self.program_a,
            )

        # SCN-042: Aaliyah Thompson (multi-program client — dual enrolment)
        if not _client_exists("Aaliyah"):
            aaliyah = ClientFile.objects.create(is_demo=False)
            aaliyah.first_name = "Aaliyah"
            aaliyah.last_name = "Thompson"
            aaliyah.status = "active"
            aaliyah.save()
            ClientProgramEnrolment.objects.create(
                client_file=aaliyah, program=self.program_a,
            )
            ClientProgramEnrolment.objects.create(
                client_file=aaliyah, program=self.program_b,
            )
            ProgressNote.objects.create(
                client_file=aaliyah, author=staff,
                author_program=self.program_a, note_type="quick",
            )

        # SCN-070: David Park (consent client with notes for PIPEDA withdrawal)
        if not _client_exists("David"):
            david = ClientFile.objects.create(is_demo=False)
            david.first_name = "David"
            david.last_name = "Park"
            david.status = "active"
            david.consent_given_at = timezone.now()
            david.consent_type = "written"
            david.save()
            ClientProgramEnrolment.objects.create(
                client_file=david, program=self.program_a,
            )
            for i in range(5):
                note = ProgressNote.objects.create(
                    client_file=david, author=staff,
                    author_program=self.program_a, note_type="quick",
                )
                note.notes_text = f"Session {i + 1} progress note."
                note.save()

        # SCN-015, SCN-058: Maria Santos (batch notes, cognitive load)
        if not _client_exists("Maria"):
            maria = ClientFile.objects.create(is_demo=False)
            maria.first_name = "Maria"
            maria.last_name = "Santos"
            maria.status = "active"
            maria.save()
            ClientProgramEnrolment.objects.create(
                client_file=maria, program=self.program_a,
            )
            if hasattr(self, "phone_field"):
                ClientDetailValue.objects.create(
                    client_file=maria, field_def=self.phone_field,
                    value="416-555-0147",
                )

        # SCN-015: Alex Chen (batch note entry)
        if not _client_exists("Alex"):
            alex = ClientFile.objects.create(is_demo=False)
            alex.first_name = "Alex"
            alex.last_name = "Chen"
            alex.status = "active"
            alex.save()
            ClientProgramEnrolment.objects.create(
                client_file=alex, program=self.program_a,
            )

        # SCN-015, SCN-025: Priya Patel (batch notes, receptionist lookup)
        if not _client_exists("Priya"):
            priya = ClientFile.objects.create(is_demo=False)
            priya.first_name = "Priya"
            priya.last_name = "Patel"
            priya.status = "active"
            priya.save()
            ClientProgramEnrolment.objects.create(
                client_file=priya, program=self.program_a,
            )
            if hasattr(self, "phone_field"):
                ClientDetailValue.objects.create(
                    client_file=priya, field_def=self.phone_field,
                    value="905-555-0233",
                )

        # SCN-049: Marcus Williams (shared-device handoff, data bleed test)
        if not _client_exists("Marcus"):
            marcus = ClientFile.objects.create(is_demo=False)
            marcus.first_name = "Marcus"
            marcus.last_name = "Williams"
            marcus.status = "active"
            marcus.save()
            ClientProgramEnrolment.objects.create(
                client_file=marcus, program=self.program_a,
            )
            ProgressNote.objects.create(
                client_file=marcus, author=staff,
                author_program=self.program_a, note_type="quick",
            )

        # SCN-062: 8 clients for ARIA live region fatigue test
        # Re-fetch client list after additions above
        all_clients = list(ClientFile.objects.all())
        existing_full = {
            f"{c.first_name} {c.last_name}".strip()
            for c in all_clients
        }
        aria_clients = [
            ("Alice", "Martin"), ("Bob", "Garcia"),
            ("Carol", "Nguyen"), ("David", "Okafor"),
            ("Elena", "Petrov"), ("Frank", "Yamamoto"),
            ("Grace", "Ibrahim"), ("Henry", "Lavoie"),
        ]
        for first, last in aria_clients:
            full = f"{first} {last}"
            if full not in existing_full:
                c = ClientFile.objects.create(is_demo=False)
                c.first_name = first
                c.last_name = last
                c.status = "active"
                c.save()
                ClientProgramEnrolment.objects.create(
                    client_file=c, program=self.program_a,
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

        # QA-W2: Capture browser console output for diagnostics
        self._console_messages = []

        def _on_console(msg):
            level = msg.type  # 'log', 'warning', 'error', 'info', etc.
            text = msg.text
            self._console_messages.append(f"[{level}] {text}")

        def _on_page_error(error):
            self._console_messages.append(f"[exception] {error}")

        self.page.on("console", _on_console)
        self.page.on("pageerror", _on_page_error)

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
                # Encrypted field — must check in Python.
                # Compare full name (first + last), not just first_name.
                all_c = ClientFile.objects.all()
                found = any(
                    f"{c.first_name} {c.last_name}".strip() == req_name
                    for c in all_c
                )
                if not found:
                    self.fail(
                        f"PREREQUISITE MISSING: Client '{req_name}' not "
                        f"found. Seed demo data or run the setup scenario "
                        f"first. (Scenario: {scenario['id']})"
                    )

            elif req_type == "clients":
                # Plural form — list of client names (SCN-015, SCN-058)
                from apps.clients.models import ClientFile
                req_names = requirement.get("names", [])
                all_c = ClientFile.objects.all()
                existing = {
                    f"{c.first_name} {c.last_name}".strip()
                    for c in all_c
                }
                missing = [n for n in req_names if n not in existing]
                if missing:
                    self.fail(
                        f"PREREQUISITE MISSING: Clients not found: "
                        f"{', '.join(missing)}. "
                        f"(Scenario: {scenario['id']})"
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

    # ------------------------------------------------------------------
    # QA-W1: Pre-flight check — verify login, language, and data
    # ------------------------------------------------------------------

    def _run_preflight(self, persona, personas=None):
        """Verify the browser is logged in and ready before running steps.

        Runs AFTER _setup_context_for_scenario() and _auto_login_for_scenario()
        to validate that login succeeded, the correct language is active,
        and the dashboard loads with visible test data.

        Args:
            persona: Persona ID string (e.g. 'DS1').
            personas: Dict of persona_id -> persona_data.

        Returns:
            Tuple of (success: bool, reason: str).
        """
        personas = personas or self.personas or {}
        persona_data = personas.get(persona, {})
        expected_lang = _get_persona_language(persona_data)

        # 1. Verify login succeeded (URL should NOT be the login page)
        current_url = self.page.url
        if "/auth/login" in current_url:
            return (False, f"Still on login page ({current_url})")

        # 2. Verify a user badge or welcome indicator is present
        has_user_indicator = self.page.evaluate("""() => {
            const badge = document.querySelector(
                '[data-user-badge], .user-badge, .user-menu, '
                + 'nav [data-username], .navbar .dropdown'
            );
            return !!badge;
        }""")
        if not has_user_indicator:
            # Also check visible text for display name as fallback
            body_text = self.page.evaluate(
                "() => (document.body.innerText || '').substring(0, 3000)"
            )
            display_name = persona_data.get("display_name", "")
            username = _get_persona_username(persona_data)
            if display_name and display_name not in body_text:
                if not username or username not in body_text:
                    return (False, "No user badge or display name found on page")

        # 3. Verify correct language is set
        doc_lang = self.page.evaluate(
            "() => document.documentElement.lang || ''"
        )
        if expected_lang.startswith("fr") and not doc_lang.startswith("fr"):
            return (False, f"Expected French (fr), got lang='{doc_lang}'")
        if expected_lang.startswith("en") and doc_lang.startswith("fr"):
            return (False, f"Expected English (en), got lang='{doc_lang}'")

        # 4. Verify dashboard loaded (check for main content area)
        has_main_content = self.page.evaluate("""() => {
            const main = document.querySelector('main, [role="main"], .main-content');
            return main && main.innerText.trim().length > 10;
        }""")
        if not has_main_content:
            return (False, "Dashboard main content area is empty or missing")

        # 5. Verify at least one client is accessible (navigate to client list)
        self.page.goto(self.live_url("/clients/"))
        self._wait_for_idle()
        has_clients = self.page.evaluate("""() => {
            const rows = document.querySelectorAll(
                'table tbody tr, .client-card, [data-client-id]'
            );
            return rows.length > 0;
        }""")
        if not has_clients:
            return (False, "No clients visible in client list")

        # Navigate back to dashboard so scenario steps start from expected state
        self.page.goto(self.live_url("/"))
        self._wait_for_idle()

        return (True, "")

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
    # QA-W4: Action verification — retry + log on failure
    # ------------------------------------------------------------------

    def _verify_action(self, action_type, expected, actual, action_detail=""):
        """Check if an action produced the expected result.

        If verification fails, returns False so the caller can retry once.
        Logs ACTION_FAILED if the retry also fails.

        Args:
            action_type: 'fill', 'click', or 'login_as'.
            expected: The expected value or state description.
            actual: The actual value or state observed.
            action_detail: Human-readable description of the action.

        Returns:
            True if expected matches actual, False otherwise.
        """
        if expected == actual:
            return True

        logger.warning(
            "ACTION_VERIFY: %s mismatch — expected %r, got %r (%s)",
            action_type, expected, actual, action_detail,
        )
        return False

    def _log_action_failed(self, action_type, detail):
        """Log a failed action after retry was also unsuccessful."""
        logger.warning("ACTION_FAILED: %s — %s", action_type, detail)

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

        # QA-W1: Pre-flight check — verify login, language, and data
        preflight_ok, preflight_reason = self._run_preflight(
            persona_id, personas
        )
        if not preflight_ok:
            logger.warning(
                "Preflight FAILED for %s in %s: %s",
                persona_id, scenario["id"], preflight_reason,
            )
            result = ScenarioResult(
                scenario_id=scenario["id"],
                title=scenario.get("title", ""),
            )
            result.step_evaluations.append(
                StepEvaluation(
                    scenario_id=scenario["id"],
                    step_id=0,
                    persona_id=persona_id,
                    one_line_summary=(
                        f"BLOCKED: preflight failed — {preflight_reason}"
                    ),
                )
            )
            return result

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

                        # QA-W4: Verify login — should not be on login page
                        try:
                            post_login_url = self.page.url
                            if "/auth/login" in post_login_url:
                                # Retry once
                                self.login_via_browser(new_user)
                                post_login_url = self.page.url
                                if "/auth/login" in post_login_url:
                                    self._log_action_failed(
                                        "login_as",
                                        f"user={new_user} — still on "
                                        f"login page after retry",
                                    )
                        except Exception:
                            pass  # Verification failed — don't crash

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

            # QA-W2: Attach console messages and clear buffer for next step
            if hasattr(self, "_console_messages"):
                capture.console_log = list(self._console_messages)
                self._console_messages.clear()

                # Write console log file alongside screenshot (only if non-empty)
                if capture.console_log and screenshot_dir:
                    log_filename = (
                        f"{scenario['id']}_step{step_id}_{actor}_console.log"
                    )
                    log_path = os.path.join(screenshot_dir, log_filename)
                    os.makedirs(screenshot_dir, exist_ok=True)
                    with open(log_path, "w", encoding="utf-8") as f:
                        f.write("\n".join(capture.console_log))

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
                    model=self.eval_model,
                    temperature=self.eval_temperature,
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
            self._wait_for_idle()

            capture = capture_step_state(
                page=self.page,
                scenario_id=scenario["id"],
                step_id=len(result.step_evaluations) + 1,
                actor_persona=persona_id,
                screenshot_dir=screenshot_dir,
                run_axe_fn=self.run_axe if hasattr(self, "run_axe") else None,
            )

            # QA-W2: Attach console messages and clear buffer for next step
            if hasattr(self, "_console_messages"):
                capture.console_log = list(self._console_messages)
                self._console_messages.clear()

                if capture.console_log and screenshot_dir:
                    step_num = len(result.step_evaluations) + 1
                    log_filename = (
                        f"{scenario['id']}_step{step_num}"
                        f"_{persona_id}_console.log"
                    )
                    log_path = os.path.join(screenshot_dir, log_filename)
                    os.makedirs(screenshot_dir, exist_ok=True)
                    with open(log_path, "w", encoding="utf-8") as f:
                        f.write("\n".join(capture.console_log))

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
                    model=self.eval_model,
                    temperature=self.eval_temperature,
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

        # QA-W5: Capture screenshots for each key_moment defined in YAML
        key_moments = scenario.get("key_moments", [])
        for i, moment in enumerate(key_moments):
            moment_url = moment.get("url") or moment.get("page", "")
            if not moment_url:
                logger.info(
                    "DITL %s: key_moment %d has no url/page — skipping",
                    scenario["id"], i,
                )
                continue

            # Build a descriptive slug for the screenshot filename
            moment_label = moment.get("label", moment.get("event", ""))
            slug = _slugify(moment_label) if moment_label else f"page{i}"

            try:
                if moment_url.startswith("/"):
                    moment_url = self.live_url(moment_url)
                self.page.goto(moment_url)
                self._wait_for_idle()

                # Check for 404 / error page and skip if so
                status_text = self.page.evaluate(
                    "() => document.title || ''"
                )
                if "404" in status_text or "Not Found" in status_text:
                    logger.info(
                        "DITL %s: key_moment %d (%s) returned 404 — skipping",
                        scenario["id"], i, moment_url,
                    )
                    continue

                # Capture screenshot with a descriptive filename
                capture = capture_step_state(
                    page=self.page,
                    scenario_id=scenario["id"],
                    step_id=len(result.step_evaluations) + 1,
                    actor_persona=persona_id,
                    screenshot_dir=screenshot_dir,
                    run_axe_fn=(
                        self.run_axe if hasattr(self, "run_axe") else None
                    ),
                )

                # QA-W5: Also save a clearly-named screenshot file
                if screenshot_dir:
                    moment_filename = (
                        f"{scenario['id']}_moment{i}_{persona_id}_{slug}.png"
                    )
                    moment_path = os.path.join(screenshot_dir, moment_filename)
                    os.makedirs(screenshot_dir, exist_ok=True)
                    try:
                        self.page.screenshot(
                            path=moment_path, full_page=True, timeout=15000,
                        )
                    except Exception:
                        self.page.screenshot(
                            path=moment_path, full_page=False, timeout=15000,
                        )

                # Attach console messages
                if hasattr(self, "_console_messages"):
                    capture.console_log = list(self._console_messages)
                    self._console_messages.clear()

                # Objective scores for this moment's capture
                objective_scores = compute_objective_scores(
                    capture=capture,
                    actions=None,
                    expected_lang=expected_lang,
                )

                if self.use_llm:
                    persona_desc = format_persona_for_prompt(persona_data)
                    page_state_text = capture_to_evaluation_context(capture)

                    narrative = scenario.get("narrative", "")
                    moment_texts = "\n".join(
                        f"- {m.get('time', '')}: {m.get('event', '')} — "
                        f"{_get_moment_action(m)}"
                        for m in moments
                    )
                    eval_focus = "\n".join(
                        f"- {f}"
                        for f in scenario.get("evaluation_focus", [])
                    )

                    step = {
                        "id": len(result.step_evaluations) + 1,
                        "actor": persona_id,
                        "intent": (
                            f"Key moment: {moment_label or slug} — "
                            f"{narrative[:150]}"
                        ),
                        "satisfaction_criteria": scenario.get(
                            "evaluation_focus", []
                        ),
                        "frustration_triggers": [],
                    }

                    context = (
                        f"NARRATIVE CONTEXT:\n{narrative}\n\n"
                        f"DAY'S MOMENTS:\n{moment_texts}\n\n"
                        f"EVALUATION FOCUS:\n{eval_focus}\n\n"
                        f"KEY MOMENT {i}: {moment_label}\n\n"
                        f"SCORING NOTE: {scenario.get('scoring_note', '')}"
                    )

                    evaluation = evaluate_step(
                        persona_desc=persona_desc,
                        step=step,
                        page_state_text=page_state_text,
                        context_from_previous=context,
                        model=self.eval_model,
                        temperature=self.eval_temperature,
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
                        one_line_summary=(
                            f"[DRY RUN] DITL moment {i}: {capture.url}"
                        ),
                        objective_scores=objective_scores,
                    )
                    result.step_evaluations.append(placeholder)

            except Exception as exc:
                logger.warning(
                    "DITL %s: key_moment %d failed — %s: %s",
                    scenario["id"], i, type(exc).__name__, exc,
                )
                continue  # Don't abort — proceed to next moment

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
                self._wait_for_idle()

            elif "fill" in action:
                selector, value = action["fill"]
                try:
                    self.page.fill(selector, value, timeout=5000)
                except Exception:
                    pass  # Field not found — the LLM evaluator will note the issue

                # QA-W4: Verify fill — check the field has the expected value
                try:
                    actual_value = self.page.input_value(selector, timeout=2000)
                    if not self._verify_action(
                        "fill", value, actual_value,
                        f"selector={selector}",
                    ):
                        # Retry once
                        try:
                            self.page.fill(selector, "", timeout=2000)
                            self.page.fill(selector, value, timeout=5000)
                            actual_value = self.page.input_value(
                                selector, timeout=2000,
                            )
                            if not self._verify_action(
                                "fill", value, actual_value,
                                f"selector={selector} (retry)",
                            ):
                                self._log_action_failed(
                                    "fill",
                                    f"selector={selector}, "
                                    f"expected={value!r}, "
                                    f"got={actual_value!r}",
                                )
                        except Exception:
                            self._log_action_failed(
                                "fill",
                                f"selector={selector} — retry failed",
                            )
                except Exception:
                    pass  # Verification itself failed — don't crash

            elif "clear" in action:
                selector = action["clear"]
                try:
                    self.page.fill(selector, "", timeout=5000)
                except Exception:
                    pass

            elif "click" in action:
                selector = action["click"]
                # QA-W4: Record pre-click state for verification
                try:
                    pre_click_url = self.page.url
                    pre_click_text = self.page.evaluate(
                        "() => (document.body.innerText || '').substring(0, 500)"
                    )
                except Exception:
                    pre_click_url = ""
                    pre_click_text = ""

                try:
                    self.page.click(selector, timeout=5000)
                except Exception:
                    pass  # Click failed — the LLM evaluator will note the issue

                # QA-W4: Verify click — URL changed OR page content changed
                try:
                    # Brief wait for navigation/DOM update after click
                    self.page.wait_for_timeout(300)
                    post_click_url = self.page.url
                    post_click_text = self.page.evaluate(
                        "() => (document.body.innerText || '').substring(0, 500)"
                    )
                    url_changed = post_click_url != pre_click_url
                    dom_changed = post_click_text != pre_click_text
                    if not url_changed and not dom_changed:
                        # Retry once
                        try:
                            self.page.click(selector, timeout=5000)
                            self.page.wait_for_timeout(300)
                            retry_url = self.page.url
                            retry_text = self.page.evaluate(
                                "() => (document.body.innerText || '')"
                                ".substring(0, 500)"
                            )
                            retry_url_changed = retry_url != pre_click_url
                            retry_dom_changed = retry_text != pre_click_text
                            if not retry_url_changed and not retry_dom_changed:
                                self._log_action_failed(
                                    "click",
                                    f"selector={selector} — no URL or DOM "
                                    f"change detected after retry",
                                )
                        except Exception:
                            self._log_action_failed(
                                "click",
                                f"selector={selector} — retry failed",
                            )
                except Exception:
                    pass  # Verification itself failed — don't crash

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
                    self._wait_for_idle()

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

            elif "voice_command" in action:
                # Dragon NaturallySpeaking voice commands mapped to Playwright
                command = action["voice_command"]
                if command.lower().startswith("click "):
                    target_text = command[6:]  # Strip "Click "
                    try:
                        self.page.get_by_text(target_text, exact=False).first.click(timeout=5000)
                    except Exception:
                        pass  # Voice target not found — evaluator will note
                elif command.lower().startswith("go to "):
                    target = command[6:]  # Strip "Go to "
                    try:
                        self.page.get_by_label(target, exact=False).first.focus()
                    except Exception:
                        pass
                logger.info(f"Voice command: {command}")

            elif "dictate" in action:
                # Dragon dictation mapped to keyboard typing
                text = action["dictate"]
                self.page.keyboard.type(text)
                logger.info(f"Dictation: {text}")

            elif "intercept_network" in action:
                # Mock error responses via Playwright route interception
                config = action["intercept_network"]
                url_pattern = config.get("url", "**/*")
                status = config.get("status", 500)

                def _make_handler(s):
                    def handler(route):
                        route.fulfill(status=s, body=f"Mocked {s} error")
                    return handler

                self.page.route(url_pattern, _make_handler(status))

            elif "close_tab" in action:
                self.page.close()
                # Switch to the last open page in the context
                pages = self._context.pages
                if pages:
                    self.page = pages[-1]

            elif "open_new_tab" in action:
                new_page = self._context.new_page()
                self.page = new_page

            elif "go_back" in action:
                self.page.go_back()

            elif "screenshot" in action:
                # Explicit named screenshot capture
                name = action["screenshot"]
                screenshot_dir = os.environ.get("SCENARIO_HOLDOUT_DIR", "")
                if screenshot_dir:
                    path = os.path.join(
                        screenshot_dir, "reports", "screenshots",
                        f"{name}.png",
                    )
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    try:
                        self.page.screenshot(
                            path=path, full_page=True, timeout=15000,
                        )
                    except Exception:
                        self.page.screenshot(
                            path=path, full_page=False, timeout=15000,
                        )

            # Small pause between actions for realism
            self.page.wait_for_timeout(100)
