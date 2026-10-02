# Sitzungsjournal — ZippoWorkz Single Source of Truth

- Datum/Zeit: 2026-10-02, 07:18 Europe/Berlin
- Agent: Codex
- Ziel der Sitzung: Ein Main, ein Deployment-Checkout, eine operative DB und
  ein aktiver Engineering-Branch ohne Verlust gültiger Deltas.

## Ausgangslage

- Live-Runtime nutzte `codex_ingest` bei `7ca2512`; `origin/main` war mit
  Claude-mitverfasstem DM-Echo-Guard, fail-closed Polling und Diagnose voraus.
- Drei Windows-Wartungs-Tasks und der Autostart verwiesen auf nicht mehr
  vorhandene Skripte im alten Documents-Checkout. Der bestehende Supervisor
  lief dagegen aus `codex_ingest`.
- Operative DB: Schema 8, Integrity `ok`, FK 0. Der DM-Hardening-Branch hatte
  zwei gültige ungemergte Commits, aber Schema 9 und Konflikte mit neuerem Main.

## Durchgeführt

- Claude/Main-Deltas und sieben damalige Worktrees inventarisiert.
  `config.toml` und `creator_ops_scheduler.ps1` hatten keinen vom Main
  abweichenden Runtime-Delta. Main behielt den neueren `instagram-dm-diagnose`;
  `instagram-dm-smoke` und andere Schema-9-Hardening-Änderungen bleiben im
  separaten Engineering-Branch.
- Main-Commits `fabf172` (Wartungs-Healthcheck/Backup-Skripte) und `39ccc62`
  (kein Katalog-Zeitstempel-Update ohne Inhaltsänderung) getestet und gepusht.
- Windows-Taskdefinitionen, Git-Refs und die operative DB vor dem Cutover
  gesichert. Die DB wurde in den neuen Main-Deployment-Checkout verschoben,
  die bestehende `.venv` und 15 nicht versionierte Runtime-Bilder ebenfalls;
  20 versionierte Bilder waren hashgleich vorhanden. Keine Secrets kopiert.
- Web, Supervisor, Scheduler, Watchdog, drei Wartungs-Tasks und Autostart auf
  `C:\Zippoworkz\Workspace\codex_deploy\creator-collab` umgestellt.
- Fünf historische Worktrees archiviert und gesperrt. Die zwei geänderten
  DM-P1-Dokumente und ein unversioniertes Journal vorher separat hash-geprüft
  gesichert. Das frühere `codex_ingest` war das Git-Hauptverzeichnis: Nach
  vollständig geprüftem Git-Bundle wurde es manuell ins Archiv verschoben und
  alle Link-Worktrees mit `git worktree repair` repariert. Ein leerer Restordner
  blieb wegen lokaler Löschsperre am alten Pfad, ohne Projektdateien.

## Verifiziert

- `origin/main` und Deployment-HEAD vor diesem Dokumentations-Commit:
  `39ccc62950b2e7530a7988e7a7695da51254c471`.
- Vollsuite direkt im Deployment-Checkout: 254 Python-Tests + 24 Subtests;
  7 Node/Dashboard-Tests; Compilecheck; Secret-Scan 408 Dateien; Diff-Check.
- HTTP `/api/health`: `ok`, `database=ok`; Web und Supervisor-Prozesspfade
  zeigen auf Deployment. Kontrollierter Scheduler und Watchdog: Exit 0.
- Operative DB nach Cutover: Schema 8, Integrity `ok`, FK 0, 8 Publications,
  50 Assets, 0 DM-Inbound/Conversations/Outbox. Gegen das Pre-Cutover-Backup
  keine Tabellen- oder Count-Abweichungen beim ersten finalen Start.
- Leona und Mara: read-only Identity-/Conversations-GET erfolgreich, Handles
  passend, gültige erste Seite mit je 0 Conversations. `account_id_match` ist
  aktuell bei beiden `false`; keine Schlussfolgerung zur Ursache ohne Beleg.
  Kein DM-Send und kein DM-Live-Proof.

## Entscheidungen

- Schema-9-Hardening bleibt produktiv **nicht** gemergt: Web-Initialisierung
  würde die operative Schema-8-DB automatisch migrieren. Das widerspricht der
  Anweisung, keine unnötige Migration vorzunehmen. Der Branch ist gesichert
  und ist der eine aktive Engineering-Stand.
- Die DailyTrigger der namentlichen Weekly-/Monthly-Tasks wurden erhalten;
  ihre Skripte überspringen bereits vorhandene Perioden-Backups. Kein neuer
  Zeitplan ohne separaten Auftrag.
- Ältere Handoff-Aussagen „Diagnose unmerged“, „ID-Match true“ oder
  „DM-Live-Proof“ sind keine aktuelle Runtime-Evidence.

## Offen oder blockiert

- `BOT_WORKS=NO`: Noch kein API-sichtbarer Inbound→Send→Reconcile→DELIVERED.
  Der unerklärte ID-Mismatch im read-only Diagnosepfad ist eine separate
  Meta-Prüfung, kein Beleg für fehlende Berechtigung.
- Das Schema-9-Hardening bleibt für einen späteren isolierten Migrations-/
  Integrationsentscheid im Engineering-Branch. Kein Owner-Eingriff für die
  abgeschlossene Runtime-Konsolidierung nötig.
- Ein leerer Restordner `Workspace/codex_ingest/.git` konnte wegen lokaler
  Löschsperre nicht entfernt werden; Git und Runtime benutzen ihn nicht.

## Nächster Agent

1. Nur bei neuem echten DM-Signal den read-only ID-/Inbound-Abgleich und
   anschließend einen kontrollierten Roundtrip prüfen; keinen Erfolg erfinden.
2. Schema-9-Hardening gegen den aktuellen Main isoliert reconciliieren und
   Migration ausschließlich auf DB-Kopie testen, bevor Live-DB berührt wird.
3. Danach erst die nächste Produktfunktion beginnen.
