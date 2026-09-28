# CODEX NEXT TASK — Virality + Topic-to-Short Factory MVP

**Status:** READY_FOR_CODEX  
**Priorität:** P1  
**Stand:** 28.09.2026

## Vor dem Start

1. `../ZIPPOWORKZ_START_HERE.md` bzw. Repo-Root `ZIPPOWORKZ_START_HERE.md` lesen.
2. `ZIPPOWORKZ_OWNER_POLICY.md` vollständig lesen.
3. `creator-collab/AGENTS.md`, `CURRENT_HANDOFF.md`, `docs/CURRENT_STATE.json`,
   `docs/ARCHITECTURE.md` und `docs/BACKLOG.md` lesen.
4. Keine alte Owner-Decision oder Chat-Erinnerung gegen die zentrale Policy stellen.

## Ziel

Baue die kleinste wirklich nutzbare erste Version für zwei zusammenhängende P1-Bausteine:

- **Virality / Trend Intelligence**
- **Topic-to-Short Factory**

Der Ablauf soll später sein:

`Trend/Hook -> eigenes Konzept -> Script -> Voice/Shotplan -> Media/Editing -> Captions -> QA -> Publish -> 24/72/168h Insights -> Learning`

Dieser Auftrag implementiert zunächst den internen, testbaren Kern bis einschließlich QA-/Produktionsvorbereitung.
## Architekturregeln

- Bestehenden Creator-Ops-Kern erweitern, keine zweite App und kein Framework-Wechsel.
- Python/SQLite/aktuelles Dashboard-Muster weiterverwenden.
- `data/review_dashboard.db` bleibt operative Hauptdatenbank.
- Keine zweite Wahrheit neben Creator Ops erzeugen.
- Neue Tabellen/Schema nur additiv und migrationssicher.
- Bestehende Publishing-Pipeline nicht destabilisieren.
- Kein kostenpflichtiger Dienst, kein Kauf, kein externer Publish in diesem Auftrag.
- Keine Secrets in Code, DB, Tests, Logs oder Doku.

## MVP-Funktionen

1. **Trend-Brief ingestieren**
   - strukturierter Input mit Plattform, Quelle/URL, Datum, Nische, Hook-Muster,
     Visual-Muster, Caption/CTA-Muster und kurzer Begründung;
   - Quelle und Analyse getrennt speichern;
   - keine fremden Texte einfach kopieren.

2. **Pattern Extraction**
   - wiederverwendbare Mechaniken extrahieren: Hook-Typ, Spannungsbogen,
     Visual-Rhythmus, CTA, Länge, Format;
   - Originalquelle als Evidence/Referenz behalten.

3. **Originales Short-Konzept erzeugen**
   - Input: Thema + Zielgruppe + Persona/Kunde + ausgewählte Pattern;
   - Output: eigener Hook, Script, Shot-/B-Roll-Plan, Voice-Hinweise,
     Caption/Subtitles-Plan und CTA;
   - keine bloße Kopie des Quellposts.

4. **Pipeline-State**
   - mindestens: `RESEARCHED -> CONCEPT_READY -> SCRIPT_READY -> MEDIA_PLAN_READY -> QA_READY`;
   - jeder Schritt mit Timestamp/Evidence/Status;
   - externe Publish-/Media-Ausführung noch nicht automatisch auslösen.
5. **Learning Hook**
   - Schnittstelle/Datenmodell vorbereiten, damit 24/72/168h-Analytics später
     wieder Pattern/Hook/Timing bewerten können;
   - keine erfundenen Metriken.

6. **Bedienung**
   - mindestens CLI oder bestehende interne Service-Schnittstelle;
   - wenn mit wenig Aufwand passend: kleine read-only Dashboard-Ansicht/Statuskarte,
     aber keine neue Dashboard-Architektur.

## Akzeptanzkriterien

- Ein lokaler Beispiel-Trendbrief kann gespeichert werden.
- Daraus kann ein neues, eigenständiges Short-Konzept für eine bestehende Persona erzeugt/angelegt werden.
- Pipeline-Status und Evidence sind nachvollziehbar.
- Kein externer Publish, keine Kosten, keine Secret-Ausgabe.
- Bestehende Tests bleiben grün.
- Neue fokussierte Tests für Trend-Ingest, Originalitäts-/Source-Trennung,
  Pipeline-State und Learning-Hook hinzufügen.
- `pytest` für relevante Tests ausführen.
- Python-Compilecheck für neue/geänderte Module.
- SQLite-Integrität/Foreign Keys nach Schemaänderung prüfen.

## Abschluss

Nach grünem Teststand:

1. `docs/CURRENT_STATE.json`, `CURRENT_HANDOFF.md` und bei Bedarf `docs/ARCHITECTURE.md` aktualisieren.
2. Backlog-Punkt nicht als vollständig DONE markieren, wenn Media-/Voice-/Publish-Worker noch fehlen.
3. Sauberen Commit erstellen und nach Policy normal nach `main` übernehmen, sofern kein kritischer Gate-Bereich betroffen ist.
4. Abschlussbericht mit:
   - geändert/neu,
   - Tests,
   - DB-Migration,
   - offenen Punkten,
   - Commit-Hash,
   - nächstem kleinsten sinnvollen Schritt.

**Leitsatz:** Der Owner gibt Thema/Ziel vor; ZippoWorkz macht daraus möglichst automatisch einen messbaren Content-Workflow.
