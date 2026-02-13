"""Admin workflow UX walkthrough tests — scenario-based.

Walks through every administrator workflow as if a new admin is setting
up KoNote for the first time.  Each scenario creates data, verifies the
CRUD cycle works, checks UX quality (labels, headings, CSRF, a11y), and
records results into the shared walkthrough report.

Run all admin scenarios:
    pytest tests/ux_walkthrough/test_admin_workflows.py -v

Run a single scenario:
    pytest tests/ux_walkthrough/test_admin_workflows.py::AdminProgramWorkflow -v
"""
from django.test import override_settings

from .base import TEST_KEY, UxScenarioBase
from .checker import Severity


# =====================================================================
# 1. Admin Dashboard — Finding Your Way
# =====================================================================


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AdminDashboardWorkflow(UxScenarioBase):
    """Scenario: Admin logs in and navigates the settings dashboard."""

    SCENARIO = "Admin Dashboard"

    def test_dashboard_navigation(self):
        self.login_as("admin")
        role = "Admin"

        # Home page — should have a link to admin settings
        resp = self.visit(
            role, "Home page (find admin link)", "/",
            role_should_see=["Settings"],
        )
        self.record_scenario(
            self.SCENARIO, role, "Home page — admin link visible",
            "/", resp.status_code, [],
        )

        # Admin dashboard — shows all configuration areas
        resp = self.visit(
            role, "Admin settings dashboard", "/admin/settings/",
            role_should_see=["Terminology", "Features"],
        )
        self.record_scenario(
            self.SCENARIO, role, "Admin dashboard loads",
            "/admin/settings/", resp.status_code, [],
        )

        # Verify non-admin can't access
        self.login_as("staff")
        resp = self.visit_forbidden(
            "Direct Service", "Admin dashboard (403)", "/admin/settings/",
        )
        self.record_scenario(
            self.SCENARIO, "Direct Service", "Non-admin blocked (403)",
            "/admin/settings/", resp.status_code, [],
        )


# =====================================================================
# 2. Feature Toggles
# =====================================================================


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AdminFeatureToggleWorkflow(UxScenarioBase):
    """Scenario: Admin enables custom fields and events."""

    SCENARIO = "Feature Toggles"

    def test_toggle_features(self):
        self.login_as("admin")
        role = "Admin"

        # View features page
        resp = self.visit(role, "Features page", "/admin/settings/features/")
        self.record_scenario(
            self.SCENARIO, role, "View feature toggles",
            "/admin/settings/features/", resp.status_code, [],
        )

        # Enable custom_fields
        resp = self.visit_and_follow(
            role, "Enable custom fields",
            "/admin/settings/features/",
            data={"feature_key": "custom_fields", "action": "enable"},
            expected_redirect="/admin/settings/features/",
        )
        self.record_scenario(
            self.SCENARIO, role, "Enable custom fields",
            "/admin/settings/features/", resp.status_code, [],
        )

        # Enable events
        resp = self.visit_and_follow(
            role, "Enable events",
            "/admin/settings/features/",
            data={"feature_key": "events", "action": "enable"},
            expected_redirect="/admin/settings/features/",
        )
        self.record_scenario(
            self.SCENARIO, role, "Enable events",
            "/admin/settings/features/", resp.status_code, [],
        )

        # Disable a feature
        resp = self.visit_and_follow(
            role, "Disable alerts",
            "/admin/settings/features/",
            data={"feature_key": "alerts", "action": "disable"},
            expected_redirect="/admin/settings/features/",
        )
        self.record_scenario(
            self.SCENARIO, role, "Disable alerts",
            "/admin/settings/features/", resp.status_code, [],
        )


# =====================================================================
# 3. Instance Settings
# =====================================================================


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AdminInstanceSettingsWorkflow(UxScenarioBase):
    """Scenario: Admin configures agency name and session timeout."""

    SCENARIO = "Instance Settings"

    def test_instance_settings(self):
        self.login_as("admin")
        role = "Admin"

        # View instance settings form
        resp = self.visit(
            role, "Instance settings form", "/admin/settings/instance/",
        )
        self.record_scenario(
            self.SCENARIO, role, "View instance settings",
            "/admin/settings/instance/", resp.status_code, [],
        )

        # Save instance settings
        resp = self.visit_and_follow(
            role, "Save instance settings",
            "/admin/settings/instance/",
            data={
                "product_name": "Hope House KoNote",
                "support_email": "admin@hopehouse.ca",
                "date_format": "Y-m-d",
                "session_timeout_minutes": "30",
                "document_storage_provider": "none",
                "document_storage_url_template": "",
                "logo_url": "",
                "privacy_officer_name": "Jane Smith",
                "privacy_officer_email": "privacy@hopehouse.ca",
            },
            expected_redirect="/admin/settings/instance/",
        )
        self.record_scenario(
            self.SCENARIO, role, "Save instance settings",
            "/admin/settings/instance/", resp.status_code, [],
        )


# =====================================================================
# 4. Program CRUD
# =====================================================================


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AdminProgramWorkflow(UxScenarioBase):
    """Scenario: Admin creates a new program, assigns staff, edits it."""

    SCENARIO = "Program Management"

    def test_program_crud(self):
        self.login_as("admin")
        role = "Admin"

        # View programs list
        resp = self.visit(role, "Programs list", "/programs/")
        self.record_scenario(
            self.SCENARIO, role, "View programs list",
            "/programs/", resp.status_code, [],
        )

        # Create program form
        resp = self.visit(
            role, "Create program form", "/programs/create/",
        )
        self.record_scenario(
            self.SCENARIO, role, "Open create program form",
            "/programs/create/", resp.status_code, [],
        )

        # Submit create program
        resp = self.visit_and_follow(
            role, "Submit new program",
            "/programs/create/",
            data={
                "name": "Employment Readiness",
                "description": "Helps clients prepare for employment.",
                "colour_hex": "#6366F1",
                "service_model": "individual",
                "status": "active",
            },
            expected_redirect="/programs/",
        )
        self.record_scenario(
            self.SCENARIO, role, "Create program",
            "/programs/create/", resp.status_code, [],
        )

        # Find the new program
        from apps.programs.models import Program
        new_program = Program.objects.filter(name="Employment Readiness").first()
        self.assertIsNotNone(new_program, "Program creation failed")
        pid = new_program.pk

        # View program detail
        resp = self.visit(
            role, "Program detail", f"/programs/{pid}/",
            role_should_see=["Edit"],
        )
        self.record_scenario(
            self.SCENARIO, role, "View program detail",
            f"/programs/{pid}/", resp.status_code, [],
        )

        # Edit program
        resp = self.visit(role, "Edit program form", f"/programs/{pid}/edit/")
        self.record_scenario(
            self.SCENARIO, role, "Open edit program form",
            f"/programs/{pid}/edit/", resp.status_code, [],
        )

        resp = self.visit_and_follow(
            role, "Update program",
            f"/programs/{pid}/edit/",
            data={
                "name": "Employment Readiness Plus",
                "description": "Updated description.",
                "colour_hex": "#6366F1",
                "service_model": "both",
                "status": "active",
            },
            expected_redirect=f"/programs/{pid}/",
        )
        self.record_scenario(
            self.SCENARIO, role, "Edit program saved",
            f"/programs/{pid}/edit/", resp.status_code, [],
        )

        # Assign a staff member to the program (HTMX partial response)
        url = f"/programs/{pid}/roles/add/"
        resp = self.client.post(
            url,
            data={"user": self.staff_user.pk, "role": "staff"},
            HTTP_HX_REQUEST="true",
        )
        issues = []
        if resp.status_code == 200:
            from .checker import UxChecker
            checker = UxChecker(resp, url, role, "Assign staff to program", is_partial=True)
            issues = checker.run_all_checks()
        self.report.record_step(role, "Assign staff to program", url, resp.status_code, issues)
        self.record_scenario(
            self.SCENARIO, role, "Assign staff to program",
            url, resp.status_code, [],
        )

    def test_form_validation(self):
        """Submit program form with missing name — verify error."""
        self.login_as("admin")
        role = "Admin"

        response = self.client.post("/programs/create/", {
            "name": "",
            "description": "",
            "colour_hex": "#000000",
            "service_model": "individual",
            "status": "active",
        })

        from .checker import UxChecker
        checker = UxChecker(
            response, "/programs/create/", role,
            "Form validation — empty program name",
        )
        checker.check_form_errors()
        checker.run_all_checks()
        self.report.record_step(
            role, "Program form validation",
            "/programs/create/", response.status_code, checker.issues,
        )


# =====================================================================
# 5. Metric Library CRUD
# =====================================================================


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AdminMetricWorkflow(UxScenarioBase):
    """Scenario: Admin creates a custom metric, toggles it, edits it."""

    SCENARIO = "Metric Library"

    def test_metric_crud(self):
        self.login_as("admin")
        role = "Admin"

        # View metric library
        resp = self.visit(role, "Metric library", "/plans/admin/metrics/")
        self.record_scenario(
            self.SCENARIO, role, "View metric library",
            "/plans/admin/metrics/", resp.status_code, [],
        )

        # Create metric form
        resp = self.visit(
            role, "Create metric form", "/plans/admin/metrics/create/",
        )
        self.record_scenario(
            self.SCENARIO, role, "Open create metric form",
            "/plans/admin/metrics/create/", resp.status_code, [],
        )

        # Submit create metric
        resp = self.visit_and_follow(
            role, "Submit new metric",
            "/plans/admin/metrics/create/",
            data={
                "name": "Housing Stability Index",
                "definition": "1-5 scale measuring housing stability.",
                "category": "housing",
                "min_value": "1",
                "max_value": "5",
                "unit": "score",
            },
            expected_redirect="/plans/admin/metrics/",
        )
        self.record_scenario(
            self.SCENARIO, role, "Create metric",
            "/plans/admin/metrics/create/", resp.status_code, [],
        )

        # Find the new metric
        from apps.plans.models import MetricDefinition
        metric = MetricDefinition.objects.filter(
            name="Housing Stability Index"
        ).first()
        self.assertIsNotNone(metric, "Metric creation failed")
        mid = metric.pk

        # Edit metric
        resp = self.visit(
            role, "Edit metric form", f"/plans/admin/metrics/{mid}/edit/",
        )
        self.record_scenario(
            self.SCENARIO, role, "Open edit metric form",
            f"/plans/admin/metrics/{mid}/edit/", resp.status_code, [],
        )

        resp = self.visit_and_follow(
            role, "Update metric",
            f"/plans/admin/metrics/{mid}/edit/",
            data={
                "name": "Housing Stability Index v2",
                "definition": "Updated scale.",
                "category": "housing",
                "min_value": "1",
                "max_value": "10",
                "unit": "score",
            },
            expected_redirect="/plans/admin/metrics/",
        )
        self.record_scenario(
            self.SCENARIO, role, "Edit metric saved",
            f"/plans/admin/metrics/{mid}/edit/", resp.status_code, [],
        )

        # Toggle metric (HTMX)
        resp = self.visit_htmx(
            role, "Toggle metric off",
            f"/plans/admin/metrics/{mid}/toggle/",
        )
        self.record_scenario(
            self.SCENARIO, role, "Toggle metric",
            f"/plans/admin/metrics/{mid}/toggle/", resp.status_code, [],
        )


# =====================================================================
# 6. Plan Templates CRUD
# =====================================================================


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AdminPlanTemplateWorkflow(UxScenarioBase):
    """Scenario: Admin creates a plan template with sections and targets."""

    SCENARIO = "Plan Templates"

    def test_plan_template_crud(self):
        self.login_as("admin")
        role = "Admin"

        # View template list
        resp = self.visit(role, "Plan template list", "/admin/templates/")
        self.record_scenario(
            self.SCENARIO, role, "View plan template list",
            "/admin/templates/", resp.status_code, [],
        )

        # Create template form
        resp = self.visit(
            role, "Create template form", "/admin/templates/create/",
        )
        self.record_scenario(
            self.SCENARIO, role, "Open create template form",
            "/admin/templates/create/", resp.status_code, [],
        )

        # Submit create template
        resp = self.visit_and_follow(
            role, "Submit new template",
            "/admin/templates/create/",
            data={
                "name": "Standard Intake Plan",
                "description": "Default plan template for new intakes.",
                "status": "active",
            },
            expected_redirect="/admin/templates/",
        )
        self.record_scenario(
            self.SCENARIO, role, "Create template",
            "/admin/templates/create/", resp.status_code, [],
        )

        # Find the new template
        from apps.plans.models import PlanTemplate
        template = PlanTemplate.objects.filter(
            name="Standard Intake Plan"
        ).first()
        self.assertIsNotNone(template, "Template creation failed")
        tid = template.pk

        # View template detail
        resp = self.visit(
            role, "Template detail", f"/admin/templates/{tid}/",
            role_should_see=["Add Section"],
        )
        self.record_scenario(
            self.SCENARIO, role, "View template detail",
            f"/admin/templates/{tid}/", resp.status_code, [],
        )

        # Add a section
        resp = self.visit(
            role, "Add section form",
            f"/admin/templates/{tid}/sections/create/",
        )
        self.record_scenario(
            self.SCENARIO, role, "Open add section form",
            f"/admin/templates/{tid}/sections/create/", resp.status_code, [],
        )

        resp = self.visit_and_follow(
            role, "Submit new section",
            f"/admin/templates/{tid}/sections/create/",
            data={
                "name": "Housing Goals",
                "program": self.program_a.pk,
                "sort_order": "1",
            },
            expected_redirect=f"/admin/templates/{tid}/",
        )
        self.record_scenario(
            self.SCENARIO, role, "Create section",
            f"/admin/templates/{tid}/sections/create/", resp.status_code, [],
        )

        # Find the section
        from apps.plans.models import PlanTemplateSection
        section = PlanTemplateSection.objects.filter(
            plan_template=template, name="Housing Goals"
        ).first()
        self.assertIsNotNone(section, "Section creation failed")
        sid = section.pk

        # Add a target to the section
        resp = self.visit(
            role, "Add target form",
            f"/admin/templates/sections/{sid}/targets/create/",
        )
        self.record_scenario(
            self.SCENARIO, role, "Open add target form",
            f"/admin/templates/sections/{sid}/targets/create/",
            resp.status_code, [],
        )

        resp = self.visit_and_follow(
            role, "Submit new target",
            f"/admin/templates/sections/{sid}/targets/create/",
            data={
                "name": "Find stable housing within 6 months",
                "description": "Measured by Housing Stability Index.",
                "sort_order": "1",
            },
            expected_redirect=f"/admin/templates/{tid}/",
        )
        self.record_scenario(
            self.SCENARIO, role, "Create target",
            f"/admin/templates/sections/{sid}/targets/create/",
            resp.status_code, [],
        )

        # Edit the template
        resp = self.visit(
            role, "Edit template form", f"/admin/templates/{tid}/edit/",
        )
        self.record_scenario(
            self.SCENARIO, role, "Open edit template form",
            f"/admin/templates/{tid}/edit/", resp.status_code, [],
        )

        resp = self.visit_and_follow(
            role, "Update template",
            f"/admin/templates/{tid}/edit/",
            data={
                "name": "Standard Intake Plan v2",
                "description": "Updated template.",
                "status": "active",
            },
            expected_redirect=f"/admin/templates/{tid}/",
        )
        self.record_scenario(
            self.SCENARIO, role, "Edit template saved",
            f"/admin/templates/{tid}/edit/", resp.status_code, [],
        )


# =====================================================================
# 7. Note Templates CRUD
# =====================================================================


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AdminNoteTemplateWorkflow(UxScenarioBase):
    """Scenario: Admin creates a note template with sections."""

    SCENARIO = "Note Templates"

    def test_note_template_crud(self):
        self.login_as("admin")
        role = "Admin"

        # View template list
        resp = self.visit(
            role, "Note template list",
            "/admin/settings/note-templates/",
        )
        self.record_scenario(
            self.SCENARIO, role, "View note template list",
            "/admin/settings/note-templates/", resp.status_code, [],
        )

        # Create template form
        resp = self.visit(
            role, "Create note template form",
            "/admin/settings/note-templates/create/",
        )
        self.record_scenario(
            self.SCENARIO, role, "Open create note template form",
            "/admin/settings/note-templates/create/", resp.status_code, [],
        )

        # Submit create note template with one section (formset)
        # Prefix is "sections" from related_name on the FK
        resp = self.visit_and_follow(
            role, "Submit new note template",
            "/admin/settings/note-templates/create/",
            data={
                "name": "Standard Session Note",
                "default_interaction_type": "session",
                "status": "active",
                # Formset management data
                "sections-TOTAL_FORMS": "1",
                "sections-INITIAL_FORMS": "0",
                "sections-MIN_NUM_FORMS": "0",
                "sections-MAX_NUM_FORMS": "1000",
                # Section 0
                "sections-0-name": "Session Summary",
                "sections-0-section_type": "basic",
                "sections-0-sort_order": "1",
            },
            expected_redirect="/admin/settings/note-templates/",
        )
        self.record_scenario(
            self.SCENARIO, role, "Create note template with section",
            "/admin/settings/note-templates/create/",
            resp.status_code, [],
        )

        # Find the template
        from apps.notes.models import ProgressNoteTemplate
        template = ProgressNoteTemplate.objects.filter(
            name="Standard Session Note"
        ).first()
        self.assertIsNotNone(template, "Note template creation failed")

        # Edit the template
        resp = self.visit(
            role, "Edit note template form",
            f"/admin/settings/note-templates/{template.pk}/edit/",
        )
        self.record_scenario(
            self.SCENARIO, role, "Open edit note template form",
            f"/admin/settings/note-templates/{template.pk}/edit/",
            resp.status_code, [],
        )


# =====================================================================
# 8. Event Types CRUD
# =====================================================================


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AdminEventTypeWorkflow(UxScenarioBase):
    """Scenario: Admin creates event types for tracking."""

    SCENARIO = "Event Types"

    def test_event_type_crud(self):
        self.login_as("admin")
        role = "Admin"

        # View event types
        resp = self.visit(
            role, "Event types list", "/events/admin/types/",
        )
        self.record_scenario(
            self.SCENARIO, role, "View event types list",
            "/events/admin/types/", resp.status_code, [],
        )

        # Create event type form
        resp = self.visit(
            role, "Create event type form", "/events/admin/types/create/",
        )
        self.record_scenario(
            self.SCENARIO, role, "Open create event type form",
            "/events/admin/types/create/", resp.status_code, [],
        )

        # Submit create event type
        resp = self.visit_and_follow(
            role, "Submit new event type",
            "/events/admin/types/create/",
            data={
                "name": "Court Date",
                "description": "Upcoming court appearances.",
                "colour_hex": "#EF4444",
                "status": "active",
            },
            expected_redirect="/events/admin/types/",
        )
        self.record_scenario(
            self.SCENARIO, role, "Create event type",
            "/events/admin/types/create/", resp.status_code, [],
        )

        # Find the event type
        from apps.events.models import EventType
        et = EventType.objects.filter(name="Court Date").first()
        self.assertIsNotNone(et, "Event type creation failed")

        # Edit event type
        resp = self.visit(
            role, "Edit event type form",
            f"/events/admin/types/{et.pk}/edit/",
        )
        self.record_scenario(
            self.SCENARIO, role, "Open edit event type form",
            f"/events/admin/types/{et.pk}/edit/", resp.status_code, [],
        )

        resp = self.visit_and_follow(
            role, "Update event type",
            f"/events/admin/types/{et.pk}/edit/",
            data={
                "name": "Court Hearing",
                "description": "Updated description.",
                "colour_hex": "#DC2626",
                "status": "active",
            },
            expected_redirect="/events/admin/types/",
        )
        self.record_scenario(
            self.SCENARIO, role, "Edit event type saved",
            f"/events/admin/types/{et.pk}/edit/", resp.status_code, [],
        )

        # Create a second event type to verify list shows multiple
        self.client.post("/events/admin/types/create/", {
            "name": "Hospital Visit",
            "description": "Emergency room or hospital visit.",
            "colour_hex": "#F59E0B",
            "status": "active",
        })
        resp = self.visit(
            role, "Event types list (multiple)", "/events/admin/types/",
            role_should_see=["Court Hearing", "Hospital Visit"],
        )
        self.record_scenario(
            self.SCENARIO, role, "List shows multiple event types",
            "/events/admin/types/", resp.status_code, [],
        )


# =====================================================================
# 9. Custom Client Fields CRUD
# =====================================================================


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AdminCustomFieldWorkflow(UxScenarioBase):
    """Scenario: Admin creates field groups and field definitions."""

    SCENARIO = "Custom Client Fields"

    def test_custom_field_crud(self):
        self.login_as("admin")
        role = "Admin"

        # View custom field admin
        resp = self.visit(
            role, "Custom field admin", "/clients/admin/fields/",
        )
        self.record_scenario(
            self.SCENARIO, role, "View custom field admin",
            "/clients/admin/fields/", resp.status_code, [],
        )

        # Create field group
        resp = self.visit(
            role, "Create field group form",
            "/clients/admin/fields/groups/create/",
        )
        self.record_scenario(
            self.SCENARIO, role, "Open create field group form",
            "/clients/admin/fields/groups/create/", resp.status_code, [],
        )

        resp = self.visit_and_follow(
            role, "Submit new field group",
            "/clients/admin/fields/groups/create/",
            data={
                "title": "Intake Information",
                "sort_order": "1",
                "status": "active",
            },
            expected_redirect="/clients/admin/fields/",
        )
        self.record_scenario(
            self.SCENARIO, role, "Create field group",
            "/clients/admin/fields/groups/create/", resp.status_code, [],
        )

        # Find the group
        from apps.clients.models import CustomFieldGroup
        group = CustomFieldGroup.objects.filter(title="Intake Information").first()
        self.assertIsNotNone(group, "Field group creation failed")

        # Create a dropdown field definition
        resp = self.visit(
            role, "Create field definition form",
            "/clients/admin/fields/create/",
        )
        self.record_scenario(
            self.SCENARIO, role, "Open create field definition form",
            "/clients/admin/fields/create/", resp.status_code, [],
        )

        resp = self.visit_and_follow(
            role, "Submit dropdown field",
            "/clients/admin/fields/create/",
            data={
                "group": group.pk,
                "name": "Referral Source",
                "input_type": "select",
                "placeholder": "",
                "is_required": "",
                "is_sensitive": "",
                "front_desk_access": "view",
                "options_json": '["Self-referral", "Agency", "Hospital", "Other"]',
                "sort_order": "1",
                "status": "active",
            },
            expected_redirect="/clients/admin/fields/",
        )
        self.record_scenario(
            self.SCENARIO, role, "Create dropdown field",
            "/clients/admin/fields/create/", resp.status_code, [],
        )

        # Create a text field
        resp = self.visit_and_follow(
            role, "Submit text field",
            "/clients/admin/fields/create/",
            data={
                "group": group.pk,
                "name": "Housing Status",
                "input_type": "text",
                "placeholder": "e.g., Housed, Sheltered, Unsheltered",
                "is_required": "",
                "is_sensitive": "on",
                "front_desk_access": "none",
                "options_json": "[]",
                "sort_order": "2",
                "status": "active",
            },
            expected_redirect="/clients/admin/fields/",
        )
        self.record_scenario(
            self.SCENARIO, role, "Create sensitive text field",
            "/clients/admin/fields/create/", resp.status_code, [],
        )

        # Verify the admin page shows both fields
        resp = self.visit(
            role, "Custom field admin (populated)", "/clients/admin/fields/",
            role_should_see=["Referral Source", "Housing Status"],
        )
        self.record_scenario(
            self.SCENARIO, role, "Fields visible in admin",
            "/clients/admin/fields/", resp.status_code, [],
        )

        # Edit a field
        from apps.clients.models import CustomFieldDefinition
        field_def = CustomFieldDefinition.objects.filter(
            name="Referral Source"
        ).first()
        self.assertIsNotNone(field_def, "Field definition not found")

        resp = self.visit(
            role, "Edit field definition form",
            f"/clients/admin/fields/{field_def.pk}/edit/",
        )
        self.record_scenario(
            self.SCENARIO, role, "Open edit field definition form",
            f"/clients/admin/fields/{field_def.pk}/edit/",
            resp.status_code, [],
        )


# =====================================================================
# 10. User Management CRUD
# =====================================================================


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AdminUserWorkflow(UxScenarioBase):
    """Scenario: Admin creates a user, edits them, views the list."""

    SCENARIO = "User Management"

    def test_user_crud(self):
        self.login_as("admin")
        role = "Admin"

        # View user list
        resp = self.visit(role, "User list", "/admin/users/")
        self.record_scenario(
            self.SCENARIO, role, "View user list",
            "/admin/users/", resp.status_code, [],
        )

        # Create user form
        resp = self.visit(
            role, "Create user form", "/admin/users/new/",
        )
        self.record_scenario(
            self.SCENARIO, role, "Open create user form",
            "/admin/users/new/", resp.status_code, [],
        )

        # Submit create user
        resp = self.visit_and_follow(
            role, "Submit new user",
            "/admin/users/new/",
            data={
                "username": "newstaff",
                "display_name": "Sarah New Staff",
                "is_admin": "",
                "password": "SecurePass123!",
                "password_confirm": "SecurePass123!",
                "email": "sarah@hopehouse.ca",
            },
            expected_redirect="/admin/users/",
        )
        self.record_scenario(
            self.SCENARIO, role, "Create user",
            "/admin/users/new/", resp.status_code, [],
        )

        # Find the new user
        from apps.auth_app.models import User
        new_user = User.objects.filter(username="newstaff").first()
        self.assertIsNotNone(new_user, "User creation failed")

        # Edit user
        resp = self.visit(
            role, "Edit user form", f"/admin/users/{new_user.pk}/edit/",
        )
        self.record_scenario(
            self.SCENARIO, role, "Open edit user form",
            f"/admin/users/{new_user.pk}/edit/", resp.status_code, [],
        )

        resp = self.visit_and_follow(
            role, "Update user",
            f"/admin/users/{new_user.pk}/edit/",
            data={
                "display_name": "Sarah Staff Updated",
                "is_admin": "",
                "is_active": "on",
                "email": "sarah.updated@hopehouse.ca",
                "new_password": "",
            },
            expected_redirect="/admin/users/",
        )
        self.record_scenario(
            self.SCENARIO, role, "Edit user saved",
            f"/admin/users/{new_user.pk}/edit/", resp.status_code, [],
        )

    def test_password_mismatch_validation(self):
        """Submit user form with mismatched passwords — verify error."""
        self.login_as("admin")
        role = "Admin"

        response = self.client.post("/admin/users/new/", {
            "username": "baduser",
            "display_name": "Bad User",
            "is_admin": "",
            "password": "Password123!",
            "password_confirm": "DifferentPassword!",
            "email": "",
        })

        from .checker import UxChecker
        checker = UxChecker(
            response, "/admin/users/new/", role,
            "Form validation — password mismatch",
        )
        checker.check_form_errors()
        checker.run_all_checks()
        self.report.record_step(
            role, "User form password mismatch",
            "/admin/users/new/", response.status_code, checker.issues,
        )


# =====================================================================
# 11. Invite System
# =====================================================================


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AdminInviteWorkflow(UxScenarioBase):
    """Scenario: Admin creates an invite link."""

    SCENARIO = "Invite System"

    def test_invite_crud(self):
        self.login_as("admin")
        role = "Admin"

        # View invite list
        resp = self.visit(role, "Invite list", "/auth/invites/")
        self.record_scenario(
            self.SCENARIO, role, "View invite list",
            "/auth/invites/", resp.status_code, [],
        )

        # Create invite form
        resp = self.visit(
            role, "Create invite form", "/auth/invites/new/",
        )
        self.record_scenario(
            self.SCENARIO, role, "Open create invite form",
            "/auth/invites/new/", resp.status_code, [],
        )

        # Submit create invite
        resp = self.visit_and_follow(
            role, "Submit new invite",
            "/auth/invites/new/",
            data={
                "role": "staff",
                "programs": [self.program_a.pk],
                "expires_days": "7",
            },
            expected_redirect="/auth/invites/",
        )
        self.record_scenario(
            self.SCENARIO, role, "Create invite link",
            "/auth/invites/new/", resp.status_code, [],
        )


# =====================================================================
# 12. Registration Links & Submissions
# =====================================================================


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AdminRegistrationWorkflow(UxScenarioBase):
    """Scenario: Admin creates a registration link, views submissions."""

    SCENARIO = "Registration Links"

    def test_registration_crud(self):
        self.login_as("admin")
        role = "Admin"

        # View registration links
        resp = self.visit(
            role, "Registration links list", "/admin/registration/",
        )
        self.record_scenario(
            self.SCENARIO, role, "View registration links",
            "/admin/registration/", resp.status_code, [],
        )

        # Create registration link form
        resp = self.visit(
            role, "Create registration link form",
            "/admin/registration/create/",
        )
        self.record_scenario(
            self.SCENARIO, role, "Open create registration link form",
            "/admin/registration/create/", resp.status_code, [],
        )

        # Submit create registration link
        resp = self.visit_and_follow(
            role, "Submit new registration link",
            "/admin/registration/create/",
            data={
                "program": self.program_a.pk,
                "title": "Housing Support Registration",
                "description": "Public registration for housing program.",
                "auto_approve": "",
                "max_registrations": "",
                "closes_at": "",
                "is_active": "on",
            },
            expected_redirect="/admin/registration/",
        )
        self.record_scenario(
            self.SCENARIO, role, "Create registration link",
            "/admin/registration/create/", resp.status_code, [],
        )

        # View submissions page
        resp = self.visit(
            role, "Pending submissions", "/admin/submissions/",
        )
        self.record_scenario(
            self.SCENARIO, role, "View pending submissions",
            "/admin/submissions/", resp.status_code, [],
        )


# =====================================================================
# 13. Audit Logs
# =====================================================================


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AdminAuditLogWorkflow(UxScenarioBase):
    """Scenario: Admin reviews audit logs."""

    SCENARIO = "Audit Logs"

    def test_audit_log_review(self):
        self.login_as("admin")
        role = "Admin"

        # View audit log
        resp = self.visit(role, "Audit log list", "/admin/audit/")
        self.record_scenario(
            self.SCENARIO, role, "View audit log",
            "/admin/audit/", resp.status_code, [],
        )

        # Filter audit log by date
        resp = self.visit(
            role, "Audit log filtered",
            "/admin/audit/?date_from=2020-01-01&date_to=2030-12-31",
        )
        self.record_scenario(
            self.SCENARIO, role, "Filter audit log by date",
            "/admin/audit/?date_from=2020-01-01&date_to=2030-12-31",
            resp.status_code, [],
        )

        # Diagnose charts
        resp = self.visit(
            role, "Diagnose charts", "/admin/settings/diagnose-charts/",
        )
        self.record_scenario(
            self.SCENARIO, role, "Diagnose charts tool",
            "/admin/settings/diagnose-charts/", resp.status_code, [],
        )


# =====================================================================
# 14. Full Admin Setup Flow — end-to-end scenario
# =====================================================================


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AdminFullSetupScenario(UxScenarioBase):
    """End-to-end scenario: A new admin sets up a fresh agency.

    This ties the individual workflows together into a single story.
    """

    SCENARIO = "Full Agency Setup"

    def test_full_setup_flow(self):
        self.login_as("admin")
        role = "Admin"

        # Step 1: Dashboard
        resp = self.visit(role, "Start at dashboard", "/admin/settings/")
        self.record_scenario(
            self.SCENARIO, role, "1. Start at admin dashboard",
            "/admin/settings/", resp.status_code, [],
        )

        # Step 2: Enable features
        resp = self.visit_and_follow(
            role, "Enable events feature",
            "/admin/settings/features/",
            data={"feature_key": "events", "action": "enable"},
            expected_redirect="/admin/settings/features/",
        )
        self.record_scenario(
            self.SCENARIO, role, "2. Enable events feature",
            "/admin/settings/features/", resp.status_code, [],
        )

        # Step 3: Create a program
        resp = self.visit_and_follow(
            role, "Create first program",
            "/programs/create/",
            data={
                "name": "Settlement Services",
                "description": "Newcomer settlement program.",
                "colour_hex": "#10B981",
                "service_model": "individual",
                "status": "active",
            },
            expected_redirect="/programs/",
        )
        self.record_scenario(
            self.SCENARIO, role, "3. Create program",
            "/programs/create/", resp.status_code, [],
        )

        # Step 4: Create a metric
        resp = self.visit_and_follow(
            role, "Create first metric",
            "/plans/admin/metrics/create/",
            data={
                "name": "Language Proficiency",
                "definition": "CLB level 1-12.",
                "category": "settlement",
                "min_value": "1",
                "max_value": "12",
                "unit": "CLB level",
            },
            expected_redirect="/plans/admin/metrics/",
        )
        self.record_scenario(
            self.SCENARIO, role, "4. Create metric",
            "/plans/admin/metrics/create/", resp.status_code, [],
        )

        # Step 5: Create an event type
        resp = self.visit_and_follow(
            role, "Create first event type",
            "/events/admin/types/create/",
            data={
                "name": "Orientation Session",
                "description": "Initial program orientation.",
                "colour_hex": "#3B82F6",
                "status": "active",
            },
            expected_redirect="/events/admin/types/",
        )
        self.record_scenario(
            self.SCENARIO, role, "5. Create event type",
            "/events/admin/types/create/", resp.status_code, [],
        )

        # Step 6: Create a user
        resp = self.visit_and_follow(
            role, "Create first staff user",
            "/admin/users/new/",
            data={
                "username": "settlementworker",
                "display_name": "Amir Settlement Worker",
                "is_admin": "",
                "password": "WorkerPass123!",
                "password_confirm": "WorkerPass123!",
                "email": "",
            },
            expected_redirect="/admin/users/",
        )
        self.record_scenario(
            self.SCENARIO, role, "6. Create staff user",
            "/admin/users/new/", resp.status_code, [],
        )

        # Step 7: Assign user to program
        from apps.programs.models import Program
        program = Program.objects.filter(name="Settlement Services").first()
        self.assertIsNotNone(program, "Program not found")
        from apps.auth_app.models import User
        worker = User.objects.filter(username="settlementworker").first()
        self.assertIsNotNone(worker, "User not found")

        resp = self.client.post(
            f"/programs/{program.pk}/roles/add/",
            data={"user": worker.pk, "role": "staff"},
            HTTP_HX_REQUEST="true",
        )
        url = f"/programs/{program.pk}/roles/add/"
        issues = []
        if resp.status_code == 200:
            from .checker import UxChecker
            checker = UxChecker(resp, url, role, "Assign worker to program", is_partial=True)
            issues = checker.run_all_checks()
        self.report.record_step(role, "Assign worker to program", url, resp.status_code, issues)
        self.record_scenario(
            self.SCENARIO, role, "7. Assign staff to program",
            url, resp.status_code, [],
        )

        # Step 8: Verify the program detail shows the user
        resp = self.visit(
            role, "Program with staff", f"/programs/{program.pk}/",
            role_should_see=["Amir"],
        )
        self.record_scenario(
            self.SCENARIO, role, "8. Verify staff visible on program",
            f"/programs/{program.pk}/", resp.status_code, [],
        )


# =====================================================================
# 15. French Admin Workflows
# =====================================================================


@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY)
class AdminFrenchWorkflow(UxScenarioBase):
    """Scenario: Admin navigates key admin pages in French."""

    SCENARIO = "Admin in French"

    def test_french_admin_pages(self):
        self.login_as("admin")
        self.switch_language("fr")
        role = "Admin (FR)"

        pages = [
            ("Admin dashboard", "/admin/settings/"),
            ("Features", "/admin/settings/features/"),
            ("Instance settings", "/admin/settings/instance/"),
            ("Terminology", "/admin/settings/terminology/"),
            ("User list", "/admin/users/"),
            ("Metric library", "/plans/admin/metrics/"),
            ("Programs list", "/programs/"),
            ("Event types", "/events/admin/types/"),
            ("Note templates", "/admin/settings/note-templates/"),
            ("Custom fields", "/clients/admin/fields/"),
            ("Registration links", "/admin/registration/"),
            ("Audit log", "/admin/audit/"),
        ]

        for step_name, url in pages:
            resp = self.visit(
                role, step_name, url,
                expected_lang="fr",
            )
            self.record_scenario(
                self.SCENARIO, role, step_name,
                url, resp.status_code, [],
            )

        self.switch_language("en")
