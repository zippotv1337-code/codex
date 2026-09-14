# ZippoWorkz — Local AI Next Run

## Auftrag

Arbeite ausschließlich lokal in `C:\Zippoworkz`. Verwende den bestehenden
Workspace, die kanonische Datenbank `data/review_dashboard.db` und den
installierten begrenzten Worker. Keine neue Architektur und keine externe
Plattformaktion.

## Aktueller neuer Input

- Mara-Paket: `Hofladen am Sonntag`
- Fünf Bilder unter
  `data/media/sfw/mara-field/2026-09-15/mara-hofladen-sonntag/`
- Paketbeschreibung: `docs/MARA_HOFLADEN_SONNTAG_2026-09-14.md`
- Herkunft: Cloud-generiert aus dem bestehenden fiktiven Mara-Referenzavatar
- Sicherheit: vorgeprüft `SFW + PUBLIC_SFW`; Owner-Review bleibt erforderlich

## Begrenzte Aufgaben

1. Health und SQLite-Integrität lesen.
2. Fünf Bilddateien, Dateigrößen und SHA-256 erfassen.
3. Hash-Dubletten gegen den bestehenden lokalen Assetbestand prüfen.
4. Prüfen, ob alle fünf erwarteten Pose-Slots als Metadaten vorhanden sind.
5. Posting-Kit auf Persona-Ton, CTA, Hashtags und fehlende Felder prüfen.
6. Vorhandene veröffentlichte Assets gegen die neue Auswahl abgleichen.
7. Top-3-Reihenfolge als Vorschlag prüfen; keine Owner-Entscheidung erfinden.
8. Fehlende Analytics weiterhin als `UNKNOWN`/`NULL` behandeln.
9. Secret-freien Ergebnisbericht nach `C:\Zippoworkz\Handoff` schreiben.
10. Danach `IDLE_CLEAN`; keine DONE-Aufgaben wiederholen.

## Verboten

Kein Instagram/Fiverr/Meta-Zugriff, kein Publish, keine Kommentare/DMs,
keine Persona-Änderung, keine Modellinstallation, kein Git-Push, keine
Passwort-/Tokenverarbeitung, keine erfundenen Bildbewertungen und keine
automatisch generierten Shellbefehle.

## Erwarteter Output

- `LOCAL_AI_HOFLADEN_QA.json`
- `LOCAL_AI_HOFLADEN_RESULT.md`
- externer Aktionsstatus immer `NONE`
