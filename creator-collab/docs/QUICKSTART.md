# Creator Ops MVP – Quickstart

## Windows

Im Ordner `creator-collab`:

```powershell
.\run_mvp.ps1 -RunDate 2026-09-03
```

Das Skript sucht zuerst ein installiertes `python` und verwendet andernfalls
die gebündelte lokale Codex-Python-Laufzeit. Es führt zuerst alle Tests aus und
startet nur bei erfolgreichem Ergebnis den Evening Run um 20:00 Uhr lokaler
Berliner Zeit für beide Mock-Pipelines.

Nur Tests:

```powershell
.\run_mvp.ps1 -TestOnly
```

## Freigabeoberfläche

```powershell
.\run_dashboard.ps1
```

Im Browser `http://127.0.0.1:4180/` öffnen. Die Oberfläche verwendet
standardmäßig `data/review_dashboard.db` und legt automatisch zwei Pakete für
morgen an:

- fünf registrierte Bilder je Persona
- drei empfohlene Top Picks
- Carousel, Caption, Musik-Fallback und Prime Time geprüft
- ein klarer Freigabe-Button je Persona

Eine Freigabe erstellt ausschließlich einen lokalen `mock-draft`. Es wird kein
Social-Media-Adapter aufgerufen und nichts live veröffentlicht.

## Direkter Python-Aufruf

```powershell
python -m unittest discover -s tests -v
python -m creator_ops.cli --db data/creator_ops.db demo --date 2026-09-03
python -m creator_ops.cli --db data/creator_ops.db evening-run --at 2026-09-03T20:00:00
python -m creator_ops.cli --db data/creator_ops.db engagement --status PROPOSED
python -m creator_ops.cli --db data/creator_ops.db engagement-approve 1
python -m creator_ops.cli --db data/creator_ops.db export --out backups --label latest
python -m creator_ops.cli --db data/creator_ops.db backup --out backups --label latest
python -m creator_ops.cli --db data/creator_ops.db status
```

## Wichtige Eigenschaften

- Live-Publishing ist technisch ausgeschlossen: Der Adapter erzeugt nur
  `mock://`-URLs.
- Approval ist eine ausdrücklich gekennzeichnete Simulation und keine echte
  Veröffentlichungsfreigabe.
- Die SQLite-Datei liegt unter `data/` und wird nicht versioniert.
- Wiederholte Läufe mit gleichem Datum, Creator und Serie verwenden den
  bestehenden Abschlussstand.
- Secrets werden weder in Konfiguration noch Datenbank gespeichert.
- Der Evening Run arbeitet nur von 19:00 bis 22:00 Uhr in `Europe/Berlin`.
- `engagement` liefert Vorschläge; auch freigegebene Einträge werden niemals
  automatisch ausgeführt.
- JSON-Exporte lassen das Feld `secret_reference` grundsätzlich aus.
- SQLite-Backups werden nach dem Schreiben mit `PRAGMA integrity_check` geprüft.
