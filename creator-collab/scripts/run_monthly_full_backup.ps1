param([string]$Destination)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not $Destination) {
  $preferred = Join-Path ([Environment]::GetFolderPath('Desktop')) 'CreatorOps_Backups'
  try { New-Item -ItemType Directory -Force -Path $preferred | Out-Null; $Destination = $preferred }
  catch { $Destination = Join-Path $projectRoot 'backups' }
}
$month = (Get-Date).ToString('yyyy-MM')
$existing = Get-ChildItem -LiteralPath $Destination -Filter "Backup_Monat_${month}_FULL_*.zip" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($existing) { [pscustomobject]@{Status='CURRENT';Backup=$existing.FullName}; return }
$candidates = @((Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'),'python.exe','py.exe')
$python = $candidates | Where-Object { $_ -and (Get-Command $_ -ErrorAction SilentlyContinue) } | Select-Object -First 1
if (-not $python) { throw 'Python runtime not found.' }
Push-Location $projectRoot
try { & $python -m creator_ops.cli --db data\review_dashboard.db recovery-backup --kind monthly --out $Destination; if ($LASTEXITCODE) { exit $LASTEXITCODE } }
finally { Pop-Location }
