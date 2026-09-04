param(
    [string]$Database = 'data/review_dashboard.db',
    [int]$Port = 4180,
    [string]$Cloudflared = 'cloudflared'
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

    $dashboard = Start-Process -FilePath $pythonExecutable `
        -ArgumentList @(
            '-m', 'creator_ops.web', '--db', $Database,
            '--host', '127.0.0.1', '--port', "$Port"
        ) `
        -WorkingDirectory $PSScriptRoot -PassThru -WindowStyle Hidden

    Start-Sleep -Seconds 2
    if ($dashboard.HasExited) {
        throw "Creator Ops konnte nicht gestartet werden. Ist Port $Port bereits belegt?"
    }

    Write-Host ''
    Write-Host 'Creator Ops läuft lokal mit Passwortschutz.' -ForegroundColor Green
    Write-Host "Lokal: http://127.0.0.1:$Port" -ForegroundColor DarkGray
    Write-Host 'Quick Tunnel startet. Die ausgegebene trycloudflare.com-Adresse im Arbeitsbrowser öffnen.' -ForegroundColor Cyan
    Write-Host 'Die URL ändert sich bei jedem Neustart.' -ForegroundColor DarkGray
    Write-Host ''

    try {
        & $cloudflaredExecutable tunnel --url "http://127.0.0.1:$Port"
    }
    finally {
        if (-not $dashboard.HasExited) {
            Stop-Process -Id $dashboard.Id -Force
        }
    }
}
finally {
    $env:CREATOR_OPS_PASSWORD = $null
    Pop-Location
}
