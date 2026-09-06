# Creator Ops Backup-/Restore-Kette

Aktuelle Owner-Regel:

- Mini-Journal nach jedem Autopilot-Run.
- Normale kleine Deltas als manifestiertes Patch-Backup.
- Full-/Meilenstein-Backup nur bei begründetem technischen Meilenstein.
- SQLite wird niemals als selbstgebautes Binärdelta gespeichert; jedes Patch-
  ZIP enthält eine sanitizierte vollständige SQLite-Momentaufnahme.
- Nach vier bis fünf Patches wird ein neuer Full-Stand geprüft, aber nicht
  automatisch erzwungen.

## Gültige Basis vor 1.4

- `backups/creator-ops-backup-post-revenue-first-v130.db`
- SHA256:
  `99A8AF434095B9F9DB1318EDABECA214D754E18954410EF8B9DDE7C9FA5F56FB`
- Integrität: `ok`, Schema 4.

## 1.4-Meilenstein

- `backups/Backup_Meilenstein_20260905-1308.zip`
- SHA256:
  `02BC196D60787F2F7C68A49644C43D7A6076468F57DAFA7E04811023F0729F82`
- Begründung: additive Schema-5-Migration mit durable Publish Queue,
  Background-Run-State, DB-Lease und Recovery-Validierungsänderung.
- Enthält sanitizierte SQLite-Kopie; Member-Hashes validiert.

Zusätzlicher direkter SQLite-Restore-Punkt:

- `backups/creator-ops-backup-post-v140.db`
- SHA256:
  `10F7EB0CEC1ECF94A7AB9DAFA2D10C55CA555B494D194F044609C7C578F444FC`
- Real in `tmp/restore-v140-20260905-1310.db` wiederhergestellt:
  Integrität `ok`, Schema 5, drei Queuejobs.

## Restore-Reihenfolge

1. Letztes gültiges Meilenstein-ZIP validieren.
2. Abschluss-Patch `Patch_v140-final-docs_20260905-1309.zip` anwenden; SHA256
   `AD7167703DB5E5BB4074549B601AF84D6BE92464A0E715CF835783E32D8BE769`.
3. Release-Index-Patch `Patch_v140-release-index_20260905-1310.zip` anwenden;
   SHA256
   `0D727D1C42B15F06AFD60BA9A24DDA04AF5461591D0255177D0E531E6A69608C`.
4. Darin enthaltene `recovery/creator_ops.db` in einen frischen Zielpfad
   extrahieren und `PRAGMA integrity_check` ausführen.
5. Nachfolgende Patch-ZIPs in Manifest-Reihenfolge prüfen und anwenden.
6. Niemals eine laufende Datenbank blind überschreiben; zuerst Server stoppen
   und in einen frischen Zielpfad wiederherstellen.

## 1.4.1 High-Autopilot-Abschluss

- `backups/creator-ops-backup-high-autopilot-final-20260905-193722.db`
- SHA256:
  `2142C60A9D874C05CC7D137D8B0437F3989D4E8107D2DCA0D5E21CEBB942C985`
- Frischer Restore:
  `tmp/restore-check-v141-20260905-193722.db`
- Verifiziert: SQLite-Integrität `ok`, sechs Inhalte, drei Queuejobs.
- Der Snapshot entstand nach Datenreparatur und vor den rein statischen
  Abschlussdokumenten; es wurden keine Secrets oder externen Zugangsdaten
  ergänzt.

## 1.6.4-beta Live-Safety-Meilenstein

- `backups/Backup_Meilenstein_20260906-0809.zip`
- SHA256:
  `e937c16d6e80c52bc9d96ee746f6f71989d3a5687bb7cf26bd3bf553b6b41401`
- Größe: 51.535.236 Bytes.
- Frischer Restore:
  `tmp/restore-check-20260906-080949/recovery/creator_ops.db`
- Verifiziert: SQLite-Integrität `ok`, sechs Inhalte, sechs Publikationen,
  drei Queuejobs und null `secret_reference`-Einträge.
- Das Archiv enthält `config.toml`, Standalone-Start/Stop und alle aktuell
  vorhandenen schema-validierten Meta-Receipts. Beim Erstellen existierten
  noch keine Meta-Receipts, weil dieser Run keinen Live-Publish ausführte.
