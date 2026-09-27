param()
$ErrorActionPreference = 'Stop'
$generic = Join-Path $PSScriptRoot 'sync_connector_secrets_to_localai.ps1'
if (-not (Test-Path -LiteralPath $generic)) { throw 'generic_connector_secret_sync_missing' }
& $generic
exit $LASTEXITCODE
