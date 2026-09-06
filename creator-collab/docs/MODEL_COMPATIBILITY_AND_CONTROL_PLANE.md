# Modellkompatibilität und Control Plane

Stand: 6. September 2026

## Verbindliche Baseline

Creator Ops benötigt kein angekündigtes oder zukünftiges Modell. Der komplette
Workflow muss mit dem aktuell stabil verfügbaren Modell funktionieren. Mehr
Leistung eines späteren Modells darf Qualität oder Geschwindigkeit erhöhen,
aber keine Route, kein Datenformat und keinen sicheren Betriebsablauf erst
ermöglichen.

Die im Owner-Auftrag genannte Datei
`CREATOR_OPS_MODELLKOMPATIBLER_PITCH_2026-09-05.md` war im Projekt, Desktop und
den verfügbaren Übergabeanhängen nicht vorhanden. Deshalb wurden keine Inhalte
dieser fehlenden Quelle erfunden. Die ausdrücklich im Owner-Auftrag genannten
Kompatibilitätsregeln sind direkt umgesetzt.

## Optionaler Astra-Pfad

`config/model_routing.toml` bevorzugt `gpt-6-astra` mit Reasoning `high`, wenn
die laufende Umgebung dieses Modell tatsächlich anbietet. `gpt-5.6-sol` bleibt
der stabile Fallback; kennt die Runtime keines von beiden, bleibt Creator Ops
mit ihrem Runtime-Default arbeitsfähig. Weder Datenbank, Queue, Dashboard noch
Publishing hängen von Astra ab.

Der aktuelle Stand ist bewusst ein validierter Routing-Vertrag plus reiner
Resolver. Die Control Plane veröffentlicht diese Policy mit
`selected_model = null` und `selection_source = resolved-at-runtime`; sie fragt
noch kein externes Modellinventar ab und startet keinen Modell-Executor. Eine
echte Auswahl darf später nur an einem kostenlosen/owner-freigegebenen
Executor-Adapter erfolgen. Bis dahin ist „Astra unterstützt“ nicht gleich
„Creator Ops führt selbst Astra-Aufträge aus“.

Am 6. September wurde Astra HIGH getrennt vom Creator-Ops-Laufzeitprozess als
read-only Codex-Zweitprüfung eingesetzt. Diese Prüfung fand drei P1-Risiken,
die anschließend behoben und nachgeprüft wurden. Sie aktiviert keinen Executor
im Produkt, speichert keinen Schlüssel und macht Astra nicht zur Voraussetzung.

Der Modellname und die Reasoning-Stufen wurden am 5. September 2026 gegen die
[offizielle OpenAI-Modellseite](https://developers.openai.com/api/docs/models/gpt-6-astra)
geprüft. Creator Ops ruft dadurch noch keine OpenAI-API auf, speichert keinen
API-Schlüssel und erzeugt keine zusätzlichen Kosten.

## P1: Control Plane / Autopilot

Die Route `/control` läuft auf demselben Python-/SQLite-Kern und unter denselben
Login-, Session-, CSRF- und LAN-/Remote-Schutzregeln wie das bestehende
Dashboard. Es gibt kein zweites Backend und keine zweite Datenbank.

`GET /api/control-plane` liefert einen versionierten Vertrag mit:

- Baseline `stable-current-model`
- spätere Modellleistung `optional-capability-bonus`
- expliziter Rückwärtskompatibilität
- Capability-Matrix statt Modellnamen
- lokaler Arbeitsqueue und unveränderten Owner-Gates

Sichere POST-Kommandos sind `run-once`, `pause`, `resume` und `checkpoint`.
Sie verändern ausschließlich den lokalen, atomar geschriebenen Speicherstand
`data/autopilot_control.json`. `run-once` prüft die lokale Review-Queue und
checkpointet den nächsten Fortsetzungspunkt. Eine Publishing-, Engagement-,
Account- oder Zahlungsaktion existiert in dieser Control Plane nicht.

## P2: große Instagram-artige Vorschau

Jede Reviewkarte besitzt `Große Instagram-Vorschau`. Das Overlay zeigt die
Top 3 in ihrer echten Carousel-Reihenfolge, ein großes 4:5-Bild, Persona,
Caption, Pose, Qualität und Prime Time. Pfeiltasten, Vor/Zurück-Schaltflächen,
Escape und mobile Einspaltendarstellung werden unterstützt.

Die Darstellung ist ausdrücklich eine lokale Layout-Vorschau. Sie imitiert
keine Instagram-Anmeldung und besitzt keinen Plattformadapter.

## Rückwärtskompatibilität

- keine Migration und keine neue externe Abhängigkeit
- bestehende Review-/Asset-/Publishing-Daten unverändert
- neue API und neue Seite ausschließlich additiv
- alte Clients können alle bisherigen Routen weiterverwenden
- unbekannter oder beschädigter Control-State fällt auf einen sicheren
  `IDLE`-Default zurück
- externe Fähigkeiten bleiben Capability `OWNER_GATE`
