# WORK 001–005 — P0 Delta Matrix

Status: `PHASE_A_COMPLETE / FINAL_RECONCILIATION_APPENDED`

Baseline: WORK 001–005 vom 25.09.2026, zusammengefasst in
`CODEX_WORK001_005_P0_DELTA_RUN.md`

Vergleichsstand: `origin/main` / `79a08e34cc1630b3220102c36a477eabc1c59be5`

Bewertung: 29.09.2026

Die ursprünglichen fünf Einzeldokumente sind weder im aktuellen Git-Baum noch
in den Archiv-Tags `archive/ai-ops-20260913-final` und
`archive/20260928-next-stack-final` enthalten. Diese Matrix verwendet deshalb
die vollständige materielle Baseline des aktuellen Delta-Auftrags; alte
Dateinamen oder vorgeschlagene Verzeichnisbäume werden nicht als Selbstzweck
rekonstruiert.

| Requirement/source | Original intent | Current evidence/path | Classification | Remaining delta | Action |
|---|---|---|---|---|---|
| WORK 001 · eindeutige Ladefolge | Neue Runs ohne alte Chats arbeitsfähig machen | `ZIPPOWORKZ_START_HERE.md`, Root-`AGENTS.md`, `creator-collab/AGENTS.md` | `EXPANDED` | Kein funktionales Delta | Aktuelle Struktur bewahren |
| WORK 001 · eine Policy-Hierarchie | Dauerhafte Rechte und Gates eindeutig ordnen | `ZIPPOWORKZ_OWNER_POLICY.md` v1.2 ist projektweit kanonisch | `EXPANDED` | Kein Policy-Delta; Policy darf in diesem Run nicht geändert werden | Nur referenzieren |
| WORK 001 · alte Owner-Decisions entschärfen | Parallele aktive Policies verhindern | `OWNER_DECISIONS.md` und Root-`docs/OWNER_DECISIONS.md` sind bereits reine Policy-Pointer | `DONE` | Keines | Unverändert lassen |
| WORK 001 · vorgeschlagener `context/state/handoff/archive`-Baum | Verantwortlichkeiten trennen | START_HERE + Policy + CurrentStateService + Handoff/Journale lösen das Problem ohne zweite Baumstruktur | `SUPERSEDED_BY_BETTER_CURRENT_DESIGN` | Keines | Keinen Parallelbaum anlegen |
| WORK 001 · aktueller Handoff statt konkurrierender Aufgabenlisten | Neueste Evidenz von Historie trennen | `CURRENT_HANDOFF.md` hat aktuelle Kopfabschnitte, danach aber alte Abschnitte mit historischem `AKTUELL`-Wortlaut | `OPEN` | Harte Leseregel und historische Grenze fehlen | Pointer-/Grenzmarker ergänzen, nichts löschen |
| WORK 002 · bestehender Runtime-Snapshot | Einen geheimnisfreien, dynamischen Statusgenerator verwenden | `creator_ops/current_state.py::CurrentStateService`, CLI `status`, `/api/status` | `EXPANDED` | Snapshot braucht explizite Rollen-/Quellenprovenienz | Additive Metadaten ergänzen |
| WORK 002 · kein zweiter Statusgenerator | JSON/Handoff nicht zu manueller Runtime-Wahrheit machen | `docs/CURRENT_STATE.json` wird aus `CurrentStateService` erzeugt; Handoff ist Evidence | `DONE` | Keines | Generator beibehalten |
| WORK 002/004 · genau eine operative DB | `data/review_dashboard.db` als operative Wahrheit | `config.toml`, Web/Launcher, Backups und Architektur nutzen die kanonische DB; CLI-Default zeigt noch auf `data/creator_ops.db` | `OPEN` | CLI-Default und README-Kopf sind legacy-driftig | Default auf kanonische DB; Demo gegen operative DB fail-closed |
| WORK 002/004 · Legacy-DBs nicht blind mergen | Historisch/Fixture/Backup von operativ unterscheiden | README markiert `creator_ops.db` und `verification.db` als Legacy; Current State listet sie als `legacy_databases` | `DONE` | Keines | Keine Migration, kein Merge |
| WORK 002/004 · Migration nur mit Backup/Tests/Rollback | Datenrisiko kontrollieren | additive Schema-Migrationen, Recovery-Services und Schema-6-Backups sind getestet | `EXPANDED` | Kein Schema-Delta in diesem Run | Architektur schützen |
| WORK 003 · alten AI-Branch nicht blind mergen | Divergente historische Implementierung selektiv behandeln | `docs/AI_BRANCH_DELTA_REPORT_2026-09-28.md` | `SUPERSEDED_BY_BETTER_CURRENT_DESIGN` | Keines | Nicht wieder öffnen |
| WORK 003 · brauchbare AI-/Security-Deltas portieren | Nur aktuelle, sinnvolle Teile übernehmen | wertfreier Secret-Scanner und optionaler Pre-Push-Guard sind auf Main | `EXPANDED` | Keines | Bestehende Tests erneut ausführen |
| WORK 003 · Altbranch archivieren/retiren | Geschichte erhalten, aktive Parallelentwicklung beenden | Tag `archive/ai-ops-20260913-final`; aktiver Branch entfernt | `DONE` | Keines | Historische Evidenz bewahren |
| WORK 003 · Secret-Erkennung fail-closed und wertfrei | Secrets verhindern, Werte nie ausgeben | `creator_ops/secret_scan.py`, `tests/test_secret_scan.py` | `EXPANDED` | Kein Code-Delta | Tracked-Scan im Abschluss ausführen |
| WORK 003 · Publishing-/Testisolation | Tests dürfen nie echte Publishes auslösen | fail-closed Isolation aus AI-Integration plus Adaptertests | `EXPANDED` | Kein Code-Delta | Relevante Suite ausführen |
| WORK 003 · getrackte öffentliche/generierte Medien | Absicht, Rechte und Herkunft der öffentlichen Assets belegbar machen | 44 getrackte Dateien; Provenienz ist über mehrere Paketdocs/Journale verteilt | `OPEN` | Ein kompakter paketweiser Provenienznachweis fehlt; einzelne Rechte bleiben `NOT_VERIFIED` | Nicht-destruktiven Manifestbericht erstellen |
| WORK 003 · aktive Release-/Binary-Artefakte | Alte ausführbare/ZIP-Artefakte nicht als aktuellen Release behandeln | Keine getrackten `.zip/.7z/.rar/.exe/.msi/.db/.sqlite/.dll` im aktuellen Baum | `DONE` | Keines | Ergebnis dokumentieren |
| WORK 004 · Git/Creator Ops/Local AI/VPS Rollen | Operative Wahrheit und Evidence klar trennen | Owner Policy §§14/18, `docs/ARCHITECTURE.md`, explizite Job-/Evidence-Rollen | `EXPANDED` | Kein neuer Austausch-Layer erforderlich | Keine zweite DB oder App bauen |
| WORK 004 · abgeleitete Zustände mit Zeit/Provenienz | UNKNOWN statt erfundener Werte; Quelle sichtbar | `generated_at`, `NULL/UNKNOWN`, DB-/Config-Ableitung vorhanden | `OPEN` | `CURRENT_STATE` benennt Rolle, kanonische DB, Config und Policy-Hash noch nicht maschinenlesbar | Additiven `state_contract` ergänzen |
| WORK 005 · kleine reversible Changesets und geordnete Abnahme | P0.1 → P0.2 → P0.3, Tests und Rollback | AI-/Next-Stack-Integrationen sind in kleinen, getesteten Commits abgeschlossen | `HISTORICAL_ONLY` | Nur die vier oben benannten Deltas bleiben | Getrennte Checkpoint-Commits, dann Validierung |

## Summary

- `DONE`: 5
- `EXPANDED`: 8
- `SUPERSEDED_BY_BETTER_CURRENT_DESIGN`: 2
- `OPEN`: 4
- `BLOCKED_BY_OWNER_GATE`: 0
- `HISTORICAL_ONLY`: 1

## Verbleibender sicherer P0-Umfang

1. `CURRENT_HANDOFF.md` als abgeleitete Evidenz markieren und historische
   Abschnitte eindeutig vom aktuellen Kopf trennen.
2. CLI-Default auf `data/review_dashboard.db` setzen; `demo` gegen diese DB
   explizit verweigern und README/Tests an Schema 6 angleichen.
3. `CurrentStateService` um maschinenlesbare, wertfreie Provenienz ergänzen,
   ohne eine zweite Policy oder einen zweiten Statusgenerator zu schaffen.
4. Die 44 getrackten Medien paketweise klassifizieren; ungeklärte Rechte
   bleiben ausdrücklich `NOT_VERIFIED`. Nichts löschen und keine Historie
   umschreiben.

Keine externe Plattformaktion, kein Kostenereignis, kein Secret, keine neue DB,
keine neue Policy und keine neue Dashboard-Anwendung gehören zu diesem Delta.

## Final reconciliation

Nach Umsetzung und Verifikation wurden die vier `OPEN`-Zeilen so geschlossen:

| Vorher offenes Delta | Ergebnis | Finale Klassifikation |
|---|---|---|
| Handoff-Grenze | Der Kopf benennt Rolle und Quellen; eine sichtbare Grenze macht alle älteren Abschnitte zu historischer Evidence. | `EXPANDED` |
| Kanonischer CLI-DB-Vertrag | CLI-Default ist `review_dashboard.db`; `demo` verweigert diese DB fail-closed; README nennt Schema 6. | `EXPANDED` |
| Asset-Provenienz | 44 Dateien sind paketweise in `TRACKED_ASSET_PROVENANCE_2026-09-29.md` klassifiziert; ungeklärte Rechte werden nicht erfunden. | `BLOCKED_BY_OWNER_GATE` für spätere Wiederverwendung der drei unvollständig belegten Pakete |
| Current-State-Provenienz | `state_contract` nennt Rolle, operative DB, Config, Policy-Version und Policy-Hash; der Kompatibilitätsblock ist ausdrücklich nicht autoritativ. | `EXPANDED` |

Finale Summenzählung:

- `DONE`: 5
- `EXPANDED`: 11
- `SUPERSEDED_BY_BETTER_CURRENT_DESIGN`: 2
- `OPEN`: 0
- `BLOCKED_BY_OWNER_GATE`: 1
- `HISTORICAL_ONLY`: 1
