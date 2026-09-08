# Sitzungsjournal — Analytics Capture bereit

- Datum/Zeit: 2026-09-08, 12:52 Europe/Berlin
- Agent: Codex
- Ziel: T-002 sinnvoll erweitern, ohne reale Werte zu erfinden oder eine zweite Analytics-Architektur zu bauen.

## Ausgangslage

Der bestehende Analytics-Service hatte bereits pro echter Publication getrennte 24-/72-/168-Stunden-Fenster und einen append-only Owner-Import über die CLI. Live-Stand: vier echte Instagram-Publikationen, null echte Snapshot-Ereignisse, fünf fällige Fenster und zwölf UNKNOWN-Fenster. Diese Zustände wurden nicht als schlechte Performance oder als Nullwerte interpretiert.

## Durchgeführt

- Bestehenden Analytics-Service erweitert: Vergleich Leona/Mara über jeweils neuesten realen Snapshot je Publication, Top-Posts der letzten 7/30 Tage, vorsichtige Muster für Format/Thema/Hook/Postingzeit und eine nachvollziehbare Learning-Entscheidung.
- Ohne echte Werte lautet die Entscheidung ausdrücklich `UNKNOWN`. Bei wenigen Werten bleibt sie vorsichtig `VARIATE`; erst aus mindestens zwei gleichartigen realen Beispielen wird ein Muster angezeigt. Kein automatischer Content- oder Postingwechsel.
- `/analytics` zeigt nun alle vorhandenen Metriken und bietet nur für fällige 24/72/168h-Fenster ein lokales Owner-Formular. Werte werden als `MANUAL_OWNER` append-only importiert; mindestens ein echter Wert ist nötig. Der Vorgang ruft keine Instagram- oder Meta-API auf und setzt keinen Publish.
- Dashboard nach Code-Änderung kontrolliert neu gestartet; Health weiterhin ok.

## Verifiziert

- 32 gezielte Python-Tests grün, inklusive echter Test-HTTP-Capture: leeres Formular → 409, echter Wert → lokales Event und `CAPTURED` bei erneutem Lesen. Kein externer Versand.
- Analytics-JavaScript-Syntax grün.
- Laufender lokaler Vertrag: vier reale Publikationen, fünf DUE-Fenster, null CAPTURED, Leona/Mara beide sichtbar, Learning `UNKNOWN`.

## GOAL UPDATES

| Goal ID | Before | After | Evidence | Next |
|---|---|---|---|---|
| M-02 | ACTIVE | ACTIVE | Capture, Vergleich und Learning lokal aktiv; 32 Tests grün | reale Insights importieren |
| T-002 | ACTIVE | ACTIVE — READY_FOR_REAL_VALUES | `/analytics` mit fünf fälligen Fenstern | erster realer 24h/72h/168h Snapshot |
| T-003 | NEXT | NEXT | nicht geöffnet | Fiverr Output-Run |
| E-001 | LIVE_OWNER_REPORTED | LIVE_OWNER_REPORTED | keine neuen Signale | warten |

## Offen oder blockiert

Echte Instagram-Insights sind noch nicht im Workspace verfügbar. Für die aktuell fälligen Fenster müssen ausschließlich die sichtbaren Werte aus dem richtigen Instagram-Insights-Screen übertragen werden. Kein Wert bedeutet `UNKNOWN`, nicht 0. Meta bleibt `WAITING_SIGNAL`.

## Nächster Agent

1. Reale Analytics eintragen, sobald sichtbar verfügbar.
2. Fiverr Gig 1 in separatem Output-Run öffentlich verifizieren/veröffentlichen.
3. GoFundMe erst bei einem echten Spenden-, Share- oder Feedbacksignal bewerten.
