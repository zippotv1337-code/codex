param(
    [string]$PackageRoot = $PSScriptRoot,
    [string]$OutputDirectory = (Join-Path $PSScriptRoot 'result')
)

$ErrorActionPreference = 'Stop'
$checkedAt = [DateTimeOffset]::UtcNow.ToString('o')
$healthUrl = [Environment]::GetEnvironmentVariable('ZIPPOWORKZ_HEALTH_URL', 'Process')
$result = [ordered]@{
    protocol_version = 'zippo-workz-vps-v1'
    checked_at = $checkedAt
    package_integrity = 'UNKNOWN'
    health = 'NOT_CONFIGURED'
    health_url_configured = [bool]$healthUrl
    external_actions = 'NONE'
    database_writes = 'NONE'
    platform_actions = 'NONE'
    detail = ''
}

$hashFile = Join-Path $PackageRoot 'SHA256SUMS.txt'
if (Test-Path -LiteralPath $hashFile) {
    $ok = $true
    foreach ($line in Get-Content -LiteralPath $hashFile) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        $parts = $line -split '\s+', 2
        if ($parts.Count -ne 2) { $ok = $false; break }
        $path = Join-Path $PackageRoot $parts[1]
        if (-not (Test-Path -LiteralPath $path)) { $ok = $false; break }
        $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash
        if ($actual -ne $parts[0]) { $ok = $false; break }
    }
    $result.package_integrity = if ($ok) { 'OK' } else { 'ERROR' }
} else {
    $result.package_integrity = 'NO_MANIFEST'
}

if ($healthUrl) {
    if (-not $healthUrl.StartsWith('https://', [StringComparison]::OrdinalIgnoreCase)) {
        $result.health = 'BLOCKED_INSECURE_URL'
        $result.detail = 'Only an explicit HTTPS health URL is accepted.'
    } else {
        try {
            $response = Invoke-RestMethod -Uri $healthUrl -Method Get -TimeoutSec 10
            $result.health = if ($response.status) { [string]$response.status } else { 'REACHABLE' }
            $result.detail = 'One bounded read-only health request completed.'
        } catch {
            $result.health = 'OFFLINE'
            $result.detail = $_.Exception.Message
        }
    }
}

New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
$jsonPath = Join-Path $OutputDirectory 'VPS_RESULT.json'
$mdPath = Join-Path $OutputDirectory 'VPS_RESULT.md'
$result | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $jsonPath -Encoding utf8
@(
    '# ZippoWorkz VPS Result',
    '',
    "- Checked: $checkedAt",
    "- Package integrity: $($result.package_integrity)",
    "- Health: $($result.health)",
    "- Detail: $($result.detail)",
    '- External actions: NONE',
    '- Database writes: NONE',
    '- Platform actions: NONE'
) | Set-Content -LiteralPath $mdPath -Encoding utf8

Write-Output ($result | ConvertTo-Json -Depth 5)
