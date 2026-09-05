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

try {
  $health = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$Port/api/health" -TimeoutSec 5
  if ($health.StatusCode -eq 200) {
    Write-WatchdogLog 'health check ok'
    exit 0
  }
} catch {
  Write-WatchdogLog "health check failed: $($_.Exception.Message)"
}

$now = [DateTimeOffset]::Now
$attempts = @()
if (Test-Path -LiteralPath $statePath) {
  try {
    $state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
    $attempts = @($state.restart_attempts | ForEach-Object { [DateTimeOffset]::Parse($_) })
  } catch {
    Write-WatchdogLog 'invalid watchdog state ignored'
  }
}
$cutoff = $now.AddMinutes(-$WindowMinutes)
$attempts = @($attempts | Where-Object { $_ -gt $cutoff })
if ($attempts.Count -ge $MaximumRestarts) {
  Write-WatchdogLog "restart circuit open ($($attempts.Count)/$MaximumRestarts)"
  exit 2
}

Start-Sleep -Seconds $BackoffSeconds
$attempts += $now
@{ restart_attempts = @($attempts | ForEach-Object { $_.ToString('o') }) } |
  ConvertTo-Json | Set-Content -LiteralPath $statePath -Encoding UTF8

$starter = Join-Path $projectRoot 'START_CREATOR_OPS.ps1'
if (-not (Test-Path -LiteralPath $starter)) {
  Write-WatchdogLog 'START_CREATOR_OPS.ps1 missing'
  exit 3
}

try {
  & $starter -NoBrowser
  Write-WatchdogLog 'restart requested'
} catch {
  Write-WatchdogLog "restart failed: $($_.Exception.Message)"
  exit 4
}
