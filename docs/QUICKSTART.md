# Virtual Creator Codex Bundle – Quickstart

Dieses Bundle ist so strukturiert, dass der Inhalt direkt in ein bestehendes Repository kopiert werden kann.

## Zielstruktur im Repository

```text
/
├── AGENTS.md
└── docs/
    ├── MASTER_HANDOFF_VIRTUAL_CREATORS.md
    ├── PROJECT_CONTEXT_VIRTUAL_CREATORS.md
    ├── CODEX_STARTAUFTRAG.md
    └── OWNER_DECISIONS.md
```

## Schnellste Umsetzung

1. Den Inhalt des Ordners `repo-layout/` in das Root-Verzeichnis des Ziel-Repositories kopieren.
2. Falls dort bereits eine `AGENTS.md` existiert, nicht blind überschreiben: die Virtual-Creator-Regeln als eigenen Abschnitt übernehmen und widersprüchliche ältere Projektregeln entfernen.
3. Einen neuen Codex-Lauf im Repository starten und auf `docs/CODEX_STARTAUFTRAG.md` verweisen.
4. Codex soll zuerst Repository, vorhandenen Code, Konfiguration und Dokumentation untersuchen und danach einen kurzen Ist-Stand samt priorisiertem Umsetzungsplan liefern.
5. Keine Zugangsdaten in Markdown-Dateien speichern. Secrets ausschließlich über die vorgesehene Secret-/Environment-Verwaltung einbinden.

## Direkt nutzbarer Startprompt

```text
Lies zuerst /AGENTS.md und anschließend alle Dateien unter /docs/, insbesondere
/docs/MASTER_HANDOFF_VIRTUAL_CREATORS.md und /docs/CODEX_STARTAUFTRAG.md.
Analysiere danach den vorhandenen Code, erhalte funktionierende Komponenten und
setze den Startauftrag inkrementell um. Arbeite selbstständig innerhalb der
festgelegten Grenzen. Veröffentliche nichts, gib kein Geld aus und führe keine
wesentlichen externen Aktionen ohne ausdrückliche Freigabe aus.
```

## Wichtige Einordnung

- Leona Voss und Mara Field sind die etablierten Kernpersonas.
- Trends sind kurzfristige, optionale Formate und dürfen die Persona nicht verbiegen.
- Fanvue ist die bevorzugte AI-freundliche Bezahlplattform, vorbehaltlich aktueller Regelprüfung vor Anbindung oder Veröffentlichung.
- Der Zielzustand ist hohe Automatisierung mit menschlicher Endfreigabe, nicht vollständig unbeaufsichtigtes Publizieren.
