$ErrorActionPreference = "Continue"
$project = "c:\Users\gilli\OneDrive\Documents\GitHub\konote-web"
$python = "$project\.venv\Scripts\python.exe"

# Set env vars so base.py's load_dotenv() is harmless even if .env is unreadable
$env:SECRET_KEY = "test-secret-key-not-for-production"
$env:DATABASE_URL = "sqlite://:memory:"
$env:AUDIT_DATABASE_URL = "sqlite://:memory:"
$env:FIELD_ENCRYPTION_KEY = "ly6OqAlMm32VVf08PoPJigrLCIxGd_tW1-kfWhXxXj8="
$env:DJANGO_SETTINGS_MODULE = "konote.settings.test"

Set-Location $project
& $python -m django test --verbosity=1 2>&1 | ForEach-Object { "$_" }
exit $LASTEXITCODE
