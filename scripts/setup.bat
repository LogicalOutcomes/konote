@echo off
echo Setting up KoNote development environment...
echo.

REM Activate custom git hooks
git config core.hooksPath .githooks
if %ERRORLEVEL% EQU 0 (
    echo [OK] Pre-commit hook activated
) else (
    echo [WARN] Could not set git hooks path. Are you in the repo root?
)

echo.
echo Setup complete!
