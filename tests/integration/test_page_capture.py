"""Page capture test for QA screenshot generation.

Captures screenshots of every page in the page inventory for every
authorized persona at multiple breakpoints. Outputs to the
konote-qa-scenarios repo for the /run-page-audit skill.

Run all pages:
    pytest tests/integration/test_page_capture.py -v -s

Filter to specific pages:
    set PAGE_CAPTURE_PAGES=auth-login,client-list
    pytest tests/integration/test_page_capture.py -v -s

Filter to specific personas:
    set PAGE_CAPTURE_PERSONAS=R1,DS1
    pytest tests/integration/test_page_capture.py -v -s

Filter to a single breakpoint:
    set PAGE_CAPTURE_BREAKPOINTS=1366x768
    pytest tests/integration/test_page_capture.py -v -s
"""
import os

from tests.ux_walkthrough.browser_base import BrowserTestBase, TEST_PASSWORD
from tests.utils.page_capture import (
    MANIFEST_PATH,
    PERSONA_MAP,
    PHASE1_STATES,
    SCREENSHOT_DIR,
    capture_page_screenshot,
    expand_personas,
    load_page_inventory,
    new_manifest,
    resolve_url_pattern,
    write_manifest,
)


class TestPageCapture(BrowserTestBase):
    """Capture screenshots of all pages for all authorized personas."""

    def _create_test_data(self):
        """Extend base test data with all persona users + groups."""
        super()._create_test_data()
        self._create_extra_persona_users()
        self._create_group_data()

    # ------------------------------------------------------------------
    # Extra persona users (mirrors scenario_runner.py lines 123-218)
    # ------------------------------------------------------------------

    def _create_extra_persona_users(self):
        from apps.auth_app.models import User
        from apps.programs.models import UserProgramRole

        # DS1b: Casey's first week (new staff user)
        if not User.objects.filter(username="staff_new").exists():
            u = User.objects.create_user(
                username="staff_new", password=TEST_PASSWORD,
                display_name="Casey New",
            )
            UserProgramRole.objects.create(
                user=u, program=self.program_a, role="staff",
            )

        # DS2: Jean-Luc (French-speaking staff)
        if not User.objects.filter(username="staff_fr").exists():
            u = User.objects.create_user(
                username="staff_fr", password=TEST_PASSWORD,
                display_name="Jean-Luc Bergeron",
            )
            UserProgramRole.objects.create(
                user=u, program=self.program_a, role="staff",
            )

        # DS3: Amara (accessibility / keyboard-only staff)
        if not User.objects.filter(username="staff_a11y").exists():
            u = User.objects.create_user(
                username="staff_a11y", password=TEST_PASSWORD,
                display_name="Amara Osei",
            )
            UserProgramRole.objects.create(
                user=u, program=self.program_a, role="staff",
            )

        # R2: Omar (tech-savvy part-time receptionist)
        if not User.objects.filter(username="frontdesk2").exists():
            u = User.objects.create_user(
                username="frontdesk2", password=TEST_PASSWORD,
                display_name="Omar Hussain",
            )
            UserProgramRole.objects.create(
                user=u, program=self.program_b, role="receptionist",
            )

        # R2-FR: Amelie (French receptionist)
        if not User.objects.filter(username="frontdesk_fr").exists():
            u = User.objects.create_user(
                username="frontdesk_fr", password=TEST_PASSWORD,
                display_name="Amelie Tremblay",
            )
            UserProgramRole.objects.create(
                user=u, program=self.program_a, role="receptionist",
            )

        # DS1c: Casey with ADHD (cognitive accessibility)
        if not User.objects.filter(username="staff_adhd").exists():
            u = User.objects.create_user(
                username="staff_adhd", password=TEST_PASSWORD,
                display_name="Casey Parker",
            )
            UserProgramRole.objects.create(
                user=u, program=self.program_a, role="staff",
            )

        # DS4: Riley Chen (voice navigation / Dragon user)
        if not User.objects.filter(username="staff_voice").exists():
            u = User.objects.create_user(
                username="staff_voice", password=TEST_PASSWORD,
                display_name="Riley Chen",
            )
            UserProgramRole.objects.create(
                user=u, program=self.program_a, role="staff",
            )

        # PM1: Morgan Tremblay (program manager, cross-program)
        # Base class creates "manager" with program_a; add program_b for cross-program scenarios.
        mgr = User.objects.filter(username="manager").first()
        if mgr is None:
            mgr = User.objects.create_user(
                username="manager", password=TEST_PASSWORD,
                display_name="Morgan Tremblay",
            )
            UserProgramRole.objects.create(
                user=mgr, program=self.program_a, role="program_manager",
            )
        if not UserProgramRole.objects.filter(
            user=mgr, program=self.program_b,
        ).exists():
            UserProgramRole.objects.create(
                user=mgr, program=self.program_b, role="program_manager",
            )

        # E2: Kwame Asante (second executive/admin)
        if not User.objects.filter(username="admin2").exists():
            u = User.objects.create_user(
                username="admin2", password=TEST_PASSWORD,
                display_name="Kwame Asante",
            )
            u.is_admin = True
            u.save()
            UserProgramRole.objects.create(
                user=u, program=self.program_a, role="executive",
            )
            UserProgramRole.objects.create(
                user=u, program=self.program_b, role="executive",
            )

    # ------------------------------------------------------------------
    # Group data (for group-related pages)
    # ------------------------------------------------------------------

    def _create_group_data(self):
        from datetime import date

        from apps.groups.models import Group, GroupMembership, GroupSession

        self.group = Group.objects.create(
            name="Weekly Check-In",
            group_type="group",
            program=self.program_a,
            description="Weekly peer support session",
        )
        GroupMembership.objects.create(
            group=self.group, client_file=self.client_a, role="member",
        )
        self.group_session = GroupSession.objects.create(
            group=self.group,
            facilitator=self.staff_user,
            session_date=date.today(),
        )
        self.group_session.notes = "Good session today."
        self.group_session.save()

    # ------------------------------------------------------------------
    # Main capture test
    # ------------------------------------------------------------------

    def test_capture_all_pages(self):
        """Iterate pages x personas x states x breakpoints and screenshot."""
        pages = load_page_inventory()
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

        # Build lookup of real IDs for URL resolution
        test_data = self._build_test_data_dict()

        # Environment variable filters
        filter_pages = _env_list("PAGE_CAPTURE_PAGES")
        filter_personas = _env_list("PAGE_CAPTURE_PERSONAS")
        filter_breakpoints = _env_list("PAGE_CAPTURE_BREAKPOINTS")

        manifest = new_manifest()
        personas_seen = set()
        states_seen = set()
        current_persona = None  # track to avoid redundant logins

        for page_entry in pages:
            page_id = page_entry["page_id"]
            url_pattern = page_entry["url_pattern"]
            authorized = page_entry.get("authorized_personas", [])
            states = page_entry.get("states", ["default"])
            breakpoints = page_entry.get(
                "breakpoints", ["1366x768", "1920x1080", "375x667"]
            )

            if filter_pages and page_id not in filter_pages:
                continue

            # Skip non-routable URL patterns like "(any 403 error)"
            if url_pattern.startswith("("):
                manifest["skipped"].append({
                    "page_id": page_id,
                    "reason": f"Non-routable URL pattern: {url_pattern}",
                })
                continue

            # Resolve dynamic URL
            resolved = resolve_url_pattern(url_pattern, test_data)
            if resolved is None:
                manifest["skipped"].append({
                    "page_id": page_id,
                    "reason": f"Could not resolve URL: {url_pattern}",
                })
                continue

            # Phase 1: only capture default/populated states
            capturable_states = [s for s in states if s in PHASE1_STATES]
            if not capturable_states:
                manifest["skipped"].append({
                    "page_id": page_id,
                    "reason": f"No Phase 1 states (only {states})",
                })
                continue

            # Expand special persona tokens
            persona_ids = expand_personas(authorized)

            page_manifest = {
                "page_id": page_id,
                "url": resolved,
                "personas_captured": [],
                "states_captured": [],
                "screenshot_count": 0,
            }

            for persona_id in persona_ids:
                if filter_personas and persona_id not in filter_personas:
                    continue

                is_unauthenticated = (persona_id == "unauthenticated")
                username = None if is_unauthenticated else PERSONA_MAP.get(persona_id)

                if not is_unauthenticated and not username:
                    manifest["missing_screenshots"].append({
                        "page_id": page_id,
                        "persona": persona_id,
                        "reason": f"No username mapping for persona {persona_id}",
                    })
                    continue

                # Log in (or switch user) if persona changed
                if persona_id != current_persona:
                    try:
                        if is_unauthenticated:
                            # New context with no login
                            self.page.close()
                            self._context.close()
                            self._context = self._browser.new_context()
                            self.page = self._context.new_page()
                        else:
                            self.switch_user(username)
                        current_persona = persona_id
                    except Exception as exc:
                        manifest["missing_screenshots"].append({
                            "page_id": page_id,
                            "persona": persona_id,
                            "reason": f"Login failed: {exc}",
                        })
                        current_persona = None
                        continue

                for state in capturable_states:
                    for bp in breakpoints:
                        if filter_breakpoints and bp not in filter_breakpoints:
                            continue

                        filename = f"{page_id}-{persona_id}-{state}-{bp}.png"
                        filepath = SCREENSHOT_DIR / filename

                        try:
                            full_url = self.live_url(resolved)
                            self.page.goto(full_url, timeout=15000)
                            self._wait_for_idle()
                            capture_page_screenshot(self.page, filepath, bp)

                            manifest["total_screenshots"] += 1
                            page_manifest["screenshot_count"] += 1
                            personas_seen.add(persona_id)
                            states_seen.add(state)

                            if persona_id not in page_manifest["personas_captured"]:
                                page_manifest["personas_captured"].append(persona_id)
                            if state not in page_manifest["states_captured"]:
                                page_manifest["states_captured"].append(state)

                            print(f"  OK  {filename}", flush=True)

                        except Exception as exc:
                            manifest["missing_screenshots"].append({
                                "page_id": page_id,
                                "persona": persona_id,
                                "state": state,
                                "breakpoint": bp,
                                "reason": str(exc),
                            })
                            print(f"  FAIL  {filename}: {exc}", flush=True)

            manifest["pages"].append(page_manifest)
            manifest["pages_captured"] += 1

        # Finalise manifest
        manifest["personas_tested"] = sorted(personas_seen)
        manifest["states_captured"] = sorted(states_seen)
        write_manifest(manifest)

        # Summary
        total = manifest["total_screenshots"]
        skipped = len(manifest["skipped"])
        missing = len(manifest["missing_screenshots"])
        print(f"\nPage State Capture Complete")
        print(f"===========================")
        print(f"Pages captured: {manifest['pages_captured']}")
        print(f"Personas tested: {len(personas_seen)}")
        print(f"Total screenshots: {total}")
        print(f"Skipped pages: {skipped}")
        print(f"Missing screenshots: {missing}")
        print(f"\nManifest: {MANIFEST_PATH}")

        self.assertGreater(total, 0, "No screenshots were captured!")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_test_data_dict(self):
        """Build dict of placeholder name → real ID for URL resolution."""
        data = {
            "client_id": self.client_a.id,
            "note_id": self.note.id,
            "program_id": self.program_a.id,
            "group_id": self.group.id,
        }
        # plan section + target
        if hasattr(self, "plan_section"):
            data["section_id"] = self.plan_section.id
        if hasattr(self, "plan_target"):
            data["target_id"] = self.plan_target.id
        # slug for public registration forms
        data["slug"] = "intake"
        return data

    def _wait_for_idle(self):
        """Wait for network idle, falling back to domcontentloaded."""
        try:
            self.page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            self.page.wait_for_load_state("domcontentloaded")


def _env_list(var_name):
    """Read a comma-separated env var into a list, or None if not set."""
    val = os.environ.get(var_name, "").strip()
    if not val:
        return None
    return [x.strip() for x in val.split(",") if x.strip()]
