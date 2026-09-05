param(
    [Nullable[int]]$Port = $null,
    [string]$Database = '',
    [string]$Config = '',
    [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
. (Join-Path $projectRoot 'scripts\runtime_config.ps1')
$runtimeConfig = Get-CreatorOpsRuntimeConfig -ProjectRoot $projectRoot -ConfigPath $Config
if ($null -eq $Port) { $Port = $runtimeConfig.Port }
if (-not $Database) { $Database = $runtimeConfig.Database }
$runtimeDir = Join-Path $projectRoot 'data'
$logDir = Join-Path $runtimeDir 'logs'
$logPath = Join-Path $logDir 'local_server.log'
$errorPath = Join-Path $logDir 'local_server.error.log'
$pidPath = Join-Path $runtimeDir 'creator_ops.pid'
$url = "http://127.0.0.1:$Port"
$healthUrl = "$url/api/health"

function Test-CreatorOpsHealth {
    try {
        $result = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 2
        return $result.status -eq 'ok'
    } catch { return $false }
}

New-Item -ItemType Directory -Force -Path $runtimeDir,$logDir | Out-Null

if (Test-CreatorOpsHealth) {
    Write-Host "Creator Ops läuft bereits: $url" -ForegroundColor Green
    if (-not $NoBrowser) { Start-Process $url }
    exit 0
}

$listener = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1
if ($listener) {
    throw "Port $Port ist durch Prozess $($listener.OwningProcess) belegt, aber Creator Ops antwortet dort nicht."
}

$python = Resolve-CreatorOpsPython -ProjectRoot $projectRoot
$databasePath = if ([IO.Path]::IsPathRooted($Database)) { $Database } else { Join-Path $projectRoot $Database }

Push-Location $projectRoot
try {
    & $python -c "import sys; assert sys.version_info >= (3,10)" 2>$null
    if ($LASTEXITCODE -ne 0) { throw 'Creator Ops benötigt Python 3.10 oder neuer.' }

    $process = Start-Process -FilePath $python `
        -ArgumentList @('-m','creator_ops.web','--db',('"{0}"' -f $databasePath),'--host','127.0.0.1','--port',"$Port") `
        -WorkingDirectory $projectRoot -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput $logPath -RedirectStandardError $errorPath
    Set-Content -LiteralPath $pidPath -Value $process.Id -Encoding ascii

    $healthy = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        if ($process.HasExited) { break }
        if (Test-CreatorOpsHealth) { $healthy = $true; break }
        Start-Sleep -Milliseconds 250
    }
    if (-not $healthy) {
        Remove-Item -LiteralPath $pidPath -Force -ErrorAction SilentlyContinue
        $detail = Get-Content -LiteralPath $errorPath -Raw -ErrorAction SilentlyContinue
        throw "Creator Ops konnte nicht gesund starten. Details: $detail"
    }
    Write-Host "Creator Ops läuft: $url" -ForegroundColor Green
    Write-Host "Log: $logPath" -ForegroundColor DarkGray
    if (-not $NoBrowser) { Start-Process $url }
} finally {
    Pop-Location
}
