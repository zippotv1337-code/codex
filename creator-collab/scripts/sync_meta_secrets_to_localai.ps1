param()

$ErrorActionPreference = 'Stop'
$Root = 'C:\Zippoworkz'
$ProjectRoot = Join-Path $Root 'Workspace\codex_ingest\creator-collab'
$Replication = Join-Path $ProjectRoot 'scripts\secret_replication.ps1'
$RecipientPublic = Join-Path $Root 'Exchange\LOCALAI_TO_VPS\Current\LOCALAI_SECRET_REPLICATION_PUBLIC.json'
$Bundle = Join-Path $Root 'Exchange\VPS_TO_LOCALAI\Current\META_SECRETS_FOR_LOCALAI.json'
$SecretMeta = Join-Path $Root '_system\Secrets\metadata.json'

if (-not (Test-Path -LiteralPath $RecipientPublic)) {
  [ordered]@{ok=$true;status='WAITING_FOR_LOCALAI_PUBLIC_KEY';bundle_present=(Test-Path -LiteralPath $Bundle)} | ConvertTo-Json -Compress
  exit 0
}

$recipient = Get-Content -LiteralPath $RecipientPublic -Raw | ConvertFrom-Json
if ($recipient.schema -ne 'zippoworkz-secret-replication-public-v1') { throw 'localai_public_key_schema_invalid' }
if ([string]$recipient.machine_id -ne 'ZIPPOWORKZ-LOCALAI') { throw 'localai_public_key_machine_mismatch' }
if ([string]$recipient.fingerprint -notmatch '^[0-9a-f]{64}$') { throw 'localai_public_key_fingerprint_invalid' }
if (-not (Test-Path -LiteralPath $SecretMeta)) { throw 'vps_secret_metadata_missing' }

$needsExport = -not (Test-Path -LiteralPath $Bundle)
if (-not $needsExport) {
  $bundleTime = (Get-Item -LiteralPath $Bundle).LastWriteTimeUtc
  if ((Get-Item -LiteralPath $RecipientPublic).LastWriteTimeUtc -gt $bundleTime) { $needsExport = $true }
  if ((Get-Item -LiteralPath $SecretMeta).LastWriteTimeUtc -gt $bundleTime) { $needsExport = $true }
}

if (-not $needsExport) {
  [ordered]@{ok=$true;status='CURRENT';recipient_machine=$recipient.machine_id;recipient_fingerprint=$recipient.fingerprint;bundle=$Bundle} | ConvertTo-Json -Compress
  exit 0
}

$result = & $Replication -Mode ExportMeta -RecipientPublicKey $RecipientPublic -BundlePath $Bundle
if ($LASTEXITCODE -ne 0) { throw 'meta_secret_replication_export_failed' }
[ordered]@{ok=$true;status='BUNDLE_REFRESHED';recipient_machine=$recipient.machine_id;recipient_fingerprint=$recipient.fingerprint;bundle=$Bundle} | ConvertTo-Json -Compress