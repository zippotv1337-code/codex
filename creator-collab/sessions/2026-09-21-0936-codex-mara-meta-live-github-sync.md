# Sitzungsjournal

- Datum/Zeit: 21. September 2026, 09:36 Uhr (Europe/Berlin)
- Agent: `Codex`
- Ziel der Sitzung: Den bewiesenen offiziellen Meta-Pfad für ein reales Mara-
  Paket ausführen und den secret-freien Projektstand zu GitHub synchronisieren.

## Ausgangslage

- Leona „Rainy Berlin Afterwork“ war bereits offiziell über den Meta-Adapter
  veröffentlicht und vollständig reconciliiert.
- Mara-Credentials waren ausschließlich im Windows-User-Environment vorhanden
  und read-only dem Konto `mara.field.ai` zugeordnet.
- Die operativen Mara-Reviewkarten enthielten noch Mock-Dateien; diese wurden
  nicht veröffentlicht. Das ältere Maschinencheck-Set blieb wegen der früheren
  Owner-Ablehnung ausgeschlossen.

## Durchgeführt

- Das historisch QA-bestandene, unveröffentlichte Paket „Küchenfenster“ mit
  fünf realen KI-generierten SFW-/PUBLIC_SFW-Originalen verwendet.
- Top 3 gemäß dokumentierter Auswahl: S4 Ganzkörper/Bewegung → S3 Fenster
  rechts 3/4 → S5 candid am Tisch mit Notizbuch.
- SQLite-Backup vor Zustandsänderung erstellt und Integrität geprüft.
- Fünf Originale in Content `4` importiert; Caption, Hook, CTA, Hashtags,
  Disclosure, Asset-Reihenfolge und lokale Owner-Freigabe gespeichert.
- Drei JPEGs mechanisch erzeugt und in einem separaten, secret-freien
  GitHub-Mediencommit veröffentlicht, damit Meta unveränderliche öffentliche
  HTTPS-URLs abrufen konnte.
- Read-only Meta-Preflight vollständig `READY`: richtige Account-ID und
  Username, `BUSINESS`, Quote 0/100, drei HTTP-200-JPEGs, Live-Gate gesetzt.
- Genau einen fälligen Mara-Queuejob über den offiziellen Adapter ausgeführt.
- Current-State-Logik korrigiert, damit bestätigte Meta-Graph-Publikationen als
  echter Live-Kanal und `proven_live` gezählt werden.
- Einen kalenderabhängigen Dashboard-Test auf eine dynamische zukünftige Zeit
  umgestellt; keine Produktionslogik geändert.

## Verifiziert

- Live: https://www.instagram.com/p/DdioXo1Ec9j/
- Graph: Media-ID `18090373508475307`, `CAROUSEL_ALBUM`, Username
  `mara.field.ai`, Plattform-Zeit `2026-09-21T07:32:09+00:00`.
- Publication `2`, Queue `2`, Content `4` und drei Top-Pick-Assets stehen
  `PUBLISHED`; Receipt `CONFIRMED`; ein Versuch, kein Fehler.
- Zweiter Dispatch: `due=0`; kein Doppelpost.
- SQLite `integrity_check = ok`.
- 44 fokussierte Current-State-, Meta-, Preflight-, Queue- und Dashboard-Tests
  bestanden.
- Git enthält keine DB, Backups, Receipts oder Secrets. Normaler Push auf
  `origin/main`; kein Force-Push und kein History-Rewrite.

## Entscheidungen

- Mock-Assets wurden nicht als reale Medien behandelt.
- Die dokumentierte Top-3-Auswahl wurde beibehalten, statt ein neues Set zu
  generieren.
- Globale unbeaufsichtigte Live-Schalter bleiben deaktiviert; die Owner-
  Freigabe galt ausschließlich diesem konkreten Mara-Paket.

## Offen oder blockiert

- Die im Chat offengelegten Meta-Tokens sollten lokal rotiert werden.
- 24h/72h/168h-Analytics für beide neuen offiziellen Publikationen fehlen noch
  und bleiben bis zur Fälligkeit `UNKNOWN/NULL`.

## GOAL UPDATES

| Goal ID | Before | After | Evidence | Next |
|---|---|---|---|---|
| M-03 | DONE für Leona | DONE für Leona + Mara | zwei Graph-bestätigte Carousels, zwei Receipts | nur nach Defekt/Rotation reopen |
| T-004 | DONE für Leona | DONE für Leona + Mara | Mara Permalink und Media-ID bestätigt | none |
| M-12 | normaler Sync offen | DONE / SYNC_VERIFIED_2026_09_21 | secret-freier `origin/main`-Push | normale Abschluss-Syncs |
| M-02 | OBSERVING | ACTIVE / zwei neue Messfenster vorgemerkt | zwei neue reale Publikationen | 24h/72h/168h erfassen |

## Nächster Agent

1. Meta-Tokens über den lokalen Secret-Weg rotieren und nur read-only prüfen.
2. Fällige 24h/72h/168h-Insights für Leona und Mara erfassen.
3. Fiverr Gig 1 öffentlich verifizieren, sobald die Seite erreichbar ist.
