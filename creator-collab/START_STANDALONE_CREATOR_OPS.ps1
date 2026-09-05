param([string]$Config = '',[switch]$NoBrowser)

$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
. (Join-Path $projectRoot 'scripts\runtime_config.ps1')
$runtimeConfig = Get-CreatorOpsRuntimeConfig -ProjectRoot $projectRoot -ConfigPath $Config
& (Join-Path $projectRoot 'START_CREATOR_OPS.ps1') `
  -Config $runtimeConfig.ConfigPath -NoBrowser:$NoBrowser

$pidPath = Join-Path $projectRoot 'data\creator_ops_supervisor.pid'
if (Test-Path -LiteralPath $pidPath) {
  $existingId = [int](Get-Content -LiteralPath $pidPath -Raw)
  if (Get-Process -Id $existingId -ErrorAction SilentlyContinue) {
    Write-Host "Creator Ops Supervisor läuft bereits (PID $existingId)." -ForegroundColor Green
    exit 0
  }
  Remove-Item -LiteralPath $pidPath -Force -ErrorAction SilentlyContinue
}

$supervisor = Join-Path $projectRoot 'scripts\creator_ops_supervisor.ps1'
$arguments = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$supervisor`" -Config `"$($runtimeConfig.ConfigPath)`""
Start-Process -FilePath 'powershell.exe' -ArgumentList $arguments `
  -WorkingDirectory $projectRoot -WindowStyle Hidden | Out-Null
for ($attempt=0; $attempt -lt 20; $attempt++) {
  if (Test-Path -LiteralPath $pidPath) {
    $supervisorId = [int](Get-Content -LiteralPath $pidPath -Raw)
    if (Get-Process -Id $supervisorId -ErrorAction SilentlyContinue) {
      Write-Host "Creator Ops Standalone läuft (Supervisor PID $supervisorId)." -ForegroundColor Green
      exit 0
    }
  }
  Start-Sleep -Milliseconds 250
}
throw 'Creator Ops Supervisor konnte nicht gestartet werden.'
