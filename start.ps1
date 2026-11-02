# Start the local application without depending on two open terminal windows.
[CmdletBinding()]
param([ValidateRange(10, 600)][int]$StartupTimeoutSeconds = 180)

$ErrorActionPreference = 'Stop'
$repoRoot = $PSScriptRoot
$logDirectory = Join-Path $repoRoot 'output/logs'

function Test-ApiReady([string]$Url) {
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
        $body = $response.Content | ConvertFrom-Json
        return ($response.StatusCode -eq 200 -and $body.service -eq 'Patent Intelligence API' -and $body.status -eq 'ok')
    } catch { return $false }
}

function Test-FrontendReady {
    try {
        $response = Invoke-WebRequest -Uri 'http://localhost:5173/' -UseBasicParsing -TimeoutSec 2
        return ($response.StatusCode -eq 200 -and $response.Content -match '/@vite/client')
    } catch { return $false }
}

function Wait-ForService([string]$Name, [scriptblock]$Check, $StartedProcess, [string]$ErrorLog) {
    $deadline = (Get-Date).AddSeconds($StartupTimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (& $Check) { return }
        if ($null -ne $StartedProcess) {
            $StartedProcess.Refresh()
            if ($StartedProcess.HasExited) {
                throw "$Name exited with code $($StartedProcess.ExitCode). Check $ErrorLog"
            }
        }
        Start-Sleep -Milliseconds 500
    }
    throw "$Name did not become ready within $StartupTimeoutSeconds seconds. Check $ErrorLog"
}

New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
$apiHealth = 'http://127.0.0.1:8000/api/health'
if (Test-ApiReady $apiHealth) {
    Write-Host 'Backend is already running.'
} else {
    $listener = Get-NetTCPConnection -State Listen -LocalPort 8000 -ErrorAction SilentlyContinue
    $apiProcess = $null
    $apiErrorLog = Join-Path $logDirectory 'backend.stderr.log'
    if ($listener) {
        Write-Host 'Port 8000 is in use; waiting for the existing backend to become ready...'
    } else {
        $python = Join-Path $repoRoot 'venv/Scripts/python.exe'
        if (-not (Test-Path -LiteralPath $python)) {
            throw 'Project Python environment is missing. Follow the README setup instructions first.'
        }
        # A single Uvicorn process avoids the development reloader's extra
        # process. Logs and the server survive this launcher returning.
        $apiProcess = Start-Process -FilePath $python -ArgumentList @('-u', '-m', 'uvicorn', 'api.main:app', '--host', '127.0.0.1', '--port', '8000') -WorkingDirectory (Join-Path $repoRoot 'backend') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logDirectory 'backend.stdout.log') -RedirectStandardError $apiErrorLog -PassThru
        Write-Host "Starting backend (PID $($apiProcess.Id)); waiting for model loading..."
    }
    Wait-ForService 'Backend' { Test-ApiReady $apiHealth } $apiProcess $apiErrorLog
}

if (Test-FrontendReady) {
    Write-Host 'Frontend is already running.'
} else {
    if (Get-NetTCPConnection -State Listen -LocalPort 5173 -ErrorAction SilentlyContinue) {
        throw 'Port 5173 is occupied by a different service. Stop that service or use the manual README commands.'
    }
    $vite = Join-Path $repoRoot 'frontend/node_modules/vite/bin/vite.js'
    if (-not (Test-Path -LiteralPath $vite)) {
        throw 'Frontend dependencies are missing. Run npm install in frontend first.'
    }
    $node = (Get-Command node.exe -ErrorAction Stop).Source
    $frontendErrorLog = Join-Path $logDirectory 'frontend.stderr.log'
    $frontendProcess = Start-Process -FilePath $node -ArgumentList @(('"' + $vite + '"'), '--host', 'localhost', '--port', '5173', '--strictPort') -WorkingDirectory (Join-Path $repoRoot 'frontend') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logDirectory 'frontend.stdout.log') -RedirectStandardError $frontendErrorLog -PassThru
    Write-Host "Starting frontend (PID $($frontendProcess.Id))..."
    Wait-ForService 'Frontend' { Test-FrontendReady } $frontendProcess $frontendErrorLog
}

if (-not (Test-ApiReady 'http://localhost:5173/api/health')) {
    throw "The backend is healthy but the frontend API proxy is failing. Check the frontend logs in $logDirectory"
}
Write-Host 'Ready: http://localhost:5173'
Write-Host "Servers run in the background. Logs: $logDirectory"
