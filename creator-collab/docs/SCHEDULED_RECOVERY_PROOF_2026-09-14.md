# Scheduled Recovery Proof — 14.09.2026

## Zweck

Nachweis, dass der aktuelle owner-freigegebene ZippoWorkz-Stand aus dem
Approval-Backup wiederherstellbar ist und bei fehlendem offiziellen
Instagram-Adapter sicher blockiert, ohne Doppelposts oder Fake-Receipts zu
erzeugen.

## Quelle

- Kanonische DB:
  `C:\Zippoworkz\Workspace\codex_ingest\creator-collab\data\review_dashboard.db`
- Backup:
  `C:\Zippoworkz\backups\creator-ops-backup-ai-ops-approved-20260914.db`
- Wiederholbares Prüfskript: `scripts/validate_scheduled_recovery.py`

## Ergebnis

- Restore in eine frische temporäre SQLite-Datenbank: erfolgreich.
- Schema: 5.
- `PRAGMA integrity_check`: `ok`.
- Foreign-Key-Verstöße: 0.
- Kernzählungen identisch:
  - Creators: 2
  - Contentpakete: 2
  - Assets: 10
  - Plattformvarianten: 2
  - Publikationen: 2
  - Queuejobs: 2
- Simulierter erster fälliger Dispatch mit ausdrücklich unkonfiguriertem
  Adapter: 2 fällig, 0 veröffentlicht, 2 sicher blockiert.
- Zweiter Dispatch: 0 fällig, 0 veröffentlicht. Kein erneuter Send-Versuch.
- Reconciliation: 0 neue Jobs, 0 neue Publikationen.
- Queue-Schlüssel unverändert; Queue-Anzahl unverändert.
- Externe IDs, Permalinks und `published_at`: weiterhin leer.
- Fake-Receipts: keine.
- Externe Aktionen: keine.

## Schutz der echten Datenbank

SHA-256 vor und nach dem gesamten Proof:

`C705EB48C0408B9A25AD313B29ED653A439FC484868D28DF34C1DF5663344A32`

Der Hash ist identisch. Die echte kanonische Datenbank wurde nicht verändert.
Die temporäre Restore-Kopie wurde nach dem Test entfernt.

## Wiederholen

```powershell
python scripts\validate_scheduled_recovery.py `
  --backup C:\Zippoworkz\backups\creator-ops-backup-ai-ops-approved-20260914.db
```

Das Skript verwendet ausschließlich `UnconfiguredInstagramAdapter` und kann
deshalb selbst bei vorhandenen Credentials keine Plattformaktion auslösen.
