param([string]$Destination)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not $Destination) {
  $preferred = Join-Path ([Environment]::GetFolderPath('Desktop')) 'CreatorOps_Backups'
  try { New-Item -ItemType Directory -Force -Path $preferred | Out-Null; $Destination = $preferred }
  catch { $Destination = Join-Path $projectRoot 'backups' }
}
$now = Get-Date
$week = [System.Globalization.ISOWeek]::GetWeekOfYear($now)
$existing = Get-ChildItem -LiteralPath $Destination -Filter ("Backup_Woche_KW{0:D2}_{1}_*.zip" -f $week,$now.Year) -ErrorAction SilentlyContinue | Select-Object -First 1
if ($existing) { [pscustomobject]@{Status='CURRENT';Backup=$existing.FullName}; return }
$candidates = @(
  (Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'),
  'python.exe', 'py.exe'
)
$python = $candidates | Where-Object { $_ -and (Get-Command $_ -ErrorAction SilentlyContinue) } | Select-Object -First 1
if (-not $python) { throw 'Python runtime not found.' }
Push-Location $projectRoot
try { & $python -m creator_ops.cli --db data\review_dashboard.db recovery-backup --kind weekly --out $Destination; if ($LASTEXITCODE) { exit $LASTEXITCODE } }
finally { Pop-Location }
