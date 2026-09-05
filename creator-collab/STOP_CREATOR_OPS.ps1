$ErrorActionPreference = 'Stop'
$pidPath = Join-Path $PSScriptRoot 'data\creator_ops.pid'
if (-not (Test-Path -LiteralPath $pidPath)) {
    Write-Host 'Kein verwalteter Creator-Ops-Prozess gefunden.'
    exit 0
}
$processId = [int](Get-Content -LiteralPath $pidPath -Raw)
$process = Get-Process -Id $processId -ErrorAction SilentlyContinue
if ($process) {
    $details = Get-CimInstance Win32_Process -Filter "ProcessId=$processId"
    if (-not $details -or $details.CommandLine -notmatch 'creator_ops\.web' -or $details.CommandLine -notmatch 'review_dashboard\.db') {
        throw "PID $processId gehört nicht zum verwalteten Creator-Ops-Server. Abbruch ohne Prozessänderung."
    }
    $process.Kill()
    if (-not $process.WaitForExit(5000)) {
        throw "Creator Ops PID $processId konnte nicht innerhalb von 5 Sekunden beendet werden."
    }
}
Remove-Item -LiteralPath $pidPath -Force
Write-Host 'Creator Ops wurde beendet.' -ForegroundColor Green
