# Human Handoff — einzige aktive Owner-Inbox

Stand: 5. September 2026, 19:40 Uhr · Creator Ops 1.4.1

## JETZT

1. Öffne `http://127.0.0.1:4180/` und entscheide bei Mara
   „Fünf Minuten Maschinencheck“: **APPROVE**, **CHANGE** oder **REJECT**.
   Der zuvor tote CHANGE-/REJECT-Dialog ist repariert und im eingebetteten
   Browser sichtbar geprüft. APPROVE ist aktiv und legt nur einen lokalen
   Queue-Eintrag an; es wird nichts live veröffentlicht.
2. Kontrolliere die drei bereits `LOCAL_SCHEDULED` markierten Pakete. Der
   offizielle Instagram-Adapter ist nicht konfiguriert; lokale Terminierung ist
   kein Beleg für einen Instagram-Post.

## SEPARATE FREIGABEN

- Live-Publishing, Kommentare, Likes, Follows, DMs und Accountänderungen.
- Installation der vorbereiteten Windows-Aufgaben. Zuerst nur ansehen:
  `scripts/install_runtime_tasks.ps1`; tatsächliche Installation ausschließlich
  nach bewusster Entscheidung mit `-Apply`.
- Git/GitHub bleiben nach Owner-Anweisung geparkt.

## DANACH

- Echte Instagram-Insights nach 24, 72 und 168 Stunden manuell erfassen.
- Konkrete echte Kommentare bereitstellen, wenn individuelle Antwortentwürfe
  gewünscht sind; ohne Quelldaten wird nichts erfunden.
- Nächste Bildproduktion erst aus realen Signalen wählen. Dokumentierte
  Kandidaten bleiben Leona „Gym Reset“ und Mara „Werkstatt-Feierabend“.

## Betrieb

- Dashboard: `http://127.0.0.1:4180/`
- Offline-Leseansicht: `output/offline/index.html`
- Status: `docs/CURRENT_STATE.json`
- Letztes Backup:
  `backups/creator-ops-backup-high-autopilot-final-20260905-193722.db`
- Verifikation: 96/96 Tests; Datenbank und Restore `ok`; Kosten 0 EUR.
