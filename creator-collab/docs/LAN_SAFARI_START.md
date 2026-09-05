# Creator Ops im Heimnetz und in Safari

Aktuell erkannte PC-Adresse: `192.168.188.131`.

`192.168.1.188` ist keine Adresse dieses PCs und gehört außerdem zu einem
anderen `/24`-Subnetz als das aktive WLAN mit Gateway `192.168.188.1`.

## Start

Im Projektordner ausführen:

```powershell
.\START_LAN_CREATOR_OPS.ps1
```

Ein temporäres Passwort mit mindestens zwölf Zeichen eingeben. Das Passwort
wird weder in einer Datei noch in SQLite gespeichert. Anschließend auf dem
Handy im gleichen WLAN in Safari öffnen:

`http://192.168.188.131:4180/`

Falls Windows den Zugriff blockiert, PowerShell einmal als Administrator öffnen
und ausführen:

```powershell
.\START_LAN_CREATOR_OPS.ps1 -ConfigureFirewall
```

Die Regel gilt nur für das private lokale Subnetz und TCP-Port 4180. Es wird
kein Routerport geöffnet und kein Zugriff aus dem Internet eingerichtet.

Beenden:

```powershell
.\STOP_CREATOR_OPS.ps1
```

Die Oberfläche besitzt einen mobilen Viewport und einspaltige Layoutregeln für
kleine Safari-Bildschirme.
