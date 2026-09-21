param(
  [string]$Database = '',
  [string]$OfflineOutput = '',
  [string]$Config = ''
)

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'runtime_config.ps1')
$runtimeConfig = Get-CreatorOpsRuntimeConfig -ProjectRoot $projectRoot -ConfigPath $Config
if (-not $Database) { $Database = Join-Path $projectRoot $runtimeConfig.Database }
if (-not $OfflineOutput) { $OfflineOutput = Join-Path $projectRoot $runtimeConfig.OfflineOutput }

# The long-running supervisor can predate values written with `setx`. Hydrate
# only the explicitly supported local secret names for this bounded child
# process. Values are never logged or added to command-line arguments.
$userEnvironmentNames = @(
  'CREATOR_OPS_PASSWORD',
  'META_IG_USER_ID_LEONA_VOSS',
  'META_ACCESS_TOKEN_LEONA_VOSS',
  'META_IG_USER_ID_MARA_FIELD',
  'META_ACCESS_TOKEN_MARA_FIELD',
  'META_GRAPH_API_VERSION',
  'META_GRAPH_HOST',
  'CREATOR_OPS_META_MEDIA_MANIFEST'
)
foreach ($name in $userEnvironmentNames) {
  $userValue = [Environment]::GetEnvironmentVariable($name, 'User')
  if (-not [string]::IsNullOrWhiteSpace($userValue)) {
    [Environment]::SetEnvironmentVariable($name, $userValue, 'Process')
  }
}

$databasePath = [System.IO.Path]::GetFullPath($Database)
$offlinePath = [System.IO.Path]::GetFullPath($OfflineOutput)
$logDirectory = Join-Path $projectRoot 'data\logs'
$logPath = Join-Path $logDirectory 'standalone_scheduler.log'
New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null

$python = Resolve-CreatorOpsPython -ProjectRoot $projectRoot

function Write-RunLog([string]$Message) {
  $stamp = [DateTimeOffset]::Now.ToString('o')
  Add-Content -LiteralPath $logPath -Value "$stamp $Message" -Encoding UTF8
}

function Invoke-CreatorOpsStep([string[]]$CommandArgs) {
  $output = & $python -m creator_ops.cli --db $databasePath `
    --config $runtimeConfig.ConfigPath @CommandArgs 2>&1
  $exit = $LASTEXITCODE
  $output | ForEach-Object { Write-RunLog $_ }
  if ($exit -ne 0) {
    throw "Creator Ops step failed with exit code ${exit}: $($CommandArgs -join ' ')"
  }
}

Push-Location $projectRoot
try {
  Write-RunLog 'scheduler invocation started'
  Invoke-CreatorOpsStep -CommandArgs @('publish-reconcile')
  $passwordReady = -not [string]::IsNullOrEmpty($env:CREATOR_OPS_PASSWORD) -and `
    $env:CREATOR_OPS_PASSWORD.Length -ge 12
  $completeLiveGate = $runtimeConfig.DispatchLive -and `
    $runtimeConfig.PublishingLiveEnabled -and `
    $runtimeConfig.OfficialInstagramPublish -and `
    $runtimeConfig.LiveExternalActions -and `
    $runtimeConfig.PublishingAdapter -eq 'meta-graph' -and `
    $passwordReady
  if ($completeLiveGate) {
    Invoke-CreatorOpsStep -CommandArgs @('publish-dispatch-due', '--at', [DateTimeOffset]::Now.ToString('o'))
  } else {
    Write-RunLog 'live dispatch skipped by complete owner gate'
  }

  $berlin = [TimeZoneInfo]::FindSystemTimeZoneById('W. Europe Standard Time')
  $localNow = [TimeZoneInfo]::ConvertTime([DateTimeOffset]::UtcNow, $berlin)
  if ($localNow.Hour -eq $runtimeConfig.MorningHour -and $localNow.Minute -ge $runtimeConfig.MorningMinute) {
    Invoke-CreatorOpsStep -CommandArgs @('morning-run', '--at', $localNow.ToString('o'))
  }

  Invoke-CreatorOpsStep -CommandArgs @('offline-snapshot', '--out', $offlinePath)
  Write-RunLog 'scheduler invocation completed'
} catch {
  Write-RunLog "ERROR $($_.Exception.Message)"
  exit 1
} finally {
  Pop-Location
}
