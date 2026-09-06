# Human Handoff — einzige aktive Owner-Inbox

Stand: 6. September 2026, 08:10 Uhr · Creator Ops 1.6.4-beta

## JETZT

1. Öffne `http://127.0.0.1:4180/`.
2. Bei Leona „Spätsommer in Berlin“ den vorgeschlagenen neuen Termin
   **6. September, 19:30 Uhr** übernehmen oder unverändert zur Prüfung lassen.
   Das ändert ausschließlich die lokale Queue.
3. Bei Mara „Fünf Minuten Maschinencheck“ **APPROVE**, **CHANGE** oder
   **REJECT** wählen. Auch APPROVE veröffentlicht nicht live.

Leona „September Roofline“ und Mara „Küchenfenster“ stehen bereits lokal auf
6. September, 19:30 Uhr. Der aktuelle `local-mock`-Modus sendet sie nicht an
Instagram.

## NICHT DRINGEND

- „Berlin Filmlook“ und „Werkstattabend“ sind ältere unvollständige Karten mit
  je nur einem realen Asset. Sie gehören nicht zur produktiven Vier-Paket-
  Reserve und können später bereinigt oder ergänzt werden.
- Pro Persona sind 10 reale Assets unveröffentlicht; 9 davon liegen in den
  zwei feedfähigen Paketen.

## SEPARATE FREIGABEN

- Jede einzelne Live-Veröffentlichung benötigt nach lokaler Freigabe noch den
  separaten Live-Zweiklick-Gate.
- Meta-Credentials, öffentliche Asset-URLs und natives KI-Disclosure müssen
  vollständig eingerichtet sein; Anleitung: `OFFICIAL_META_PUBLISHING.md`.
- Kommentare, Likes, Follows, DMs, Fiverr, kostenpflichtige Dienste und eine
  Änderung der GitHub-Sichtbarkeit bleiben eigene Owner-Entscheidungen.

## DANACH

- Echte Instagram-Insights nach 24, 72 und 168 Stunden manuell erfassen.
- Ohne echte Kommentartexte oder Analytics wird nichts erfunden.
- Erst danach die nächste Produktion datenbasiert auswählen.

## Betrieb und Belege

- Dashboard: `http://127.0.0.1:4180/`
- Offline-Leseansicht: `output/offline/index.html`
- Status: `docs/CURRENT_STATE.json`
- Tests: 116/116 grün
- Datenbank: Integrität `ok`
- Backup: `backups/Backup_Meilenstein_20260906-0809.zip`
- Restore: Integrität `ok`, 0 Secret-Referenzen
- Externe Aktionen dieses Runs: 0
