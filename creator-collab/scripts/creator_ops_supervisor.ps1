param(
  [string]$Config = '',
  [Nullable[int]]$PollSeconds = $null
)

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'runtime_config.ps1')
$runtimeConfig = Get-CreatorOpsRuntimeConfig -ProjectRoot $projectRoot -ConfigPath $Config
if ($null -eq $PollSeconds) { $PollSeconds = $runtimeConfig.SupervisorPollSeconds }
$logDirectory = Join-Path $projectRoot 'data\logs'
$logPath = Join-Path $logDirectory 'standalone_supervisor.log'
$pidPath = Join-Path $projectRoot 'data\creator_ops_supervisor.pid'
$watchdog = Join-Path $PSScriptRoot 'creator_ops_watchdog.ps1'
$scheduler = Join-Path $PSScriptRoot 'creator_ops_scheduler.ps1'
New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null

function Write-SupervisorLog([string]$Message) {
  Add-Content -LiteralPath $logPath -Value "$([DateTimeOffset]::Now.ToString('o')) $Message" -Encoding UTF8
}

function Invoke-BoundedChild([string]$Script,[string]$Label) {
  $arguments = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$Script`" -Config `"$($runtimeConfig.ConfigPath)`""
  $process = Start-Process -FilePath 'powershell.exe' -ArgumentList $arguments `
    -WindowStyle Hidden -Wait -PassThru
  Write-SupervisorLog "$Label exit=$($process.ExitCode)"
  return $process.ExitCode
}

$createdNew = $false
$mutex = [Threading.Mutex]::new($true, 'Local\CreatorOpsStandaloneSupervisor', [ref]$createdNew)
if (-not $createdNew) {
  Write-SupervisorLog 'second supervisor invocation ignored'
  exit 0
}

Set-Content -LiteralPath $pidPath -Value $PID -Encoding ascii
$lastWatchdog = [DateTimeOffset]::MinValue
$lastScheduler = [DateTimeOffset]::MinValue
Write-SupervisorLog 'supervisor started'
try {
  while ($true) {
    $now = [DateTimeOffset]::Now
    if (($now - $lastWatchdog).TotalMinutes -ge $runtimeConfig.WatchdogIntervalMinutes) {
      [void](Invoke-BoundedChild -Script $watchdog -Label 'watchdog')
      $lastWatchdog = $now
    }
    if (($now - $lastScheduler).TotalMinutes -ge $runtimeConfig.SchedulerIntervalMinutes) {
      [void](Invoke-BoundedChild -Script $scheduler -Label 'scheduler')
      $lastScheduler = $now
    }
    Start-Sleep -Seconds $PollSeconds
  }
} finally {
  Remove-Item -LiteralPath $pidPath -Force -ErrorAction SilentlyContinue
  $mutex.ReleaseMutex()
  $mutex.Dispose()
  Write-SupervisorLog 'supervisor stopped'
}
