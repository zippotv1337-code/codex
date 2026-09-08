# ZippoWorkz — Local Ops für Codex

Stand: 2026-09-08. Status: **CODEX_REFERENCE_INTEGRATED**.

## Geltung und Abgrenzung

Neueste Owner-Klarstellung: „es soll erstmal nur für codex integriert werden“.
Diese Datei integriert die Arbeitsregeln in das bestehende Projekt. Sie löst
keine Desktop-Einrichtung, Installation, Dienstaktivierung oder Plattformaktion
aus. Es gibt keine globale Änderung an Codex-Einstellungen außerhalb des Projekts.

Quelle: `C:\Users\ZiPPo\Desktop\CODEX_ZIPPOWORKZ_LOCAL_DESKTOP_OPS_SETUP.md`.
SHA256 der unveränderten Quelle:
`E96A1301AB62A7B3BE34A9B07C3BB5AA7C10D34DCB3530C514D196083A6CEF12`.

Die Quelle enthält einen größeren Desktop-Setup-Plan. Die folgenden Regeln sind
dessen für Codex angepasste Fassung; die dortigen Ausführungsaufträge bleiben
durch die neuere Owner-Klarstellung zurückgestellt.

## Verbindliche Arbeitsgrundlage

- Nur im vorhandenen `creator-collab/` arbeiten. Keine systemweite Projektsuche
  oder Ersatzkopie; bei unklarem Workspace nachfragen.
- Lokale Codex-Python-Jobs mit `.venv\Scripts\python.exe` ausführen. Am
  08.09.2026 hier direkt bestätigt: **Python 3.14.7**, virtuelle Umgebung aktiv
  (`sys.prefix != sys.base_prefix`). Eine Shell-Aktivierung ist dafür nicht nötig.
- Projektpakete nur in dieser bestehenden Umgebung, nicht global installieren.
  Keine zweite VENV, keine Entfernung anderer Python-Versionen, keine unnötige
  Änderung am System-PATH. Neuinstallationen gehören nicht zu dieser Integration.
- **Operative Hauptdatenbank: `data/review_dashboard.db`**, Schema-5-Baseline.
  Die Quelldatei benennt abweichend `creator_ops.db` als MAIN. Das ist kein Auftrag
  zum Umschalten: weitere DB-Dateien sind kein Ersatz für den kanonischen Core.
  Ihre konkrete Rolle bei Bedarf prüfen; keine automatische Migration/Zusammenführung.
- Vorhandener Einstieg: `START_ZIPPOWORKZ.ps1`; maßgebliche Laufzeitkonfiguration:
  `config.toml`. Aktuell konfiguriert: `192.168.188.131:4180` und die obige DB.
  Das ist eine Konfigurationsfeststellung, kein neuer Erreichbarkeitsnachweis.
- Bestehende Runtime-/Supervisor-Interpreterwahl nicht ungefragt ändern. Die
  VENV-Regel für Codex-Jobs belegt keine erfolgte Migration des laufenden Dienstes.
- Vorhandene Health-/Backup-Wege wiederverwenden: `scripts/healthcheck.py`,
  `scripts/run_weekly_backup.ps1`, `scripts/run_monthly_full_backup.ps1`.
  Kein zweites Dashboard, Backup-System oder zusätzlicher Backend-Prozess.
- Vor kritischer DB-Arbeit passendes sicheres Backup und Integritätsprüfung;
  bei normalen Änderungen nur risikogerechte Sicherung/Tests. Laufende SQLite-DBs
  nicht ungesichert als normale Datei kopieren. Wiederherstellbarkeit prüfen.
- Keine Passwörter, Tokens, Cookies oder Schlüssel in Git, DB, Journal, Desktop-
  Dateien oder Exporten. Vorhandene sichere Umgebungsvariablen nicht ausgeben.

## Health- und Statusregeln für spätere beauftragte Anpassungen

- Fehler der tatsächlich aktiven DB: `ERROR`; Lesefehler eines alten Backups:
  `BACKUP_WARN`, nicht automatisch Ausfall der aktiven DB.
- Kompakte Zusammenfassung bevorzugen: Python/VENV/SQLite/Disk, Hauptdatenbank,
  geprüfte weitere DBs und Backup-Zähler; nicht jedes alte Backup verbose ausgeben.
- Fehlende Messwerte bleiben `UNKNOWN`/`NULL`. Ein Statusdatum muss zu einer
  tatsächlich durchgeführten Prüfung gehören.
- Die Quelle meldet frühere erfolgreiche DB-Prüfungen, ca. 440 GB freien Speicher,
  bestimmte Toolversionen und eine alte Backup-Warnung. Diese Angaben sind in
  dieser Integration **nicht neu verifiziert** und kein aktueller Health-Receipt.
- `scripts/healthcheck.py` wurde nicht geändert und nicht ausgeführt; sein
  vorhandener rekursiver DB-Scan wurde nicht als neue Routine gestartet.

## Zurückgestellt — nicht automatisch ausführen

Desktop-Steuerordner mit Start/Healthcheck/Backup/Dashboard/Projekt/Logs,
optionale `local_ops_status.json`, kompakterer Healthcheck und zusätzliche lokale
Job-Einstiege bleiben vorbereitete Anforderungen für einen späteren Owner-Auftrag.
Bestehende Backup- und Launcherwege zuerst nutzen, nicht duplizieren.

Keine neuen Windows-Tasks registrieren, keine zusätzlichen Dienste starten,
keinen Tunnel, Router-Port oder RDP öffentlich freigeben. `cloudflared`/SQLite CLI
nicht neu installieren. Externer Zugriff und Job-Aktivierung sind eigene Schritte.
Ein lokaler Scheduler erteilt keine neue Freigabe für Instagram/Fiverr/Nachrichten
oder Zahlungen; aktuelle plattformspezifische Owner-/Safety-Gates bleiben maßgeblich.

Git/GitHub: in dieser Local-Ops-Integration keine Änderungen, Commits oder Pushes.
Das ist **keine neue dauerhafte Git-Sperre** für unabhängige spätere Aufträge.

## Abschluss und Fortsetzung

Dokumentationsintegration ist abgeschlossen. Kein Desktop-Setup als DONE melden.
Journal, Handoff und Checkpoint führen die tatsächlichen Änderungen. Anschließend
STOP; weiterführende Ideen gehören in die bestehende Master Goals, nicht in eine
zweite aktive Aufgabenliste.
