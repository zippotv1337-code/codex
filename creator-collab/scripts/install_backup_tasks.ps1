param([switch]$Apply)
$ErrorActionPreference = 'Stop'
$weekly = Join-Path $PSScriptRoot 'run_weekly_backup.ps1'
$monthly = Join-Path $PSScriptRoot 'run_monthly_full_backup.ps1'
$plans = @(
  @{ Name='CreatorOps Weekly Recovery'; Script=$weekly; At='03:00' },
  @{ Name='CreatorOps Monthly Full Recovery'; Script=$monthly; At='03:30' }
)
if (-not $Apply) {
  $plans | ForEach-Object { [pscustomobject]@{Task=$_.Name; Time=$_.At; Script=$_.Script; Action='DRY RUN — rerun with -Apply'} }
  return
}
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew
foreach ($plan in $plans) {
  $action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$($plan.Script)`""
  $trigger = New-ScheduledTaskTrigger -Daily -At $plan.At
  Register-ScheduledTask -TaskName $plan.Name -Action $action -Trigger $trigger -Settings $settings -Description 'Creator Ops local secret-free recovery backup' -Force | Out-Null
  Write-Host "Registered: $($plan.Name)"
}
