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

import pytest

from tests.ux_walkthrough.browser_base import BrowserTestBase, TEST_PASSWORD
from tests.utils.page_capture import (
    AXE_REPORT_PATH,
    MANIFEST_PATH,
    PAGE_INVENTORY_PATH,
    PERSONA_MAP,
    PHASE1_STATES,
    SCREENSHOT_DIR,
    capture_page_screenshot,
    expand_personas,
    load_page_inventory,
    new_manifest,
    resolve_url_pattern,
    run_axe_for_page,
    write_axe_report,
    write_manifest,
)


@pytest.mark.skipif(
    not PAGE_INVENTORY_PATH.exists(),
    reason=f"QA scenarios repo not available: {PAGE_INVENTORY_PATH}",
)
class TestPageCapture(BrowserTestBase):
    """Capture screenshots of all pages for all authorized personas."""

    def _create_test_data(self):
        """Extend base test data with all persona users + groups + messages."""
        super()._create_test_data()
        self._create_extra_persona_users()
        self._create_group_data()
        self._create_message_data()

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
                preferred_language="en",  # BUG-14: explicit preference prevents
                                          # stale cookie from setting lang="fr"
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
        """Create group with 8+ members and 12+ sessions for attendance grid.

        QA-PA-TEST1: The groups-attendance page needs a populated attendance
        matrix (8 members x 12 sessions = 96 cells) so page captures show
        a realistic attendance report rather than a sparse grid.
        """
        import random
        from datetime import date, timedelta

        from apps.clients.models import ClientFile, ClientProgramEnrolment
        from apps.groups.models import (
            Group,
            GroupMembership,
            GroupSession,
            GroupSessionAttendance,
        )

        self.group = Group.objects.create(
            name="Weekly Check-In",
            group_type="group",
            program=self.program_a,
            description="Weekly peer support session",
        )

        # --- 8 group members (2 existing clients + 6 named non-clients) ---
        member_a = GroupMembership.objects.create(
            group=self.group, client_file=self.client_a, role="member",
        )
        member_b = GroupMembership.objects.create(
            group=self.group, client_file=self.client_b, role="member",
        )

        # Create 6 additional clients for realistic member names
        extra_names = [
            ("Amara", "Osei"),
            ("Jean-Luc", "Bergeron"),
            ("Priya", "Sharma"),
            ("Marcus", "Williams"),
            ("Fatima", "Hassan"),
            ("Riley", "Chen"),
        ]
        extra_memberships = [member_a, member_b]
        for first, last in extra_names:
            cf = ClientFile.objects.create(is_demo=False)
            cf.first_name = first
            cf.last_name = last
            cf.status = "active"
            cf.save()
            ClientProgramEnrolment.objects.create(
                client_file=cf, program=self.program_a,
            )
            m = GroupMembership.objects.create(
                group=self.group, client_file=cf, role="member",
            )
            extra_memberships.append(m)

        # Make one member a leader for variety
        extra_memberships[0].role = "leader"
        extra_memberships[0].save()

        all_memberships = extra_memberships  # 8 total

        # --- 12 weekly sessions over the past 12 weeks ---
        rng = random.Random(42)  # deterministic for reproducible captures
        vibes = ["rough", "low", "solid", "great", "solid", "great"]
        session_notes = [
            "Good energy today. Several members shared updates.",
            "Quieter session — two members absent.",
            "Great discussion on housing barriers.",
            "New member introduced themselves.",
            "Follow-up on referrals from last week.",
            "Group discussed coping strategies.",
            "Short session due to holiday schedule.",
            "Facilitator covered budgeting basics.",
            "Peer mentoring pairs formed.",
            "Mid-program check-in — goals reviewed.",
            "Guest speaker on employment readiness.",
            "Wrap-up and celebration of milestones.",
        ]

        sessions = []
        today = date.today()
        for i in range(12):
            session_date = today - timedelta(weeks=11 - i)
            gs = GroupSession.objects.create(
                group=self.group,
                facilitator=self.staff_user,
                session_date=session_date,
                group_vibe=vibes[i % len(vibes)],
            )
            gs.notes = session_notes[i]
            gs.save()
            sessions.append(gs)

        # --- Attendance records: realistic pattern (mostly present) ---
        for gs in sessions:
            for membership in all_memberships:
                # ~80% attendance rate with some variation per member
                present = rng.random() < 0.80
                GroupSessionAttendance.objects.create(
                    group_session=gs,
                    membership=membership,
                    present=present,
                )

        # Keep reference to first session for backward compatibility
        self.group_session = sessions[0]

    # ------------------------------------------------------------------
    # Staff message data (for comm-my-messages populated state)
    # ------------------------------------------------------------------

    def _create_message_data(self):
        """Create staff messages so the My Messages page shows populated state.

        QA-PA-TEST2: The comm-my-messages page needs actual StaffMessage
        records so the populated state screenshot shows a realistic inbox
        with unread and urgent messages, rather than the empty state.
        """
        from apps.auth_app.models import User
        from apps.communications.models import StaffMessage

        # Messages for the main staff user (DS1 = "staff" username)
        messages_for_staff = [
            {
                "left_by": self.receptionist_user,
                "content": "Mike Thompson called — wants to reschedule Wednesday appointment to Friday.",
                "is_urgent": False,
            },
            {
                "left_by": self.receptionist_user,
                "content": "Jane's mother dropped off completed intake forms at front desk.",
                "is_urgent": False,
            },
            {
                "left_by": self.manager_user,
                "content": "Please update Jane Doe's plan before the monthly review on Friday.",
                "is_urgent": True,
            },
            {
                "left_by": self.receptionist_user,
                "content": "Voicemail from CMHA — returning your call about housing referral.",
                "is_urgent": False,
            },
            {
                "left_by": self.receptionist_user,
                "content": "Bob Smith is here for his 2pm appointment, waiting in the lobby.",
                "is_urgent": True,
            },
        ]

        for msg_data in messages_for_staff:
            msg = StaffMessage(
                client_file=self.client_a,
                for_user=self.staff_user,
                left_by=msg_data["left_by"],
                author_program=self.program_a,
                is_urgent=msg_data["is_urgent"],
            )
            msg.content = msg_data["content"]
            msg.save()

        # Also create messages for other personas so their "populated" captures work
        # DS1b (staff_new), DS2 (staff_fr), PM1 (manager)
        staff_new = User.objects.filter(username="staff_new").first()
        if staff_new:
            msg = StaffMessage(
                client_file=self.client_a,
                for_user=staff_new,
                left_by=self.receptionist_user,
                author_program=self.program_a,
            )
            msg.content = "Welcome note: your first client file is ready for review."
            msg.save()

        staff_fr = User.objects.filter(username="staff_fr").first()
        if staff_fr:
            msg = StaffMessage(
                client_file=self.client_a,
                for_user=staff_fr,
                left_by=self.receptionist_user,
                author_program=self.program_a,
            )
            msg.content = "Message from reception — appel de la famille de Jane Doe."
            msg.save()

        # Message for manager (PM1 sees all programme messages)
        msg = StaffMessage(
            client_file=self.client_b,
            for_user=self.manager_user,
            left_by=self.staff_user,
            author_program=self.program_a,
        )
        msg.content = "Monthly statistics are ready for your review."
        msg.save()

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
        skip_axe = os.environ.get("PAGE_CAPTURE_SKIP_AXE", "").strip() == "1"

        manifest = new_manifest()
        axe_scans = []  # Accumulated for standalone axe report
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
                "axe_results": [],
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
                    # Navigate once per page+persona+state (not per breakpoint)
                    full_url = self.live_url(resolved)
                    try:
                        self.page.goto(full_url, timeout=15000)
                        self._wait_for_idle()
                        page_loaded = True
                    except Exception as exc:
                        page_loaded = False
                        for bp in breakpoints:
                            if filter_breakpoints and bp not in filter_breakpoints:
                                continue
                            manifest["missing_screenshots"].append({
                                "page_id": page_id,
                                "persona": persona_id,
                                "state": state,
                                "breakpoint": bp,
                                "reason": str(exc),
                            })
                        print(
                            f"  FAIL  {page_id}/{persona_id}/{state}: {exc}",
                            flush=True,
                        )
                        continue

                    # Axe scan (once per page+persona+state, before viewport resizing)
                    if not skip_axe and page_loaded:
                        axe_result = run_axe_for_page(self.run_axe)
                        axe_result["page_id"] = page_id
                        axe_result["persona"] = persona_id
                        axe_result["state"] = state
                        axe_scans.append(axe_result)

                        page_manifest["axe_results"].append({
                            "persona": persona_id,
                            "state": state,
                            "violation_count": axe_result["violation_count"],
                            "violations": axe_result["violations"],
                        })

                        manifest["axe_total_scans"] += 1
                        if axe_result["violation_count"] > 0:
                            manifest["axe_total_violations"] += (
                                axe_result["violation_count"]
                            )
                            print(
                                f"  AXE  {page_id}/{persona_id}/{state}: "
                                f"{axe_result['violation_count']} violations",
                                flush=True,
                            )
                        elif axe_result.get("error"):
                            print(
                                f"  AXE  {page_id}/{persona_id}/{state}: "
                                f"ERROR {axe_result['error'][:60]}",
                                flush=True,
                            )

                    # Screenshots at each breakpoint
                    for bp in breakpoints:
                        if filter_breakpoints and bp not in filter_breakpoints:
                            continue

                        filename = f"{page_id}-{persona_id}-{state}-{bp}.png"
                        filepath = SCREENSHOT_DIR / filename

                        try:
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

        # Compute axe pages-with-violations count
        if axe_scans:
            pages_with_axe_issues = {
                s["page_id"] for s in axe_scans if s["violation_count"] > 0
            }
            manifest["axe_pages_with_violations"] = len(pages_with_axe_issues)

        # Finalise manifest
        manifest["personas_tested"] = sorted(personas_seen)
        manifest["states_captured"] = sorted(states_seen)
        write_manifest(manifest)

        # Write standalone axe report
        if axe_scans:
            write_axe_report(axe_scans, manifest["timestamp"])

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
        if not skip_axe:
            axe_scans_count = manifest.get("axe_total_scans", 0)
            axe_violations = manifest.get("axe_total_violations", 0)
            axe_pages = manifest.get("axe_pages_with_violations", 0)
            axe_errors = sum(1 for s in axe_scans if s.get("error"))
            print(f"\nAccessibility (axe-core)")
            print(f"------------------------")
            print(f"Axe scans: {axe_scans_count}")
            print(f"Pages with violations: {axe_pages}")
            print(f"Total violations: {axe_violations}")
            if axe_errors and axe_errors == axe_scans_count:
                print(f"WARNING: All {axe_errors} axe scans failed — "
                      f"check CDN connectivity or network access")
            elif axe_errors:
                print(f"Axe scan errors: {axe_errors}")
            print(f"Axe report: {AXE_REPORT_PATH}")
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
