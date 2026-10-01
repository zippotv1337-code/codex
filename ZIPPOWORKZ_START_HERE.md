# ZIPPOWORKZ_START_HERE

Status: CANONICAL BOOTSTRAP
Stand: 01.10.2026

## Zweck

Diese Datei ist der Einstiegspunkt für jeden neuen ZippoWorkz-Chat, Work-Run,
Codex-Run, VPS-Run, Local-AI-Run und Creator-Ops-Run.

Chat-Memory ist hilfreich, aber niemals die alleinige Projektwahrheit.

## Verbindliche Lade-Reihenfolge

1. ZIPPOWORKZ_OWNER_POLICY.md vollständig lesen.
2. Aktuellen Projekt-/Runtime-Status lesen, soweit für die Aufgabe relevant.
3. Bei creator-collab:
   - creator-collab/PROJECT_RESUME.md
   - creator-collab/CURRENT_HANDOFF.md
   - neuestes Sitzungsjournal
4. Nur danach aufgabenbezogene Detaildateien laden.
5. Delta-Ingest / gezielte Reads bevorzugen, keinen unnötigen Vollscan.

## Konfliktregel

Bei Widerspruch gilt die Rangfolge aus ZIPPOWORKZ_OWNER_POLICY.md.

Insbesondere:
- keine alten Owner-Decisions über die aktuelle Policy stellen,
- keine historische Handoff-Datei als aktuelle Owner-Freigabe behandeln,
- keine Chat-Erinnerung verwenden, um GitHub-Policy zu überschreiben,
- keine bereits dokumentierte Owner-Entscheidung erneut abfragen.

## Zwei Arten von Wahrheit

Dauerhafte Regeln / Rechte / Gates:
ZIPPOWORKZ_OWNER_POLICY.md

Aktueller Live-Zustand:
Current State, Dashboard, Handoffs, Runtime-Evidence und aktuelle Logs.

Eine Runtime-Datei darf keine neuen Owner-Rechte erfinden.
Die Owner-Policy darf keine volatilen Runtime-Zahlen vortäuschen.

## Neue Owner-Entscheidung

Wenn der Owner eine dauerhafte Regel ausdrücklich ändert:
1. ZIPPOWORKZ_OWNER_POLICY.md aktualisieren,
2. Policy-Version erhöhen,
3. Änderung committen und pushen,
4. alle Agenten verwenden danach dieselbe Version.

Keine separaten Owner-Policies pro VPS, Local AI, Codex oder Creator Ops anlegen.

## Kurzform

Memory hilft.
START_HERE erklärt die Ladefolge.
OWNER_POLICY entscheidet die Regeln.
CURRENT STATE sagt, was jetzt tatsächlich läuft.

## AI-Team / Claude-Codex

Verbindlicher Arbeitsstil: Owner setzt Ziel -> Claude schneidet Root-Cause/Plan -> Codex implementiert/testet -> Reality-Check.
Owner wird nur bei echten Owner-Gates benötigt. Fehlende technische Evidence ist kein erfundenes Owner-Gate.
Für gemeinsame Claude/Codex-Arbeit gilt zusätzlich:
C:\Zippoworkz\Context\Sync\CLAUDE_CODEX_COLLABORATION.md
Single-writer: keine parallelen Änderungen am selben Datei-/Codesatz.
