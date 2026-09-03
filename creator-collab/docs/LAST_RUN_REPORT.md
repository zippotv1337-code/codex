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
- Asset Registry: fertig
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
- Live-Publishing: absichtlich nicht implementiert

## Wichtige Dateien und Module

- `creator_ops/database.py` – Schema, Verbindungen, Persona-Seeding
- `creator_ops/models.py` – Status-, Safety- und Ergebnisobjekte
- `creator_ops/pipeline.py` – Compliance, Statusmaschine, Pipeline,
  MockPublisher, Analytics und Learning
- `creator_ops/scheduling.py` – Evening Window, History-Scoring und Slot-Abstand
- `creator_ops/services.py` – Audio-, Asset-Fallback- und Engagement-Dienste
- `creator_ops/evening.py` – idempotente Evening-Run-Orchestrierung
- `creator_ops/exporting.py` – JSON-Export und SQLite-Backup
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
Ran 16 tests
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
- Keine HTTP-Oberfläche; Bedienung erfolgt aktuell über CLI und SQLite.
- Asset-Dateien sind Mock-Referenzen, nicht erzeugte Bilddateien.
- Prime-Time lernt aus simulierten Metriken; echte Plattformdaten fehlen noch.
- Engagement-Vorschläge beziehen sich im Mock-Betrieb auf `mock://`-Ziele.
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

1. Einfache lokale Review- und Queue-API oder UI
   - Nutzen: hoch
   - Aufwand: mittel
   - Risiko: niedrig
   - Größe: M
2. Restore-Prüfung und dokumentierter Disaster-Recovery-Test
   - Nutzen: mittel
   - Aufwand: klein
   - Risiko: niedrig
   - Größe: S
3. Reale Bilddateien als Asset Registry importieren und per Hash prüfen
   - Nutzen: hoch
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

1. Vertikaler MVP für Leona und Mara ist funktionsfähig.
2. Beide Läufe enden in `ANALYZED`.
3. Pro Persona werden fünf Asset-Kandidaten registriert.
4. Pro Persona werden drei Top Picks gewählt.
5. QA prüft SFW, KI-Hinweis und Medienrechte.
6. Adult-Inhalte werden auf öffentlichen SFW-Plattformen blockiert.
7. Review und Owner-Freigabe sind klar als Simulation markiert.
8. Prime Time ist konfigurierbar und verwendet `Europe/Berlin`.
9. `MockPublisher` verhindert versehentliche Live-Veröffentlichung.
10. Analytics-Snapshots existieren für 24h, 72h und 7d.
11. Learning nutzt mehrere Qualitätsmetriken statt nur Views.
12. Gleiche Abend-Läufe sind idempotent.
13. Provider-Fehler enden in `PARTIAL_READY`.
14. Retry nach Fehler funktioniert.
15. Sechzehn Tests sind grün.
16. Neue Kosten betragen 0 EUR.
17. Keine Secrets werden gespeichert.
18. Nächster größter Nutzen ist eine lokale Review- und Queue-Oberfläche.
19. GitHub-Sync ist auf `main` erfolgt; lokaler und Remote-Stand waren identisch.
20. Threads bleibt extern durch Metas Identitätsprüfung blockiert.
