param([string]$Database='data\review_dashboard.db',[int]$Port=4180,[switch]$NoBrowser)
& (Join-Path $PSScriptRoot 'START_CREATOR_OPS.ps1') -Database $Database -Port $Port -NoBrowser:$NoBrowser
