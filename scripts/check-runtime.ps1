param(
    [int]$FrontendPort = 3000,
    [int]$BackendPort = 8000,
    [switch]$NoRestart
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$frontendUrl = "http://127.0.0.1:$FrontendPort"
$backendUrl = "http://127.0.0.1:$BackendPort"

function Test-Runtime {
    $frontend = Invoke-WebRequest $frontendUrl -UseBasicParsing
    if ($frontend.StatusCode -ne 200) {
        throw "Frontend returned status $($frontend.StatusCode)"
    }

    $health = Invoke-RestMethod "$backendUrl/api/health"
    if ($health.status -ne "ok") {
        throw "Backend health failed"
    }

    $assetUrls = $frontend.Content |
        Select-String -Pattern '/_next/static/[^"''<> ]+' -AllMatches |
        ForEach-Object { $_.Matches.Value.TrimEnd('\') } |
        Select-Object -Unique

    foreach ($assetUrl in $assetUrls) {
        $response = Invoke-WebRequest "$frontendUrl$assetUrl" -UseBasicParsing
        if ($response.StatusCode -ne 200) {
            throw "Asset $assetUrl returned status $($response.StatusCode)"
        }
    }

    return [pscustomobject]@{
        AssetCount = $assetUrls.Count
    }
}

try {
    $result = Test-Runtime
}
catch {
    if ($NoRestart) {
        throw
    }

    Write-Output "runtime=unhealthy action=restart reason=$($_.Exception.Message)"
    & (Join-Path $root "scripts\start-local.ps1") -FrontendPort $FrontendPort -BackendPort $BackendPort
    Start-Sleep -Seconds 2
    $result = Test-Runtime
}

Write-Output "frontend=$frontendUrl status=200"
Write-Output "backend=$backendUrl status=ok"
Write-Output "assets=$($result.AssetCount) status=200"
