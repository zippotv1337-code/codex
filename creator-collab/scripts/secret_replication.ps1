param(
  [ValidateSet('Init','Status','ExportMeta','ImportMeta','ExportConnector','ImportConnector')]
  [string]$Mode = 'Status',
  [string]$Connector = 'meta-instagram',
  [string]$RecipientPublicKey = '',
  [string]$BundlePath = '',
  [string]$NodeRole = '',
  [switch]$DeleteBundle
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Security
$Root = 'C:\Zippoworkz'
$ProjectRoot = Join-Path $Root 'Workspace\codex_ingest\creator-collab'
. (Join-Path $ProjectRoot 'scripts\runtime_config.ps1')
$Python = Resolve-CreatorOpsPython -ProjectRoot $ProjectRoot
$Helper = Join-Path $ProjectRoot 'scripts\secret_bundle_helper.py'
$SecretDir = Join-Path $Root '_system\Secrets'
$IdentityPath = Join-Path $SecretDir 'replication_identity.json'
$PrivatePath = Join-Path $SecretDir 'replication_private.dpapi'
$Machine = Get-Content (Join-Path $Root 'MACHINE_ID.json') -Raw | ConvertFrom-Json
if (-not $NodeRole) { if ([string]$Machine.package_type -like 'VPS*') { $NodeRole = 'VPS' } else { $NodeRole = 'LOCALAI' } }
$NodeRole = $NodeRole.ToUpperInvariant()
New-Item -ItemType Directory -Force -Path $SecretDir | Out-Null

function Get-Public-Key-Path {
  if ($NodeRole -eq 'VPS') { $dir=Join-Path $Root 'Exchange\VPS_TO_LOCALAI\Current'; $name='VPS_SECRET_REPLICATION_PUBLIC.json' }
  else { $dir=Join-Path $Root 'Exchange\LOCALAI_TO_VPS\Current'; $name='LOCALAI_SECRET_REPLICATION_PUBLIC.json' }
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
  return Join-Path $dir $name
}

function Get-Identity {
  if (-not (Test-Path -LiteralPath $IdentityPath)) { return $null }
  try { return Get-Content -LiteralPath $IdentityPath -Raw | ConvertFrom-Json } catch { return $null }
}

function Get-Fingerprint([byte[]]$PublicBlob) {
  $sha=[Security.Cryptography.SHA256]::Create()
  try { return ([BitConverter]::ToString($sha.ComputeHash($PublicBlob))).Replace('-','').ToLowerInvariant() } finally { $sha.Dispose() }
}

function Load-Private-Rsa {
  if (-not (Test-Path -LiteralPath $PrivatePath)) { throw 'replication_private_key_missing' }
  $protected=[Convert]::FromBase64String((Get-Content -LiteralPath $PrivatePath -Raw).Trim())
  $private=[Security.Cryptography.ProtectedData]::Unprotect($protected,$null,[Security.Cryptography.DataProtectionScope]::CurrentUser)
  $rsa=New-Object System.Security.Cryptography.RSACryptoServiceProvider
  $rsa.PersistKeyInCsp=$false
  $rsa.ImportCspBlob($private)
  [Array]::Clear($private,0,$private.Length)
  return $rsa
}

if ($Mode -eq 'Init') {
  $identity=Get-Identity
  $publicPath=Get-Public-Key-Path
  if ($identity -and (Test-Path -LiteralPath $PrivatePath) -and (Test-Path -LiteralPath $publicPath)) {
    [ordered]@{ok=$true;mode='Init';reused=$true;machine_id=$Machine.machine_id;node_role=$NodeRole;fingerprint=$identity.fingerprint;public_key=$publicPath} | ConvertTo-Json -Compress
    exit 0
  }
  $rsa=New-Object System.Security.Cryptography.RSACryptoServiceProvider 3072
  $rsa.PersistKeyInCsp=$false
  try {
    $public=$rsa.ExportCspBlob($false)
    $private=$rsa.ExportCspBlob($true)
    $protected=[Security.Cryptography.ProtectedData]::Protect($private,$null,[Security.Cryptography.DataProtectionScope]::CurrentUser)
    [Convert]::ToBase64String($protected) | Set-Content -LiteralPath $PrivatePath -Encoding ASCII
    $fingerprint=Get-Fingerprint $public
    $pub=[ordered]@{schema='zippoworkz-secret-replication-public-v1';machine_id=[string]$Machine.machine_id;node_role=$NodeRole;key_bits=3072;fingerprint=$fingerprint;public_csp_blob_b64=[Convert]::ToBase64String($public);created_at=[DateTimeOffset]::Now.ToString('o')}
    $pub | ConvertTo-Json | Set-Content -LiteralPath $publicPath -Encoding UTF8
    $identity=[ordered]@{schema='zippoworkz-secret-replication-identity-v1';machine_id=[string]$Machine.machine_id;node_role=$NodeRole;fingerprint=$fingerprint;created_at=[DateTimeOffset]::Now.ToString('o')}
    $identity | ConvertTo-Json | Set-Content -LiteralPath $IdentityPath -Encoding UTF8
    [Array]::Clear($private,0,$private.Length)
  } finally { $rsa.Dispose() }
  [ordered]@{ok=$true;mode='Init';reused=$false;machine_id=$Machine.machine_id;node_role=$NodeRole;fingerprint=$fingerprint;public_key=$publicPath} | ConvertTo-Json -Compress
  exit 0
}

if ($Mode -eq 'Status') {
  $identity=Get-Identity
  [ordered]@{ok=$true;mode='Status';machine_id=$Machine.machine_id;node_role=$NodeRole;identity_present=[bool]$identity;private_key_present=(Test-Path -LiteralPath $PrivatePath);public_key=(Get-Public-Key-Path);fingerprint=$(if($identity){$identity.fingerprint}else{$null})} | ConvertTo-Json -Compress
  exit 0
}

if ($Mode -eq 'ExportMeta' -or $Mode -eq 'ImportMeta') { $Connector = 'meta-instagram' }

if ($Mode -eq 'ExportMeta' -or $Mode -eq 'ExportConnector') {
  if (-not $RecipientPublicKey -or -not (Test-Path -LiteralPath $RecipientPublicKey)) { throw 'recipient_public_key_missing' }
  if (-not $BundlePath) { throw 'bundle_path_missing' }
  $recipient=Get-Content -LiteralPath $RecipientPublicKey -Raw | ConvertFrom-Json
  if ($recipient.schema -ne 'zippoworkz-secret-replication-public-v1' -or -not $recipient.public_csp_blob_b64) { throw 'recipient_public_key_invalid' }
  $rsa=New-Object System.Security.Cryptography.RSACryptoServiceProvider
  $rsa.PersistKeyInCsp=$false
  $rsa.ImportCspBlob([Convert]::FromBase64String([string]$recipient.public_csp_blob_b64))
  [Environment]::SetEnvironmentVariable('ZW_SECRET_EXPORT_INTERNAL','1','Process')
  try { $payloadRaw=& $Python $Helper export $Connector }
  finally { [Environment]::SetEnvironmentVariable('ZW_SECRET_EXPORT_INTERNAL',$null,'Process') }
  if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($payloadRaw)) { $rsa.Dispose(); throw 'secret_payload_export_failed' }
  try {
    $payload=$payloadRaw | ConvertFrom-Json
    $encrypted=[ordered]@{}
    foreach($prop in $payload.secrets.PSObject.Properties) {
      $bytes=[Text.Encoding]::UTF8.GetBytes([string]$prop.Value)
      $chunks=@()
      for($i=0;$i -lt $bytes.Length;$i+=300) {
        $len=[Math]::Min(300,$bytes.Length-$i)
        $chunk=New-Object byte[] $len
        [Array]::Copy($bytes,$i,$chunk,0,$len)
        $chunks += [Convert]::ToBase64String($rsa.Encrypt($chunk,$true))
      }
      $encrypted[$prop.Name]=$chunks
      [Array]::Clear($bytes,0,$bytes.Length)
    }
    $bundle=[ordered]@{schema='zippoworkz-secret-replication-bundle-v2';scope=[string]$Connector;source_machine=[string]$Machine.machine_id;recipient_machine=[string]$recipient.machine_id;recipient_fingerprint=[string]$recipient.fingerprint;created_at=[DateTimeOffset]::Now.ToString('o');encrypted=$encrypted}
    $dir=Split-Path -Parent $BundlePath
    if($dir){New-Item -ItemType Directory -Force -Path $dir | Out-Null}
    $bundle | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $BundlePath -Encoding UTF8
  } finally { $payloadRaw=$null; $payload=$null; $rsa.Dispose() }
  [ordered]@{ok=$true;mode=$Mode;connector=$Connector;bundle=$BundlePath;recipient_machine=$recipient.machine_id;recipient_fingerprint=$recipient.fingerprint} | ConvertTo-Json -Compress
  exit 0
}

if ($Mode -eq 'ImportMeta' -or $Mode -eq 'ImportConnector') {
  if (-not $BundlePath -or -not (Test-Path -LiteralPath $BundlePath)) { throw 'bundle_missing' }
  $identity=Get-Identity
  if (-not $identity) { throw 'replication_identity_missing' }
  $bundle=Get-Content -LiteralPath $BundlePath -Raw | ConvertFrom-Json
  if ($bundle.schema -ne 'zippoworkz-secret-replication-bundle-v2' -or [string]$bundle.scope -ne [string]$Connector) { throw 'bundle_schema_invalid' }
  if ([string]$bundle.recipient_fingerprint -ne [string]$identity.fingerprint) { throw 'bundle_recipient_mismatch' }
  $rsa=Load-Private-Rsa
  $secrets=[ordered]@{}
  try {
    foreach($prop in $bundle.encrypted.PSObject.Properties) {
      $buffer=New-Object System.Collections.Generic.List[byte]
      foreach($cipherText in @($prop.Value)) { $plainChunk=$rsa.Decrypt([Convert]::FromBase64String([string]$cipherText),$true); $buffer.AddRange([byte[]]$plainChunk) }
      $secrets[$prop.Name]=[Text.Encoding]::UTF8.GetString($buffer.ToArray())
    }
    $payload=[ordered]@{schema='zippoworkz-secret-bundle-v2';scope=[string]$Connector;worker='';created_at=[DateTimeOffset]::Now.ToString('o');secrets=$secrets} | ConvertTo-Json -Depth 6 -Compress
    $catalog=Get-Content -LiteralPath (Join-Path $ProjectRoot 'config\connector_secret_catalog.json') -Raw | ConvertFrom-Json
    $connectorConfig=$catalog.connectors.PSObject.Properties | Where-Object { $_.Name -eq $Connector } | Select-Object -First 1
    if(-not $connectorConfig){throw 'connector_scope_unknown'}
    $payloadObject=$payload | ConvertFrom-Json
    $payloadObject.worker=[string]$connectorConfig.Value.worker
    $payload=$payloadObject | ConvertTo-Json -Depth 6 -Compress
    [Environment]::SetEnvironmentVariable('ZW_SECRET_PAYLOAD',$payload,'Process')
    $result=& $Python $Helper import-env $Connector
    if($LASTEXITCODE -ne 0){throw 'secret_payload_import_failed'}
  } finally { [Environment]::SetEnvironmentVariable('ZW_SECRET_PAYLOAD',$null,'Process'); $payload=$null; $secrets=$null; $rsa.Dispose() }
  if($DeleteBundle){Remove-Item -LiteralPath $BundlePath -Force}
  $result
  exit 0
}