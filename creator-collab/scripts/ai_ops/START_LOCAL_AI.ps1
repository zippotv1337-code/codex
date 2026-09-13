param(
    [string]$Root = 'C:\Zippoworkz',
    [string]$Model = 'qwen3:8b',
    [ValidateSet('Start','Pause','Resume','Stop','Status')][string]$Action = 'Start'
)
$ErrorActionPreference = 'Stop'
$project = Join-Path $Root 'Workspace\codex_ingest\creator-collab'
if (-not (Test-Path -LiteralPath (Join-Path $project 'creator_ops\local_ai_runtime.py'))) {
    throw 'Vorhandener ZippoWorkz-Workspace fehlt. Kein Download, kein Ersatzprojekt.'
}
. (Join-Path $project 'scripts\runtime_config.ps1')
$python = Resolve-CreatorOpsPython -ProjectRoot $project
Push-Location $project
try {
    if ($Action -in @('Pause','Resume','Stop')) {
        & $python -m creator_ops.local_ai_runtime --root $Root --command $Action.ToLower()
        if ($LASTEXITCODE -ne 0) { throw 'Lokaler Steuerbefehl fehlgeschlagen.' }
        if ($Action -ne 'Resume') { return }
    }
    if ($Action -eq 'Status') {
        $config = Get-CreatorOpsRuntimeConfig -ProjectRoot $project
        Invoke-RestMethod -Uri "http://$($config.Host):$($config.Port)/api/health" -TimeoutSec 3 |
            Select-Object status,database,auth
        return
    }
    # Existing server, canonical DB and password handling. No second dashboard.
    & (Join-Path $project 'START_CREATOR_OPS.ps1') -NoBrowser
    if ($LASTEXITCODE -ne 0) { throw 'Dashboard-Start fehlgeschlagen.' }
    # Existing lease checked before spawn; process log is append-only.
    & $python -m creator_ops.local_ai_runtime --root $Root --model $Model --launch
    if ($LASTEXITCODE -ne 0) { throw 'Local AI konnte nicht gestartet werden.' }
    Write-Host 'ZippoWorkz AI Ops gestartet. Begrenzter Lauf, Pause bei aktiver Bedienung.'
    Write-Host 'Dashboard: http://192.168.188.131:4180/ai-ops'
} finally { Pop-Location }
