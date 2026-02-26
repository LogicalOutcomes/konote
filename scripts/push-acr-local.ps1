# push-acr-local.ps1
# Build and push KoNote Docker image to Azure Container Registry with date-based tags.
#
# Example:
#   .\scripts\push-acr-local.ps1 -AcrName konoteregistry
#   .\scripts\push-acr-local.ps1 -AcrName konoteregistry -Suffix 2
#   .\scripts\push-acr-local.ps1 -AcrName konoteregistry -Dockerfile Dockerfile.alpine -ImageName konote-fullhost
#   .\scripts\push-acr-local.ps1 -AcrName konoteregistry -SeedSourceFile "D:\Elysra\konote-prosper-canada\apps\admin_settings\management\commands\seed_prosper_canada_demo.py"
#   .\scripts\push-acr-local.ps1 -AcrName konoteregistry -RedeployLatest -ResourceGroup KoNote-prod -ContainerAppName konote-web
#   .\scripts\push-acr-local.ps1 -AcrName konoteregistry -RedeployLatest -ReseedRemoteDemoData -IUnderstandRemoteDataWillBeDeleted `
#       -SeedSourceFile "D:\Elysra\konote-prosper-canada\apps\admin_settings\management\commands\seed_prosper_canada_demo.py"

[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)]
    [string]$AcrName,

    [string]$ImageName = "konote",

    [string]$Dockerfile = "Dockerfile",

    [string]$ContextPath = ".",

    [string]$DateTag = (Get-Date -Format "yyyy-MM-dd"),

    [string]$Suffix,

    [string]$SeedSourceFile,

    [string]$SeedDestinationFile = "apps/admin_settings/management/commands/seed_prosper_canada_demo.py",

    [switch]$KeepSeedOverride,

    [switch]$RedeployLatest,

    [string]$ResourceGroup = "KoNote-prod",

    [string]$ContainerAppName = "konote-web",

    [switch]$ReseedRemoteDemoData,

    [string]$RemoteReseedCommand = "seed_prosper_canada_demo --reset",

    [switch]$IUnderstandRemoteDataWillBeDeleted,

    [switch]$SkipDailyTag,

    [switch]$SkipLatest
)

$ErrorActionPreference = "Stop"

function Test-CommandExists {
    param(
        [Parameter(Mandatory = $true)]
        [string]$CommandName
    )

    return [bool](Get-Command -Name $CommandName -ErrorAction SilentlyContinue)
}

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock]$ScriptBlock,

        [Parameter(Mandatory = $true)]
        [string]$FailureMessage
    )

    & $ScriptBlock
    if ($LASTEXITCODE -ne 0) {
        throw $FailureMessage
    }
}

if (-not (Test-CommandExists -CommandName "az")) {
    throw "Azure CLI is not installed or not on PATH."
}

if ($RedeployLatest -and $SkipLatest) {
    throw "Cannot redeploy to latest when -SkipLatest is set. Remove -SkipLatest or disable -RedeployLatest."
}

if ($ReseedRemoteDemoData -and -not $IUnderstandRemoteDataWillBeDeleted) {
    throw "Remote reseed is destructive. Re-run with -IUnderstandRemoteDataWillBeDeleted to confirm."
}

$dockerAvailable = Test-CommandExists -CommandName "docker"
$useAcrBuild = -not $dockerAvailable

if ($useAcrBuild) {
    Write-Host "Docker not found; using Azure cloud build (az acr build)." -ForegroundColor Yellow
}

$seedOverrideApplied = $false
$seedDestinationExistedBefore = $false
$seedBackupPath = $null
$resolvedSeedDestination = $null

if (-not [string]::IsNullOrWhiteSpace($SeedSourceFile)) {
    $resolvedSourceFile = (Resolve-Path -Path $SeedSourceFile -ErrorAction Stop).Path
    $resolvedContextPath = (Resolve-Path -Path $ContextPath -ErrorAction Stop).Path

    if ([System.IO.Path]::IsPathRooted($SeedDestinationFile)) {
        $resolvedSeedDestination = $SeedDestinationFile
    }
    else {
        $resolvedSeedDestination = Join-Path -Path $resolvedContextPath -ChildPath $SeedDestinationFile
    }

    $seedDestinationDirectory = Split-Path -Path $resolvedSeedDestination -Parent
    if (-not (Test-Path -Path $seedDestinationDirectory)) {
        throw "Seed destination directory does not exist: $seedDestinationDirectory"
    }

    if ([string]::Equals($resolvedSourceFile, $resolvedSeedDestination, [System.StringComparison]::OrdinalIgnoreCase)) {
        Write-Host "Seed source and destination are the same file; using existing local seed file." -ForegroundColor Yellow
    }
    else {
        $seedDestinationExistedBefore = Test-Path -Path $resolvedSeedDestination
        if ($seedDestinationExistedBefore) {
            $seedBackupPath = [System.IO.Path]::GetTempFileName()
            Copy-Item -Path $resolvedSeedDestination -Destination $seedBackupPath -Force
        }

        Copy-Item -Path $resolvedSourceFile -Destination $resolvedSeedDestination -Force
        $seedOverrideApplied = $true

        Write-Host "Using external seed file for this build:" -ForegroundColor Cyan
        Write-Host "  Source:      $resolvedSourceFile"
        Write-Host "  Destination: $resolvedSeedDestination"
    }
}

if ([string]::IsNullOrWhiteSpace($Suffix)) {
    $gitSuffix = ""
    if (Test-CommandExists -CommandName "git") {
        $gitSuffix = (git rev-parse --short HEAD 2>$null)
    }

    if (-not [string]::IsNullOrWhiteSpace($gitSuffix)) {
        $Suffix = $gitSuffix.Trim()
    }
    else {
        $Suffix = (Get-Date -Format "HHmmss")
    }
}

$immutableTag = "$DateTag.$Suffix"
$tagsToPush = New-Object System.Collections.Generic.List[string]
$tagsToPush.Add($immutableTag)

if (-not $SkipDailyTag) {
    $tagsToPush.Add($DateTag)
}

if (-not $SkipLatest) {
    $tagsToPush.Add("latest")
}

$localBuildTag = "$ImageName:local-build"

Write-Host "=== KoNote local ACR push ===" -ForegroundColor Cyan
Write-Host "ACR:            $AcrName"
Write-Host "Image:          $ImageName"
Write-Host "Dockerfile:     $Dockerfile"
Write-Host "Context path:   $ContextPath"
Write-Host "Immutable tag:  $immutableTag"
Write-Host "All tags:       $($tagsToPush -join ', ')"
if ($RedeployLatest) {
    Write-Host "Redeploy:       Enabled (Container App: $ContainerAppName in $ResourceGroup)"
}
if ($ReseedRemoteDemoData) {
    Write-Host "Remote reseed:  Enabled (command: python manage.py $RemoteReseedCommand)" -ForegroundColor Yellow
}
Write-Host ""

try {
    if ($PSCmdlet.ShouldProcess("Azure Container Registry '$AcrName'", "Resolve login server")) {
        $acrLoginServer = az acr show --name $AcrName --query loginServer --output tsv
        if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($acrLoginServer)) {
            throw "Could not resolve ACR login server for '$AcrName'. Ensure you are logged in (az login) and the registry exists."
        }
        $acrLoginServer = $acrLoginServer.Trim()
    }

    if (-not $useAcrBuild) {
        if ($PSCmdlet.ShouldProcess("Docker image '$localBuildTag'", "Build")) {
            Invoke-Checked -ScriptBlock {
                docker build -f $Dockerfile -t $localBuildTag $ContextPath
            } -FailureMessage "Docker build failed."
        }

        if ($PSCmdlet.ShouldProcess("Azure Container Registry '$AcrName'", "Login")) {
            Invoke-Checked -ScriptBlock {
                az acr login --name $AcrName
            } -FailureMessage "Azure Container Registry login failed."
        }

        foreach ($tag in $tagsToPush) {
            $remoteImage = "$acrLoginServer/${ImageName}:$tag"

            if ($PSCmdlet.ShouldProcess($remoteImage, "Tag image")) {
                Invoke-Checked -ScriptBlock {
                    docker tag $localBuildTag $remoteImage
                } -FailureMessage "Failed to tag image '$remoteImage'."
            }

            if ($PSCmdlet.ShouldProcess($remoteImage, "Push image")) {
                Invoke-Checked -ScriptBlock {
                    docker push $remoteImage
                } -FailureMessage "Failed to push image '$remoteImage'."
            }
        }
    }
    else {
        if ($PSCmdlet.ShouldProcess("Azure Container Registry '$AcrName'", "Build immutable image '${ImageName}:$immutableTag'")) {
            Invoke-Checked -ScriptBlock {
                az acr build --registry $AcrName --image "${ImageName}:$immutableTag" --file $Dockerfile $ContextPath
            } -FailureMessage "ACR cloud build failed for '${ImageName}:$immutableTag'."
        }

        foreach ($tag in $tagsToPush) {
            if ($tag -eq $immutableTag) {
                continue
            }

            if ($PSCmdlet.ShouldProcess("$acrLoginServer/${ImageName}:$tag", "Create tag from immutable image via ACR import")) {
                Invoke-Checked -ScriptBlock {
                    az acr import --name $AcrName --source "$acrLoginServer/${ImageName}:$immutableTag" --image "${ImageName}:$tag" --force
                } -FailureMessage "Failed to create tag '${ImageName}:$tag' from '${ImageName}:$immutableTag'."
            }
        }
    }

    if ($RedeployLatest) {
        $latestImage = "$acrLoginServer/${ImageName}:latest"

        if ($PSCmdlet.ShouldProcess("Container App '$ContainerAppName'", "Update image to $latestImage")) {
            Invoke-Checked -ScriptBlock {
                az containerapp update --resource-group $ResourceGroup --name $ContainerAppName --image $latestImage
            } -FailureMessage "Container App redeploy to latest failed."
        }

        Write-Host "Container App redeployed to latest image: $latestImage" -ForegroundColor Green
    }

    if ($ReseedRemoteDemoData) {
        $remoteCommand = "python manage.py $RemoteReseedCommand"

        if ($PSCmdlet.ShouldProcess("Container App '$ContainerAppName'", "Run remote reseed command: $remoteCommand")) {
            Invoke-Checked -ScriptBlock {
                az containerapp exec --resource-group $ResourceGroup --name $ContainerAppName --command $remoteCommand
            } -FailureMessage "Remote reseed command failed."
        }

        Write-Host "Remote reseed command completed." -ForegroundColor Green
    }

    Write-Host ""
    Write-Host "Push complete." -ForegroundColor Green
    Write-Host "Use immutable tag for production rollouts: $immutableTag" -ForegroundColor Green
}
finally {
    if ($seedOverrideApplied -and -not $KeepSeedOverride) {
        if ($seedDestinationExistedBefore -and -not [string]::IsNullOrWhiteSpace($seedBackupPath)) {
            Copy-Item -Path $seedBackupPath -Destination $resolvedSeedDestination -Force
        }
        else {
            Remove-Item -Path $resolvedSeedDestination -Force -ErrorAction SilentlyContinue
        }

        if (-not [string]::IsNullOrWhiteSpace($seedBackupPath) -and (Test-Path -Path $seedBackupPath)) {
            Remove-Item -Path $seedBackupPath -Force -ErrorAction SilentlyContinue
        }

        Write-Host "Restored local seed file after build." -ForegroundColor DarkGray
    }
}
