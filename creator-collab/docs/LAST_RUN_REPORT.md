# Last Run Report – Creator Ops MVP

Stand: 3. September 2026

## Wichtigste Veränderungen

- Ein eigenständiger lokaler Creator-Ops-MVP wurde unter `creator-collab/`
  implementiert.
- Leona Voss und Mara Field sind zentral in `config/personas.json` definiert.
- Ein SQLite-Schema bildet Creator, Character-Versionen, Assets, Serien,
  Content, Plattformvarianten, Review, Scheduling, Mock-Publishing, Analytics,
  Experimente, Audio, Links, Kosten, Umsatz und Plattformkonten ab.
- Ein vollständiger vertikaler Mock-Lauf funktioniert für beide Personas.
- Ein wiederholter Abend-Lauf erzeugt keine doppelten Inhalte oder Assets.
- Ein Provider-Ausfall endet nachvollziehbar in `PARTIAL_READY` und lässt sich
  anschließend erfolgreich erneut starten.
- Der Evening Run erzwingt 19:00–22:00 Uhr in `Europe/Berlin`.
- Die Prime-Time-Auswahl nutzt nach dem Cold Start historische 7-Tage-Metriken
  und vermeidet zu eng belegte Slots pro Creator.
- Audio-, Asset-Reserve-, Engagement- und Export/Backup-Pfade sind ausführbar.
- Eine lokale, responsive Morgen-Freigabeoberfläche zeigt Leona und Mara als
  getrennte Review-Karten mit fünf Assets, Top 3, Checklist und Freigabe.
- Lokale JPG-, PNG- und WebP-Dateien lassen sich mit SFW- und Rechteangabe in
  vorhandene Review-Slots importieren und erscheinen als echte Previews.
- Fehlende Bilddateien bleiben ehrliche Mock-Kacheln; der Fallback crasht nicht.
- Ein verifiziertes SQLite-Backup wurde erfolgreich in eine frische Datenbank
  zurückgespielt und erneut auf Integrität sowie Kernzahlen geprüft.
- Die Review-UX ist heller, saisonal und zeigt größere Checks, klare Statusfarben,
  eine konkrete Owner-Aufgabe sowie getrennte Porträts für Leona und Mara.

## Größter Fortschritt

Der im Startpaket geforderte End-to-End-Kern läuft für Leona und Mara:

```text
Idea / Series
-> Content Draft
-> 5 Assets
-> QA / Duplicate / Compliance
-> 3 Top Picks
-> Review Queue
-> Approval Simulation
-> Prime-Time Scheduling
-> Mock Publishing
-> Analytics 24h / 72h / 7d
-> Learning Decision
```

Beide Demo-Inhalte endeten im Status `ANALYZED` und erhielten ausschließlich
lokale `mock://`-Publikationsadressen.

## Aktueller MVP-Status

- SQLite + Models: fertig
- Asset Registry inklusive lokalem Bildimport: fertig
- Content-/Series-/Status-Modell: fertig
- Review Queue: fertig
- Scheduling/Prime Time: Cold-Start-Grundlage fertig
- MockPublisher: fertig
- Analytics Simulation: fertig
- Leona Vertical Run: erfolgreich
- Mara Vertical Run: erfolgreich
- Idempotenter Evening Run: erfolgreich
- `PARTIAL_READY` + Retry: erfolgreich
- Audio-Grundlage: drei sichere Kandidatenzustände vorhanden
- Evening-Run-Orchestrierung: fertig
- Prime-Time-History und Slot-Abstand: fertig
- Audio-Adapter plus Safe-No-Audio-Fallback: fertig
- Asset-Plan mit Primary, Alternates und Reserves: fertig
- Engagement Queue ohne automatische Ausführung: fertig
- JSON-Export und SQLite-Backup: fertig
- Lokale Review-/Approval-Oberfläche mit echten Preview-Fallbacks: fertig
- SQLite-Restore: fertig und verifiziert
- Live-Publishing: absichtlich nicht implementiert

## Wichtige Dateien und Module

- `creator_ops/database.py` – Schema, Verbindungen, Persona-Seeding
- `creator_ops/models.py` – Status-, Safety- und Ergebnisobjekte
- `creator_ops/pipeline.py` – Compliance, Statusmaschine, Pipeline,
  MockPublisher, Analytics und Learning
- `creator_ops/scheduling.py` – Evening Window, History-Scoring und Slot-Abstand
- `creator_ops/services.py` – Audio-, Asset-Fallback- und Engagement-Dienste
- `creator_ops/evening.py` – idempotente Evening-Run-Orchestrierung
- `creator_ops/exporting.py` – JSON-Export, SQLite-Backup und Restore
- `creator_ops/asset_import.py` – lokaler, hashbasierter SFW-Bildimport
- `creator_ops/review.py` – Morgen-Pakete, Read Model und auditierbare Freigabe
- `creator_ops/web.py` – lokale HTTP-/JSON-Oberfläche
- `dashboard/` – responsive Arbeitsfläche ohne externe Abhängigkeiten
- `creator_ops/cli.py` – `init`, `demo` und `status`
- `config/personas.json` – zentrale Persona-Daten
- `config/prime_time.json` – anpassbare Cold-Start-Zeitfenster
- `tests/test_pipeline.py` – sechs End-to-End- und Regeltests
- `run_mvp.ps1` – reproduzierbarer Windows-Start

## Datenmodelle

Das Schema enthält:

`creators`, `character_versions`, `assets`, `series`, `runs`, `content_items`,
`content_status_events`, `platform_variants`, `review_events`,
`posting_windows`, `publications`, `analytics_snapshots`, `experiments`,
`audio_candidates`, `link_campaigns`, `revenue_events`, `cost_events` und
`platform_accounts`.

`platform_accounts.secret_reference` ist optional; echte Passwörter oder Tokens
werden nicht gespeichert. JSON-Exporte schließen dieses Feld ausdrücklich aus.

## Architekturentscheidungen

- Python 3.12 und `sqlite3` aus der Standardbibliothek bilden den Kern.
- SQLAlchemy/FastAPI wurden nicht installiert, weil sie für den ersten lokalen
  vertikalen MVP nicht erforderlich sind.
- Das Schema und die Pipeline sind getrennt, damit später ein ORM oder API-Layer
  ergänzt werden kann.
- Social-Publishing ist über `MockPublisher` hart vom Live-Betrieb getrennt.
- Öffentliche Plattformen blockieren Adult-Inhalte; KI-Disclosure und bestätigte
  Medienrechte sind Pflicht.
- Prime-Time-Werte kommen aus Konfiguration und sind nicht im Pipeline-Code
  fest verdrahtet.

## Tests und Ergebnisse

Ausgeführt mit der gebündelten Python-3.12-Laufzeit:

```text
Ran 22 tests
OK
```

Abgedeckt:

- vollständiger Lauf für Leona und Mara
- zehn Assets, sechs Top Picks, zwei Publikationen und sechs Snapshots
- Idempotenz bei identischem Abend-Lauf
- vollständige Statushistorie bis `ANALYZED`
- Blockierung von Adult-Inhalten auf Instagram
- Pflicht für KI-Hinweis und Medienrechte
- simulierter Publisher-Ausfall, `PARTIAL_READY` und erfolgreicher Retry
- Evening-Run-Schranke innerhalb und außerhalb von 19:00–22:00 Uhr
- Prime-Time-Wechsel von Cold Start zu History sowie Slot-Kollisionsvermeidung
- Audio-Fallback bei Adapterausfall und Auswahl bestätigter eigener Musik
- Primary-, Alternate- und Reserve-Zuordnung aller Assets
- rein manuelle Engagement Queue
- geheimnisfreier JSON-Export und valides SQLite-Backup
- vollständige Review-Karten für beide Personas
- idempotente Vorbereitung eines Tages
- Freigabe erzeugt nur einen Mock-Draft ohne externe ID oder URL
- HTTP-Lesen, HTTP-Freigabe und Health-Check
- lokaler Bildimport, sichere Preview-Auslieferung und Mock-Fallback
- Backup-Restore in eine frische Datenbank mit Integritätsprüfung
- Python-Kompilierung aller Module und Tests

## Demo-Laufergebnis

Bestätigter lokaler Datenstand nach dem erweiterten Lauf:

- 2 Creator
- 2 Serien
- 2 Content Items
- 10 Assets
- 2 Plattformvarianten
- 2 Review-Ereignisse
- 2 Mock-Publikationen
- 6 Analytics-Snapshots
- 2 Learning-Experimente
- 6 Audio-Kandidaten
- 10 Asset-Plan-Einträge
- 6 protokollierte Adapter-Aufrufe
- 4 Engagement-Vorschläge
- 1 Evening Batch
- 2 abgeschlossene Export-Jobs
- 0 EUR Kosten
- 0 EUR Umsatz

Der zweite identische Lauf meldete für beide Personas `reused: true`; die
Tabellenzahlen blieben unverändert.

## Bekannte Fehler und Grenzen

- Keine echte Generator-, Publishing- oder Analytics-API angebunden.
- Nicht importierte Asset-Slots bleiben weiterhin Mock-Referenzen.
- Prime-Time lernt aus simulierten Metriken; echte Plattformdaten fehlen noch.
- Engagement-Vorschläge beziehen sich im Mock-Betrieb auf `mock://`-Ziele.
- Importierte Dateien werden lokal verwaltet und als echte Thumbnails angezeigt;
  noch nicht importierte Plätze bleiben klar erkennbare Mock-Kacheln.
- WebMCP ist im Client feature-detected, konnte in der vorhandenen lokalen
  Browserumgebung aber nicht als Browserstandard verifiziert werden.
- Threads ist extern durch Metas Selfie-Prüfung für Mara blockiert; auch die
  Leona-Anmeldung wird in dieselbe ausgesetzte Threads-Sitzung geleitet.

## Blocker und fehlende Zugänge

- Kein produktiver Social-API-Zugang; für diesen MVP nicht erforderlich.
- Keine echte Analytics-API; Simulation deckt den Lernpfad ab.
- Keine echte Generator-API; Mock-Assets halten die Pipeline testbar.
- GitHub-Synchronisation auf `main` wurde erfolgreich bestätigt.
- Threads verlangt eine persönliche offizielle Identitätsprüfung. Es wird keine
  KI-Aufnahme als Verifizierungs-Selfie verwendet.

## Kosten

Neue laufende Kosten: `0 EUR`.

Es wurden keine Dienste gebucht und keine Pakete aus dem Internet installiert.

## Fünf sinnvollste nächste Aufgaben

1. Je Persona fünf finale, rechtlich geklärte Posting-Kandidaten importieren
   - Nutzen: hoch
   - Aufwand: klein
   - Risiko: niedrig
   - Größe: S
2. Engagement Queue als zweite Dashboard-Ansicht ergänzen
   - Nutzen: mittel
   - Aufwand: klein
   - Risiko: niedrig
   - Größe: S
3. Import-UX später um einen lokalen Dateiauswahldialog ergänzen
   - Nutzen: mittel
   - Aufwand: mittel
   - Risiko: niedrig
   - Größe: M
4. Offiziellen Analytics-Adapter hinter der bestehenden Schnittstelle ergänzen
   - Nutzen: hoch
   - Aufwand: mittel
   - Risiko: mittel
   - Größe: M
5. Prime-Time-Baseline nach ersten echten 24h-/72h-/7d-Werten aktualisieren
   - Nutzen: hoch
   - Aufwand: klein
   - Risiko: niedrig
   - Größe: S

## FUTURE_OPPORTUNITIES

- SQLAlchemy/Alembic erst ergänzen, wenn Migrationen oder mehrere Worker den
  Zusatzaufwand rechtfertigen.
- FastAPI als dünnen Adapter über die vorhandene Pipeline setzen.
- Perceptual Hashing später gegen echte Bilddaten statt Mock-Pfade rechnen.
- Winner Remix als isoliertes Experiment mit genau einer geänderten Variable.

## Für Auswertung mit ChatGPT

1. Bestehender Vertikal-MVP für Leona und Mara blieb unverändert funktionsfähig.
2. Der Review-Flow zeigt weiterhin fünf Kandidaten und Top 3 pro Persona.
3. JPG, PNG und WebP können lokal und ohne neue Abhängigkeit importiert werden.
4. Importdateien werden in verwalteten Projektpfaden abgelegt und gehasht.
5. Rechteangabe ist auf `AI_GENERATED`, `OWNED` oder `LICENSED` begrenzt.
6. Der Import akzeptiert für dieses Dashboard ausschließlich SFW-Inhalte.
7. Echte Bilder erscheinen über sichere asset-id-basierte Preview-URLs.
8. Fehlende echte Bilder fallen stabil auf Mock-Kacheln zurück.
9. Das Dashboard ist heller, saisonal und je Persona klar getrennt.
10. Owner-Aufgabe, Statusbadges und größere Checks sind direkt sichtbar.
11. Leona und Mara besitzen eigene, fiktive KI-generierte Profilporträts.
12. Backup und Restore wurden real gegen eine frische SQLite-Datei geprüft.
13. Die wiederhergestellte DB enthält 2 Creator, 2 Inhalte und 10 Assets.
14. Alle 22 Tests und die Python-Kompilierung sind grün.
15. Live-Publishing, neue externe Pakete, Secrets und neue Kosten bleiben bei null.
