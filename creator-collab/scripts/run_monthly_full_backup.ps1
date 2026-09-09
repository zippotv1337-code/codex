param([string]$Destination = '', [string]$Config = '')
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'runtime_config.ps1')
$runtimeConfig = Get-CreatorOpsRuntimeConfig -ProjectRoot $projectRoot -ConfigPath $Config
$python = Resolve-CreatorOpsPython -ProjectRoot $projectRoot
if (-not $Destination) { $Destination = Join-Path $projectRoot 'backups' }
Push-Location $projectRoot
try {
  & $python -m creator_ops.local_ops monthly --config $runtimeConfig.ConfigPath --destination $Destination
  exit $LASTEXITCODE
} finally { Pop-Location }
