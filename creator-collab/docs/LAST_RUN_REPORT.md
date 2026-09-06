# Last Run Report – Creator Ops MVP

Stand: 4. September 2026

## Final Fast Apply 1.4 — 5. September 2026

Der 1.3.0-Stand wurde zuerst vollständig abgeschlossen und erneut bestätigt.
Danach wurden ausschließlich echte Deltas des neuen Pakets umgesetzt: durable
Background-Runs mit Lease/Capacity/Journal, ehrliche lokale Publish Queue,
idempotenter 05:30-Morning-Run, validierte Patch-Backup-Kette und leichte
interne `mz_poke`-Experimentmarkierung. Aktive DB: Schema 5, Integrität `ok`,
drei lokale Queuejobs, keine externe Ausführung. Final 81/81 Tests grün.
Vollbericht: `docs/RUN_REPORT_FINAL_FAST_APPLY_V1_4.md`.

## Story-/Collections-Sidequests – 5. September 2026

Nach dem stabilen lokalen P0-Server wurden genau zwei kleine Sidequests aus dem
vorherigen Bündel umgesetzt. `/stories` erzeugt aus den vier vorhandenen
Feedpaketen zwölf owner-reviewbare Frames, ohne neue Bilder oder Publikation.
`/collections` stellt dieselben Asset-IDs als vier filterbare Alben mit Cover,
Tags, Reserve, veröffentlichten Assets und Top 3 dar. Fehlende Performancewerte
bleiben ausdrücklich unbekannt.

Verifikation: 59/59 Tests, Syntaxprüfungen und SQLite-Integrität grün. Beide
Ansichten wurden sichtbar gegen die reale DB geprüft. Backup SHA256:
`3BF0A5CF67BF659C9D26BAF683223188ADDC8C966E12C63BDFE9FB46C7BA64A2`.
Keine neue Bildserie, keine externe Aktion und keine Git-/GitHub-Arbeit.

## Abschluss-/Betriebsrun – 4. September 2026, 22:14 Uhr

Die vier Feedpakete sind jetzt gemeinsam und vollständig entscheidungsfähig im
Owner Review. Veröffentlichte Einzelassets werden ausgeschlossen, Top 1–3
nummeriert und alle Postingmetadaten unmittelbar angezeigt. APPROVE legt nur
einen lokalen Mock-Draft an; CHANGE und REJECT speichern auditierte lokale
Owner-Entscheidungen.

Engagement bleibt streng evidenzgebunden: vier Vorschläge zu echten Posts sind
vorhanden, aber bei null echten Kommentartexten werden null Antwortentwürfe
erzeugt. `AUTOPILOT_CHECKPOINT.md` wurde als atomarer Savegame-Mechanismus
ergänzt.

Der anschließend gelieferte P0-Serverauftrag wurde minimal umgesetzt. Der neue
Startweg prüft Python, Verzeichnisse, Port, absolute DB-Pfade und Health, öffnet
den Browser erst danach und schreibt PID sowie Logs. Start, Status,
`/api/review-queue` mit vier Karten und Stop wurden real verifiziert.

- Tests: 54/54 grün
- Compileall und JavaScript-Syntax: grün
- SQLite `integrity_check`: ok
- Backup: `creator-ops-backup-post-owner-review-server-fix.db`
- SHA256: `E5E59FD1ECB9B2E896EE9FD2DA40C7BC00915381CE10DC003EABEC6414625509`
- Externe Aktionen/Kosten: keine / 0 EUR
- Git/GitHub: gemäß Owner-Regel vollständig geparkt

### LAN und Mobile Safari

Die tatsächliche WLAN-Adresse ist `192.168.188.131`, nicht
`192.168.1.188`. Ein neuer LAN-Start erkennt die lokale Adresse automatisch,
erzwingt ein temporäres Sitzungspasswort und startet Creator Ops ohne
Routerfreigabe. Der Healthcheck über die LAN-Adresse meldete `ok` und
`auth=true`. Eine optionale Firewallregel ist auf privates Profil, lokales
Subnetz und TCP 4180 begrenzt und muss bewusst mit Administratorrechten
aktiviert werden. Die responsive Oberfläche ist für Mobile Safari vorbereitet.

Final: 55/55 Tests, PowerShell-Syntax und SQLite-Integrität grün. Backup
`creator-ops-backup-post-lan-safari.db`, SHA256
`090DA23B61C0F140AF1913A3E28A2DE0FAF2B8987F73E90FECCD53530D733609`.

## Restzeit-Brücke bis Dienstag

### Was tatsächlich gebaut wurde

- `docs/CHATGPT_BRIDGE_TO_TUESDAY.md` enthält acht vollständige Produktionsbriefs;
  die dafür benötigten Bildsets fehlen noch.
- Vier Briefs gehören zu Leona, vier zu Mara; geplant von Samstag bis Dienstag.
- Jeder Brief enthält Idee, Hook, Format, fünf Shots, Pose-Matrix, Top 3,
  Caption, CTA, Hashtags, Prime Time, Audio A/B/ohne Musik, Assetbedarf,
  Persona-Fit und QA.
- Es wurde keine neue technische Architektur begonnen.

### Content-Reserve Leona

1. Spätsommer in Berlin – City-Carousel.
2. Gym Reset, aber echt – kurzes Routine-Reel.
3. Ein Blazer, drei Stimmungen – Fashion-Carousel.
4. Golden Hour an der Tram – filmisches City-Reel.

### Content-Reserve Mara

1. Fünf Minuten Maschinencheck – Nutzwert-Carousel.
2. Werkstatt: Feierabend in drei Handgriffen – Routine-Carousel.
3. Pause am Feldrand – nahbarer Landleben-Post.
4. Was verrät das Reifenbild? – vorsichtiges Lern-Carousel.

### Engagement-Vorschläge

- Keine neue Plattformaktion ausgeführt.
- Die bestehende DB-Queue bleibt rein manuell und enthält weiterhin nur Mock-
  Vorschläge. Neue Follow-/Kommentarlisten wurden in diesem letzten Sparlauf
  bewusst nicht begonnen, damit der vollständige Brief- und Abschlussstand
  gesichert werden kann.

### Dashboard, Tests, Fehler und Kosten

- Dashboard-Stand dieses Abschlusslaufs unverändert; der vorherige Asset-/UX-
  Boost bleibt aktiv.
- Bestehende Suite zuletzt mit 22 grünen Tests bestätigt.
- Fehler: keine neuen Produktfehler; Instagram-Webseiten waren über allgemeine
  Websuche nicht zuverlässig lesbar, daher keine ungeprüften Handles übernommen.
- Blocker: Mara Threads bleibt in persönlicher Selfie-Verifizierung.
- Kosten: 0 EUR; keine API, kein Abo und kein Credit eingesetzt.

### OWNER_DECISIONS_REQUIRED

1. Welche der acht Briefs sollen zuerst als Bilder produziert werden?
2. Pro Reel Audio A, Audio B oder Originalton/ohne Musik wählen.
3. Vor Produktion prüfen, ob sichtbare Landmaschinen markenfrei bleiben sollen.
4. Für spätere Engagement-Vorschläge konkrete aktuelle Zielposts manuell bestätigen.

### Nächste fünf sinnvolle Aufgaben

1. Owner wählt je Persona den ersten Brief.
2. Für die gewählten Briefs jeweils fünf konsistente Assets erzeugen.
3. Top 3 im Dashboard visuell bestätigen und Caption final lesen.
4. Erst danach die manuelle Engagement-Reserve mit aktuellen Zielposts füllen.
5. Nach Freigabe nur planen; tatsächliches Posting separat bestätigen.

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

1. Der funktionierende Creator-Ops-Kern blieb unverändert.
2. Acht vollständige Briefs liegen in `docs/CHATGPT_BRIDGE_TO_TUESDAY.md`.
3. Leona hat vier unterschiedliche Reserveformate bis Dienstag.
4. Mara hat vier unterschiedliche Reserveformate bis Dienstag.
5. Jeder Brief besitzt fünf Shots, Pose-Matrix und eine klare Top 3.
6. Caption, Hook, CTA und Hashtags sind sofort weiterverwendbar.
7. Audio A/B/ohne Musik und Prime Time sind je Brief vorbereitet.
8. Alle Motive sind SFW und für fiktive erwachsene KI-Personas formuliert.
9. KI-Transparenz bleibt über Bio und natives Plattform-Label erhalten.
10. Dashboard, echter Asset-Import und Mock-Fallback funktionieren weiterhin.
11. Backup/Restore und zuletzt 22 Tests waren grün.
12. Engagement bleibt Vorschlag/Mock; nichts wurde automatisch ausgeführt.
13. Keine Live-Posts, DMs, Accounts, Käufe oder externen Verpflichtungen.
14. Nächste Entscheidung: je Persona den ersten Produktionsbrief auswählen.
15. Danach fünf Assets erzeugen, Top 3 prüfen und nur als Draft planen.

## Bestandsauswertung und Website-Exposé – 4. September 2026

Im Sparmodus wurden Repository, SQLite-Datenbanken, Backups, JSON-Exporte,
Asset-Verzeichnisse, Instagram-Belege und der zugängliche Teil des Projektchats
`haupt` ausgewertet. Es wurden bewusst keine neuen Bilder generiert.

### Verifizierter Medienbestand

- Leona: 1 eindeutige lokale PNG-Masterdatei, 1 exakte Importkopie und 5
  veröffentlichte Instagram-Referenzen ohne lokale Masterdatei.
- Mara: 1 eindeutige lokale PNG-Masterdatei, 1 exakte Importkopie und 5
  veröffentlichte Instagram-Referenzen ohne lokale Masterdatei.
- Review-Datenbank: 2 echte lokale Imports und 8 Mock-Slots.
- Letzter Pipeline-Export: 20 Mock-Assets; diese besitzen keine Bilddateien und
  werden nicht als Content gezählt.
- Chat-Anhänge: 10 erreichbar, davon 8 System-/Dashboard-Screenshots und 2
  Instagram-Profilübersichten; keine hochauflösenden Einzelmotive.

### Erzeugte Unterlagen

- `docs/CONTENT_ASSET_INVENTORY.md`
- `docs/CONTENT_ASSET_INVENTORY.csv`
- `docs/WEBSITE_ASSET_SHORTLIST.md`
- `docs/WEBSITE_EXPOSE.md`
- `docs/POSTING_BRIDGE_TO_TUESDAY.md`

### Readiness-Entscheidung

Die 4 Leona- und 4 Mara-Pakete sind als vollständige Produktionsbriefs
vorbereitet, aber nicht bildseitig `READY_FOR_REVIEW`. Je Persona existiert nur
ein passendes lokales Porträt; kein Brief besitzt bereits 3–4 lokale
Masterbilder. Deshalb wurde die Regel „nur 1–2 Lücken ergänzen“ noch nicht
ausgelöst. Der nächste Schritt ist die Recovery der zehn bereits
veröffentlichten Originaldateien mit Herkunfts-/Rechteinformationen.

### Für Auswertung mit ChatGPT – Bestandslauf

1. Zwei eindeutige lokale Bildmaster gefunden: je einer für Leona und Mara.
2. Zwei Importdateien sind exakte Duplikate und keine zusätzlichen Motive.
3. Zehn öffentliche Instagram-Posts sind als Portfolio-Referenzen belegt.
4. Deren lokale Masterdateien und eindeutiger Rechtepfad fehlen.
5. 28 `.mock`-Datensätze sind nur Test-/UI-Platzhalter.
6. Acht Content-Pakete sind textlich vollständig vorbereitet.
7. Null neue Feed-Posts sind derzeit asset-komplett `READY_FOR_REVIEW`.
8. Story-Reshares vorhandener Posts sind ein manueller Null-Generierungs-Fallback.
9. Prime Times stammen aus Creator Ops, aber bisher nur aus Mock-/Cold-Start-Daten.
10. Leona eignet sich für Rooftop, Café, Fashion, Gym und Abendlook.
11. Mara eignet sich für Hof/Traktor, Feldrand, Küche und Werkstatt.
12. Beste lokale Website-Assets sind die beiden Profilporträts.
13. Beste spätere Hero-Referenzen sind Leona Rooftop und Mara Hof/Feldrand.
14. Keine Bilder, Posts, Accounts oder externen Dienste wurden neu erzeugt.
15. Nächste Priorität: Originale sichern, registrieren, matchen und erst dann gezielt Lücken erzeugen.

## Content-Production-Run – 4. September 2026

Der priorisierte Bridge-to-Tuesday-Lauf wurde ohne neue Systemarchitektur
abgeschlossen. Zuerst wurde der lokale Bestand verwendet; anschließend wurden
nur die für vier vollständige Pakete fehlenden Motive mit Built-in ImageGen
erzeugt. Ein fünftes Paket wurde bewusst nicht begonnen.

### Fertige Pakete

| Persona | Paket | Kandidaten | Top 3 | Status |
|---|---|---:|---|---|
| Leona | Spätsommer in Berlin | 5 | Full-body Walk -> Café links 3/4 -> Café candid | `READY_FOR_REVIEW` |
| Mara | Fünf Minuten Maschinencheck | 5 | Hof-Walk -> Reifencheck -> Traktor candid | `READY_FOR_REVIEW` |
| Leona | September Roofline | 5 | Rooftop-Walk -> Geländer links 3/4 -> sitzend candid | `READY_FOR_REVIEW` |
| Mara | Küchenfenster | 5 | Küchen-Walk -> Fenster rechts 3/4 -> Tisch candid | `READY_FOR_REVIEW` |

### Asset- und Dashboard-Nachweis

- 18 neue fotorealistische SFW-Bilder erzeugt.
- 2 vorhandene Profilanker gezielt als Front-Slots wiederverwendet.
- 20 Paketdateien mit SHA-256 dokumentiert.
- 20/20 Bilder über den bestehenden Importweg registriert; Rechte-/Herkunft
  `AI_GENERATED`, Safety `SFW`.
- Für Content `3–6` jeweils 5 echte Preview-URLs, 3 Top-Picks, `ready=true`,
  `approved=false` und Prime Time `19:30` aus `cold-start-config` bestätigt.
- Veralteten lokalen Dashboardprozess ersetzt; der aktuelle Server auf
  `http://127.0.0.1:4180/` liefert die neue Review-Datenbank. HTTP-Prüfung:
  10/10 Preview-URLs für den 6. September, erster PNG-Endpunkt `200 OK`.
- Caption, Hook, CTA, Hashtags, Musik A/B/ohne und Carousel-Folge je Paket
  finalisiert.
- Keine externe Veröffentlichung und keine Owner-Freigabe ausgelöst.

### Kleine isolierte Korrektur

Neue Review-Captions hängen den strukturierten KI-Hinweis nicht mehr
automatisch als Standardfooter an und erzeugen nicht mehr automatisch den
Hashtag `kigeneriert`. Die KI-Transparenz bleibt separat als Plattformmetadatum
erhalten. Ein Test schützt dieses Verhalten.

### Tests, Export und Restore

- `python -m unittest discover -s tests -v`: **22/22 grün**.
- `python -m compileall -q creator_ops tests`: **grün**.
- Secret-freier Export:
  `backups/creator-ops-export-content-reserve-20260904-1019.json`.
- SQLite-Backup:
  `backups/creator-ops-backup-content-reserve-20260904-1019.db`.
- Restore-Prüfung:
  `backups/creator-ops-restore-check-content-reserve-20260904-1019.db`.
- Backup und Restore jeweils `PRAGMA integrity_check = ok`, 2 Creator,
  6 Content-Items, 30 Assets, 22 lokale Imports und 6 review-bereite Inhalte.
- GitHub-Synchronisierung bestätigt: Content-Commit `fa998be`
  (`handoff: finish bridge-to-tuesday content reserve`) sowie anschließender
  Dokumentations-Folgecommit wurden erfolgreich auf `main` gepusht.

### Für Auswertung mit ChatGPT – Content-Run

1. Vier vollständige hochwertige Pakete sind produziert.
2. Leona besitzt 10 lokale Kandidaten in zwei Paketen.
3. Mara besitzt 10 lokale Kandidaten in zwei Paketen.
4. Insgesamt wurden 18 neue Bilder erzeugt und 2 Anker wiederverwendet.
5. Jede Pose-Matrix deckt frontal, links 3/4, rechts 3/4, Bewegung und candid ab.
6. Maximal zwei ähnliche Bilder pro Set; alle vier Sets bestanden die visuelle QA.
7. Pro Paket sind drei unterschiedliche Carousel-Slides kuratiert.
8. Alle 20 Bilder erscheinen als echte Vorschau im bestehenden Dashboard.
9. Alle vier Zielpakete sind `READY_FOR_REVIEW`, aber nicht freigegeben.
10. Caption, Hook, CTA, Hashtags und Musik A/B/ohne sind vollständig.
11. Prime Time ist 19:30 Uhr aus der Cold-Start-Konfiguration.
12. Der automatische KI-Caption-Footer wurde isoliert entfernt; Metadaten bleiben.
13. 22 Tests und Compileall sind grün.
14. Export, Backup und Restore wurden erfolgreich verifiziert.
15. ChatGPT sollte bis Dienstag Owner-Feedback/Top-3-Änderungen sammeln; keine neuen Pakete nötig.

## Kostenloser Remote-Access-Patch – 4. September 2026

Das bereitgestellte Patch-Archiv wurde gegen den aktuellen Creator-Ops-Stand
integriert und dabei ergänzt. Der lokale Standardmodus bleibt kompatibel: Ohne
`CREATOR_OPS_PASSWORD` sind Dashboard und API auf `127.0.0.1` wie bisher offen.

### Implementiert

- Optionaler Passwort-Login mit konstantzeitlichem Vergleich.
- Passwort-Mindestlänge 12 Zeichen; ausschließlich Prozessumgebung, nicht Git
  oder SQLite.
- Zufällige In-Memory-Sessions mit 12 Stunden Laufzeit.
- `HttpOnly`-/`SameSite=Strict`-Session-Cookie und separates CSRF-Cookie;
  `Secure` bei HTTPS-Forwarding.
- CSRF-Prüfung für Freigabe und Logout.
- Sechs Fehlversuche pro Client in fünf Minuten als einfache Login-Sperre.
- CSP, Frame-, Referrer- und MIME-Sicherheitsheader; HSTS über HTTPS.
- Öffentlicher minimaler Health-Endpunkt mit sichtbarem Auth-Modus.
- Dashboard-JavaScript für Session, CSRF, Login-Weiterleitung und Logout.
- Kostenloses Startskript `run_remote_free.ps1` für lokalen Server plus
  optionalen Cloudflare Quick Tunnel; Bindung bleibt `127.0.0.1`, keine
  Router-Portfreigabe.
- Anleitung `docs/REMOTE_ACCESS_FREE.md`; `tools/` und `.env*` werden ignoriert.

### Verifiziert

- Bestehende 22 Tests bleiben grün.
- 4 Auth-Unit-Tests grün.
- 5 echte HTTP-Tests grün:
  - Review-API ohne Login -> `401`
  - falsches Passwort -> `401`
  - korrektes Passwort -> Session- und CSRF-Cookie
  - Freigabe ohne CSRF -> `403`
  - Freigabe mit Session + CSRF -> lokaler `mock-draft`
- Gesamtsuite: **31/31 grün**.
- Compileall: grün.
- Kein Live-Publishing, keine Secrets und keine neue externe Abhängigkeit.

### Noch manuell

`cloudflared` ist auf dem aktuellen Rechner nicht installiert. Ein echter
temporärer Link wird daher erst erzeugt, nachdem der Owner den kostenlosen
Client installiert, `.\run_remote_free.ps1` startet und ein neues Passwort mit
mindestens 12 Zeichen eingibt. Das Passwort wird nicht per E-Mail oder GitHub
verteilt.

GitHub-Commit `d616bf4` wurde auf `main` bestätigt. Die Ergebnis-Mail mit
Commit-Link, 31/31-Teststatus und Startanleitung ging anschließend an das
verbundene eigene Gmail-Konto; Nachrichten-ID `1a06b99169f3809f`.

## Abschlussdatei und Sichtbarkeit

Die GitHub-Metadaten bestätigen `visibility=public`, Standardbranch `main` und
`archived=false` für `zippotv1337-code/codex`. Andere können daher auch die 20
eingecheckten Creator-Bilder lesen und herunterladen. Die vollständige
Owner-Übergabe mit Projektstand, Verifikation und Restschritten steht in
`docs/FINAL_ABSCHLUSS.md`. Die Repository-Sichtbarkeit wurde nicht verändert.

## Native Instagram-Veröffentlichungen – 4. September 2026

Nach ausdrücklicher Owner-Freigabe wurden zwei vorhandene, rechtlich als
`AI_GENERATED` dokumentierte Paket-Assets nativ über Instagram veröffentlicht.
Dies war eine manuelle Plattformaktion und keine Aktivierung oder Erweiterung
des lokalen `MockPublisher`.

- Mara „Fünf Minuten Maschinencheck“, S4
  (`04-full-body-morning-walk.png`):
  <https://www.instagram.com/mara.field.ai/p/Dc3d7CHgO3S/>
- Leona „September Roofline“, S4
  (`04-full-body-rooftop-walk.png`, 4:5-Zuschnitt):
  <https://www.instagram.com/leonavoss.ai/p/Dc3elLhAC2-/>

Bei beiden Veröffentlichungen war das native Instagram-KI-Label aktiviert.
Instagram zeigte jeweils „Dein Beitrag wurde geteilt“, anschließend waren die
neuen Beiträge in den Profilrastern sichtbar. Beide Profile enthalten damit je
sechs Feed-Beiträge. Lokale Review-Karten bleiben technisch
`READY_FOR_REVIEW`/`approved=false`, bis eine separate Synchronisierung dieses
externen Zustands implementiert oder bewusst manuell dokumentiert wird.

## Daily-Usable v1.1 – 4. September 2026, 16:00 Uhr

Der Master-Export wurde von einfachen, reversiblen Änderungen zu den schwereren
Sicherheits- und Medienpunkten abgearbeitet. Funktionierende MVP-Bausteine
blieben erhalten.

### Ergebnis

- Additive Schema-2-Migration mit `ALLTAG`, `TEASER`, `ADULT_18`,
  `PUBLIC_SFW`, `ADULT_ONLY`, `LOCAL_ONLY` und fünf Pose-Slots.
- Datenbank- und Compliance-Hartblock gegen Stage-/Safety-/Visibility-Mismatch
  sowie Adult-Ausgabe an öffentliche Plattformen.
- Gewichtete Top-3-Kuratierung (30/25/20/15/10) mit Pose- und
  Ähnlichkeitsregeln.
- Automatische QA für fünf Dateien, eindeutige Hashes, fünf Pose-Slots,
  maximal zwei ähnliche Assets und drei diverse Top-Picks.
- 40/35/25-Mixplaner, ohne Generierungs- oder Publishing-Seiteneffekt.
- Öffentlicher JSON-Export auf `PUBLIC_SFW` begrenzt.
- Dashboard-Stage-Filter, geschützte Blur-Vorschau, Pose-/QA-/Visibility-Anzeige.
- Dynamischer Status per CLI und `/api/status`.
- Remote-URL-Erkennung, Clipboard, zwei Healthchecks, ephemerer Status und
  optionaler Notification-Hook; Nicht-Loopback ohne Passwort gesperrt.

### Verifikation

- 42/42 Tests grün; Compileall, JavaScript- und PowerShell-Syntax grün.
- Reale DB erfolgreich auf Schema 2 migriert.
- Post-Migrationsbackup und Restore: `integrity=ok`, 6 Pakete, 30 Assets.
- Alle 20 Git-Medien besitzen verifizierte lokale Kopien; zusätzliches
  Medien-ZIP mit 50 Einträgen und SHA-256
  `2816BA6E69BF6B0B0793442033E2D4737D1285D958EF97B2C8D3A9D4C300C15D`.
- Keine neue Veröffentlichung, kein Adult-Asset, keine Kosten, keine Secrets.

### Owner-Gate

GitHub wurde sichtbar als `Public` bestätigt. Die Privatstellung und das
anschließende Entfernen der 20 Medien aus dem Git-Index warten auf die direkt
vor der Cloud-Berechtigungsänderung erforderliche Owner-Bestätigung. Ein
History Rewrite ist ausdrücklich nicht Teil dieses Laufs.
# Creator Ops v1.2.0 – Betriebsmodus (4. September 2026, 21:08 Uhr)

Der bestehende Daily-Usable-v1.1-Kern wurde gezielt erweitert, nicht neu
gebaut. Schema 3 ergänzt owner-bestätigte native Publikationen und append-only
manuelle Analytics. Die zwei bereits bestätigten Instagram-Posts sind lokal
idempotent abgeglichen; es fand in diesem Lauf keine externe Aktion statt.

Das Dashboard bietet nun `Morgen`, `Archiv` und `Top 3`. Archiv zeigt reale
Posts standardmäßig getrennt von Mock-Drafts. Top 3 verwendet die Gewichtung
Saves 25, Shares 20, Comments 15, Profile Visits 15, Follows 10, Link Clicks
10, Likes 5 und berechnet Raten, sobald Reach oder Views vorhanden sind.

Recovery ist dauerhaft vorbereitet: Wochen- und Monatsarchive enthalten eine
bereinigte SQLite-Kopie, Manifest und SHA256, werden nach ZIP-/DB-Integrität
validiert und löschen keine Vorgänger. Der Scheduler-Dry-Run ist rein lesend;
`-Apply` bleibt eine bewusste Owner-Aktion. Der LAN-Start erkennt NIC, Gateway
und IPv4 automatisch, verlangt mindestens 12 Passwortzeichen und öffnet keine
Routerports.

Verifikation: 47/47 Tests, compileall, JavaScript- und PowerShell-Syntax grün;
Archiv und Top 3 wurden gegen die reale DB sichtbar geprüft. Reale DB:
Schema 3, 6 Pakete, 30 Assets, 2 echte owner-bestätigte und 2 Mock-
Publikationen, 0 manuelle Analytics-Events. Kosten: 0 €; Secrets: keine.

Backups:

- Woche: `Backup_Woche_KW36_2026_20260904-2107.zip`, SHA256
  `C4DC9E0FDEB8E9806F84AB5EEE27F3EA95789A258A0828CD17AEF204FBC8C13D`.
- Monat: `Backup_Monat_2026-09_FULL_20260904-2107.zip`, SHA256
  `6D1154028ED27968411634A854859FD4AFD6C42C1640B9B38EDB0BF72D121ECC`.

GitHub-Privatstellung, Commit und Push bleiben Human-Handoff: GitHub wartet
auf persönliche Sudo-Bestätigung; die aktuelle Sandbox verweigert Schreibzugriff
auf `.git/index.lock`. Es wurde kein unsicherer Workaround eingesetzt.
# Medium-Autopilot – Contentbetrieb (4. September 2026, 21:29 Uhr)

Git und GitHub waren für diesen Run ausdrücklich geparkt. Der lokale Betrieb
wurde dennoch fortgeführt: Bereits veröffentlichte S4-Assets werden bei einer
erneuten Reconciliation aus den Carousel-Top-3 entfernt. Mara Maschinencheck
und Leona Roofline verwenden jetzt jeweils S2, S3 und S5. Maras kollidierender
Mock-Zeitplan ist pausiert und benötigt eine neue Owner-Freigabe.

Die neue read-only Seite `/engagement` zeigt vier Vorschläge zu den zwei echten
Posts und filtert Mock-Daten standardmäßig aus. Es gibt weiterhin keine
automatische Kommentar-, Like-, Follow- oder DM-Ausführung. Prime Time zieht
künftig echte 168-h-Daten vor Mock-Historie heran.

Content-Reserve: je Persona neun unveröffentlichte reale Assets in zwei
feedfähigen Paketen; zusätzlich je drei vollständige Briefs ohne Assets.
Nächste Produktionskandidaten sind Leona „Gym Reset, aber echt“ und Mara
„Werkstatt: Feierabend in drei Handgriffen“. Vorhandene Reserve wurde zuerst
ausgeschöpft; keine halbfertige Bildserie erzeugt.

Verifikation: 48/48 Tests, compileall und JavaScript-Syntax grün. Die
Engagement-Seite wurde sichtbar gegen die reale DB geprüft. Post-Run-Backup:
`creator-ops-backup-post-medium-autopilot.db`, SHA256
`982A61EC493CCA29CBF7DD2DC9D0832DB23671BCF5E1ABED9597017B7A33BEC0`.
Public-SFW-Export: SHA256
`FFAC86A73F2E07F56DB334CD3C717F17C37E0B55423370B71E1F2F833EC14252`.
Kosten und externe Aktionen: 0.

# Modellkompatible Control Plane und große Vorschau – 5. September 2026

Der bestehende Creator-Ops-Kern wurde nicht neu gebaut. P1 ergänzt unter
`/control` eine versionierte, capability-basierte Control Plane auf demselben
Server. Das aktuell stabile Modell ist die vollständige Baseline; spätere
Modelle sind ausschließlich als optionaler Bonus ausgewiesen. Die sicheren
Kommandos prüfen die lokale Queue, pausieren/fortsetzen und schreiben einen
atomaren Speicherstand. Externes Publishing bleibt ein nicht ausführbares
Owner-Gate.

Erst nach P1 wurde P2 umgesetzt: Jede Reviewkarte öffnet ihre echten Top 3 in
einer großen, responsiven 4:5-Carousel-Vorschau mit Caption, Persona, Pose,
Qualität und Prime Time. Die Vorschau hat keinen Instagram-Zugriff.

Verifikation: 63/63 Tests, Python-/JavaScript-Syntax und SQLite-Integrität
grün. Control Plane und große Vorschau wurden im laufenden lokalen Dashboard
sichtbar geprüft. Vorab-Backup:
`backups/creator-ops-backup-pre-control-plane.db/creator-ops-backup-20260905-080028.db`,
SHA256 `54292848E9573DFA3AA67DCD013C35506CA635F1A99F84B5421713767AFF1C5B`.
Keine externe Plattformaktion, keine Kosten, keine Secrets und keine
Git-/GitHub-Arbeit.

Post-Run-Backup: `backups/creator-ops-backup-post-control-plane-preview.db`,
SQLite-Integrität `ok`, SHA256
`54FB260AA13535B2AAE334051E0DB769BD06EA89680A61BA51BEA2EF87398186`.

# Revenue-first Creator Ops 1.3.0 – 5. September 2026

Der neue Owner-Auftrag reaktivierte ausdrücklich ein überarbeitetes V1.1-
Paket. Der bestehende Kern wurde um drei SFW-Service-Packs, Fiverr-/Intake-/
Fulfillment-Unterlagen, `/offer`, `/revenue` und eine isolierte AdWorks-Schicht
erweitert. Preise und Rechts-/Lieferentscheidungen wurden nicht erfunden.

Schema 4 ist additiv. Der lokale Akzeptanztest erzeugt idempotent vier als Mock
markierte Events von Click bis Purchase und ein Feedbacksignal. Das Board zeigt
123,45 € synthetisch, aber weiterhin 0 € real. Paid Spend und externe
Veröffentlichung bleiben technisch beziehungsweise organisatorisch gesperrt.

68/68 Tests, Python-/JavaScript-/PowerShell-Syntax, SQLite-Integrität und ein
Restore mit Schema 4, drei Packs und vier Funnel-Events sind grün. Finales
Backup: `creator-ops-backup-post-revenue-first-v130.db`, SHA256
`99A8AF434095B9F9DB1318EDABECA214D754E18954410EF8B9DDE7C9FA5F56FB`.
Keine externe Aktion, Kosten, Secrets oder Git-/GitHub-Arbeit.

# Creator Ops 1.4.1 – High-Autopilot-Härtung – 5. September 2026

Der bestehende Kern wurde gezielt gehärtet: Queue und Prime-Time verwenden die
lokale Publish Queue als maßgebliche Quelle, Audio bleibt ohne bestätigte
Lizenz fail-closed, veröffentlichte Assets bleiben aus neuen Empfehlungen
ausgeschlossen und fehlende Analytics werden nicht künstlich gerankt.
Background-Runs erneuern ihre Lease, setzen echte Wartezeiten fort und schützen
Abschlusszustände vor verlorenen Leases.

Für den Betrieb ohne laufenden Codex wurden ein secrets-reduzierter, read-only
Offline-Snapshot sowie begrenzte Scheduler-, Watchdog- und Windows-Aufgaben-
Skripte vorbereitet. Die Installation blieb bis zu einer ausdrücklichen
Owner-Entscheidung im reinen Vorschaumodus.

Der gemeldete tote Owner-Review-Pfad wurde reproduziert: Der eingebettete
Browser unterstützt `window.prompt()` nicht. CHANGE und REJECT verwenden nun
einen eigenen responsiven Dialog. Große Vorschau, Dialog und Abbruch ohne
Datenänderung wurden im laufenden Dashboard sichtbar geprüft; das offene
Mara-Paket blieb unverändert `READY_FOR_REVIEW`.

Verifikation: 96/96 Tests, Python-Compilecheck, 9/9 JavaScript-Syntaxchecks,
PowerShell-Parser und SQLite-Integrität grün. Finales SQLite-Backup:
`backups/creator-ops-backup-high-autopilot-final-20260905-193722.db`, SHA256
`2142C60A9D874C05CC7D137D8B0437F3989D4E8107D2DCA0D5E21CEBB942C985`.
Der Restore in eine frische Datenbank ergab `integrity_check = ok`, sechs
Inhalte und drei Queuejobs. Keine externe Veröffentlichung, keine Kosten und
keine Secrets.

# Creator Ops 1.6.4-beta — Live-Safety-Abschluss — 6. September 2026

Der bestehende Kern wurde nicht neu gebaut. Der Run beendete die offene
Standalone-, GitHub-, Publishing- und Recovery-Arbeit aus dem Beta-1.6.4-
Paket und stoppte danach an einem atomaren Checkpoint.

## Umgesetzt

- Dauerbetrieb über genau einen lokalen Supervisor, persönlichen Windows-
  Autostart, Watchdog, begrenzten Scheduler und read-only Offline-Snapshot.
- Vollständiger Scheduler-Gate: Dispatch nur bei zwei Publishing-Schaltern,
  zwei externen Capabilities, Adapter `meta-graph` und sicherem Laufzeitlogin.
- Offizieller Meta-Carousel-Adapter mit persona-fester Kontozuordnung, exakt
  drei unveröffentlichten PUBLIC_SFW-Top-Picks, nativer KI-Kennzeichnung,
  separater Live-Freigabe, Containerprüfung und bestätigter ID/Permalink.
- Persistenter Publish-Intent vor dem externen Publish. Unsichere Ergebnisse,
  abgestürzte Claims und fehlende Receipts blockieren ohne Blind-Retry.
- Neuplanung behält den Queue-Key und kann keine alte Intent-/Receipt-Sperre
  umgehen.
- Patch-Recovery enthält validierte Meta-Receipts automatisch. Full-Recovery
  enthält `config.toml` und die Standalone-Start/Stop-Wrapper.
- Modellrouting bevorzugt Astra HIGH nur capability-basiert und optional;
  Sol/Runtime-Default bleiben vollständige Fallbacks. Kein externer Model-
  Executor und kein API-Aufruf wurden aktiviert.
- GitHub `main` wurde in drei sicheren Fast-Forward-Schritten synchronisiert;
  kein Force-Push und kein History-Rewrite.

## Astra-Zweitprüfung

Eine unabhängige read-only Astra-HIGH-Prüfung fand drei P1-Risiken: einen
möglichen Doppelpostpfad nach Stale-Publishing plus Neuplanung, fehlende Meta-
Receipts in Patch-Backups und fehlende Standalone-Bootdateien in Full-Backups.
Alle drei Punkte wurden gezielt behoben, mit Regressionstests abgesichert und
anschließend von Astra ohne offenen P0/P1-Blocker nachgeprüft.

## Verifikation

- 116/116 Tests grün
- Python-Compilecheck grün
- alle vorhandenen Dashboard-JavaScript-Dateien syntaktisch grün
- alle PowerShell-Projektskripte parsebar
- `git diff --check` grün
- Runtime: Health `ok`, Version `1.6.4-beta`, genau ein Supervisor
- SQLite: `integrity_check = ok`, 6 Inhalte, 30 Assets, 6 Publikationen,
  3 Queuejobs
- Schedulerlog bestätigt `live dispatch skipped by complete owner gate`

## Backup/Restore

- Backup: `backups/Backup_Meilenstein_20260906-0809.zip`
- SHA256:
  `e937c16d6e80c52bc9d96ee746f6f71989d3a5687bb7cf26bd3bf553b6b41401`
- Frischer Restore:
  `tmp/restore-check-20260906-080949/recovery/creator_ops.db`
- Ergebnis: Integrität `ok`, 6 Inhalte, 6 Publikationen, 3 Queuejobs,
  0 Secret-Referenzen; `config.toml` und Standalone-Wrapper vorhanden.

## Betriebsstand

- Je Persona 11 reale Assets, davon 10 unveröffentlicht. Neun unveröffentlichte
  Assets je Persona liegen in zwei feedfähigen Paketen; je ein zusätzliches
  Asset gehört zu einer älteren unvollständigen Karte.
- Zwei Pakete sind lokal für 6. September, 19:30 Uhr vorgemerkt.
- Ein Leona-Paket benötigt Owner-Neuplanung, ein Mara-Paket Owner-Review.
- Zwei frühere manuelle native Posts bleiben dokumentiert.
- Live-Posts, externe Meta-Aufrufe, Fiverr-Aktionen, Kommentare, Likes, Follows,
  DMs, Kosten und neue Secrets dieses Runs: jeweils 0.

## Für Auswertung mit ChatGPT

1. Creator Ops 1.6.4-beta läuft ohne Codex lokal weiter.
2. 116/116 Tests und echter Restore sind grün.
3. GitHub `main` ist ohne Force-Push synchronisiert.
4. Der Meta-Pfad ist implementiert, aber standardmäßig vollständig aus.
5. Lokales APPROVE ist niemals die Live-Freigabe.
6. Jede Live-Freigabe gilt nur für ein konkretes Paket.
7. Unsicherer Publish-Ausgang wird niemals automatisch wiederholt.
8. Queue-Key bleibt bei Neuplanung stabil.
9. Meta-Receipts überleben Patch- und Full-Restore.
10. Astra ist optionaler Bonus, keine Voraussetzung.
11. Pro Persona sind 10 reale Assets unveröffentlicht.
12. Zwei Feedpakete stehen lokal auf 19:30 Uhr.
13. Eine Leona-Neuplanung und eine Mara-Reviewentscheidung sind offen.
14. Reale Analytics fehlen und dürfen nicht erfunden werden.
15. Dieser Run führte keine externe Plattformaktion aus.
