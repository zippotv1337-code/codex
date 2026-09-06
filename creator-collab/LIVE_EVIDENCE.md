# Live Evidence

Stand: 2026-09-06T08:10:00+02:00 · Europe/Berlin

## Instagram

- **Run-Status:** TECHNISCH BEREIT / EXTERNES OWNER-GATE
- **INSTAGRAM_AUTOMATION_PROOF:** 0/10
- **Live in diesem Run:** 0
- **Externe Requests in diesem Run:** 0
- **Lokaler Modus:** `local-mock`, Live-Schalter vollständig aus
- **Queue:** 2 × `LOCAL_SCHEDULED`, 1 × `NEEDS_RESCHEDULE_REVIEW`

Der offizielle Meta-Graph-Carousel-Pfad ist lokal implementiert. Echte Meta-
Bestätigung, Instagram-Permalink, persona-feste Kontozuordnung, native KI-
Kennzeichnung und ein separater Live-Gate pro Paket sind Pflicht. Fake-
Transporttests beweisen die lokale Zustandslogik, nicht die externe Produktion.

### Bereits früher owner-bestätigte manuelle Veröffentlichungen

Diese Datenbankbelege zählen nicht zur Automation-Proof-Serie und wurden in
diesem Run nicht erneut im Browser geöffnet.

- Mara Field · Content 4 · `instagram-native-manual` ·
  https://www.instagram.com/mara.field.ai/p/Dc3d7CHgO3S/
- Leona Voss · Content 5 · `instagram-native-manual` ·
  https://www.instagram.com/leonavoss.ai/p/Dc3elLhAC2-/

## Fiverr

- **Status:** ENTWURF / OWNER-GATE
- Kein Formular, Account, Preis, Liefertermin oder Gig wurde extern verändert.
- Keine Anbieter-, Steuer- oder Identitätsangabe wurde erfunden.

## Technische Belege

- Runtime: `http://127.0.0.1:4180/`, Health `ok`, Version `1.6.4-beta`
- Genau ein Supervisor; Watchdog und Scheduler real erfolgreich
- Schedulerlog: `live dispatch skipped by complete owner gate`
- SQLite: `integrity_check = ok`, 6 Inhalte, 6 Publikationen, 3 Queuejobs
- Tests: 116/116 grün; Compile-, JavaScript- und PowerShell-Prüfungen grün
- Astra-HIGH-Zweitprüfung: drei P1-Funde behoben und Nachprüfung ohne Blocker
- GitHub-Codebaseline: `origin/main` auf `8ed82dd` fast-forward synchronisiert;
  diese Abschlussdokumente folgen als separater Handoff-Commit
- Recovery: `Backup_Meilenstein_20260906-0809.zip`, SHA256
  `e937c16d6e80c52bc9d96ee746f6f71989d3a5687bb7cf26bd3bf553b6b41401`
- Restore: Integrität `ok`, 0 Secret-Referenzen, Standalone-Bootdateien enthalten
