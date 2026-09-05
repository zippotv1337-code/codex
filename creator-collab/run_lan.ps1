param([int]$Port=4180,[switch]$ConfigureFirewall)
$ErrorActionPreference='Stop'
if (-not $env:CREATOR_OPS_PASSWORD -or $env:CREATOR_OPS_PASSWORD.Length -lt 12) { throw 'Set CREATOR_OPS_PASSWORD to at least 12 characters before LAN start.' }
$route = Get-NetRoute -DestinationPrefix '0.0.0.0/0' -AddressFamily IPv4 | Where-Object {$_.State -eq 'Alive'} | Sort-Object RouteMetric,InterfaceMetric | Select-Object -First 1
if (-not $route) { throw 'No active IPv4 default route found.' }
$ip = Get-NetIPAddress -InterfaceIndex $route.InterfaceIndex -AddressFamily IPv4 | Where-Object {$_.AddressState -eq 'Preferred' -and $_.IPAddress -notlike '169.254.*'} | Select-Object -First 1
if (-not $ip) { throw 'No suitable LAN IPv4 found.' }
$adapter = Get-NetAdapter -InterfaceIndex $route.InterfaceIndex
$gateway = (Get-NetIPConfiguration -InterfaceIndex $route.InterfaceIndex).IPv4DefaultGateway.NextHop
if ($ConfigureFirewall) {
  $name="Creator Ops LAN TCP $Port"
  if (-not (Get-NetFirewallRule -DisplayName $name -ErrorAction SilentlyContinue)) { New-NetFirewallRule -DisplayName $name -Direction Inbound -Action Allow -Protocol TCP -LocalPort $Port -Profile Private | Out-Null }
}
[pscustomobject]@{Interface=$adapter.Name;Gateway=$gateway;IPv4=$ip.IPAddress;Port=$Port;LocalURL="http://127.0.0.1:$Port";LANURL="http://$($ip.IPAddress):$Port";Mode='LAN + password'} | Format-List
$python = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if (-not (Test-Path -LiteralPath $python)) { $python=(Get-Command python.exe -ErrorAction Stop).Source }
Push-Location $PSScriptRoot
try { & $python -m creator_ops.web --db data\review_dashboard.db --host $ip.IPAddress --port $Port }
finally { Pop-Location }
