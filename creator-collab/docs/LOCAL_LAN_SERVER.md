# Local-/LAN-Dashboard

Local bleibt der Standard: `http://127.0.0.1:4180` über `run_dashboard.ps1`.

Für das private Heim-LAN:

```powershell
$env:CREATOR_OPS_PASSWORD = '<mindestens 12 Zeichen>'
.\run_lan.ps1
```

Das Skript ermittelt aktive Netzwerkkarte, Default Gateway und passende IPv4
automatisch und zeigt nur Interface, Gateway, IPv4, Port und die beiden URLs.
Es öffnet keine Router-Ports, verwendet kein UPnP und gibt keine MAC-Adresse
aus. Non-loopback-Betrieb wird serverseitig ohne Passwort verweigert.

Eine Windows-Firewallregel für Private Profile/TCP 4180 wird nur mit dem
expliziten Schalter `-ConfigureFirewall` angelegt. Zugriff aus öffentlichem
Internet bleibt außerhalb dieses LAN-Modus.
