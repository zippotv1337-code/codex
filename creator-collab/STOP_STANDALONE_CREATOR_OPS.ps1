$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$pidPath = Join-Path $projectRoot 'data\creator_ops_supervisor.pid'
if (Test-Path -LiteralPath $pidPath) {
  $supervisorId = [int](Get-Content -LiteralPath $pidPath -Raw)
  $process = Get-Process -Id $supervisorId -ErrorAction SilentlyContinue
  if ($process) {
    $details = Get-CimInstance Win32_Process -Filter "ProcessId=$supervisorId"
    if (-not $details -or $details.CommandLine -notmatch 'creator_ops_supervisor\.ps1') {
      throw "PID $supervisorId gehört nicht zum Creator-Ops-Supervisor."
    }
    $process.Kill()
    [void]$process.WaitForExit(5000)
  }
  Remove-Item -LiteralPath $pidPath -Force -ErrorAction SilentlyContinue
}
& (Join-Path $projectRoot 'STOP_CREATOR_OPS.ps1')
