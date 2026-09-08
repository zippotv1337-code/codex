# Sitzungsjournal

- Datum/Zeit: 8. September 2026, 18:30 Europe/Berlin
- Agent: Codex
- Ziel der Sitzung: ZippoWorkz für den vom Owner gewünschten LAN-Betrieb im
  Bereich `192.168.188.*` vorbereiten.

## Ausgangslage

- Der vorhandene Dienst lief auf `127.0.0.1:4180`.
- Die aktive WLAN-Schnittstelle hat die private Adresse `192.168.188.131/24`.
- Der Launcher ignorierte bisher den in der Runtime-Konfiguration vorgesehenen
  Host und startete den Webserver immer auf Loopback.

## Durchgeführt

- `config.toml` auf den verifizierten Host `192.168.188.131` gesetzt.
- `START_CREATOR_OPS.ps1` so korrigiert, dass Health-URL und Webserver-Start
  den konfigurierten Host verwenden.
- Den alten Loopback-Prozess absichtlich nicht gewaltsam beendet, solange der
  passwortgeschützte LAN-Neustart nicht möglich ist.

## Verifiziert

- Konfigurierte WLAN-Adresse: `192.168.188.131/24`.
- Der bestehende Listener liegt noch auf `127.0.0.1:4180`.
- Diff-Prüfung der zwei gezielten Dateien ist ohne Whitespace-Fehler.
- Weder Prozess- noch Benutzerumgebung enthält aktuell ein
  `CREATOR_OPS_PASSWORD` mit mindestens 12 Zeichen.

## Entscheidungen

- Kein offenes Dashboard im WLAN: Der Webserver blockiert Nicht-Loopback ohne
  Passwort bewusst. Diese Sicherung bleibt erhalten.
- Keine Routerfreigabe, kein Cloud-Tunnel und keine Firewallregel angelegt.

## Offen oder blockiert

- Der Owner muss ein lokales Dashboard-Passwort festlegen oder den bereits
  vorhandenen Code lokal setzen. Das Passwort wird weder hier noch im
  Repository dokumentiert.
- Nach der Owner-Rückmeldung um 18:30 Uhr wurde die Verfügbarkeit erneut ohne
  Auslesen eines Geheimnisses geprüft. Weder Prozess- noch Benutzerumgebung
  enthält aktuell ein mindestens zwölf Zeichen langes `CREATOR_OPS_PASSWORD`.
  Deshalb wurde der bestehende Loopback-Prozess nicht beendet und kein
  ungeschützter LAN-Start versucht.

## Nächster Agent

1. Nach dem lokalen Setzen eines Passworts den vorhandenen Prozess kontrolliert
   neu starten.
2. `http://192.168.188.131:4180/` vom Rechner und danach im selben WLAN vom
   Handy/Safari öffnen.
3. Health und Passwort-Login sichtbar prüfen und erst dann den LAN-Status als
   aktiv dokumentieren.

## Abschluss — 18:38 Europe/Berlin

- Das lokal gesetzte Passwort war für einen neuen Launcher-Prozess verfügbar,
  ohne seinen Inhalt auszulesen oder zu speichern.
- Der vorhandene verwaltete Loopback-Dienst wurde mit dem Projekt-Stoppskript
  kontrolliert beendet.
- ZippoWorkz wurde anschließend über den bestehenden Supervisor auf
  `192.168.188.131:4180` gestartet.
- Verifiziert: Listener auf `192.168.188.131:4180`, `/api/health` meldet
  `status=ok`, `auth=true`, Datenbank `ok`; die Browser-Startseite zeigt den
  Passwort-Login.
- Keine Routerfreigabe, kein Tunnel, keine Firewall-Ausnahme, keine externe
  Plattformaktion und keine Secret-Protokollierung.
