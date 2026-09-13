# Sitzungsjournal — AI-Ops-Start korrigiert

- Datum/Zeit: 13.09.2026, 22:51 Europe/Berlin
- Agent: `Codex`
- Ziel: erklären und beheben, warum der Startknopf im AI-Ops-Dashboard kein
  sichtbares PowerShell-Fenster öffnet und der Lauf nicht vorankommt.

## Ausgangslage

Das Dashboard lief auf `192.168.188.131:4180`. Die Agentenkarte zeigte
`PAUSED` mit `LOCAL_MODEL_NOT_INSTALLED`; ein Workerprozess verwendete noch
`qwen2.5-coder:3b`. Der UI-Start ist als Hintergrundstart implementiert und
öffnet absichtlich kein Terminalfenster.

## Durchgeführt

- Dashboard-Service-Default auf vorhandenes `qwen3:8b` gestellt.
- Produktions-CLI-Default auf `qwen3:8b` vereinheitlicht; der alte
  `LocalWorker`-Konstruktor-Default bleibt nur für isolierte Test-Fixtures.
- Ein ausdrücklicher Start setzt einen vorherigen `STOPPED`-/`PAUSED`-Zustand
  auf `RUN`, damit der Button nicht nur eine bereits beendete Lease prüft.
- UI-Feedback ergänzt: der Worker läuft im Hintergrund, Status/Ergebnis stehen
  im Dashboard.
- Veraltete Agentenfehler werden bei einem neuen `ONLINE`-Start bzw. bei einem
  erfolgreichen Idle-Lauf gelöscht.
- Bekannten alten Worker kontrolliert über den vorgesehenen Stop-Befehl
  beendet; keinen fremden Prozess verändert.
- Creator-Ops-Server kontrolliert neu gestartet, damit der laufende Prozess
  den korrigierten Code lädt.

## Verifiziert

- `qwen3:8b` ist in Ollama lokal vorhanden.
- Frischer Workerstart mit `--model qwen3:8b` lief ohne externe Aktion; bei
  aktiver Dashboard-Bedienung wurde der Status korrekt `PAUSED`.
- Kontrollierter Server-Neustart: Health `ok`, Datenbank `ok`, Auth aktiv.
- Fokussierte Tests: **23/23 grün** (inklusive Regressionstest für den
  Dashboard-Start mit `qwen3:8b`).
- Python-Compilecheck für geänderte Module: grün.
- Externe Aktionen: `NONE`.

## Entscheidungen

- Kein sichtbares PowerShell-Fenster ist beabsichtigt und sicherer für den
  LAN-Dienst; die UI erklärt dies nun ausdrücklich.
- Nach einem Server-Neustart ist eine erneute Dashboard-Anmeldung normal, da
  lokale Sitzungen nicht dauerhaft fortgeschrieben werden.

## Offen oder blockiert

- Der Browser muss sich einmal neu anmelden, bevor `/api/ai-ops` sichtbar wird.
- Bei aktiver Owner-Bedienung pausiert der Worker automatisch; nach Ruhe kann
  er am gespeicherten Schritt fortsetzen.

## Nächster Agent

1. Im Dashboard neu anmelden und „Lokalen Lauf starten“ einmal testen.
2. Prüfen, dass `qwen3:8b`, `ONLINE`/`IDLE` und kein alter Modellfehler
   angezeigt werden.
3. Erst danach bei Bedarf lokale AI-Ergebnisse unter `C:\Zippoworkz\Handoff`
   ansehen; keine externe Plattformaktion.
