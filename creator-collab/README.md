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
python -m creator_ops.cli --db data/creator_ops.db status
python -m unittest discover -s tests -v
```

Enthalten sind:

- zentrale Leona-/Mara-Konfiguration
- Asset Registry mit fünf Kandidaten und drei Top Picks
- QA-, Duplikat-, Rechte- und KI-Disclosure-Prüfung
- Review- und Approval-Simulation
- Prime-Time-Scheduling für `Europe/Berlin`
- `MockPublisher`
- Analytics-Snapshots nach 24, 72 und 168 Stunden
- einfache Learning-Entscheidung anhand mehrerer Qualitätsmetriken
- idempotenter Abend-Lauf ohne Doppelgenerierung
