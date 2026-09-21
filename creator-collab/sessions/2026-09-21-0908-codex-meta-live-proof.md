# Sitzungsjournal

- Datum/Zeit: 21.09.2026, 09:08 Europe/Berlin
- Agent: `Codex`
- Ziel der Sitzung: Den ausdrücklich bestätigten Leona-Carousel-Pilot genau
  einmal über die offizielle Meta API veröffentlichen und vollständig
  reconciliieren.

## Ausgangslage

Leona und Mara waren read-only authentifiziert. Publication `1` / Content `1`
„Rainy Berlin Afterwork“ bestand den vollständigen geheimnisfreien Preflight:
korrekter Account, drei öffentliche JPEGs, SFW/PUBLIC_SFW, AI-Kennzeichnung,
Owner-Live-Gate und freie Quote. Queuejob `1` hatte null Versuche, keine
externe ID und kein Receipt.

## Durchgeführt

- Validiertes SQLite-Backup vor dem Live-Schritt erstellt:
  `backups/creator-ops-backup-pre-leona-meta-live-20260921.db`.
- Nach der unmittelbaren Owner-Bestätigung den bestehenden Queuejob auf den
  aktuellen Zeitpunkt gesetzt, ohne einen zweiten Job oder neuen Queue-Key zu
  erzeugen.
- Drei Meta-Kindercontainer, einen Carousel-Container und genau einen
  `media_publish` über `graph.instagram.com` ausgeführt.
- Graph-Bestätigung gelesen, Receipt geschrieben und Queue, Publication,
  Content sowie drei Top-Pick-Assets atomar auf veröffentlicht gesetzt.

## Verifiziert

- Dispatch: due 1, published 1, blocked 0, retryable 0.
- Permalink: https://www.instagram.com/p/DdilnXGEVdO/
- Media-ID: `18028287917684160`.
- Graph: `CAROUSEL_ALBUM`, Zeit `2026-09-21T07:08:04+00:00`.
- DB, Graph und Receipt stimmen bei ID und Permalink überein.
- Receipt `CONFIRMED`; Queueversuche 1; kein Fehler und kein Retry.
- Drei Top-Pick-Assets `PUBLISHED`; Content und Publication `PUBLISHED`.
- SQLite `integrity_check = ok`.
- Das Pre-Live-Backup wurde separat geöffnet; `integrity_check = ok`.
- 17 fokussierte Meta-Publishing-/Preflight-Tests grün.
- Unmittelbarer zweiter Queue-Dispatch: `due=0`, `published=0`; kein zweiter
  externer Versuch.
- Keine Tokens in Git, DB, Journal oder Handoff.

## Entscheidungen

- Globale unbeaufsichtigte Live-Schalter bleiben deaktiviert. Der Erfolg
  beweist den offiziellen paketgebundenen Pfad, nicht die Freigabe aller
  vorhandenen Queuejobs.
- Derselbe Queue-Key darf wegen des bestätigten Receipts nicht erneut extern
  publizieren.
- Die im Chat offengelegten Tokens werden als rotationsbedürftig behandelt.

## Offen oder blockiert

- Analytics für 24h, 72h und 168h sind erst zu den jeweiligen Zeitfenstern
  fällig; bis dahin `UNKNOWN/NULL` statt erfundener Werte.
- Leona- und Mara-Tokens vor dem dauerhaften Produktionsbetrieb rotieren und
  die frischen Werte ausschließlich lokal speichern.
- Mara benötigt ein eigenes vollständiges, freigegebenes Paket und einen
  separaten Preflight; das Leona-Set wird nicht wiederverwendet.

## GOAL UPDATES

| Goal ID | Before | After | Evidence | Next |
|---|---|---|---|---|
| M-03 | READY_FOR_CONTROLLED_PUBLISH | DONE | offizieller Graph-Carousel live; Receipt/DB/Graph konsistent | Analytics und Tokenrotation |
| T-004 | READY_FOR_CONTROLLED_PUBLISH | DONE | ein Versuch, bestätigter Permalink, kein Retry | nicht ohne neues Signal öffnen |
| M-02 | ACTIVE | ACTIVE | neuer echter Meta-Post als Analytics-Quelle | 24h/72h/168h erfassen |

## Nächster Agent

1. Tokens sicher rotieren und beide Konten read-only erneut prüfen.
2. Ab 22.09.2026 09:08 Europe/Berlin das echte 24h-Analytics-Fenster
   erfassen; fehlende Metriken bleiben `UNKNOWN/NULL`.
3. Eigenständiges Mara-Paket vorbereiten; Leonas veröffentlichte Assets nicht
   erneut als frische Top-Picks verwenden.
