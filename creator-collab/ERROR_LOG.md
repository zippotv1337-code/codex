# Error Log

Stand: 6. September 2026

## E-164-001 · Windows Aufgabenplanung verweigert Zugriff

- **Status:** GELÖST
- **Lösung:** benutzereigener Windows-Autostart ohne Adminrecht; genau ein
  Supervisor und Health `ok` real bestätigt.

## E-164-002 · Offizieller Meta-Publisher nicht konfiguriert

- **Status:** OFFEN / ERWARTETES OWNER-GATE
- **Ursache:** keine Meta-Umgebungswerte, keine freigegebenen öffentlichen
  Asset-URLs und keine Paket-Live-Autorisierung.
- **Verhalten:** keine externe Anfrage, kein `PUBLISHED`, kein Blind-Retry.
- **Fortsetzung:** `docs/OFFICIAL_META_PUBLISHING.md`.

## E-164-003 · Alter Posting-Slot abgelaufen

- **Status:** OWNER REVIEW
- **Betroffen:** Leona Content 3 „Spätsommer in Berlin“.
- **Vorschlag:** 6. September 2026, 19:30 Uhr; Übernahme bleibt rein lokal.

## E-164-004 · Teilweise Live-Konfiguration im Scheduler

- **Status:** GELÖST
- **Lösung:** Scheduler verlangt alle vier Konfigurations-/Capability-Gates,
  Adapter `meta-graph` und ein ausreichend langes Laufzeitpasswort.

## E-164-005 · Stale Publish konnte Neuplanungsschlüssel wechseln

- **Status:** GELÖST
- **Lösung:** abgestürzte `PUBLISHING`-Claims blockieren bis zur manuellen
  Abstimmung; Neuplanung behält den ursprünglichen Queue-Key.

## E-164-006 · Recovery-Lücken bei Receipts und Standalone-Bootdateien

- **Status:** GELÖST
- **Lösung:** Patch-Backups nehmen validierte Meta-Receipts automatisch mit;
  Full-Backups enthalten `config.toml` und Standalone-Start/Stop.
