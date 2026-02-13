"""UX quality checker — analyses HTML responses for common UX issues."""
import re
from dataclasses import dataclass, field
from enum import Enum

from bs4 import BeautifulSoup


class Severity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass
class UxIssue:
    severity: Severity
    url: str
    role: str
    step: str
    description: str
    detail: str = ""


class UxChecker:
    """Run UX quality checks on an HTTP response.

    Parameters
    ----------
    response : HttpResponse
        Django test client response.
    url : str
        The URL that was visited.
    role : str
        The user role being tested (e.g. "Front Desk").
    step : str
        Description of the walkthrough step.
    is_partial : bool
        True if this is an HTMX partial (skip full-page checks).
    expected_lang : str
        Expected lang attribute value ("en" or "fr").
    role_should_see : list[str] | None
        Action button text that SHOULD be visible for this role.
    role_should_not_see : list[str] | None
        Action button text that should NOT be visible for this role.
    """

    def __init__(
        self,
        response,
        url: str,
        role: str,
        step: str,
        is_partial: bool = False,
        expected_lang: str = "en",
        role_should_see: list | None = None,
        role_should_not_see: list | None = None,
    ):
        self.response = response
        self.url = url
        self.role = role
        self.step = step
        self.is_partial = is_partial
        self.expected_lang = expected_lang
        self.role_should_see = role_should_see or []
        self.role_should_not_see = role_should_not_see or []
        self.issues: list[UxIssue] = []
        self.content = response.content.decode("utf-8", errors="replace")
        self.soup = BeautifulSoup(self.content, "html.parser")

    def _add(self, severity: Severity, description: str, detail: str = ""):
        self.issues.append(UxIssue(
            severity=severity,
            url=self.url,
            role=self.role,
            step=self.step,
            description=description,
            detail=detail,
        ))

    def run_all_checks(self) -> list[UxIssue]:
        """Run all applicable UX checks and return issues found."""
        if not self.is_partial:
            self.check_page_title()
            self.check_heading_structure()
            self.check_main_landmark()
            self.check_navigation()
            self.check_viewport()
            self.check_skip_link()
            self.check_lang_attribute()
        # These checks apply to both full pages and partials
        self.check_form_labels()
        self.check_csrf_tokens()
        self.check_image_alt()
        self.check_button_labels()
        self.check_table_accessibility()
        self.check_empty_states()
        self.check_role_action_buttons()
        return self.issues

    # ------------------------------------------------------------------
    # Structure checks (full pages only)
    # ------------------------------------------------------------------

    def check_page_title(self):
        title = self.soup.find("title")
        if not title or not title.string or not title.string.strip():
            self._add(Severity.WARNING, "Page has no <title> or title is empty")

    def check_heading_structure(self):
        headings = self.soup.find_all(re.compile(r"^h[1-6]$"))
        if not headings:
            self._add(Severity.INFO, "No headings found on page")
            return
        h1_tags = [h for h in headings if h.name == "h1"]
        if not h1_tags:
            self._add(Severity.WARNING, "Page has no <h1> element")
        # Check for skipped heading levels
        levels = [int(h.name[1]) for h in headings]
        for i in range(1, len(levels)):
            if levels[i] > levels[i - 1] + 1:
                self._add(
                    Severity.WARNING,
                    f"Heading level skipped: <h{levels[i - 1]}> followed by <h{levels[i]}>",
                )
                break  # Report once per page

    def check_main_landmark(self):
        main = self.soup.find("main")
        if not main:
            self._add(Severity.WARNING, "No <main> landmark element found")
            return
        main_id = main.get("id", "")
        skip = self.soup.find("a", href="#main-content")
        if skip and main_id != "main-content":
            self._add(
                Severity.WARNING,
                "Skip link targets #main-content but <main> has "
                f"id=\"{main_id}\"",
            )

    def check_navigation(self):
        nav = self.soup.find("nav")
        if not nav:
            self._add(Severity.WARNING, "No <nav> element found on full page")
            return
        nav_text = nav.get_text().lower()
        if self.role in ("Front Desk", "Direct Service"):
            if "admin" in nav_text.split():
                self._add(
                    Severity.WARNING,
                    f"Admin link visible to {self.role} role in navigation",
                )

    def check_viewport(self):
        meta = self.soup.find("meta", attrs={"name": "viewport"})
        if not meta:
            self._add(Severity.INFO, "No <meta name=\"viewport\"> tag found")

    def check_skip_link(self):
        skip = self.soup.find("a", href="#main-content")
        if not skip:
            self._add(Severity.INFO, "No skip navigation link found")

    def check_lang_attribute(self):
        html_tag = self.soup.find("html")
        if not html_tag:
            self._add(Severity.WARNING, "No <html> element found")
            return
        lang = html_tag.get("lang", "")
        if not lang:
            self._add(Severity.WARNING, "<html> element missing lang attribute")
        elif self.expected_lang and not lang.startswith(self.expected_lang):
            self._add(
                Severity.WARNING,
                f"Expected lang=\"{self.expected_lang}\" but found "
                f"lang=\"{lang}\"",
            )

    # ------------------------------------------------------------------
    # Form checks (full pages and partials)
    # ------------------------------------------------------------------

    def check_form_labels(self):
        inputs = self.soup.find_all(["input", "select", "textarea"])
        for inp in inputs:
            input_type = (inp.get("type") or "").lower()
            if input_type in ("hidden", "submit", "button", "image"):
                continue
            input_id = inp.get("id", "")
            input_name = inp.get("name", "")
            has_label = False
            # Method 1: <label for="id">
            if input_id:
                label = self.soup.find("label", attrs={"for": input_id})
                if label:
                    has_label = True
            # Method 2: wrapped in <label>
            if not has_label and inp.find_parent("label"):
                has_label = True
            # Method 3: ARIA
            if not has_label and (
                inp.get("aria-label") or inp.get("aria-labelledby")
            ):
                has_label = True
            # Method 4: Pico CSS uses <label> wrapping implicitly
            if not has_label:
                prev = inp.find_previous_sibling("label")
                if prev:
                    has_label = True
            if not has_label:
                field_desc = input_name or input_id or input_type
                self._add(
                    Severity.WARNING,
                    f"Form input '{field_desc}' has no associated label",
                )

    def check_csrf_tokens(self):
        forms = self.soup.find_all("form")
        for form in forms:
            method = (form.get("method") or "GET").upper()
            if method == "POST":
                csrf = form.find("input", attrs={"name": "csrfmiddlewaretoken"})
                if not csrf:
                    action = form.get("action", "(no action)")
                    self._add(
                        Severity.CRITICAL,
                        f"POST form missing CSRF token (action: {action})",
                    )

    def check_form_errors(self):
        """Check that form error messages are properly associated with fields.

        Call this explicitly after submitting an invalid form.
        Looks for Django's .errorlist, Pico-styled .badge-danger, and
        custom .error elements.
        """
        error_lists = self.soup.find_all(class_="errorlist")
        # Also check for KoNote's custom error patterns
        badge_errors = self.soup.find_all(class_="badge-danger")
        custom_errors = self.soup.find_all(
            lambda tag: tag.name == "small" and "error" in (tag.get("class") or [])
        )
        all_errors = error_lists + badge_errors + custom_errors
        if not all_errors:
            self._add(
                Severity.WARNING,
                "Expected form errors but none found (no .errorlist, .badge-danger, or .error elements)",
            )
            return
        # If we found errors via non-standard patterns, skip the aria check
        # (it only applies to .errorlist elements)
        if not error_lists:
            return
        # Check for aria-describedby association — check the error element
        # itself and its parent wrapper (templates often wrap Django's
        # errorlist in a <div> with its own id referenced by aria-describedby).
        for error_el in error_lists:
            ids_to_check = []
            error_id = error_el.get("id", "")
            if error_id:
                ids_to_check.append(error_id)
            # Also check parent wrapper id
            parent = error_el.parent
            if parent:
                parent_id = parent.get("id", "")
                if parent_id:
                    ids_to_check.append(parent_id)
            if ids_to_check:
                found = False
                for eid in ids_to_check:
                    if self.soup.find(
                        attrs={"aria-describedby": re.compile(eid)}
                    ):
                        found = True
                        break
                if not found:
                    self._add(
                        Severity.INFO,
                        f"Error list #{ids_to_check[0]} not linked via aria-describedby",
                    )

    # ------------------------------------------------------------------
    # Accessibility checks
    # ------------------------------------------------------------------

    def check_image_alt(self):
        images = self.soup.find_all("img")
        for img in images:
            if not img.get("alt") and img.get("alt") != "":
                src = img.get("src", "(unknown)")
                self._add(
                    Severity.WARNING,
                    f"Image missing alt attribute: {src}",
                )

    def check_button_labels(self):
        buttons = self.soup.find_all("button")
        for btn in buttons:
            text = btn.get_text(strip=True)
            if not text and not btn.get("aria-label") and not btn.get("aria-labelledby"):
                btn_type = btn.get("type", "button")
                self._add(
                    Severity.WARNING,
                    f"Button (type={btn_type}) has no text or aria-label",
                )

    def check_table_accessibility(self):
        tables = self.soup.find_all("table")
        for table in tables:
            caption = table.find("caption")
            if not caption and not table.get("aria-label") and not table.get("aria-labelledby"):
                self._add(
                    Severity.INFO,
                    "Table missing <caption> or aria-label",
                )
            ths = table.find_all("th")
            for th in ths:
                if not th.get("scope"):
                    text = th.get_text(strip=True)[:30]
                    self._add(
                        Severity.INFO,
                        f"<th> missing scope attribute: \"{text}\"",
                    )
                    break  # One per table is enough

    def check_message_containers(self):
        """Check that Django message containers use aria-live or role=alert."""
        messages = self.soup.find_all(class_=re.compile(r"messages?|alert"))
        for msg in messages:
            role = msg.get("role", "")
            aria_live = msg.get("aria-live", "")
            if role not in ("alert", "status") and not aria_live:
                self._add(
                    Severity.INFO,
                    "Message container missing role=\"alert\" or aria-live",
                )
                break  # Once per page

    # ------------------------------------------------------------------
    # UX quality checks
    # ------------------------------------------------------------------

    def check_empty_states(self):
        tables = self.soup.find_all("table")
        for table in tables:
            tbody = table.find("tbody")
            if tbody:
                rows = tbody.find_all("tr")
                if not rows:
                    parent = table.parent
                    if parent and not parent.find(
                        string=re.compile(r"no |none|empty|nothing", re.I)
                    ):
                        self._add(
                            Severity.INFO,
                            "Empty table without an empty-state message",
                        )

    def check_role_action_buttons(self):
        """Check that visible action buttons match the role's permissions."""
        pattern_cache = {}

        def _find_elements(text):
            """Find <a> or <button> elements whose visible text contains text.

            Uses get_text() so elements with child nodes (e.g.
            <a>Notes<span>1</span></a>) are still matched.
            """
            if text not in pattern_cache:
                pattern_cache[text] = re.compile(re.escape(text), re.I)
            pat = pattern_cache[text]
            return [
                el for el in self.soup.find_all(["a", "button"])
                if pat.search(el.get_text())
            ]

        for btn_text in self.role_should_not_see:
            if _find_elements(btn_text):
                self._add(
                    Severity.WARNING,
                    f"\"{btn_text}\" button/link visible but should be hidden "
                    f"for {self.role}",
                )
        for btn_text in self.role_should_see:
            if not _find_elements(btn_text):
                self._add(
                    Severity.INFO,
                    f"\"{btn_text}\" button/link expected but not found "
                    f"for {self.role}",
                )

    def check_403_quality(self):
        """Check that a 403 page has helpful content and a way back.

        Call this explicitly when a 403 response is expected.
        """
        text = self.soup.get_text()
        if len(text.strip()) < 20:
            self._add(
                Severity.WARNING,
                "403 page has very little content — may not be helpful",
            )
        back_link = self.soup.find("a")
        if not back_link:
            self._add(
                Severity.WARNING,
                "403 page has no links — user may be stuck",
            )

    def check_success_message(self):
        """Check that a Django success message is present after a POST.

        Call this explicitly after a successful form submission.
        """
        # Django messages framework renders with specific CSS classes
        messages = self.soup.find_all(class_=re.compile(r"messages?"))
        if not messages:
            # Also check for any element with role="alert" that has success text
            alerts = self.soup.find_all(attrs={"role": "alert"})
            if not alerts:
                self._add(
                    Severity.INFO,
                    "No success message found after form submission",
                )
