# Error Log

Stand: 5. September 2026

## E-164-001 · Windows Aufgabenplanung verweigert Zugriff

- **Bereich:** Standalone Runtime
- **Schwere:** mittel
- **Sanitizer Fehler:** `access denied`
- **Status:** GELÖST
- **Lösung:** benutzereigene Startdatei
  `CreatorOpsStandalone.cmd` im persönlichen Windows-Autostart; kein Admin-
  Recht und keine Registry-Abhängigkeit erforderlich
- **Test:** Autostart-Datei vorhanden, genau ein Supervisor aktiv, Health OK

## E-164-002 · Offizieller Meta-Publisher nicht konfiguriert

- **Bereich:** Instagram Publishing
- **Schwere:** erwartetes Owner-Gate
- **Status:** OFFEN / FAIL-CLOSED
- **Ursache:** keine Meta-Umgebungswerte und kein lokales Medienmanifest
- **Verhalten:** keine externe Anfrage, kein `PUBLISHED`, kein Blind-Retry
- **Fortsetzung:** `docs/OFFICIAL_META_PUBLISHING.md`

## E-164-003 · Alter Posting-Slot abgelaufen

- **Bereich:** Publish Queue
- **Schwere:** niedrig
- **Status:** OWNER REVIEW
- **Betroffen:** Leona Content 3
- **Verhalten:** `NEEDS_RESCHEDULE_REVIEW`, zukünftiger Vorschlag vorhanden
- **Fix:** getesteter Owner-Button übernimmt den Vorschlag ausschließlich lokal
