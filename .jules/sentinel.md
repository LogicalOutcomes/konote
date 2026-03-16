## 2024-03-05 - [CSV Injection in Consortium Export]
**Vulnerability:** User-controlled data (consortium names, demographic labels, metrics) was not sanitized before being written to CSV exports in `apps/consortia/views.py`. The unsanitized `consortium.name` was also directly included in the `Content-Disposition` header filename.
**Learning:** This exposes the application to CSV injection (Formula execution in Excel/LibreOffice) and potential HTTP header injection/path traversal attacks in dynamically generated filenames. This pattern was missing in the newer consortia app despite protections existing in the older reports app.
**Prevention:** Always use `sanitise_csv_row` and `sanitise_filename` from `apps.reports.csv_utils` whenever dynamically generating CSV files and headers that contain user-provided text values.
## 2024-05-24 - Rate Limiting Bypass in django-ratelimit

**Vulnerability:** The `@ratelimit` decorator from `django-ratelimit` was used on sensitive endpoints (like `password_reset_confirm` and `demo_login`) without the `block=True` argument, and the views did not manually check `request.limited`. This meant the decorator would track the rate but never block requests, allowing attackers to completely bypass rate limits and perform brute-force attacks against password reset tokens.
**Learning:** In this project, `django-ratelimit` defaults to just setting `request.limited = True` if the limit is exceeded. It does not automatically return a 403 response unless `block=True` is explicitly passed.
**Prevention:** Always verify that `@ratelimit` decorators on sensitive endpoints either include `block=True` or that the view explicitly contains `if getattr(request, 'limited', False):` logic to handle the rate limit.
