param([switch]$Apply)

$ErrorActionPreference = 'Stop'
$taskNames = @(
  'Creator Ops - Autostart',
  'Creator Ops - Watchdog',
  'Creator Ops - Scheduler',
  'Creator Ops - Daily Healthcheck',
  'CreatorOps Weekly Recovery',
  'CreatorOps Monthly Full Recovery'
)

if (-not $Apply) {
  $taskNames | ForEach-Object {
    [pscustomobject]@{ Task=$_; Action='PREVIEW ONLY - rerun with -Apply to remove' }
  }
  return
}

foreach ($taskName in $taskNames) {
  $existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
  if ($null -ne $existing) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host "Removed: $taskName"
  } else {
    Write-Host "Not installed: $taskName"
  }
}
$startupFile = Join-Path ([Environment]::GetFolderPath('Startup')) 'CreatorOpsStandalone.cmd'
if (Test-Path -LiteralPath $startupFile) {
  Remove-Item -LiteralPath $startupFile -Force
  Write-Host "Removed: per-user Creator Ops autostart fallback ($startupFile)"
}
