<#
.SYNOPSIS
    End-to-end backup/restore test for KoNote using Docker Compose.

.DESCRIPTION
    Backs up both PostgreSQL databases (app + audit), destroys and recreates
    the volumes, restores from backup, then runs the verify_backup_restore
    management command to confirm data integrity.

.PARAMETER ComposeFile
    Path to docker-compose.yml (default: docker-compose.yml in script directory's parent).

.PARAMETER BackupDir
    Directory to store backup files (default: ./backups).

.PARAMETER KeepBackups
    If set, backup files are kept after the test completes.

.PARAMETER Force
    Skip the confirmation prompt before destroying volumes.

.EXAMPLE
    .\scripts\test-backup-restore.ps1
    .\scripts\test-backup-restore.ps1 -Force -KeepBackups
#>

[CmdletBinding()]
param(
    [string]$ComposeFile = (Join-Path $PSScriptRoot "..\docker-compose.yml"),
    [string]$BackupDir = (Join-Path $PSScriptRoot "..\backups"),
    [switch]$KeepBackups,
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Helpers ────────────────────────────────────────────────────────

function Write-Step {
    param([string]$Message)
    $ts = Get-Date -Format "HH:mm:ss"
    Write-Host "[$ts] " -ForegroundColor DarkGray -NoNewline
    Write-Host $Message -ForegroundColor Cyan
}

function Write-Pass {
    param([string]$Message)
    $ts = Get-Date -Format "HH:mm:ss"
    Write-Host "[$ts] PASS " -ForegroundColor Green -NoNewline
    Write-Host $Message
}

function Write-Fail {
    param([string]$Message)
    $ts = Get-Date -Format "HH:mm:ss"
    Write-Host "[$ts] FAIL " -ForegroundColor Red -NoNewline
    Write-Host $Message
}

function Wait-ForHealthy {
    param(
        [string]$Service,
        [int]$TimeoutSeconds = 60
    )
    Write-Step "Waiting for $Service to be healthy (timeout: ${TimeoutSeconds}s)..."
    $elapsed = 0
    while ($elapsed -lt $TimeoutSeconds) {
        $status = docker compose -f $ComposeFile ps --format json $Service 2>$null |
            ConvertFrom-Json |
            Select-Object -ExpandProperty Health -ErrorAction SilentlyContinue
        if ($status -eq "healthy") {
            Write-Pass "$Service is healthy."
            return
        }
        Start-Sleep -Seconds 2
        $elapsed += 2
    }
    Write-Fail "$Service did not become healthy within ${TimeoutSeconds}s."
    exit 1
}

# ── Pre-flight ─────────────────────────────────────────────────────

$startTime = Get-Date

Write-Step "Pre-flight checks..."

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Fail "Docker is not installed or not on PATH."
    exit 1
}

$dockerInfo = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Fail "Docker daemon is not running."
    exit 1
}

$ComposeFile = Resolve-Path $ComposeFile -ErrorAction Stop
if (-not (Test-Path $ComposeFile)) {
    Write-Fail "Compose file not found: $ComposeFile"
    exit 1
}

Write-Pass "Docker is running, compose file found."

# Read env vars from .env next to compose file for pg_dump credentials
$envFile = Join-Path (Split-Path $ComposeFile) ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            [System.Environment]::SetEnvironmentVariable($Matches[1].Trim(), $Matches[2].Trim(), "Process")
        }
    }
}

$pgUser = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "postgres" }
$pgDb   = if ($env:POSTGRES_DB)   { $env:POSTGRES_DB }   else { "konote" }
$auditUser = if ($env:AUDIT_POSTGRES_USER)     { $env:AUDIT_POSTGRES_USER }     else { "postgres" }
$auditDb   = if ($env:AUDIT_POSTGRES_DB)       { $env:AUDIT_POSTGRES_DB }       else { "konote_audit" }

# ── Ensure containers are up ──────────────────────────────────────

Write-Step "Starting database containers..."
docker compose -f $ComposeFile up -d db audit_db
if ($LASTEXITCODE -ne 0) { Write-Fail "Failed to start containers."; exit 1 }

Wait-ForHealthy -Service "db"
Wait-ForHealthy -Service "audit_db"

# ── Create backup directory ──────────────────────────────────────

if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
}

$mainBackup  = Join-Path $BackupDir "konote_backup.dump"
$auditBackup = Join-Path $BackupDir "konote_audit_backup.dump"

# ── Backup ─────────────────────────────────────────────────────────

Write-Step "Backing up main database ($pgDb)..."
docker compose -f $ComposeFile exec -T db pg_dump -U $pgUser -Fc $pgDb > $mainBackup
if ($LASTEXITCODE -ne 0) { Write-Fail "Main database backup failed."; exit 1 }
$mainSize = (Get-Item $mainBackup).Length
$mainHash = (Get-FileHash $mainBackup -Algorithm SHA256).Hash
Write-Pass "Main backup: $([math]::Round($mainSize / 1KB, 1)) KB  SHA256: $($mainHash.Substring(0,16))..."

Write-Step "Backing up audit database ($auditDb)..."
docker compose -f $ComposeFile exec -T audit_db pg_dump -U $auditUser -Fc $auditDb > $auditBackup
if ($LASTEXITCODE -ne 0) { Write-Fail "Audit database backup failed."; exit 1 }
$auditSize = (Get-Item $auditBackup).Length
$auditHash = (Get-FileHash $auditBackup -Algorithm SHA256).Hash
Write-Pass "Audit backup: $([math]::Round($auditSize / 1KB, 1)) KB  SHA256: $($auditHash.Substring(0,16))..."

# ── Destroy and recreate volumes ──────────────────────────────────

if (-not $Force) {
    Write-Host ""
    Write-Host "WARNING: This will destroy database volumes (pgdata, audit_pgdata) and restore from backup." -ForegroundColor Yellow
    $confirm = Read-Host "Continue? (yes/no)"
    if ($confirm -ne "yes") {
        Write-Host "Aborted." -ForegroundColor Yellow
        exit 0
    }
}

Write-Step "Stopping all containers and removing volumes..."
docker compose -f $ComposeFile down -v
if ($LASTEXITCODE -ne 0) { Write-Fail "Failed to tear down containers."; exit 1 }
Write-Pass "Volumes destroyed."

Write-Step "Recreating database containers with fresh volumes..."
docker compose -f $ComposeFile up -d db audit_db
if ($LASTEXITCODE -ne 0) { Write-Fail "Failed to recreate containers."; exit 1 }

Wait-ForHealthy -Service "db"
Wait-ForHealthy -Service "audit_db"

# ── Restore ───────────────────────────────────────────────────────

Write-Step "Restoring main database..."
# pg_restore into a fresh database: create the objects
Get-Content $mainBackup -AsByteStream -ReadCount 0 |
    docker compose -f $ComposeFile exec -T db pg_restore -U $pgUser -d $pgDb --no-owner --no-acl --single-transaction
if ($LASTEXITCODE -ne 0) {
    Write-Host "   (pg_restore may emit warnings for pre-existing objects — checking verification next)" -ForegroundColor Yellow
}

Write-Step "Restoring audit database..."
Get-Content $auditBackup -AsByteStream -ReadCount 0 |
    docker compose -f $ComposeFile exec -T audit_db pg_restore -U $auditUser -d $auditDb --no-owner --no-acl --single-transaction
if ($LASTEXITCODE -ne 0) {
    Write-Host "   (pg_restore may emit warnings — checking verification next)" -ForegroundColor Yellow
}

# ── Start web container and verify ────────────────────────────────

Write-Step "Starting web container for verification..."
docker compose -f $ComposeFile up -d web
if ($LASTEXITCODE -ne 0) { Write-Fail "Failed to start web container."; exit 1 }

# Give web container a moment to fully start
Start-Sleep -Seconds 5

Write-Step "Running verify_backup_restore command..."
$verifyOutput = docker compose -f $ComposeFile exec web python manage.py verify_backup_restore 2>&1
$verifyExit = $LASTEXITCODE

Write-Host ""
Write-Host $verifyOutput
Write-Host ""

# ── Summary ───────────────────────────────────────────────────────

$endTime = Get-Date
$duration = $endTime - $startTime

Write-Host ""
Write-Host "═══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Backup/Restore Test Summary" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Started:       $($startTime.ToString('yyyy-MM-dd HH:mm:ss'))"
Write-Host "  Finished:      $($endTime.ToString('yyyy-MM-dd HH:mm:ss'))"
Write-Host "  Duration:      $($duration.ToString('mm\:ss'))"
Write-Host "  Main backup:   $([math]::Round($mainSize / 1KB, 1)) KB"
Write-Host "  Audit backup:  $([math]::Round($auditSize / 1KB, 1)) KB"

if ($verifyExit -eq 0) {
    Write-Host "  Verification:  " -NoNewline
    Write-Host "PASSED" -ForegroundColor Green
} else {
    Write-Host "  Verification:  " -NoNewline
    Write-Host "FAILED" -ForegroundColor Red
}
Write-Host "═══════════════════════════════════════════" -ForegroundColor Cyan

# ── Cleanup ───────────────────────────────────────────────────────

if (-not $KeepBackups) {
    Write-Step "Cleaning up backup files..."
    Remove-Item $mainBackup, $auditBackup -Force -ErrorAction SilentlyContinue
    Write-Pass "Backup files removed."
} else {
    Write-Step "Backup files kept in: $BackupDir"
}

if ($verifyExit -ne 0) {
    exit 1
}

exit 0
