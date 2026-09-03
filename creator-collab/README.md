# Creator Collaboration Workspace

Dieser Ordner ist die gemeinsame, versionskontrollierte Übergabeschicht für
ChatGPT und Codex.

## Lesereihenfolge

1. `PROJECT_RESUME.md` – stabiler Gesamtstand und Leitplanken
2. `CURRENT_HANDOFF.md` – unmittelbar nächste Aufgaben und Blocker
3. `sessions/` – chronologische Sitzungsjournale mit Belegen

## Schreibregel

Am Ende jeder Arbeitssitzung werden ein neues Journal und der aktuelle Handoff
aktualisiert. Geheimnisse und Login-Daten gehören niemals in dieses Repository.

## Lokaler Creator-Ops-MVP

Der MVP bildet den vollständigen Freigabe- und Lernpfad lokal ab. Er verwendet
SQLite und ausschließlich Mock-Publishing; es werden keine Social-Media-APIs
aufgerufen und nichts live veröffentlicht.

```powershell
python -m creator_ops.cli --db data/creator_ops.db demo --date 2026-09-03
python -m creator_ops.cli --db data/creator_ops.db evening-run --at 2026-09-03T20:00:00
python -m creator_ops.cli --db data/creator_ops.db engagement
python -m creator_ops.cli --db data/creator_ops.db export --out backups --label latest
python -m creator_ops.cli --db data/creator_ops.db backup --out backups --label latest
python -m creator_ops.cli --db data/creator_ops.db status
python -m unittest discover -s tests -v
```

Die lokale Freigabeoberfläche startet separat:

```powershell
.\run_dashboard.ps1
```

Danach ist sie unter `http://127.0.0.1:4180/` erreichbar. Sie bereitet für den
nächsten Tag je eine Review-Karte für Leona und Mara vor. „Freigeben“ erzeugt
nur einen lokalen, auditierbaren `mock-draft`; es gibt keinen Live-Publisher.

Enthalten sind:

- zentrale Leona-/Mara-Konfiguration
- Asset Registry mit fünf Kandidaten und drei Top Picks
- QA-, Duplikat-, Rechte- und KI-Disclosure-Prüfung
- Review- und Approval-Simulation
- Prime-Time-Scheduling für `Europe/Berlin`
- harte Evening-Run-Schranke von 19:00 bis 22:00 Uhr
- Prime-Time-Lernen aus 7-Tage-Metriken und Kollisionsvermeidung
- Audio-Adapter mit lizenzsicherem „ohne Musik“-Fallback
- Primary-/Alternate-/Reserve-Plan für jedes Asset-Paket
- Engagement-Vorschlagsqueue ohne automatische externe Aktionen
- geheimnisfreier JSON-Export und integritätsgeprüftes SQLite-Backup
- visuelle Morgen-Freigabe für Leona und Mara
- `MockPublisher`
- Analytics-Snapshots nach 24, 72 und 168 Stunden
- einfache Learning-Entscheidung anhand mehrerer Qualitätsmetriken
- idempotenter Abend-Lauf ohne Doppelgenerierung
