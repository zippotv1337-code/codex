# Sitzungsjournal

- Datum/Zeit: 2026-09-29 15:35 Europe/Berlin
- Agent: `Codex`
- Ziel der Sitzung: Offiziellen 24/72/168h-Instagram-Insights- und Learning-Loop in den bestehenden ZippoWorkz-Betrieb integrieren und mit realen Daten beweisen.

## Ausgangslage

- Sechs offizielle Meta-Graph-Publikationen waren in der kanonischen DB bestätigt.
- Es gab 18 fällige Analytics-Fenster, aber noch keinen Analytics-Event in der kanonischen DB.
- Fehlende historische Fenster durften nicht aus aktuellen kumulativen Werten rekonstruiert oder als Null ausgegeben werden.

## Durchgeführt

- Offiziellen read-only `MetaInstagramInsightsService` ergänzt; Tokens bleiben ausschließlich im node-lokalen Secret Broker.
- Fällige Insights werden idempotent in die bestehende Tabelle `manual_analytics_events` geschrieben; keine zweite DB oder Statuswahrheit.
- Bei einem verspäteten ersten Read wird nur das höchste fällige Fenster als `META_GRAPH_LATE` gespeichert. Frühere Fenster bleiben sichtbar `MISSED / UNKNOWN`.
- Scheduler, CLI und vorhandenes Analytics-Dashboard an denselben Sync-Pfad angeschlossen.
- Dashboard zeigt reale Providerquelle und bietet einen geschützten manuellen read-only Trigger als Fallback.
- Bestehendes Prime-Time-Learning verarbeitet nun auch echte offizielle Meta-Graph-Publikationen.
- Der alte harte Fiverr-Status `OWNER_GATE` wurde entfernt; Analytics liest den tatsächlichen lokalen Fiverr-Accountstatus.

## Verifiziert

- Offizieller Meta-Graph-Read erfasste sechs Publikationen ohne Fehler:
  - 6 Analytics-Events, davon 5 `META_GRAPH_LATE` und 1 zeitnahes `META_GRAPH`-168h-Fenster.
  - Erfasste Felder: Reach, Views, Likes, Comments, Shares und Saves.
  - Profile Visits, Follows, Link Clicks und Revenue bleiben `NULL`, weil sie auf Medienebene nicht geliefert wurden.
- Direkter zweiter Lauf: 0 neue Events, 6 wartend/aktuell; Gesamtzahl blieb exakt 6.
- Reale Summen nach Persona:
  - Leona: Reach 17, Views 50, Likes 2, Comments 1, Shares 0, Saves 0.
  - Mara: Reach 31, Views 96, Likes 4, Comments 0, Shares 0, Saves 0.
- Learning-Status: `OBSERVING`; Empfehlung `VARIATE`, keine große Strategieänderung aus kleinen Stichproben.
- SQLite: Schema 7, `integrity_check=ok`, Foreign-Key-Verstöße 0.
- Tests: `203 passed, 22 subtests passed`; Compile-, JavaScript-, PowerShell-, Diff- und Secret-Checks grün.
- Keine externe Schreib-/Publish-Aktion, keine Kosten und keine Secrets in Ausgabe oder Git.

## Entscheidungen

- Aktuelle kumulative Insights dürfen nicht rückwirkend als exakte 24h-/72h-Werte ausgegeben werden.
- Reale beobachtete Nullen bleiben 0; nicht verfügbare Metriken bleiben `NULL`.
- Offizielle 168h-Snapshots dürfen die vorhandene Prime-Time-Logik speisen; späte Fenster werden dabei transparent als spät markiert.

## Offen oder blockiert

- Für fünf ältere Publikationen sind exakte 24h-/72h-Historien nicht mehr rekonstruierbar und bleiben `MISSED / UNKNOWN`.
- Nächste neue Publikation muss planmäßig bei 24h, 72h und 168h vom Scheduler gelesen werden, um alle drei exakten Fenster zu belegen.

## GOAL UPDATES

| Goal ID | Before | After | Evidence | Next |
|---|---|---|---|---|
| M-02 | ACTIVE / WAITING_FIRST_DUE_WINDOW | DONE — REAL_GRAPH_LEARNING_CYCLE | 6 echte Events; Dashboard/Leaderboards/Learning; idempotenter Readback | nächste Publikation exakt bei 24/72/168h verfolgen |
| T-002 | ACTIVE | DONE | offizieller Sync + 6 echte Publikationen + Learning `OBSERVING` | keine offene Temp-Aufgabe |
| M-07 | ACTIVE / Analytics offen | ACTIVE / ANALYTICS_BASELINE_AVAILABLE | Leona/Mara reale Summen und Top-30-Liste | kleine datenbasierte Variation statt blindem Rebuild |

## Nächster Agent

1. Nächste frische PUBLIC_SFW-Publikation anhand der realen Baseline als kleine Variation planen.
2. Scheduler nach deren 24h-/72h-/168h-Fenstern kontrolliert read-only laufen lassen.
3. Fiverr Gig 1 öffentlich gegen den gespeicherten 149/349/699-Stand zurücklesen, ohne Anti-Bot-Umgehung.
