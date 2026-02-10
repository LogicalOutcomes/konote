# deploy-fullhost.ps1
# Deploy KoNote to FullHost using the Jelastic REST API
#
# Usage:
#   .\deploy-fullhost.ps1 -ApiToken "your-token" -EnvName "KoNote-prod" -OrgName "My Nonprofit"
#
# Prerequisites:
#   1. FullHost account: https://app.vap.fullhost.cloud/
#   2. API token with environment/control and environment/deployment permissions
#   3. The Docker image must be pushed to ghcr.io first (run GitHub Actions workflow)

param(
    [Parameter(Mandatory=$true)]
    [string]$ApiToken,

    [Parameter(Mandatory=$true)]
    [string]$EnvName,

    [Parameter(Mandatory=$true)]
    [string]$OrgName,

    [Parameter(Mandatory=$true)]
    [string]$AdminEmail,

    [Parameter(Mandatory=$true)]
    [SecureString]$AdminPassword,

    [string]$ClientTerm = "client",

    [string]$ApiBase = "https://app.vap.fullhost.cloud/1.0"
)

$ErrorActionPreference = "Stop"

# Convert secure string to plain text for API calls
$BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($AdminPassword)
$AdminPasswordPlain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)

Write-Host "=== KoNote FullHost Deployment ===" -ForegroundColor Cyan
Write-Host ""

# Generate secure keys
function New-SecureKey {
    param([int]$Length = 50)
    $chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
    $key = -join ((1..$Length) | ForEach-Object { $chars[(Get-Random -Maximum $chars.Length)] })
    return $key
}

function New-Base64Key {
    param([int]$Bytes = 32)
    $bytes = New-Object byte[] $Bytes
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    return [Convert]::ToBase64String($bytes)
}

$SecretKey = New-SecureKey -Length 50
$EncryptionKey = New-Base64Key -Bytes 32
$DbPassword = New-SecureKey -Length 16
$AuditDbPassword = New-SecureKey -Length 16

Write-Host "Generated security keys" -ForegroundColor Green

# Step 1: Create the environment with Docker containers
Write-Host ""
Write-Host "Step 1: Creating environment '$EnvName'..." -ForegroundColor Yellow

$nodesJson = @"
[
    {
        "nodeType": "docker",
        "nodeGroup": "cp",
        "fixedCloudlets": 2,
        "flexibleCloudlets": 8,
        "displayName": "KoNote App",
        "docker": {
            "image": "ghcr.io/gilliankerr/konote-redux:fullhost-latest"
        },
        "env": {
            "JELASTIC_ENVIRONMENT": "true",
            "DJANGO_SETTINGS_MODULE": "konote.settings.production",
            "KONOTE_MODE": "production",
            "DEMO_MODE": "true",
            "AUTH_MODE": "local",
            "PORT": "8000"
        }
    },
    {
        "nodeType": "docker",
        "nodeGroup": "sqldb",
        "fixedCloudlets": 2,
        "flexibleCloudlets": 8,
        "displayName": "Main Database",
        "docker": {
            "image": "postgres:15-alpine"
        },
        "env": {
            "POSTGRES_DB": "konote",
            "POSTGRES_USER": "konote",
            "POSTGRES_PASSWORD": "$DbPassword"
        }
    },
    {
        "nodeType": "docker",
        "nodeGroup": "sqldb2",
        "fixedCloudlets": 2,
        "flexibleCloudlets": 8,
        "displayName": "Audit Database",
        "docker": {
            "image": "postgres:15-alpine"
        },
        "env": {
            "POSTGRES_DB": "konote_audit",
            "POSTGRES_USER": "audit_writer",
            "POSTGRES_PASSWORD": "$AuditDbPassword"
        }
    }
]
"@

$envJson = @{
    shortdomain = $EnvName
    region = "default"
} | ConvertTo-Json -Compress

$createBody = @{
    session = $ApiToken
    env = $envJson
    nodes = $nodesJson
}

try {
    $createResponse = Invoke-RestMethod -Uri "$ApiBase/environment/control/rest/createenvironment" -Method POST -Body $createBody
    if ($createResponse.result -ne 0) {
        Write-Host "Error creating environment: $($createResponse.error)" -ForegroundColor Red
        exit 1
    }
    Write-Host "Environment created successfully" -ForegroundColor Green
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
    exit 1
}

# Wait for environment to be ready
Write-Host ""
Write-Host "Waiting for environment to start (this may take a few minutes)..." -ForegroundColor Yellow
Start-Sleep -Seconds 60

# Step 2: Get environment info to find node IPs
Write-Host ""
Write-Host "Step 2: Getting environment info..." -ForegroundColor Yellow

$infoBody = @{
    session = $ApiToken
    envName = $EnvName
}

try {
    $infoResponse = Invoke-RestMethod -Uri "$ApiBase/environment/control/rest/getenvinfo" -Method POST -Body $infoBody
    if ($infoResponse.result -ne 0) {
        Write-Host "Error getting environment info: $($infoResponse.error)" -ForegroundColor Red
        exit 1
    }

    $appNode = $infoResponse.nodes | Where-Object { $_.nodeGroup -eq "cp" } | Select-Object -First 1
    $dbNode = $infoResponse.nodes | Where-Object { $_.nodeGroup -eq "sqldb" } | Select-Object -First 1
    $auditDbNode = $infoResponse.nodes | Where-Object { $_.nodeGroup -eq "sqldb2" } | Select-Object -First 1
    $envDomain = $infoResponse.env.domain

    Write-Host "App Node ID: $($appNode.id)" -ForegroundColor Gray
    Write-Host "DB Node IP: $($dbNode.intIP)" -ForegroundColor Gray
    Write-Host "Audit DB Node IP: $($auditDbNode.intIP)" -ForegroundColor Gray
    Write-Host "Environment Domain: $envDomain" -ForegroundColor Gray
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
    exit 1
}

# Step 3: Configure app environment variables
Write-Host ""
Write-Host "Step 3: Configuring application environment variables..." -ForegroundColor Yellow

$appVars = @{
    SECRET_KEY = $SecretKey
    FIELD_ENCRYPTION_KEY = $EncryptionKey
    DATABASE_URL = "postgresql://konote:$DbPassword@$($dbNode.intIP):5432/konote"
    AUDIT_DATABASE_URL = "postgresql://audit_writer:$AuditDbPassword@$($auditDbNode.intIP):5432/konote_audit"
    ALLOWED_HOSTS = "$envDomain,127.0.0.1,localhost"
    ORG_NAME = $OrgName
    DEFAULT_CLIENT_TERM = $ClientTerm
    DEMO_MODE = "true"
    KONOTE_MODE = "production"
} | ConvertTo-Json -Compress

$varsBody = @{
    session = $ApiToken
    envName = $EnvName
    nodeGroup = "cp"
    vars = $appVars
}

try {
    $varsResponse = Invoke-RestMethod -Uri "$ApiBase/environment/control/rest/addcontainerenvvars" -Method POST -Body $varsBody
    if ($varsResponse.result -ne 0) {
        Write-Host "Error setting environment variables: $($varsResponse.error)" -ForegroundColor Red
        exit 1
    }
    Write-Host "Environment variables configured" -ForegroundColor Green
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
    exit 1
}

# Step 4: Restart app to apply variables and run migrations
Write-Host ""
Write-Host "Step 4: Restarting app to apply configuration..." -ForegroundColor Yellow

$restartBody = @{
    session = $ApiToken
    envName = $EnvName
    nodeGroup = "cp"
}

try {
    $restartResponse = Invoke-RestMethod -Uri "$ApiBase/environment/control/rest/restartnodes" -Method POST -Body $restartBody
    if ($restartResponse.result -ne 0) {
        Write-Host "Error restarting app: $($restartResponse.error)" -ForegroundColor Red
        exit 1
    }
    Write-Host "App restarting (migrations will run automatically)" -ForegroundColor Green
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
    exit 1
}

# Wait for app to be ready
Write-Host ""
Write-Host "Waiting for app to start and run migrations..." -ForegroundColor Yellow
Start-Sleep -Seconds 60

# Step 5: Create admin user
Write-Host ""
Write-Host "Step 5: Creating admin user..." -ForegroundColor Yellow

$createUserCmd = @"
cd /app && cat > /tmp/create_admin.py << 'PYEOF'
from apps.auth_app.models import User
if User.objects.filter(is_superuser=True).count() == 0:
    user = User.objects.create_superuser(
        username='admin',
        password='$AdminPasswordPlain',
    )
    user.email = '$AdminEmail'
    user.save()
    print('Admin user created')
else:
    print('Admin user already exists')
PYEOF
python manage.py shell < /tmp/create_admin.py 2>&1
rm -f /tmp/create_admin.py
"@

$cmdBody = @{
    session = $ApiToken
    envName = $EnvName
    nodeGroup = "cp"
    commandList = "[{`"command`": `"$($createUserCmd -replace '"', '\"' -replace "`n", " ")`"}]"
}

try {
    $cmdResponse = Invoke-RestMethod -Uri "$ApiBase/environment/control/rest/execcmdbygroup" -Method POST -Body $cmdBody
    Write-Host "Admin user command sent" -ForegroundColor Green
} catch {
    Write-Host "Warning: Could not create admin user via API. You may need to create it manually." -ForegroundColor Yellow
}

# Done!
Write-Host ""
Write-Host "=== Deployment Complete! ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Your KoNote URL: https://$envDomain" -ForegroundColor Green
Write-Host ""
Write-Host "Login with:" -ForegroundColor White
Write-Host "  Email: $AdminEmail"
Write-Host "  Password: (the password you entered)"
Write-Host ""
Write-Host "=== IMPORTANT: Save This Encryption Key ===" -ForegroundColor Red
Write-Host ""
Write-Host $EncryptionKey -ForegroundColor Yellow
Write-Host ""
Write-Host "Store this key securely. If you lose it, encrypted client data cannot be recovered." -ForegroundColor Red
Write-Host ""
