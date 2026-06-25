param(
    [int]$FrontendPort = 3000,
    [int]$BackendPort = 8000
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

foreach ($port in @($FrontendPort, $BackendPort)) {
    Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
        ForEach-Object {
            Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
        }
}

Push-Location (Join-Path $root "frontend")
try {
    $previousNextDistDir = $env:NEXT_DIST_DIR
    $previousCleanNextDist = $env:CLEAN_NEXT_DIST
    $env:NEXT_DIST_DIR = ".next-runtime"
    $env:CLEAN_NEXT_DIST = "1"
    npm run build
}
finally {
    $env:NEXT_DIST_DIR = $previousNextDistDir
    $env:CLEAN_NEXT_DIST = $previousCleanNextDist
    Pop-Location
}

$frontendRoot = Join-Path $root "frontend"

Start-Process -FilePath "python" `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$BackendPort" `
    -WorkingDirectory (Join-Path $root "backend") `
    -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $root "backend\uvicorn.log") `
    -RedirectStandardError (Join-Path $root "backend\uvicorn.err.log")

Start-Process -FilePath "powershell.exe" `
    -ArgumentList "-NoProfile", "-Command", "`$env:NEXT_DIST_DIR='.next-runtime'; node node_modules/next/dist/bin/next start -H 127.0.0.1 -p $FrontendPort" `
    -WorkingDirectory $frontendRoot `
    -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $root "frontend\next.log") `
    -RedirectStandardError (Join-Path $root "frontend\next.err.log")

function Wait-HttpOk {
    param(
        [string]$Url,
        [int]$Attempts = 90
    )

    for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
        try {
            $response = Invoke-WebRequest $Url -UseBasicParsing
            if ($response.StatusCode -eq 200) {
                return $response.StatusCode
            }
        }
        catch {
            Start-Sleep -Seconds 1
        }
    }

    throw "Timed out waiting for $Url"
}

function Wait-BackendOk {
    param(
        [string]$Url,
        [int]$Attempts = 90
    )

    for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
        try {
            $health = Invoke-RestMethod $Url
            if ($health.status -eq "ok") {
                return $health.status
            }
        }
        catch {
            Start-Sleep -Seconds 1
        }
    }

    throw "Timed out waiting for $Url"
}

$frontendStatus = Wait-HttpOk "http://127.0.0.1:$FrontendPort"
$backendStatus = Wait-BackendOk "http://127.0.0.1:$BackendPort/api/health"

Write-Output "frontend=http://127.0.0.1:$FrontendPort status=$frontendStatus"
Write-Output "backend=http://127.0.0.1:$BackendPort status=$backendStatus"
