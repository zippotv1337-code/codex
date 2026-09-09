param([switch]$Apply,[string]$Config = '')
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'runtime_config.ps1')
$runtimeConfig = Get-CreatorOpsRuntimeConfig -ProjectRoot $projectRoot -ConfigPath $Config
$python = Resolve-CreatorOpsPython -ProjectRoot $projectRoot
$plans = @(
  @{ Name='Creator Ops - Daily Healthcheck'; Script=(Join-Path $PSScriptRoot 'run_healthcheck.ps1'); At='02:45' },
  @{ Name='CreatorOps Weekly Recovery'; Script=(Join-Path $PSScriptRoot 'run_weekly_backup.ps1'); At='03:00' },
  @{ Name='CreatorOps Monthly Full Recovery'; Script=(Join-Path $PSScriptRoot 'run_monthly_full_backup.ps1'); At='03:30' }
)
# The existing per-user CreatorOpsStandalone.cmd owns supervisor startup.
# Do not install a second watchdog/scheduler alongside its existing single driver.
$startupFile = Join-Path ([Environment]::GetFolderPath('Startup')) 'CreatorOpsStandalone.cmd'
foreach ($plan in $plans) {
  if (-not (Test-Path -LiteralPath $plan.Script)) { throw 'Task entrypoint missing' }
  $plan.Arguments = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$($plan.Script)`" -Config `"$($runtimeConfig.ConfigPath)`""
}
if (-not $Apply) {
  $plans | ForEach-Object {
    [pscustomobject]@{ Task=$_.Name; Trigger="Daily $($_.At), period-guarded"; Command=$_.Arguments; Python=$python; Action='PREVIEW ONLY' }
  }
  return
}
# Refuse ambiguous parallel owners instead of silently deleting existing tasks.
$legacy = @('Creator Ops - Autostart','Creator Ops - Watchdog','Creator Ops - Scheduler') |
  ForEach-Object { Get-ScheduledTask -TaskName $_ -ErrorAction SilentlyContinue } |
  Where-Object { $_.State -ne 'Disabled' }
if ($legacy) { throw 'Legacy runtime tasks need explicit reconciliation before activation.' }
$registered = @()
try {
  $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
  $principal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
  foreach ($plan in $plans) {
    $action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $plan.Arguments -WorkingDirectory $projectRoot
    $trigger = New-ScheduledTaskTrigger -Daily -At $plan.At
    Register-ScheduledTask -TaskName $plan.Name -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description 'ZippoWorkz local-only maintenance; backup period guard; no platform actions' -Force | Out-Null
    $task = Get-ScheduledTask -TaskName $plan.Name
    if ($task.Actions.Arguments -ne $plan.Arguments) { throw 'Registered command differs from preview' }
    $registered += $plan.Name
    Write-Host "Registered and verified: $($plan.Name)"
  }
  $status = 'REGISTERED'
} catch {
  $status = 'NOT_FULLY_REGISTERED'
  Write-Warning 'Windows task registration failed. Existing supervisor remains the sole local driver; no elevated retry.'
} finally {
  @{ status=$status; checked_at=[DateTimeOffset]::Now.ToString('o'); registered=$registered; supervisor_driver='existing_per_user_autostart'; external_actions=$false } |
    ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $projectRoot 'data/runtime_tasks_status.json') -Encoding UTF8
}
if ($status -ne 'REGISTERED') { exit 1 }
