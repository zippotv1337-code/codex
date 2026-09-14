# Meta Business Suite - Publishing-Handoff

Stand: 2026-09-13, Europe/Berlin

## Read-only Befund

Die geöffnete Meta-Business-Suite unter dem Business-Portfolio `118371629931703`
zeigt beide projektbezogenen Instagram-Konten:

- `@leonavoss.ai` (Asset-ID `17841429962539023`)
- `@mara.field.ai`

Die Oberfläche bietet im Bereich „Erstellen“ die Contenttypen Beitrag, Reel und
Story. Der Bereich „Content“ ist im Business-Portfolio verlinkt und eignet sich
für die native Terminierung.

## Einordnung für ZippoWorkz

Business Suite ist ein offizieller, eingeloggter UI-Weg und kann als sicherer
Publishing-Handoff verwendet werden. Der bestehende ZippoWorkz-Graph-Adapter ist
davon getrennt: `config.toml` steht aktuell auf `publishing.adapter = "unconfigured"`
und `live_enabled = false`. Daraus folgt kein API-Live-Proof.

Der kleinste robuste Ablauf ist:

1. ZippoWorkz validiert Persona, Contenttyp, SFW-/Rechte-Gate, Caption, Assets
   und Termin.
2. Der Handoff öffnet den Business-Suite-Composer im richtigen Konto.
3. Der Owner prüft die Vorschau und bestätigt den finalen „Planen“-/„Veröffentlichen“-Schritt.
4. Danach werden sichtbare Bestätigung, Termin und gegebenenfalls Permalink lokal
   als Receipt eingetragen.

Keine beliebigen Shell-Kommandos, keine Zugangsdaten im Projekt und kein
automatischer Browser-Loop. Ein echter offizieller Graph-Publish bleibt an
Meta-Credentials, HTTPS-Asset-URLs und den vorhandenen Safety-Gates gebunden.

## Status

- `BUSINESS_SUITE_ACCOUNTS_VISIBLE`: bestätigt (read-only)
- `BUSINESS_SUITE_SCHEDULING`: im UI verfügbar, für konkreten Post noch nicht ausgeführt
- `META_GRAPH_AUTOMATION_PROOF`: nicht bewiesen
- `EXTERNAL_ACTIONS_THIS_CHECK`: keine

## Für den nächsten konkreten Publish

Benötigt werden genau: Persona, Paket/Contenttyp und gewünschter Zeitpunkt.
Ohne diese Auswahl wird nichts geplant. Der letzte Klick auf „Planen“ oder
„Veröffentlichen“ bleibt ein eigener, sichtbarer Owner-Schritt.
