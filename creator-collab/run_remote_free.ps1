param(
    [string]$Database = 'data/review_dashboard.db',
    [int]$Port = 4180,
    [string]$Cloudflared = 'cloudflared',
    [string]$NotificationScript = ''
)

$ErrorActionPreference = 'Stop'

function Resolve-Python {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    $bundledPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    if ($pythonCommand) { return $pythonCommand.Source }
    if (Test-Path -LiteralPath $bundledPython) { return $bundledPython }
    throw 'Python 3.12 oder die gebündelte Codex-Python-Laufzeit wurde nicht gefunden.'
}

function Resolve-Cloudflared([string]$Requested) {
    $command = Get-Command $Requested -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    $local = Join-Path $PSScriptRoot 'tools\cloudflared.exe'
    if (Test-Path -LiteralPath $local) { return $local }
    throw 'cloudflared fehlt. Installiere es kostenlos oder lege cloudflared.exe unter creator-collab\tools\ ab.'
}

$pythonExecutable = Resolve-Python
$cloudflaredExecutable = Resolve-Cloudflared $Cloudflared

Push-Location $PSScriptRoot
try {
    $runtimeDirectory = Join-Path $PSScriptRoot 'data'
    $logDirectory = Join-Path $runtimeDirectory 'logs'
    $remoteStatePath = Join-Path $runtimeDirectory 'REMOTE_ACCESS_CURRENT.txt'
    New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
    Remove-Item -LiteralPath $remoteStatePath -Force -ErrorAction SilentlyContinue

    if (-not $env:CREATOR_OPS_PASSWORD) {
        $secure = Read-Host 'Creator-Ops-Passwort für diesen Lauf' -AsSecureString
        $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
        try {
            $env:CREATOR_OPS_PASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
        }
        finally {
            [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
        }
    }

    if (
        [string]::IsNullOrWhiteSpace($env:CREATOR_OPS_PASSWORD) -or
        $env:CREATOR_OPS_PASSWORD.Length -lt 12
    ) {
        throw 'Bitte ein Passwort mit mindestens 12 Zeichen verwenden.'
    }

    $dashboardOutput = Join-Path $logDirectory 'dashboard.out.log'
    $dashboardError = Join-Path $logDirectory 'dashboard.err.log'
    $tunnelOutput = Join-Path $logDirectory 'cloudflared.out.log'
    $tunnelError = Join-Path $logDirectory 'cloudflared.err.log'
    foreach ($logPath in @($dashboardOutput, $dashboardError, $tunnelOutput, $tunnelError)) {
        Set-Content -LiteralPath $logPath -Value '' -Encoding UTF8
    }

    $dashboard = Start-Process -FilePath $pythonExecutable `
        -ArgumentList @(
            '-m', 'creator_ops.web', '--db', $Database,
            '--host', '127.0.0.1', '--port', "$Port"
        ) `
        -WorkingDirectory $PSScriptRoot -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput $dashboardOutput -RedirectStandardError $dashboardError

    Start-Sleep -Seconds 2
    if ($dashboard.HasExited) {
        throw "Creator Ops konnte nicht gestartet werden. Ist Port $Port bereits belegt?"
    }

    Write-Host ''
    Write-Host 'Creator Ops läuft lokal mit Passwortschutz.' -ForegroundColor Green
    Write-Host "Lokal: http://127.0.0.1:$Port" -ForegroundColor DarkGray
    Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/health" -TimeoutSec 5 | Out-Null

    Write-Host 'Quick Tunnel startet. Die Adresse wird automatisch erkannt und kopiert.' -ForegroundColor Cyan
    Write-Host 'Die URL ändert sich bei jedem Neustart.' -ForegroundColor DarkGray
    Write-Host ''

    try {
        $tunnel = Start-Process -FilePath $cloudflaredExecutable `
            -ArgumentList @('tunnel', '--url', "http://127.0.0.1:$Port", '--no-autoupdate') `
            -WorkingDirectory $PSScriptRoot -PassThru -WindowStyle Hidden `
            -RedirectStandardOutput $tunnelOutput -RedirectStandardError $tunnelError

        $publicUrl = $null
        for ($attempt = 0; $attempt -lt 60; $attempt++) {
            if ($tunnel.HasExited) { break }
            $combinedLog = @(
                Get-Content -LiteralPath $tunnelOutput -Raw -ErrorAction SilentlyContinue
                Get-Content -LiteralPath $tunnelError -Raw -ErrorAction SilentlyContinue
            ) -join "`n"
            $match = [regex]::Match($combinedLog, 'https://[a-z0-9-]+\.trycloudflare\.com')
            if ($match.Success) {
                $publicUrl = $match.Value
                break
            }
            Start-Sleep -Milliseconds 500
        }

        if (-not $publicUrl) {
            throw "Keine Tunnel-URL erkannt. Details: $tunnelError"
        }

        $startedAt = [DateTimeOffset]::Now.ToString('o')
        @("URL=$publicUrl", "STARTED_AT=$startedAt") |
            Set-Content -LiteralPath $remoteStatePath -Encoding UTF8
        try { Set-Clipboard -Value $publicUrl } catch { Write-Warning 'URL konnte nicht in die Zwischenablage kopiert werden.' }

        $remoteHealth = Invoke-RestMethod -Uri "$publicUrl/api/health" -TimeoutSec 15
        if ($remoteHealth.status -ne 'ok' -or -not $remoteHealth.auth) {
            throw 'Remote-Healthcheck meldet keinen passwortgeschützten, gesunden Dienst.'
        }

        Write-Host "Remote: $publicUrl" -ForegroundColor Green
        Write-Host 'Die URL liegt in der Zwischenablage. Dieses Fenster offen lassen.' -ForegroundColor DarkGray

        if ($NotificationScript) {
            try {
                if (-not (Test-Path -LiteralPath $NotificationScript)) {
                    throw 'NotificationScript wurde nicht gefunden.'
                }
                & $NotificationScript -Url $publicUrl -StartedAt $startedAt
            }
            catch {
                Write-Warning "Optionale Benachrichtigung fehlgeschlagen: $($_.Exception.Message)"
            }
        }

        Wait-Process -Id $tunnel.Id
    }
    finally {
        Remove-Item -LiteralPath $remoteStatePath -Force -ErrorAction SilentlyContinue
        if ($tunnel -and -not $tunnel.HasExited) {
            Stop-Process -Id $tunnel.Id -Force
        }
        if (-not $dashboard.HasExited) {
            Stop-Process -Id $dashboard.Id -Force
        }
    }
}
finally {
    $env:CREATOR_OPS_PASSWORD = $null
    Pop-Location
}
