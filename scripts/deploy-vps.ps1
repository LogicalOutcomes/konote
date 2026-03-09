param(
    [ValidateSet("dev", "prod", "all")]
    [string]$Instance = "dev",

    [string]$SshHost = "konote-vps",

    [switch]$ShowLogsOnFailure
)

$ErrorActionPreference = "Stop"

function Get-DeployCommand {
    param([string]$SelectedInstance)

    switch ($SelectedInstance) {
        "prod" { return "sudo /opt/konote/scripts/deploy.sh" }
        "all" { return "sudo /opt/konote/scripts/deploy.sh --all" }
        default { return "sudo /opt/konote/scripts/deploy.sh --dev" }
    }
}

function Get-LogCommand {
    param([string]$SelectedInstance)

    switch ($SelectedInstance) {
        "prod" {
            return "cd /opt/konote && sudo docker compose -f docker-compose.yml logs web --tail=20"
        }
        "all" {
            return "printf '\n== Production ==\n'; cd /opt/konote && sudo docker compose -f docker-compose.yml logs web --tail=20; printf '\n== Dev ==\n'; cd /opt/konote-dev && sudo docker compose -f docker-compose.yml -f docker-compose.override.yml logs web --tail=20"
        }
        default {
            return "cd /opt/konote-dev && sudo docker compose -f docker-compose.yml -f docker-compose.override.yml logs web --tail=20"
        }
    }
}

$remoteCommand = Get-DeployCommand -SelectedInstance $Instance
Write-Host "Deploying '$Instance' via $SshHost..." -ForegroundColor Cyan
Write-Host "Remote command: $remoteCommand" -ForegroundColor DarkGray

ssh $SshHost $remoteCommand
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    Write-Error "Deploy failed with exit code $exitCode."

    if ($ShowLogsOnFailure) {
        $logCommand = Get-LogCommand -SelectedInstance $Instance
        Write-Host "Fetching recent web logs..." -ForegroundColor Yellow
        ssh $SshHost $logCommand
    }

    exit $exitCode
}

Write-Host "Deploy finished successfully." -ForegroundColor Green