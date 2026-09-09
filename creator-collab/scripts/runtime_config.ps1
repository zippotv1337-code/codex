function ConvertFrom-CreatorOpsTomlValue([string]$Value) {
  $clean = $Value.Trim()
  if (($clean.StartsWith('"') -and $clean.EndsWith('"')) -or
      ($clean.StartsWith("'") -and $clean.EndsWith("'"))) {
    return $clean.Substring(1, $clean.Length - 2)
  }
  if ($clean -eq 'true') { return $true }
  if ($clean -eq 'false') { return $false }
  $number = 0
  if ([int]::TryParse($clean, [ref]$number)) { return $number }
  throw "Unsupported config.toml value: $Value"
}

function Read-CreatorOpsToml([string]$Path) {
  if (-not (Test-Path -LiteralPath $Path)) {
    throw "Creator Ops config not found: $Path"
  }
  $result = @{}
  $section = ''
  foreach ($sourceLine in Get-Content -LiteralPath $Path) {
    $line = ($sourceLine -replace '\s+#.*$', '').Trim()
    if (-not $line) { continue }
    if ($line -match '^\[([A-Za-z0-9_.-]+)\]$') {
      $section = $Matches[1]
      if (-not $result.ContainsKey($section)) { $result[$section] = @{} }
      continue
    }
    if (-not $section -or $line -notmatch '^([A-Za-z0-9_-]+)\s*=\s*(.+)$') {
      throw "Invalid config.toml line: $sourceLine"
    }
    $result[$section][$Matches[1]] = ConvertFrom-CreatorOpsTomlValue $Matches[2]
  }
  return $result
}

function Get-CreatorOpsRuntimeConfig([string]$ProjectRoot,[string]$ConfigPath = '') {
  if (-not $ConfigPath) { $ConfigPath = Join-Path $ProjectRoot 'config.toml' }
  elseif (-not [System.IO.Path]::IsPathRooted($ConfigPath)) { $ConfigPath = Join-Path $ProjectRoot $ConfigPath }
  $config = Read-CreatorOpsToml ([System.IO.Path]::GetFullPath($ConfigPath))
  return [pscustomobject]@{
    ConfigPath = [System.IO.Path]::GetFullPath($ConfigPath)
    Host = [string]$config.runtime.host
    Port = [int]$config.runtime.port
    Database = [string]$config.runtime.database
    OfflineOutput = [string]$config.runtime.offline_output
    HealthPath = [string]$config.runtime.health_path
    SchedulerIntervalMinutes = [int]$config.scheduler.interval_minutes
    MorningHour = [int]$config.scheduler.morning_hour
    MorningMinute = [int]$config.scheduler.morning_minute
    DispatchLive = [bool]$config.scheduler.dispatch_live
    WatchdogIntervalMinutes = [int]$config.watchdog.interval_minutes
    MaximumRestarts = [int]$config.watchdog.maximum_restarts
    WindowMinutes = [int]$config.watchdog.window_minutes
    BackoffSeconds = [int]$config.watchdog.backoff_seconds
    SupervisorPollSeconds = [int]$config.supervisor.poll_seconds
    PublishingLiveEnabled = [bool]$config.publishing.live_enabled
    PublishingAdapter = [string]$config.publishing.adapter
    OfficialInstagramPublish = [bool]$config.capabilities.official_instagram_publish
    LiveExternalActions = [bool]$config.capabilities.live_external_actions
  }
}

function Resolve-CreatorOpsPython([string]$ProjectRoot) {
  $candidates = @(
    (Join-Path $ProjectRoot 'runtime\python\python.exe'),
    (Join-Path $ProjectRoot '.venv\Scripts\python.exe'),
    (Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe')
  )
  $command = Get-Command python.exe -ErrorAction SilentlyContinue
  if ($command) { $candidates += $command.Source }
  foreach ($candidate in $candidates) {
    if (-not (Test-Path -LiteralPath $candidate)) { continue }
    try {
      # A present executable may be an incomplete venv. Check the capabilities
      # required at startup before choosing it over the bundled runtime.
      & $candidate -c "import tomllib, sqlite3; from zoneinfo import ZoneInfo; ZoneInfo('Europe/Berlin')" 2>$null
      if ($LASTEXITCODE -eq 0) { return $candidate }
    } catch { continue }
  }
  throw 'Keine vollständige Python-Laufzeit mit TOML, SQLite und Europe/Berlin-Zeitzonendaten gefunden.'
}
