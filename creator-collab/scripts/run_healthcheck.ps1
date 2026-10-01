param([string]$Config = '')

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'runtime_config.ps1')
$runtimeConfig = Get-CreatorOpsRuntimeConfig -ProjectRoot $projectRoot -ConfigPath $Config
$database = if ([IO.Path]::IsPathRooted($runtimeConfig.Database)) { $runtimeConfig.Database } else { Join-Path $projectRoot $runtimeConfig.Database }
$python = Resolve-CreatorOpsPython -ProjectRoot $projectRoot

& $python (Join-Path $PSScriptRoot 'healthcheck.py') --db $database
exit $LASTEXITCODE
