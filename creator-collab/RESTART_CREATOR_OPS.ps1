param([Nullable[int]]$Port = $null,[string]$Database = '',[string]$Config = '',[switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'STOP_CREATOR_OPS.ps1')
$arguments = @{ NoBrowser=$NoBrowser }
if ($null -ne $Port) { $arguments.Port = $Port }
if ($Database) { $arguments.Database = $Database }
if ($Config) { $arguments.Config = $Config }
& (Join-Path $PSScriptRoot 'START_CREATOR_OPS.ps1') @arguments
