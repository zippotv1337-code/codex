param(
    [string]$BindAddress = '',
    [int]$Port = 4180,
    [string]$Database = 'data\review_dashboard.db',
    [switch]$ConfigureFirewall
)

$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$runtimeDir = Join-Path $projectRoot 'data'
$logDir = Join-Path $runtimeDir 'logs'
$logPath = Join-Path $logDir 'lan_server.log'
$errorPath = Join-Path $logDir 'lan_server.error.log'
$pidPath = Join-Path $runtimeDir 'creator_ops.pid'
New-Item -ItemType Directory -Force -Path $runtimeDir,$logDir | Out-Null

function Resolve-LanAddress {
    $text = ipconfig | Out-String
    $matches = [regex]::Matches($text, 'IPv4[^:]*:\s*(192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})')
    if ($matches.Count -eq 0) { throw 'Keine aktive private IPv4-Adresse gefunden.' }
    return $matches[0].Groups[1].Value
}

function Resolve-CreatorOpsPython {
    $bundled = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    if (Test-Path -LiteralPath $bundled) { return $bundled }
    $command = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    throw 'Python wurde nicht gefunden.'
}

if (-not $BindAddress) { $BindAddress = Resolve-LanAddress }
$localAddresses = ipconfig | Out-String
if ($localAddresses -notmatch [regex]::Escape($BindAddress)) {
    throw "$BindAddress ist keine aktuelle Adresse dieses PCs. Erkannt wurde: $(Resolve-LanAddress)"
}

$listener = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1
if ($listener) { throw "Port $Port ist bereits durch Prozess $($listener.OwningProcess) belegt." }

if ($ConfigureFirewall) {
    $identity = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    if (-not $identity.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'Für -ConfigureFirewall PowerShell einmal als Administrator starten.'
    }
    $ruleName = "Creator Ops LAN TCP $Port"
    if (-not (Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue)) {
        New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow `
            -Protocol TCP -LocalPort $Port -Profile Private -RemoteAddress LocalSubnet | Out-Null
    }
}

if (-not $env:CREATOR_OPS_PASSWORD) {
    $secure = Read-Host 'Temporäres Creator-Ops-Passwort (mindestens 12 Zeichen)' -AsSecureString
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try { $env:CREATOR_OPS_PASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer) }
}
if ([string]::IsNullOrWhiteSpace($env:CREATOR_OPS_PASSWORD) -or $env:CREATOR_OPS_PASSWORD.Length -lt 12) {
    $env:CREATOR_OPS_PASSWORD = $null
    throw 'Das Sitzungspasswort muss mindestens 12 Zeichen lang sein.'
}

$python = Resolve-CreatorOpsPython
$databasePath = if ([IO.Path]::IsPathRooted($Database)) { $Database } else { Join-Path $projectRoot $Database }
$lanUrl = "http://$BindAddress`:$Port"
try {
    $process = Start-Process -FilePath $python `
        -ArgumentList @('-m','creator_ops.web','--db',('"{0}"' -f $databasePath),'--host',$BindAddress,'--port',"$Port") `
        -WorkingDirectory $projectRoot -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput $logPath -RedirectStandardError $errorPath
    Set-Content -LiteralPath $pidPath -Value $process.Id -Encoding ascii
    $healthy = $false
    for ($attempt=0; $attempt -lt 40; $attempt++) {
        if ($process.HasExited) { break }
        try {
            $health = Invoke-RestMethod -Uri "$lanUrl/api/health" -TimeoutSec 2
            if ($health.status -eq 'ok' -and $health.auth) { $healthy=$true; break }
        } catch {}
        Start-Sleep -Milliseconds 250
    }
    if (-not $healthy) {
        Remove-Item -LiteralPath $pidPath -Force -ErrorAction SilentlyContinue
        throw "LAN-Server konnte nicht gestartet werden. Siehe $errorPath"
    }
    Write-Host "Creator Ops ist im Heimnetz erreichbar: $lanUrl" -ForegroundColor Green
    Write-Host 'Handy und PC müssen im gleichen WLAN sein. In Safari diese URL öffnen.'
    if (-not $ConfigureFirewall) {
        Write-Warning 'Falls Safari nicht verbindet: Skript einmal als Administrator mit -ConfigureFirewall starten.'
    }
} finally {
    $env:CREATOR_OPS_PASSWORD = $null
}
