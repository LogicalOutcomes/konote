## 2024-03-05 - [CSV Injection in Consortium Export]
**Vulnerability:** User-controlled data (consortium names, demographic labels, metrics) was not sanitized before being written to CSV exports in `apps/consortia/views.py`. The unsanitized `consortium.name` was also directly included in the `Content-Disposition` header filename.
**Learning:** This exposes the application to CSV injection (Formula execution in Excel/LibreOffice) and potential HTTP header injection/path traversal attacks in dynamically generated filenames. This pattern was missing in the newer consortia app despite protections existing in the older reports app.
**Prevention:** Always use `sanitise_csv_row` and `sanitise_filename` from `apps.reports.csv_utils` whenever dynamically generating CSV files and headers that contain user-provided text values.

## 2024-03-05 - [Missing Rate Limiting on Demo Endpoints]
**Vulnerability:** The `demo_portal_login` view was missing rate limiting, making it vulnerable to brute-force or DoS attacks.
**Learning:** Even endpoints designed for demo purposes need to be protected. The `django-ratelimit` decorator with `block=True` should be applied uniformly to all authentication-related endpoints.
**Prevention:** Always ensure the `@ratelimit(key="ip", rate="...", method="POST", block=True)` decorator is present on any view that processes login or authentication requests. Also make sure the import is present: `from django_ratelimit.decorators import ratelimit`.

## 2024-03-05 - [Missing Rate Limiting on Invite Endpoints]
**Vulnerability:** The `invite_accept` endpoint in `apps/auth_app/invite_views.py` allowed unauthenticated users to accept invites and register without rate limits.
**Learning:** This made it vulnerable to brute force and DoS attacks by making it easy to test combinations of `code` or flood the endpoint with POST requests.
**Prevention:** As with all public/authentication-related endpoints, ensure the `@ratelimit(key="ip", rate="...", method=["GET", "POST"], block=True)` decorator is applied. When using `key="ip"`, note that it assumes correct proxy settings are present (e.g. `X-Forwarded-For`) so it doesn't just block the proxy IP.

## 2024-10-24 - [Avoid `innerHTML` for Dynamic DOM Modifications]
**Vulnerability:** XSS risk due to modifying the DOM using `.innerHTML` with potentially dynamic or unescaped translated values in `static/js/app.js`.
**Learning:** `innerHTML` exposes a risk of executing unescaped input or malformed HTML translations. Instead of clearing nodes with `.innerHTML = ""` or creating nested HTML structures via strings, safer programmatic node manipulation should be utilized.
**Prevention:** Use `.textContent` for assigning simple text to elements. Use programmatic DOM creation methods like `document.createElement` and `node.appendChild` instead of injecting raw HTML strings into `.innerHTML`. To clear an element, loop through and use `removeChild` on its children (e.g. `while (el.firstChild) el.removeChild(el.firstChild);`).

## 2024-10-25 - [Login CSRF on Authentication Boundaries]
**Vulnerability:** The `demo_login` and `demo_portal_login` endpoints in `apps/auth_app/views.py` were decorated with `@csrf_exempt`, despite functioning as authentication boundaries and accepting POST requests.
**Learning:** Bypassing CSRF protection on login endpoints introduces a Login CSRF vulnerability, allowing an attacker to force a victim's browser to authenticate to the application using the attacker's credentials, potentially tricking the victim into revealing sensitive information.
**Prevention:** Never use `@csrf_exempt` on authentication boundaries (e.g., login, demo login, password reset) unless required by a necessary external callback. Always ensure forms in the frontend (e.g., `templates/auth/login.html`) include `{% csrf_token %}` to satisfy CSRF protection.
