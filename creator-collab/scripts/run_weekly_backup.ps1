param([string]$Destination, [string]$Config = '')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'runtime_config.ps1')
$runtimeConfig = Get-CreatorOpsRuntimeConfig -ProjectRoot $projectRoot -ConfigPath $Config
$database = if ([IO.Path]::IsPathRooted($runtimeConfig.Database)) { $runtimeConfig.Database } else { Join-Path $projectRoot $runtimeConfig.Database }
if (-not $Destination) {
  $preferred = Join-Path ([Environment]::GetFolderPath('Desktop')) 'CreatorOps_Backups'
  try { New-Item -ItemType Directory -Force -Path $preferred | Out-Null; $Destination = $preferred }
  catch { $Destination = Join-Path $projectRoot 'backups' }
}
$now = Get-Date
$week = [System.Globalization.ISOWeek]::GetWeekOfYear($now)
$existing = Get-ChildItem -LiteralPath $Destination -Filter ("Backup_Woche_KW{0:D2}_{1}_*.zip" -f $week,$now.Year) -ErrorAction SilentlyContinue | Select-Object -First 1
if ($existing) { [pscustomobject]@{Status='CURRENT';Backup=$existing.FullName}; return }
$python = Resolve-CreatorOpsPython -ProjectRoot $projectRoot
Push-Location $projectRoot
try { & $python -m creator_ops.cli --db $database --config $runtimeConfig.ConfigPath recovery-backup --kind weekly --out $Destination; if ($LASTEXITCODE) { exit $LASTEXITCODE } }
finally { Pop-Location }
