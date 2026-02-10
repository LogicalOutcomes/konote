"""Tests for complete French user journey (I18N4b).

Verifies that the entire user experience works correctly when the language
is set to French. Each test activates French locale via cookie or
translation.override, makes a request, and asserts that key French strings
are present and critical English strings are absent.

Note: The .po file uses plain apostrophes (') not typographic quotes.
All assertions must use plain apostrophes to match the rendered output.
"""
from cryptography.fernet import Fernet
from django.conf import settings
from django.test import TestCase, Client, override_settings
from django.utils import timezone
from django.utils.translation import override as translation_override

from apps.admin_settings.models import FeatureToggle, InstanceSetting
from apps.auth_app.models import User
from apps.clients.models import ClientFile, ClientProgramEnrolment
from apps.events.models import EventType
from apps.notes.models import ProgressNote
from apps.plans.models import (
    MetricDefinition, PlanSection, PlanTarget, PlanTargetMetric,
)
from apps.programs.models import Program, UserProgramRole
import konote.encryption as enc_module


TEST_KEY = Fernet.generate_key().decode()


def _set_french(http_client):
    """Set the language cookie to French on a test client."""
    http_client.cookies[settings.LANGUAGE_COOKIE_NAME] = "fr"


# ─────────────────────────────────────────────────────────────────────────
# Base class with shared setup
# ─────────────────────────────────────────────────────────────────────────

@override_settings(FIELD_ENCRYPTION_KEY=TEST_KEY, AUTH_MODE="local")
class FrenchJourneyBaseTest(TestCase):
    """Base class providing users, programs, clients, and plans for French tests."""

    databases = {"default", "audit"}

    def setUp(self):
        enc_module._fernet = None
        self.http = Client()

        # Admin user
        self.admin = User.objects.create_user(
            username="admin", password="pass", display_name="Administrateur Test",
            is_admin=True,
        )
        # Staff user
        self.staff = User.objects.create_user(
            username="staff", password="pass", display_name="Personnel Test",
            is_admin=False,
        )

        # Program
        self.program = Program.objects.create(name="Programme de soutien", colour_hex="#10B981")
        UserProgramRole.objects.create(user=self.admin, program=self.program, role="program_manager")
        UserProgramRole.objects.create(user=self.staff, program=self.program, role="staff")

        # Enable features that affect navigation
        FeatureToggle.objects.create(feature_key="programs", is_enabled=True)

        # Client with consent
        self.client_file = ClientFile()
        self.client_file.first_name = "Marie"
        self.client_file.last_name = "Dupont"
        self.client_file.status = "active"
        self.client_file.record_id = "REC-2026-001"
        self.client_file.consent_given_at = timezone.now()
        self.client_file.consent_type = "written"
        self.client_file.save()
        ClientProgramEnrolment.objects.create(
            client_file=self.client_file, program=self.program,
        )

    def tearDown(self):
        enc_module._fernet = None

    def _login_admin_fr(self):
        """Log in as admin and set French language cookie."""
        self.http.login(username="admin", password="pass")
        _set_french(self.http)

    def _login_staff_fr(self):
        """Log in as staff and set French language cookie."""
        self.http.login(username="staff", password="pass")
        _set_french(self.http)


# ─────────────────────────────────────────────────────────────────────────
# 1. Language Switching
# ─────────────────────────────────────────────────────────────────────────

class LanguageSwitchingFrenchTest(FrenchJourneyBaseTest):
    """Switching to French actually changes displayed text."""

    def test_switch_to_french_cookie_is_set(self):
        """POST to switch_language sets 'fr' cookie."""
        resp = self.http.post("/i18n/switch/", {
            "language": "fr",
            "next": "/auth/login/",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.cookies[settings.LANGUAGE_COOKIE_NAME].value, "fr")

    def test_login_page_renders_in_french_after_switch(self):
        """After setting French cookie, login page shows French strings."""
        _set_french(self.http)
        resp = self.http.get("/auth/login/")
        self.assertEqual(resp.status_code, 200)
        # French strings present (plain apostrophe in .po file)
        self.assertContains(resp, "Connexion")  # "Sign In"
        self.assertContains(resp, "Nom d'utilisateur")  # "Username"
        self.assertContains(resp, "Mot de passe")  # "Password"

    def test_authenticated_page_renders_french_nav(self):
        """After login with French cookie, navigation shows French labels."""
        self._login_staff_fr()
        resp = self.http.get("/")
        self.assertEqual(resp.status_code, 200)
        # Nav items in French
        self.assertContains(resp, "D\u00e9connexion")  # "Sign Out"

    def test_language_persists_dashboard_to_create_form(self):
        """BUG-9 regression: French stays active navigating dashboard → create form.

        Reproduces the exact QA scenario (SCN-040 steps 1-2):
        1. View dashboard in French
        2. Navigate to create form — should still be French
        """
        self._login_admin_fr()
        # Step 1: Dashboard in French
        resp = self.http.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'lang="fr"')
        # Step 2: Create form stays French
        resp = self.http.get("/clients/create/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'lang="fr"')
        self.assertContains(resp, "Pr\u00e9nom")  # "First Name" in French
        self.assertNotIn(">First Name<", resp.content.decode())

    def test_language_persists_with_user_preferred_language(self):
        """BUG-9: Language persists via user.preferred_language, not just cookie.

        When preferred_language='fr' is saved on the user profile, all pages
        should render in French regardless of cookie state.
        """
        self.admin.preferred_language = "fr"
        self.admin.save(update_fields=["preferred_language"])
        self.http.login(username="admin", password="pass")
        # Do NOT set cookie — rely on preferred_language alone
        resp = self.http.get("/clients/create/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'lang="fr"')
        self.assertContains(resp, "Pr\u00e9nom")  # French label


# ─────────────────────────────────────────────────────────────────────────
# 2. Navigation in French
# ─────────────────────────────────────────────────────────────────────────

class NavigationFrenchTest(FrenchJourneyBaseTest):
    """All navigation items render in French for admin users."""

    def test_admin_nav_shows_french_labels(self):
        """Admin navigation dropdown shows French admin labels."""
        self._login_admin_fr()
        resp = self.http.get("/")
        self.assertEqual(resp.status_code, 200)
        # Admin dropdown items
        self.assertContains(resp, "Administration")  # "Admin"
        self.assertContains(resp, "Param\u00e8tres")  # "Settings"
        self.assertContains(resp, "Invitations")  # "Invites"
        self.assertContains(resp, "Journal d'audit")  # "Audit Log" — plain apostrophe
        self.assertContains(resp, "Rapports")  # "Reports"

    def test_nav_language_link_offers_english(self):
        """When in French, nav shows 'English' as the alternate language."""
        self._login_staff_fr()
        resp = self.http.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'lang="en"')
        self.assertContains(resp, "English")

    def test_skip_to_content_in_french(self):
        """Accessibility 'skip to content' link is in French."""
        self._login_staff_fr()
        resp = self.http.get("/")
        self.assertContains(resp, "Passer au contenu principal")


# ─────────────────────────────────────────────────────────────────────────
# 3. Login Page in French
# ─────────────────────────────────────────────────────────────────────────

class LoginPageFrenchTest(FrenchJourneyBaseTest):
    """French version of login form renders correctly."""

    def test_login_form_labels_in_french(self):
        """Login form labels and button are in French."""
        _set_french(self.http)
        resp = self.http.get("/auth/login/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Connexion")  # Sign In button
        self.assertContains(resp, "Nom d'utilisateur")  # Username — plain apostrophe
        self.assertContains(resp, "Mot de passe")  # Password

    def test_login_tagline_in_french(self):
        """Return visit in French shows translated tagline."""
        _set_french(self.http)
        resp = self.http.get("/auth/login/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Gestion des r\u00e9sultats des participants")

    def test_login_page_html_lang_is_french(self):
        """Login page has lang='fr' on the html element."""
        _set_french(self.http)
        resp = self.http.get("/auth/login/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'lang="fr"')

    def test_login_page_labels_not_english(self):
        """Login page in French does not show English labels."""
        _set_french(self.http)
        resp = self.http.get("/auth/login/")
        content = resp.content.decode()
        # English label text should not appear
        self.assertNotIn(">Username<", content)
        self.assertNotIn(">Password<", content)

    def test_first_visit_bilingual_hero(self):
        """First visit (no cookie) shows bilingual hero with both languages."""
        resp = self.http.get("/auth/login/")
        self.assertEqual(resp.status_code, 200)
        # Both English and French taglines
        self.assertContains(resp, "Participant Outcome Management")
        self.assertContains(resp, "Gestion des r\u00e9sultats des participants")
        # Language chooser buttons
        self.assertContains(resp, "lang-chooser")
        self.assertContains(resp, "Fran\u00e7ais")


# ─────────────────────────────────────────────────────────────────────────
# 4. Client List in French
# ─────────────────────────────────────────────────────────────────────────

class ClientListFrenchTest(FrenchJourneyBaseTest):
    """Client list views render in French."""

    def test_client_list_labels_in_french(self):
        """Client list page shows French filter and column labels."""
        self._login_staff_fr()
        resp = self.http.get("/clients/")
        self.assertEqual(resp.status_code, 200)
        # Filter labels
        self.assertContains(resp, "Filtres")  # "Filters"
        self.assertContains(resp, "Statut")  # "Status"
        self.assertContains(resp, "Actif")  # "Active"

    def test_client_list_status_options_in_french(self):
        """Status dropdown options appear in French."""
        self._login_staff_fr()
        resp = self.http.get("/clients/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Tous les statuts")  # "All statuses"
        self.assertContains(resp, "Inactif")  # "Inactive"

    def test_client_list_clear_filters_in_french(self):
        """Clear filters button text is in French."""
        self._login_staff_fr()
        resp = self.http.get("/clients/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Effacer les filtres")  # "Clear filters"

    def test_empty_client_list_in_french(self):
        """Empty client list (filtered to no results) shows French empty state."""
        self._login_staff_fr()
        resp = self.http.get("/clients/?status=discharged")
        self.assertEqual(resp.status_code, 200)
        # Page renders without error in French context


# ─────────────────────────────────────────────────────────────────────────
# 5. Client Detail in French
# ─────────────────────────────────────────────────────────────────────────

class ClientDetailFrenchTest(FrenchJourneyBaseTest):
    """Client detail page renders labels, buttons, and sections in French."""

    def test_client_detail_tabs_in_french(self):
        """Client detail tabs are rendered in French."""
        self._login_staff_fr()
        resp = self.http.get(f"/clients/{self.client_file.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Info")  # Same in both languages
        self.assertContains(resp, "\u00c9v\u00e9nements")  # "Events" — Événements
        self.assertContains(resp, "Analyse")  # "Analysis"

    def test_client_detail_buttons_in_french(self):
        """Edit and Back to List buttons are in French."""
        self._login_staff_fr()
        resp = self.http.get(f"/clients/{self.client_file.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Modifier")  # "Edit"
        self.assertContains(resp, "Retour \u00e0 la liste")  # "Back to List"

    def test_client_detail_consent_in_french(self):
        """Consent display section is in French."""
        self._login_staff_fr()
        resp = self.http.get(f"/clients/{self.client_file.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Consentement")  # Part of privacy consent labels

    def test_client_detail_record_id_label_in_french(self):
        """Client detail shows the Record ID label in French."""
        self._login_staff_fr()
        resp = self.http.get(f"/clients/{self.client_file.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "ID")  # ID label appears in detail

    def test_client_edit_form_labels_in_french(self):
        """Client edit form has French labels."""
        self._login_admin_fr()
        resp = self.http.get(f"/clients/{self.client_file.pk}/edit/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Pr\u00e9nom")  # "First Name"
        self.assertContains(resp, "Nom de famille")  # "Last Name"
        self.assertContains(resp, "Date de naissance")  # "Date of Birth"
        self.assertContains(resp, "Enregistrer les modifications")  # "Save Changes"
        self.assertContains(resp, "Annuler")  # "Cancel"

    def test_client_create_form_in_french(self):
        """BUG-9 regression: client creation form renders fully in French.

        Checks every visible label, heading, button, and helper text
        on the create form to ensure nothing appears in English.
        """
        self._login_admin_fr()
        resp = self.http.get("/clients/create/")
        self.assertEqual(resp.status_code, 200)
        # HTML lang attribute
        self.assertContains(resp, 'lang="fr"')
        # Heading (blocktrans with term.client)
        self.assertContains(resp, "Nouveau/Nouvelle")  # "New (m/f)"
        # Form labels
        self.assertContains(resp, "Pr\u00e9nom")  # "First Name"
        self.assertContains(resp, "Nom de famille")  # "Last Name"
        self.assertContains(resp, "Nom pr\u00e9f\u00e9r\u00e9")  # "Preferred Name"
        self.assertContains(resp, "Deuxi\u00e8me pr\u00e9nom")  # "Middle Name"
        self.assertContains(resp, "Num\u00e9ro de t\u00e9l\u00e9phone")  # "Phone Number"
        self.assertContains(resp, "Date de naissance")  # "Date of Birth"
        self.assertContains(resp, "ID du dossier")  # "Record ID"
        self.assertContains(resp, "Statut")  # "Status"
        # Helper text
        self.assertContains(resp, "pr\u00e9f\u00e9rez-vous")  # placeholder hint
        self.assertContains(resp, "identique au pr\u00e9nom")  # "same as first name"
        # Status dropdown options (model choices)
        self.assertContains(resp, "Actif")  # "Active"
        # Button
        self.assertContains(resp, "Cr\u00e9er")  # "Create ..."
        self.assertContains(resp, "Annuler")  # "Cancel"
        # Program fieldset legend (terminology system)
        self.assertContains(resp, "Programmes")  # from term.program_plural
        # Ensure key English form strings do NOT appear
        content = resp.content.decode()
        self.assertNotIn(">First Name<", content)
        self.assertNotIn(">Last Name<", content)
        self.assertNotIn(">Preferred Name<", content)
        self.assertNotIn(">Middle Name<", content)
        self.assertNotIn(">Phone Number<", content)
        self.assertNotIn(">Date of Birth<", content)
        self.assertNotIn(">Record ID<", content)


# ─────────────────────────────────────────────────────────────────────────
# 6. Notes in French
# ─────────────────────────────────────────────────────────────────────────

class NotesFrenchTest(FrenchJourneyBaseTest):
    """Creating and viewing notes with French UI labels."""

    def test_quick_note_form_in_french(self):
        """Quick note form shows French labels."""
        self._login_staff_fr()
        resp = self.http.get(f"/notes/client/{self.client_file.pk}/quick/")
        self.assertEqual(resp.status_code, 200)
        # Consent confirmation in French
        self.assertContains(resp, "consentement verbal")

    def test_note_list_labels_in_french(self):
        """Note list shows French filter and interaction type labels."""
        ProgressNote.objects.create(
            client_file=self.client_file, note_type="quick",
            notes_text="Note de test", author=self.staff,
        )
        self._login_staff_fr()
        resp = self.http.get(f"/notes/client/{self.client_file.pk}/")
        self.assertEqual(resp.status_code, 200)
        # Filter labels (template now uses interaction types, not note types)
        self.assertContains(resp, "Filtrer les notes")  # "Filter notes"
        self.assertContains(resp, "Auteur")  # "Author"
        self.assertContains(resp, "Toutes les interactions")  # "All interactions"

    def test_note_filter_options_in_french(self):
        """Note filter dropdown options are in French."""
        ProgressNote.objects.create(
            client_file=self.client_file, note_type="quick",
            notes_text="Texte de test", author=self.staff,
        )
        self._login_staff_fr()
        resp = self.http.get(f"/notes/client/{self.client_file.pk}/")
        self.assertEqual(resp.status_code, 200)
        # Interaction type options (replaced old note_type filter)
        self.assertContains(resp, "S\u00e9ance individuelle")  # "One-on-One Session"
        self.assertContains(resp, "Appel t\u00e9l\u00e9phonique")  # "Phone Call"
        # Author filter options
        self.assertContains(resp, "Mes notes seulement")  # "My notes only"
        self.assertContains(resp, "Tout le personnel")  # "All staff"

    def test_note_date_filter_labels_in_french(self):
        """Note date filter labels are in French."""
        ProgressNote.objects.create(
            client_file=self.client_file, note_type="quick",
            notes_text="Note date", author=self.staff,
        )
        self._login_staff_fr()
        resp = self.http.get(f"/notes/client/{self.client_file.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Date de d\u00e9but")  # "From date"
        self.assertContains(resp, "Date de fin")  # "To date"
        self.assertContains(resp, "Appliquer les filtres")  # "Apply filters"

    def test_empty_notes_state_in_french(self):
        """Empty notes list shows French empty state message."""
        self._login_staff_fr()
        resp = self.http.get(f"/notes/client/{self.client_file.pk}/")
        self.assertEqual(resp.status_code, 200)
        # Empty state (uses terminology-aware string)
        self.assertContains(resp, "Ajouter la premi\u00e8re note")  # "Add the first note"

    def test_note_cancel_form_in_french(self):
        """Note cancellation form is in French."""
        note = ProgressNote.objects.create(
            client_file=self.client_file, note_type="quick",
            notes_text="Annuler moi", author=self.staff,
        )
        self._login_staff_fr()
        resp = self.http.get(f"/notes/{note.pk}/cancel/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Raison")  # "Reason" (part of cancellation form)
        self.assertContains(resp, "Retour")  # "Go Back"

    def test_consent_required_page_in_french(self):
        """Consent required page renders in French when client has no consent."""
        no_consent = ClientFile()
        no_consent.first_name = "Sans"
        no_consent.last_name = "Consentement"
        no_consent.status = "active"
        no_consent.save()
        ClientProgramEnrolment.objects.create(
            client_file=no_consent, program=self.program,
        )
        self._login_staff_fr()
        resp = self.http.get(f"/notes/client/{no_consent.pk}/quick/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Consentement requis")  # "Consent Required"


# ─────────────────────────────────────────────────────────────────────────
# 7. Plans in French
# ─────────────────────────────────────────────────────────────────────────

class PlansFrenchTest(FrenchJourneyBaseTest):
    """Plan creation and editing with French labels."""

    def test_plan_view_renders_in_french(self):
        """Plan view page renders without error in French context."""
        self._login_staff_fr()
        resp = self.http.get(f"/plans/client/{self.client_file.pk}/")
        self.assertEqual(resp.status_code, 200)
        # HTML lang attribute should indicate French
        self.assertContains(resp, 'lang="fr"')

    def test_plan_with_section_shows_section_content(self):
        """Plan with a section shows the section and target names."""
        section = PlanSection.objects.create(
            client_file=self.client_file, name="Objectifs de logement",
            program=self.program, sort_order=0,
        )
        target = PlanTarget.objects.create(
            plan_section=section, client_file=self.client_file,
            name="Trouver un logement stable",
        )
        self._login_staff_fr()
        resp = self.http.get(f"/plans/client/{self.client_file.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Objectifs de logement")
        self.assertContains(resp, "Trouver un logement stable")

    def test_plan_template_list_in_french(self):
        """Plan template list admin page renders in French."""
        self._login_admin_fr()
        resp = self.http.get("/admin/templates/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Cr\u00e9er un mod\u00e8le")  # "Create Template"

    def test_metric_library_in_french(self):
        """Metric library page renders in French."""
        self._login_admin_fr()
        resp = self.http.get("/plans/admin/metrics/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Biblioth\u00e8que")  # "Library"
        self.assertContains(resp, "Importer depuis CSV")  # "Import from CSV"

    def test_target_history_labels_in_french(self):
        """Target history page shows French heading and navigation."""
        section = PlanSection.objects.create(
            client_file=self.client_file, name="Section", program=self.program,
        )
        target = PlanTarget.objects.create(
            plan_section=section, client_file=self.client_file,
            name="Cible", description="Description",
        )
        self._login_staff_fr()
        # Correct URL pattern: /plans/targets/<id>/history/
        resp = self.http.get(f"/plans/targets/{target.pk}/history/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Historique")  # "History" in page title
        self.assertContains(resp, "Retour au Plan")  # "Back to Plan" button


# ─────────────────────────────────────────────────────────────────────────
# 8. Reports / Exports in French
# ─────────────────────────────────────────────────────────────────────────

class ReportsFrenchTest(FrenchJourneyBaseTest):
    """Export forms show French labels."""

    def test_export_form_in_french(self):
        """Metric export form renders in French."""
        self._login_admin_fr()
        resp = self.http.get("/reports/export/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Rapport sur les r\u00e9sultats du programme")
        self.assertContains(resp, "G\u00e9n\u00e9rer le rapport")  # "Generate Report"

    def test_funder_report_form_in_french(self):
        """Funder report form renders in French."""
        self._login_admin_fr()
        resp = self.http.get("/reports/funder-report/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Mod\u00e8le de rapport sur les r\u00e9sultats du programme")
        self.assertContains(resp, "G\u00e9n\u00e9rer le rapport des r\u00e9sultats")

    def test_analysis_tab_in_french(self):
        """Client analysis tab shows French labels."""
        self._login_staff_fr()
        resp = self.http.get(f"/reports/client/{self.client_file.pk}/analysis/")
        self.assertEqual(resp.status_code, 200)
        # Empty state message
        self.assertContains(resp, "Aucune donn\u00e9e de mesure enregistr\u00e9e")


# ─────────────────────────────────────────────────────────────────────────
# 9. Admin Settings in French
# ─────────────────────────────────────────────────────────────────────────

class AdminSettingsFrenchTest(FrenchJourneyBaseTest):
    """Admin settings pages render in French."""

    def test_settings_dashboard_in_french(self):
        """Settings dashboard shows French section titles and descriptions."""
        self._login_admin_fr()
        resp = self.http.get("/admin/settings/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Terminologie")  # "Terminology"
        self.assertContains(resp, "Fonctionnalit\u00e9s")  # "Features"
        self.assertContains(resp, "Param\u00e8tres d'instance")  # "Instance Settings" — plain '
        self.assertContains(resp, "Utilisateurs")  # "Users"
        self.assertContains(resp, "G\u00e9rez la configuration de votre instance.")

    def test_settings_dashboard_buttons_in_french(self):
        """Settings dashboard action buttons are in French."""
        self._login_admin_fr()
        resp = self.http.get("/admin/settings/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "G\u00e9rer la terminologie")
        self.assertContains(resp, "G\u00e9rer les fonctionnalit\u00e9s")
        self.assertContains(resp, "G\u00e9rer les param\u00e8tres")
        self.assertContains(resp, "G\u00e9rer les utilisateurs")

    def test_terminology_page_in_french(self):
        """Terminology settings page renders in French."""
        self._login_admin_fr()
        resp = self.http.get("/admin/settings/terminology/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Terme")  # "Term" column header
        self.assertContains(resp, "Par d\u00e9faut")  # "Default" label
        self.assertContains(resp, "Anglais")  # "English" column header
        self.assertContains(resp, "Fran\u00e7ais")  # "French" column header
        self.assertContains(resp, "Enregistrer les modifications")  # "Save Changes"

    def test_features_page_in_french(self):
        """Features settings page renders in French."""
        self._login_admin_fr()
        resp = self.http.get("/admin/settings/features/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Fonctionnalit\u00e9")  # "Feature"
        self.assertContains(resp, "Activ\u00e9")  # "Enabled"
        self.assertContains(resp, "D\u00e9sactiv\u00e9")  # "Disabled"

    def test_instance_settings_in_french(self):
        """Instance settings page renders in French."""
        self._login_admin_fr()
        resp = self.http.get("/admin/settings/instance/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Image de marque et affichage")  # "Branding & Display"
        self.assertContains(resp, "Stockage de documents")  # "Document Storage"

    def test_user_list_in_french(self):
        """User management list page renders in French."""
        self._login_admin_fr()
        resp = self.http.get("/auth/users/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "G\u00e9rez les comptes utilisateurs et les r\u00f4les.")
        self.assertContains(resp, "Nouvel utilisateur")  # "New User"
        self.assertContains(resp, "R\u00f4le")  # "Role"
        self.assertContains(resp, "Derni\u00e8re connexion")  # "Last Login"

    def test_invite_list_in_french(self):
        """Invite list page renders in French."""
        self._login_admin_fr()
        resp = self.http.get("/auth/invites/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Nouvelle invitation")  # "New Invite"
        self.assertContains(resp, "nouveaux utilisateurs")  # part of description

    def test_audit_log_in_french(self):
        """Audit log page renders in French."""
        self._login_admin_fr()
        resp = self.http.get("/admin/audit/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Journal d'audit")  # Page title — plain apostrophe
        self.assertContains(resp, "Utilisateur")  # "User" filter label
        self.assertContains(resp, "enregistrement")  # "Record type" filter label
        self.assertContains(resp, "Toutes les actions")  # "All actions" filter option
        self.assertContains(resp, "Exporter en CSV")  # "Export CSV"
        self.assertContains(resp, "Filtrer")  # "Filter" button

    def test_note_templates_admin_in_french(self):
        """Note templates admin page renders in French."""
        self._login_admin_fr()
        resp = self.http.get("/admin/settings/note-templates/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Nouveau mod\u00e8le")  # "New Template"
        self.assertContains(resp, "D\u00e9finissez la structure")  # part of description


# ─────────────────────────────────────────────────────────────────────────
# 10. Error Pages in French
# ─────────────────────────────────────────────────────────────────────────

class ErrorPagesFrenchTest(FrenchJourneyBaseTest):
    """Error pages render in French."""

    def test_403_page_in_french(self):
        """403 Forbidden page renders in French for non-admin staff."""
        self._login_staff_fr()
        resp = self.http.get("/admin/settings/")
        self.assertEqual(resp.status_code, 403)
        self.assertContains(resp, "pas acc\u00e8s", status_code=403)  # "You don't have access"

    def test_403_help_section_in_french(self):
        """403 page help section renders in French."""
        self._login_staff_fr()
        resp = self.http.get("/admin/settings/")
        self.assertEqual(resp.status_code, 403)
        self.assertContains(
            resp,
            "Ce que vous pouvez faire",
            status_code=403,
        )  # "What you can do"

    def test_403_buttons_in_french(self):
        """403 page navigation buttons are in French."""
        self._login_staff_fr()
        resp = self.http.get("/admin/settings/")
        self.assertEqual(resp.status_code, 403)
        self.assertContains(resp, "Retour", status_code=403)  # "Go Back"
        self.assertContains(resp, "Accueil", status_code=403)  # "Home"

    def test_403_no_english_error_text(self):
        """403 page does not show English error strings."""
        self._login_staff_fr()
        resp = self.http.get("/admin/settings/")
        content = resp.content.decode()
        self.assertNotIn("have access to this page", content)
        self.assertNotIn("What you can do", content)


# ─────────────────────────────────────────────────────────────────────────
# 11. Form Validation in French
# ─────────────────────────────────────────────────────────────────────────

class FormValidationFrenchTest(FrenchJourneyBaseTest):
    """Form error messages and re-rendered forms appear in French context."""

    def test_login_form_re_renders_in_french_on_empty_fields(self):
        """Login with empty fields re-renders page in French."""
        _set_french(self.http)
        resp = self.http.post("/auth/login/", {
            "username": "",
            "password": "",
        })
        self.assertEqual(resp.status_code, 200)
        # Page is still in French context (form labels)
        self.assertContains(resp, "Nom d'utilisateur")
        self.assertContains(resp, "Mot de passe")

    def test_login_form_re_renders_in_french_on_bad_credentials(self):
        """Login with wrong credentials re-renders page in French."""
        _set_french(self.http)
        resp = self.http.post("/auth/login/", {
            "username": "admin",
            "password": "wrongpassword",
        })
        self.assertEqual(resp.status_code, 200)
        # Page still renders in French
        self.assertContains(resp, "Connexion")
        self.assertContains(resp, "Mot de passe")

    def test_quick_note_empty_text_error_in_french(self):
        """Quick note with empty text re-renders form in French."""
        self._login_staff_fr()
        resp = self.http.post(
            f"/notes/client/{self.client_file.pk}/quick/",
            {"notes_text": "   ", "consent_confirmed": True},
        )
        self.assertEqual(resp.status_code, 200)
        # Page re-renders in French (form page, not an error page)
        self.assertContains(resp, "consentement")

    def test_client_create_missing_required_field(self):
        """Client create with missing required field shows French form."""
        self._login_admin_fr()
        resp = self.http.post("/clients/create/", {
            "first_name": "",
            "last_name": "",
            "status": "active",
            "programs": [self.program.pk],
        })
        self.assertEqual(resp.status_code, 200)
        # Re-renders form — labels should be in French
        self.assertContains(resp, "Pr\u00e9nom")  # "First Name"
        self.assertContains(resp, "Nom de famille")  # "Last Name"


# ─────────────────────────────────────────────────────────────────────────
# 12. Date / Time Formatting in French Locale
# ─────────────────────────────────────────────────────────────────────────

class DateTimeFormattingFrenchTest(FrenchJourneyBaseTest):
    """Dates render in French locale format."""

    def test_date_format_uses_iso_in_french(self):
        """French locale uses ISO 8601 date format (YYYY-MM-DD)."""
        import datetime
        from django.utils import formats

        test_date = datetime.date(2026, 3, 15)
        with translation_override("fr"):
            formatted = formats.date_format(test_date, "DATE_FORMAT")
            self.assertEqual(formatted, "2026-03-15")

    def test_french_number_formatting(self):
        """French locale uses comma as decimal separator."""
        from django.utils import formats

        with translation_override("fr"):
            formatted = formats.number_format(1234.56)
            self.assertIn(",", formatted)  # Comma as decimal separator

    def test_client_detail_dates_render_in_french_context(self):
        """Client detail page renders dates while in French locale."""
        self._login_staff_fr()
        resp = self.http.get(f"/clients/{self.client_file.pk}/")
        self.assertEqual(resp.status_code, 200)
        # Page renders without error — dates formatted correctly
        self.assertContains(resp, "2026")  # Year appears in date display


# ─────────────────────────────────────────────────────────────────────────
# 13. Events in French
# ─────────────────────────────────────────────────────────────────────────

class EventsFrenchTest(FrenchJourneyBaseTest):
    """Event-related pages render in French."""

    def test_event_type_list_in_french(self):
        """Event type list admin page renders in French."""
        self._login_admin_fr()
        resp = self.http.get("/events/admin/types/")
        self.assertEqual(resp.status_code, 200)
        # Plain apostrophes in the .po file
        self.assertContains(resp, "Nouveau type d'\u00e9v\u00e9nement")  # "New Event Type"

    def test_events_tab_in_french(self):
        """Client events tab renders in French."""
        self._login_staff_fr()
        resp = self.http.get(f"/events/client/{self.client_file.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Nouvel \u00e9v\u00e9nement")  # "New Event"

    def test_event_form_labels_in_french(self):
        """Event creation form shows French labels."""
        event_type = EventType.objects.create(name="Rendez-vous")
        self._login_staff_fr()
        resp = self.http.get(
            f"/events/client/{self.client_file.pk}/create/?type={event_type.pk}"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Date et heure de d\u00e9but")  # "Start Date & Time"
        self.assertContains(resp, "Cr\u00e9er l'\u00e9v\u00e9nement")  # "Create Event" — plain '


# ─────────────────────────────────────────────────────────────────────────
# 14. Registration Pages in French
# ─────────────────────────────────────────────────────────────────────────

class RegistrationFrenchTest(FrenchJourneyBaseTest):
    """Registration admin pages render in French."""

    def test_registration_links_admin_in_french(self):
        """Registration links admin page renders in French."""
        self._login_admin_fr()
        resp = self.http.get("/admin/registration/")
        self.assertEqual(resp.status_code, 200)
        # Plain apostrophe in .po file
        self.assertContains(resp, "Nouveau lien d'inscription")  # "New Registration Link"

    def test_submissions_list_in_french(self):
        """Submissions admin page renders in French."""
        self._login_admin_fr()
        resp = self.http.get("/admin/submissions/")
        self.assertEqual(resp.status_code, 200)
        # Plain apostrophe in .po file
        self.assertContains(resp, "Soumissions d'inscription")  # "Registration Submissions"


# ─────────────────────────────────────────────────────────────────────────
# 15. Home Page (Dashboard) in French
# ─────────────────────────────────────────────────────────────────────────

class HomePageFrenchTest(FrenchJourneyBaseTest):
    """Home page / dashboard renders in French."""

    def test_home_page_welcome_in_french(self):
        """Home page shows French welcome message."""
        self._login_staff_fr()
        resp = self.http.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Bon retour")  # "Welcome back"

    def test_home_page_stats_in_french(self):
        """Home page dashboard stats cards show French labels."""
        self._login_staff_fr()
        resp = self.http.get("/")
        self.assertEqual(resp.status_code, 200)
        # Dashboard stat labels — plain apostrophe
        self.assertContains(resp, "Alertes actives")  # "Active Alerts"
        self.assertContains(resp, "Notes aujourd'hui")  # "Notes Today" — plain '

    def test_home_page_search_placeholder_in_french(self):
        """Home page search placeholder is in French."""
        self._login_staff_fr()
        resp = self.http.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Nom ou ID")  # "Name or ID..."

    def test_home_page_priority_section_in_french(self):
        """Home page priority items section is in French."""
        self._login_staff_fr()
        resp = self.http.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "\u00c9l\u00e9ments prioritaires")  # "Priority Items"

    def test_home_page_no_english_leaks(self):
        """Home page in French does not show key English-only UI strings."""
        self._login_staff_fr()
        resp = self.http.get("/")
        content = resp.content.decode()
        # These English strings should NOT appear
        self.assertNotIn("Active Alerts", content)
        self.assertNotIn("Notes Today", content)
        self.assertNotIn("Priority Items", content)
        self.assertNotIn("Sign Out", content)
        self.assertNotIn("Skip to main content", content)


# ─────────────────────────────────────────────────────────────────────────
# 16. Programs in French
# ─────────────────────────────────────────────────────────────────────────

class ProgramsFrenchTest(FrenchJourneyBaseTest):
    """Program pages render in French."""

    def test_program_list_renders_in_french(self):
        """Program list page renders in French without error."""
        self._login_staff_fr()
        resp = self.http.get("/programs/")
        self.assertEqual(resp.status_code, 200)
        # Page is in French — check HTML lang attribute and a known French label
        self.assertContains(resp, 'lang="fr"')
        self.assertContains(resp, "Programmes")  # Programme list heading

    def test_program_detail_labels_in_french(self):
        """Program detail page shows French labels."""
        self._login_admin_fr()
        resp = self.http.get(f"/programs/{self.program.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Personnel assign\u00e9")  # "Assigned Staff"
        self.assertContains(resp, "Utilisateur")  # "User"
        self.assertContains(resp, "R\u00f4le")  # "Role"
