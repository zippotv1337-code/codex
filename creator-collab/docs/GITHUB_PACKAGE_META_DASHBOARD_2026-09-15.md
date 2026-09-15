# ZippoWorkz Meta-Dashboard GitHub-Paket

Stand: 15.09.2026, Europe/Berlin

Dieses Paket ist ein secret-freier Snapshot der auf GitHub getrackten
`creator-collab`-Projektdateien. Es enthält den geprüften Creator-Ops-Core,
Dashboard, Meta-Einzelpaketpfad, öffentlichen Media-Origin, Tests,
Dokumentation und die bereits getrackten SFW-Projektassets.

## Enthalten

- Creator-Ops-/ZippoWorkz-Quellcode
- Dashboard und Kanalansicht `/channels`
- Meta-Preflight und begrenzter Einzelpaket-Push
- loopback-only JPEG-Media-Origin
- Queue-, Receipt-, Idempotenz- und Reconciliation-Schutz
- Tests, Startskripte, Handoffs und Sitzungsjournale
- bereits auf GitHub getrackte SFW-Assets

## Ausgeschlossen

- SQLite-Datenbanken und Laufzeitstatus
- Backups und Recovery-Archive
- lokale Logs, temporäre Dateien und `output/`
- `.env`-Dateien, Tokens, Cookies, Passwörter und private Schlüssel
- lokale Virtual Environments und installierte Werkzeuge

Das ZIP wird direkt aus dem Git-Commit erzeugt. Dadurch gelten dieselben
getrackten Inhalte wie auf dem zugehörigen GitHub-Branch.

## Meta-Live-Gates

Der technische Dashboard-Pfad ist vorbereitet. Für einen echten Meta-
Live-Proof fehlen weiterhin:

1. echte Instagram-User-Tokens und Nutzer-IDs für Leona und/oder Mara,
2. die benötigten Instagram-Content-Publishing-Berechtigungen,
3. drei öffentliche HTTPS-JPEG-URLs für genau ein freigegebenes Paket.

App-ID und App-Geheimcode ersetzen keinen Instagram-User-Token. Im Chat
offengelegte App-Schlüssel müssen im Developer-Portal rotiert und neue Werte
ausschließlich über den sicheren Secret-Provider hinterlegt werden.

## Bedienweg nach erfüllten Gates

1. ZippoWorkz starten und `/channels` öffnen.
2. Bei genau einem Paket `Einzelpaket prüfen` ausführen.
3. Nur bei `READY` `Dieses Paket senden` ausführen.
4. Bei unklarem externen Zustand zuerst reconciliieren und keinen blinden
   Wiederholungsversand auslösen.

Der globale Scheduler bleibt durch diesen Bedienweg unverändert deaktiviert.
