param([switch]$Apply,[string]$Config = '')

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'runtime_config.ps1')
$runtimeConfig = Get-CreatorOpsRuntimeConfig -ProjectRoot $projectRoot -ConfigPath $Config
$starter = Join-Path $projectRoot 'START_CREATOR_OPS.ps1'
$watchdog = Join-Path $PSScriptRoot 'creator_ops_watchdog.ps1'
$scheduler = Join-Path $PSScriptRoot 'creator_ops_scheduler.ps1'
$standalone = Join-Path $projectRoot 'START_STANDALONE_CREATOR_OPS.ps1'
$startupDirectory = [Environment]::GetFolderPath('Startup')
$startupFile = Join-Path $startupDirectory 'CreatorOpsStandalone.cmd'
$plans = @(
  @{ Name='Creator Ops - Autostart'; Script=$starter; Trigger='AtLogOn' },
  @{ Name='Creator Ops - Watchdog'; Script=$watchdog; Trigger="Every$($runtimeConfig.WatchdogIntervalMinutes)Minutes" },
  @{ Name='Creator Ops - Scheduler'; Script=$scheduler; Trigger="Every$($runtimeConfig.SchedulerIntervalMinutes)Minutes" }
)

if (-not $Apply) {
  $plans | ForEach-Object {
    [pscustomobject]@{
      Task=$_.Name
      Trigger=$_.Trigger
      Script=$_.Script
      Action='PREVIEW ONLY - rerun with -Apply after owner review'
    }
  }
  return
}

try {
  $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew `
    -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 2) -ErrorAction Stop
  foreach ($plan in $plans) {
    $arguments = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$($plan.Script)`""
    if ($plan.Name -eq 'Creator Ops - Autostart') { $arguments += ' -NoBrowser' }
    $action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arguments -ErrorAction Stop
    if ($plan.Trigger -eq 'AtLogOn') {
      $trigger = New-ScheduledTaskTrigger -AtLogOn -ErrorAction Stop
    } else {
      $minutes = if ($plan.Name -eq 'Creator Ops - Watchdog') { $runtimeConfig.WatchdogIntervalMinutes } else { $runtimeConfig.SchedulerIntervalMinutes }
      $trigger = New-ScheduledTaskTrigger -Once -At ([DateTime]::Now.AddMinutes(1)) `
        -RepetitionInterval (New-TimeSpan -Minutes $minutes) `
        -RepetitionDuration (New-TimeSpan -Days 3650) -ErrorAction Stop
    }
    Register-ScheduledTask -TaskName $plan.Name -Action $action -Trigger $trigger `
      -Settings $settings -Description 'Creator Ops local fail-closed runtime' -Force `
      -ErrorAction Stop | Out-Null
    Write-Host "Registered: $($plan.Name)"
  }
} catch {
  $accessDenied = $_.Exception -is [System.UnauthorizedAccessException] -or
    $_.Exception.Message -match 'Zugriff verweigert|Access is denied'
  if (-not $accessDenied) { throw }
  $command = "@echo off`r`nstart `"`" powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$standalone`" -Config `"$($runtimeConfig.ConfigPath)`" -NoBrowser`r`n"
  Set-Content -LiteralPath $startupFile -Value $command -Encoding ascii
  Write-Host 'Scheduled Tasks benötigen Administratorrechte.' -ForegroundColor Yellow
  Write-Host "Installiert: sicherer Autostart-Fallback für den aktuellen Windows-Benutzer ($startupFile)." -ForegroundColor Green
}
