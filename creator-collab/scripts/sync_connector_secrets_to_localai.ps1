param()

$ErrorActionPreference = 'Stop'
$Root = 'C:\Zippoworkz'
$ProjectRoot = Join-Path $Root 'Workspace\codex_ingest\creator-collab'
. (Join-Path $ProjectRoot 'scripts\runtime_config.ps1')
$Python = Resolve-CreatorOpsPython -ProjectRoot $ProjectRoot
$Helper = Join-Path $ProjectRoot 'scripts\secret_bundle_helper.py'
$Replication = Join-Path $ProjectRoot 'scripts\secret_replication.ps1'
$CatalogPath = Join-Path $ProjectRoot 'config\connector_secret_catalog.json'
$RecipientPublic = Join-Path $Root 'Exchange\LOCALAI_TO_VPS\Current\LOCALAI_SECRET_REPLICATION_PUBLIC.json'
$OutDir = Join-Path $Root 'Exchange\VPS_TO_LOCALAI\Current'
$SecretMeta = Join-Path $Root '_system\Secrets\metadata.json'

if (-not (Test-Path -LiteralPath $RecipientPublic)) {
  [ordered]@{
    ok=$true
    status='WAITING_FOR_LOCALAI_PUBLIC_KEY'
    connector_bundles=0
  } | ConvertTo-Json -Compress
  exit 0
}
$recipient = Get-Content -LiteralPath $RecipientPublic -Raw | ConvertFrom-Json
if ($recipient.schema -ne 'zippoworkz-secret-replication-public-v1') {
  throw 'localai_public_key_schema_invalid'
}
if ([string]$recipient.machine_id -ne 'ZIPPOWORKZ-LOCALAI') {
  throw 'localai_public_key_machine_mismatch'
}
if ([string]$recipient.fingerprint -notmatch '^[0-9a-f]{64}$') {
  throw 'localai_public_key_fingerprint_invalid'
}
if (-not (Test-Path -LiteralPath $CatalogPath)) {
  throw 'connector_secret_catalog_missing'
}

$catalog = Get-Content -LiteralPath $CatalogPath -Raw | ConvertFrom-Json
$results = @()
$readyCount = 0
$bundleCount = 0
foreach ($property in $catalog.connectors.PSObject.Properties) {
  $name = [string]$property.Name
  $cfg = $property.Value
  if (-not [bool]$cfg.replicate) { continue }

  $names = @($cfg.secret_names)
  if ($names.Count -eq 0) {
    $results += [ordered]@{connector=$name;status='NO_SECRET_NAMES'}
    continue
  }

  $statusRaw = & $Python $Helper status $name
  if ($LASTEXITCODE -ne 0) {
    $results += [ordered]@{connector=$name;status='STATUS_FAILED'}
    continue
  }
  $secretStatus = $statusRaw | ConvertFrom-Json
  if (-not [bool]$secretStatus.ready) {
    $results += [ordered]@{connector=$name;status='NOT_READY_ON_VPS'}
    continue
  }
  $readyCount++
  $safeName = ($name -replace '[^A-Za-z0-9_.-]','_').ToUpperInvariant()
  $bundle = Join-Path $OutDir ("SECRETS_" + $safeName + "_FOR_LOCALAI.json")
  $needsExport = -not (Test-Path -LiteralPath $bundle)
  if (-not $needsExport) {
    $bundleTime = (Get-Item -LiteralPath $bundle).LastWriteTimeUtc
    if ((Get-Item -LiteralPath $RecipientPublic).LastWriteTimeUtc -gt $bundleTime) {
      $needsExport = $true
    }
    if ((Get-Item -LiteralPath $CatalogPath).LastWriteTimeUtc -gt $bundleTime) {
      $needsExport = $true
    }
    if ((Test-Path -LiteralPath $SecretMeta) -and
        (Get-Item -LiteralPath $SecretMeta).LastWriteTimeUtc -gt $bundleTime) {
      $needsExport = $true
    }
  }
  if ($needsExport) {
    $null = & $Replication -Mode ExportConnector -Connector $name -RecipientPublicKey $RecipientPublic -BundlePath $bundle
    if ($LASTEXITCODE -ne 0) { throw "connector_secret_export_failed:$name" }
    $results += [ordered]@{connector=$name;status='BUNDLE_REFRESHED';bundle=$bundle}
  } else {
    $results += [ordered]@{connector=$name;status='CURRENT';bundle=$bundle}
  }
  $bundleCount++
}

$overall = if ($readyCount -eq 0) {
  'WAITING_FOR_CONNECTOR_SECRETS'
} elseif ($bundleCount -eq $readyCount) {
  'CURRENT'
} else {
  'PARTIAL'
}
[ordered]@{
  ok=$true
  status=$overall
  recipient_machine=$recipient.machine_id
  ready_connectors=$readyCount
  connector_bundles=$bundleCount
  connectors=$results
} | ConvertTo-Json -Depth 6 -Compress
