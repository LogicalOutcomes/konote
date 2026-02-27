<#
.SYNOPSIS
    Back up KoNote's Azure-hosted PostgreSQL databases.

.DESCRIPTION
    Uses pg_dump to create custom-format backups of both the main (konote)
    and audit (konote_audit) databases from Azure Database for PostgreSQL
    Flexible Server. Optionally uploads backups to Azure Blob Storage.

.PARAMETER ResourceGroup
    Azure resource group containing the PostgreSQL server.

.PARAMETER ServerName
    Azure PostgreSQL Flexible Server name (e.g., konote-db-prod).

.PARAMETER MainDb
    Name of the main application database (default: konote).

.PARAMETER AuditDb
    Name of the audit database (default: konote_audit).

.PARAMETER BackupDir
    Local directory for backup files (default: ./backups).

.PARAMETER AdminUser
    PostgreSQL admin username for the Azure server.

.PARAMETER StorageAccount
    (Optional) Azure Storage account name for uploading backups.

.PARAMETER Container
    (Optional) Blob container name (default: db-backups).

.EXAMPLE
    .\scripts\backup-azure.ps1 -ResourceGroup konote-prod-rg -ServerName konote-db-prod -AdminUser konoteadmin

.EXAMPLE
    .\scripts\backup-azure.ps1 -ResourceGroup konote-prod-rg -ServerName konote-db-prod -AdminUser konoteadmin -StorageAccount konotestorage -Container db-backups
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$ResourceGroup,

    [Parameter(Mandatory)]
    [string]$ServerName,

    [string]$MainDb = "konote",

    [string]$AuditDb = "konote_audit",

    [string]$BackupDir = (Join-Path $PSScriptRoot "..\backups"),

    [Parameter(Mandatory)]
    [string]$AdminUser,

    [string]$StorageAccount,

    [string]$Container = "db-backups"
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

# ── Pre-flight ─────────────────────────────────────────────────────

$startTime = Get-Date

Write-Step "Pre-flight checks..."

# Check az CLI
if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Fail "Azure CLI (az) is not installed or not on PATH."
    exit 1
}

# Check logged in
$account = az account show 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Fail "Not logged in to Azure CLI. Run 'az login' first."
    exit 1
}
$accountInfo = $account | ConvertFrom-Json
Write-Pass "Logged in as $($accountInfo.user.name) (subscription: $($accountInfo.name))"

# Check pg_dump
if (-not (Get-Command pg_dump -ErrorAction SilentlyContinue)) {
    Write-Fail "pg_dump is not installed or not on PATH. Install PostgreSQL client tools."
    exit 1
}

# ── Resolve server FQDN ──────────────────────────────────────────

Write-Step "Resolving server FQDN..."
$serverInfo = az postgres flexible-server show `
    --resource-group $ResourceGroup `
    --name $ServerName `
    --query "fullyQualifiedDomainName" `
    --output tsv 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Fail "Could not find server '$ServerName' in resource group '$ResourceGroup'."
    Write-Fail $serverInfo
    exit 1
}
$serverFqdn = $serverInfo.Trim()
Write-Pass "Server: $serverFqdn"

# ── Prompt for password ──────────────────────────────────────────

$securePassword = Read-Host -Prompt "Enter password for $AdminUser@$ServerName" -AsSecureString
$bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
$password = [System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
[System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)

# ── Create backup directory ──────────────────────────────────────

if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$mainBackupFile  = Join-Path $BackupDir "${MainDb}_${timestamp}.dump"
$auditBackupFile = Join-Path $BackupDir "${AuditDb}_${timestamp}.dump"

# ── Backup main database ─────────────────────────────────────────

Write-Step "Backing up main database ($MainDb)..."

$env:PGPASSWORD = $password
try {
    pg_dump `
        --host=$serverFqdn `
        --port=5432 `
        --username=$AdminUser `
        --dbname=$MainDb `
        --format=custom `
        --file=$mainBackupFile `
        --no-owner `
        --verbose 2>&1 | ForEach-Object { Write-Verbose $_ }

    if ($LASTEXITCODE -ne 0) {
        Write-Fail "Main database backup failed."
        exit 1
    }

    $mainSize = (Get-Item $mainBackupFile).Length
    $mainHash = (Get-FileHash $mainBackupFile -Algorithm SHA256).Hash
    Write-Pass "Main backup: $([math]::Round($mainSize / 1MB, 2)) MB  SHA256: $($mainHash.Substring(0,16))..."

    # ── Backup audit database ─────────────────────────────────────

    Write-Step "Backing up audit database ($AuditDb)..."

    pg_dump `
        --host=$serverFqdn `
        --port=5432 `
        --username=$AdminUser `
        --dbname=$AuditDb `
        --format=custom `
        --file=$auditBackupFile `
        --no-owner `
        --verbose 2>&1 | ForEach-Object { Write-Verbose $_ }

    if ($LASTEXITCODE -ne 0) {
        Write-Fail "Audit database backup failed."
        exit 1
    }

    $auditSize = (Get-Item $auditBackupFile).Length
    $auditHash = (Get-FileHash $auditBackupFile -Algorithm SHA256).Hash
    Write-Pass "Audit backup: $([math]::Round($auditSize / 1MB, 2)) MB  SHA256: $($auditHash.Substring(0,16))..."

} finally {
    # Always clear the password from the environment
    Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
    $password = $null
}

# ── Optional: upload to Azure Blob Storage ────────────────────────

if ($StorageAccount) {
    Write-Step "Uploading backups to Azure Blob Storage ($StorageAccount/$Container)..."

    # Ensure container exists
    az storage container create `
        --name $Container `
        --account-name $StorageAccount `
        --auth-mode login `
        --output none 2>&1

    foreach ($file in @($mainBackupFile, $auditBackupFile)) {
        $blobName = "$(Get-Date -Format 'yyyy/MM/dd')/$(Split-Path $file -Leaf)"
        Write-Step "  Uploading $(Split-Path $file -Leaf) -> $blobName"

        az storage blob upload `
            --account-name $StorageAccount `
            --container-name $Container `
            --name $blobName `
            --file $file `
            --auth-mode login `
            --overwrite `
            --output none

        if ($LASTEXITCODE -ne 0) {
            Write-Fail "Failed to upload $(Split-Path $file -Leaf)."
            exit 1
        }
    }

    Write-Pass "Backups uploaded to blob storage."
}

# ── Summary ───────────────────────────────────────────────────────

$endTime = Get-Date
$duration = $endTime - $startTime

Write-Host ""
Write-Host "═══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Azure Backup Summary" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Server:        $serverFqdn"
Write-Host "  Started:       $($startTime.ToString('yyyy-MM-dd HH:mm:ss'))"
Write-Host "  Finished:      $($endTime.ToString('yyyy-MM-dd HH:mm:ss'))"
Write-Host "  Duration:      $($duration.ToString('mm\:ss'))"
Write-Host "  Main backup:   $(Split-Path $mainBackupFile -Leaf)  ($([math]::Round($mainSize / 1MB, 2)) MB)"
Write-Host "  Audit backup:  $(Split-Path $auditBackupFile -Leaf)  ($([math]::Round($auditSize / 1MB, 2)) MB)"
if ($StorageAccount) {
    Write-Host "  Blob storage:  $StorageAccount/$Container"
}
Write-Host "  Files in:      $(Resolve-Path $BackupDir)"
Write-Host "═══════════════════════════════════════════" -ForegroundColor Cyan

exit 0
