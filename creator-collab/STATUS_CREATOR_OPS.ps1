param([Nullable[int]]$Port = $null,[string]$Config = '')
$projectRoot = $PSScriptRoot
. (Join-Path $projectRoot 'scripts\runtime_config.ps1')
$runtimeConfig = Get-CreatorOpsRuntimeConfig -ProjectRoot $projectRoot -ConfigPath $Config
if ($null -eq $Port) { $Port = $runtimeConfig.Port }
$url = "http://127.0.0.1:$Port"
try {
    $health = Invoke-RestMethod -Uri "$url/api/health" -TimeoutSec 2
    [pscustomobject]@{Status='Läuft'; URL=$url; Mode=$health.mode; Passwortschutz=$health.auth} | Format-List
    exit 0
} catch {
    Write-Host "Creator Ops ist auf Port $Port nicht erreichbar." -ForegroundColor Yellow
    exit 1
}
