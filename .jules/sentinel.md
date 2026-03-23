## 2024-03-05 - [CSV Injection in Consortium Export]
**Vulnerability:** User-controlled data (consortium names, demographic labels, metrics) was not sanitized before being written to CSV exports in `apps/consortia/views.py`. The unsanitized `consortium.name` was also directly included in the `Content-Disposition` header filename.
**Learning:** This exposes the application to CSV injection (Formula execution in Excel/LibreOffice) and potential HTTP header injection/path traversal attacks in dynamically generated filenames. This pattern was missing in the newer consortia app despite protections existing in the older reports app.
**Prevention:** Always use `sanitise_csv_row` and `sanitise_filename` from `apps.reports.csv_utils` whenever dynamically generating CSV files and headers that contain user-provided text values.

## 2024-03-05 - [Missing Rate Limiting on Demo Portal Login]
**Vulnerability:** The `demo_portal_login` view in `apps/auth_app/views.py` lacked rate limiting protection.
**Learning:** Even demo-specific authentication endpoints are susceptible to brute-force or Denial-of-Service (DoS) attacks if left unprotected. All authentication-related routes must enforce uniform rate limits.
**Prevention:** Always apply the `@ratelimit(key="ip", rate="10/m", method=["POST"], block=True)` decorator (or appropriate thresholds) to all authentication endpoints, including those intended solely for demo purposes.
