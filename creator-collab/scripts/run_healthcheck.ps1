param([string]$Config = '')
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'runtime_config.ps1')
$runtimeConfig = Get-CreatorOpsRuntimeConfig -ProjectRoot $projectRoot -ConfigPath $Config
$python = Resolve-CreatorOpsPython -ProjectRoot $projectRoot
& $python (Join-Path $PSScriptRoot 'healthcheck.py') --config $runtimeConfig.ConfigPath
exit $LASTEXITCODE
