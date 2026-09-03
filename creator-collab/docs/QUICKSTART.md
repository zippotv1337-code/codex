# Creator Ops MVP – Quickstart

## Windows

Im Ordner `creator-collab`:

```powershell
.\run_mvp.ps1 -RunDate 2026-09-03
```

Das Skript sucht zuerst ein installiertes `python` und verwendet andernfalls
die gebündelte lokale Codex-Python-Laufzeit. Es führt zuerst alle Tests aus und
startet nur bei erfolgreichem Ergebnis die beiden Mock-Pipelines.

Nur Tests:

```powershell
.\run_mvp.ps1 -TestOnly
```

## Direkter Python-Aufruf

```powershell
python -m unittest discover -s tests -v
python -m creator_ops.cli --db data/creator_ops.db demo --date 2026-09-03
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

