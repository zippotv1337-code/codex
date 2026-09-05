# Modellkompatibilität und Control Plane

Stand: 5. September 2026

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
