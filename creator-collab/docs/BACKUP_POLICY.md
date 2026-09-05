# Backup-Policy

Creator Ops löscht keine älteren Backups automatisch. Die aktuelle Owner-Regel
ist meilensteinbasiert; ältere Wochen-/Monats-Skripte bleiben nur als manuell
aufrufbare Kompatibilitätswege bestehen.

- Journal: nach jedem Autopilot-Run.
- Pre-change: SQLite-Backup plus `PRAGMA integrity_check` vor kritischen Deltas.
- Normaler Run: manifestiertes Patch-Backup mit Basis-Hash, Restore-Reihenfolge,
  geänderten Dateien und vollständiger sanitizierter SQLite-Kopie.
- Full: nur bei begründetem Meilenstein, etwa Schema-, Auth- oder Control-Plane-
  Änderung.
- Nach vier bis fünf Patches wird ein neuer Full-Stand geprüft, aber nicht
  allein wegen der Anzahl erzwungen.
- Ziel: zuerst `Desktop\CreatorOps_Backups`, sonst `creator-collab\backups`.
- Alle Recovery-Archive enthalten eine bereinigte SQLite-Kopie, Manifest und
  tatsächlich validierte SHA256-Prüfsummen je Member.
- `secret_reference` wird in der Recovery-Kopie geleert. `.env`, Cookies,
  Schlüssel, Remote-Sitzungsdateien, bestehende Backups und Exporte sind
  ausgeschlossen.
- Weitere `.db`-/SQLite-Dateien werden nicht ungeprüft in Full-Archive kopiert.
- Die gültige Kette steht in `docs/BACKUP_CHAIN.md`.

Manuell testen:

```powershell
.\scripts\run_weekly_backup.ps1
.\scripts\run_monthly_full_backup.ps1
.\scripts\install_backup_tasks.ps1          # Dry Run
.\scripts\install_backup_tasks.ps1 -Apply   # bewusste lokale Einrichtung
```

Die automatische Installation dieser Legacy-Zeitpläne ist nicht mehr als
Owner-Aufgabe empfohlen.
