param(
  [Nullable[int]]$Port = $null,
  [Nullable[int]]$MaximumRestarts = $null,
  [Nullable[int]]$WindowMinutes = $null,
  [Nullable[int]]$BackoffSeconds = $null,
  [string]$Config = ''
)

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'runtime_config.ps1')
$runtimeConfig = Get-CreatorOpsRuntimeConfig -ProjectRoot $projectRoot -ConfigPath $Config
if ($null -eq $Port) { $Port = $runtimeConfig.Port }
if ($null -eq $MaximumRestarts) { $MaximumRestarts = $runtimeConfig.MaximumRestarts }
if ($null -eq $WindowMinutes) { $WindowMinutes = $runtimeConfig.WindowMinutes }
if ($null -eq $BackoffSeconds) { $BackoffSeconds = $runtimeConfig.BackoffSeconds }
$statePath = Join-Path $projectRoot 'data\watchdog_state.json'
$logDirectory = Join-Path $projectRoot 'data\logs'
$logPath = Join-Path $logDirectory 'standalone_watchdog.log'
New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null

function Write-WatchdogLog([string]$Message) {
  Add-Content -LiteralPath $logPath -Value "$([DateTimeOffset]::Now.ToString('o')) $Message" -Encoding UTF8
}

# Refuse concurrent invocations; crash releases this OS mutex automatically.
$watchdogMutex = [Threading.Mutex]::new($false, 'Local\CreatorOpsWatchdog')
try { $ownsWatchdog = $watchdogMutex.WaitOne(0) } catch [Threading.AbandonedMutexException] { $ownsWatchdog = $true }
if (-not $ownsWatchdog) { $watchdogMutex.Dispose(); exit 0 }
try {
if ($MaximumRestarts -lt 1 -or $WindowMinutes -lt 1 -or $BackoffSeconds -lt 1) {
  throw 'Unsafe watchdog bounds'
}
$attempts = @()
if (Test-Path -LiteralPath $statePath) {
  try {
    $state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
    $attempts = @($state.restart_attempts | ForEach-Object { [DateTimeOffset]::Parse($_) })
  } catch { Write-WatchdogLog 'invalid watchdog state: fail closed'; exit 2 }
}
function Save-WatchdogState([string]$Status) {
  @{ restart_attempts=@($attempts | ForEach-Object { $_.ToString('o') }); status=$Status; checked_at=[DateTimeOffset]::Now.ToString('o') } |
    ConvertTo-Json | Set-Content -LiteralPath "$statePath.tmp" -Encoding UTF8
  Move-Item -LiteralPath "$statePath.tmp" -Destination $statePath -Force
}
$controlPath = Join-Path $projectRoot 'data/autopilot_control.json'
if (Test-Path -LiteralPath $controlPath) {
  if ((Get-Content -LiteralPath $controlPath -Raw | ConvertFrom-Json).status -eq 'PAUSED') {
    Save-WatchdogState 'PAUSED'; exit 0
  }
}
$healthHost = $runtimeConfig.Host
if ($healthHost -in @('0.0.0.0','::','localhost')) { $healthHost = '127.0.0.1' }
$healthUri = "http://${healthHost}:$Port/api/health"

try {
  $health = Invoke-WebRequest -UseBasicParsing -Uri $healthUri -TimeoutSec 5 -MaximumRedirection 0
  if ($health.StatusCode -eq 200 -and ($health.Content | ConvertFrom-Json).status -eq 'ok') {
    Write-WatchdogLog 'health check ok'
    Save-WatchdogState 'HEALTHY'
    exit 0
  }
} catch {
  Write-WatchdogLog "health check failed: $($_.Exception.Message)"
}

$now = [DateTimeOffset]::Now
$cutoff = $now.AddMinutes(-$WindowMinutes)
$attempts = @($attempts | Where-Object { $_ -gt $cutoff })
if ($attempts.Count -ge $MaximumRestarts) {
  Write-WatchdogLog "restart circuit open ($($attempts.Count)/$MaximumRestarts)"
  Save-WatchdogState 'CIRCUIT_OPEN'
  exit 2
}

Start-Sleep -Seconds $BackoffSeconds
$attempts += $now
Save-WatchdogState 'RESTART_REQUESTED'

$starter = Join-Path $projectRoot 'START_CREATOR_OPS.ps1'
if (-not (Test-Path -LiteralPath $starter)) {
  Write-WatchdogLog 'START_CREATOR_OPS.ps1 missing'
  exit 3
}

try {
  & $starter -NoBrowser -Config $runtimeConfig.ConfigPath
  Write-WatchdogLog 'restart requested'
} catch {
  Write-WatchdogLog "restart failed: $($_.Exception.Message)"
  exit 4
}
} finally { $watchdogMutex.ReleaseMutex(); $watchdogMutex.Dispose() }
