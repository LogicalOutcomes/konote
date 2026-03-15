## 2024-03-05 - [CSV Injection in Consortium Export]
**Vulnerability:** User-controlled data (consortium names, demographic labels, metrics) was not sanitized before being written to CSV exports in `apps/consortia/views.py`. The unsanitized `consortium.name` was also directly included in the `Content-Disposition` header filename.
**Learning:** This exposes the application to CSV injection (Formula execution in Excel/LibreOffice) and potential HTTP header injection/path traversal attacks in dynamically generated filenames. This pattern was missing in the newer consortia app despite protections existing in the older reports app.
**Prevention:** Always use `sanitise_csv_row` and `sanitise_filename` from `apps.reports.csv_utils` whenever dynamically generating CSV files and headers that contain user-provided text values.

## 2026-03-15 - [Rate Limit Bypass on Sensitive Endpoints]
**Vulnerability:** The `@ratelimit` decorator from `django-ratelimit` was used on sensitive endpoints like `password_reset_confirm` and `demo_login` without the `block=True` parameter.
**Learning:** `django-ratelimit` defaults to just setting `request.limited = True` when limits are exceeded. Without `block=True` (or explicit checks in the view logic for `request.limited`), the execution continues and the rate limit is silently bypassed.
**Prevention:** Always include `block=True` when applying the `@ratelimit` decorator unless the view explicitly checks `request.limited` to handle rate-limited requests manually.
