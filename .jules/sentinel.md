## 2024-03-05 - [CSV Injection in Consortium Export]
**Vulnerability:** User-controlled data (consortium names, demographic labels, metrics) was not sanitized before being written to CSV exports in `apps/consortia/views.py`. The unsanitized `consortium.name` was also directly included in the `Content-Disposition` header filename.
**Learning:** This exposes the application to CSV injection (Formula execution in Excel/LibreOffice) and potential HTTP header injection/path traversal attacks in dynamically generated filenames. This pattern was missing in the newer consortia app despite protections existing in the older reports app.
**Prevention:** Always use `sanitise_csv_row` and `sanitise_filename` from `apps.reports.csv_utils` whenever dynamically generating CSV files and headers that contain user-provided text values.

## 2024-03-05 - [Missing Rate Limiting on Demo Endpoints]
**Vulnerability:** The `demo_portal_login` view was missing rate limiting, making it vulnerable to brute-force or DoS attacks.
**Learning:** Even endpoints designed for demo purposes need to be protected. The `django-ratelimit` decorator with `block=True` should be applied uniformly to all authentication-related endpoints.
**Prevention:** Always ensure the `@ratelimit(key="ip", rate="...", method="POST", block=True)` decorator is present on any view that processes login or authentication requests. Also make sure the import is present: `from django_ratelimit.decorators import ratelimit`.

## 2025-04-08 - [Missing Rate Limiting on Authentication Boundary Endpoints]
**Vulnerability:** Endpoints that consume one-time tokens or handle user registrations (like `invite_accept` in `apps/auth_app/invite_views.py` and `staff_assisted_login` in `apps/portal/views.py`) were not rate-limited.
**Learning:** These endpoints act as authentication boundaries. Without rate limits, they are vulnerable to brute-force attacks on the tokens or DoS attacks via repeated requests.
**Prevention:** All authentication-related endpoints, including those consuming one-time tokens or handling user registrations (e.g., invite accept links, staff-assisted tokens), must be uniformly protected by the `@ratelimit(key="ip", rate="...", method=["GET", "POST"], block=True)` decorator. Both GET and POST should be protected where applicable to prevent abuse.
