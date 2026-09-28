param()

$ErrorActionPreference = 'Stop'
$Root = 'C:\Zippoworkz'
$ProjectRoot = Join-Path $Root 'Workspace\codex_ingest\creator-collab'
$Replication = Join-Path $ProjectRoot 'scripts\secret_replication.ps1'
$CatalogPath = Join-Path $ProjectRoot 'config\connector_secret_catalog.json'
$InDir = Join-Path $Root 'Exchange\VPS_TO_LOCALAI\Current'
$MachinePath = Join-Path $Root 'MACHINE_ID.json'

if (-not (Test-Path -LiteralPath $MachinePath)) {
  throw 'machine_identity_missing'
}
$machine = Get-Content -LiteralPath $MachinePath -Raw | ConvertFrom-Json
if ([string]$machine.machine_id -ne 'ZIPPOWORKZ-LOCALAI') {
  [ordered]@{
    ok=$true
    status='NOT_LOCALAI_NODE'
    machine_id=$machine.machine_id
  } | ConvertTo-Json -Compress
  exit 0
}
if (-not (Test-Path -LiteralPath $CatalogPath)) {
  throw 'connector_secret_catalog_missing'
}
$catalog = Get-Content -LiteralPath $CatalogPath -Raw | ConvertFrom-Json
$results = @()
$imported = 0
$waiting = 0

foreach ($property in $catalog.connectors.PSObject.Properties) {
  $name = [string]$property.Name
  $cfg = $property.Value
  if (-not [bool]$cfg.replicate) { continue }
  $names = @($cfg.secret_names)
  if ($names.Count -eq 0) {
    $results += [ordered]@{connector=$name;status='NO_SECRET_NAMES'}
    continue
  }
  $safeName = ($name -replace '[^A-Za-z0-9_.-]','_').ToUpperInvariant()
  $bundle = Join-Path $InDir ("SECRETS_" + $safeName + "_FOR_LOCALAI.json")
  if (-not (Test-Path -LiteralPath $bundle)) {
    $results += [ordered]@{connector=$name;status='WAITING_FOR_BUNDLE'}
    $waiting++
    continue
  }

  $resultRaw = & $Replication -Mode ImportConnector -Connector $name -BundlePath $bundle -NodeRole LOCALAI -DeleteBundle
  if ($LASTEXITCODE -ne 0) {
    throw "connector_secret_import_failed:$name"
  }
  $results += [ordered]@{connector=$name;status='IMPORTED'}
  $imported++
}
$overall = if ($imported -gt 0 -and $waiting -eq 0) {
  'IMPORTED'
} elseif ($imported -gt 0) {
  'PARTIAL'
} elseif ($waiting -gt 0) {
  'WAITING_FOR_BUNDLES'
} else {
  'NOTHING_TO_IMPORT'
}

[ordered]@{
  ok=$true
  status=$overall
  machine_id=$machine.machine_id
  imported_connectors=$imported
  waiting_connectors=$waiting
  connectors=$results
} | ConvertTo-Json -Depth 6 -Compress
