param([switch]$NoBrowser)

# Primary launcher. Existing runtime, database, supervisor and port are reused.
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'START_STANDALONE_CREATOR_OPS.ps1') `
    -Config (Join-Path $PSScriptRoot 'config.toml') -NoBrowser:$NoBrowser
