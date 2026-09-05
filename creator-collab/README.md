# Creator Collaboration Workspace

Dieser Ordner ist die gemeinsame, versionskontrollierte Übergabeschicht für
ChatGPT und Codex.

## Lesereihenfolge

1. `PROJECT_RESUME.md` – stabiler Gesamtstand und Leitplanken
2. `CURRENT_HANDOFF.md` – unmittelbar nächste Aufgaben und Blocker
3. `sessions/` – chronologische Sitzungsjournale mit Belegen

## Schreibregel

Am Ende jeder Arbeitssitzung werden ein neues Journal und der aktuelle Handoff
aktualisiert. Geheimnisse und Login-Daten gehören niemals in dieses Repository.

## Lokaler Creator-Ops-MVP

Der MVP bildet den vollständigen Freigabe- und Lernpfad lokal ab. Er verwendet
SQLite, erzeugt ausschließlich lokale Mock-Drafts und kann vom Owner bereits
bestätigte native Posts nachträglich erfassen. Es werden keine Social-Media-APIs
aufgerufen und nichts live veröffentlicht.

```powershell
python -m creator_ops.cli --db data/creator_ops.db demo --date 2026-09-03
python -m creator_ops.cli --db data/creator_ops.db evening-run --at 2026-09-03T20:00:00
python -m creator_ops.cli --db data/creator_ops.db engagement
python -m creator_ops.cli --db data/creator_ops.db export --out backups --label latest
python -m creator_ops.cli --db data/creator_ops.db backup --out backups --label latest
python -m creator_ops.cli --db data/creator_ops.db restore --backup backups/creator-ops-backup-latest.db --out backups/restored.db
python -m creator_ops.cli --db data/review_dashboard.db import-assets --creator leona-voss --date 2026-09-04 --rights-status AI_GENERATED C:\Pfad\zu\bild.png
python -m creator_ops.cli --db data/creator_ops.db status
python -m creator_ops.cli --db data/creator_ops.db status --tests-passed 41 --tests-failed 0 --out docs/CURRENT_STATE.json
python -m creator_ops.cli --db data/review_dashboard.db recovery-backup --kind weekly --out backups
python -m creator_ops.cli --db data/review_dashboard.db reconcile-instagram --creator leona-voss --content-id 5 --asset-id 24 --url https://www.instagram.com/leonavoss.ai/p/Dc3elLhAC2-/ --published-at 2026-09-04
python -m creator_ops.cli --db data/review_dashboard.db manual-analytics --publication-id 4 --window 24 --reach 100 --likes 10
python -m creator_ops.cli --db data/review_dashboard.db adworks-status
python -m creator_ops.cli --db data/review_dashboard.db adworks-dry-run --pack creator-sfw-basic
python -m creator_ops.cli --db data/review_dashboard.db morning-run --at 2026-09-05T05:30:00+02:00
python -m creator_ops.cli --db data/review_dashboard.db publish-reconcile
python -m creator_ops.cli --db data/review_dashboard.db publish-queue
python -m creator_ops.cli --db data/review_dashboard.db publish-dispatch-due --at 2026-09-05T19:30:00+02:00
python -m creator_ops.cli --db data/review_dashboard.db patch-backup --base backups/<basis>.zip --reason "kleines Delta" --label v14 --file docs/HUMAN_HANDOFF.md
python -m creator_ops.cli --db data/review_dashboard.db offline-snapshot --out output/offline
python -m unittest discover -s tests -v
```

Die lokale Freigabeoberfläche startet separat:

```powershell
.\run_dashboard.ps1
```

Danach ist sie unter `http://127.0.0.1:4180/` erreichbar. Sie bereitet für den
nächsten Tag je eine Review-Karte für Leona und Mara vor. „Freigeben“ erzeugt
einen lokalen, auditierbaren Queue-Eintrag mit `LOCAL_SCHEDULED`; es gibt
keinen konfigurierten Live-Publisher.
Die Navigation enthält zusätzlich `/archive`, `/top3`, `/control`, `/offer`
und `/revenue`. Echte Einträge sind
standardmäßig von Mock-Daten getrennt; Top 3 verwendet vorhandene Raten vor
Rohwerten.

Passwortgeschützter Heim-LAN-Start ohne Router-Freigabe:

```powershell
$env:CREATOR_OPS_PASSWORD = '<mindestens 12 Zeichen>'
.\run_lan.ps1
```

Backup- und LAN-Details stehen in `docs/BACKUP_POLICY.md` und
`docs/LOCAL_LAN_SERVER.md`.

Optionaler kostenloser Remote-Testzugang:

```powershell
.\run_remote_free.ps1
```

Dieser Modus verlangt ein nur im Prozess gehaltenes Passwort mit mindestens
12 Zeichen und einen lokal installierten `cloudflared`-Client. Das Dashboard
bleibt an `127.0.0.1` gebunden; es werden keine Router-Ports geöffnet. Details,
Grenzen und Sicherheitsverhalten: `docs/REMOTE_ACCESS_FREE.md`.

Enthalten sind:

- zentrale Leona-/Mara-Konfiguration
- Asset Registry mit fünf Kandidaten und drei Top Picks
- additive Schema-Versionierung mit `ALLTAG`, `TEASER`, `ADULT_18` sowie
  verbindlicher Safety-/Sichtbarkeitsprüfung
- gewichtete, pose-diverse Top-3-Auswahl und vollständige Fünfer-Pose-Matrix
- Content-Mix-Empfehlung 40/35/25 ohne automatische Generierung
- QA-, Duplikat-, Rechte- und KI-Disclosure-Prüfung
- Review- und Approval-Simulation
- Prime-Time-Scheduling für `Europe/Berlin`
- harte Evening-Run-Schranke von 19:00 bis 22:00 Uhr
- Prime-Time-Lernen aus 7-Tage-Metriken und Kollisionsvermeidung
- Audio-Adapter mit lizenzsicherem „ohne Musik“-Fallback
- Primary-/Alternate-/Reserve-Plan für jedes Asset-Paket
- Engagement-Vorschlagsqueue ohne automatische externe Aktionen
- geheimnisfreier JSON-Export und integritätsgeprüftes SQLite-Backup
- visuelle Morgen-Freigabe für Leona und Mara
- optionaler Passwort-/Session-/CSRF-Schutz für einen temporären Remote-Test
- dynamischer, secrets-freier Projektstatus per CLI und `/api/status`
- Stufenfilter und standardmäßig verschwommene geschützte Vorschauen
- lokaler JPG-/PNG-/WebP-Import mit Rechteangabe und sicherer Thumbnail-URL
- atomarer Restore eines geprüften SQLite-Backups in eine frische Datenbank
- `MockPublisher`
- owner-bestätigte native Instagram-Reconciliation ohne Plattformaufruf
- append-only manuelle Analytics für 24/72/168 Stunden
- lokales Archiv und gewichtete Top-3-Auswertung
- validierte secret-freie Wochen-/Monats-Recovery-ZIPs
- Analytics-Snapshots nach 24, 72 und 168 Stunden
- einfache Learning-Entscheidung anhand mehrerer Qualitätsmetriken
- idempotenter Abend-Lauf ohne Doppelgenerierung
- drei SFW-Service-Packs als Owner-gated Launch-Entwurf
- lokaler AdWorks-Pfad Pack → Tracking → Funnel → Revenue → Feedback
- strikt getrennte reale und synthetische Revenue-Anzeige ohne Paid Spend
- dauerhafte lokale Publish Queue mit ehrlichen Scheduling-Zuständen
- Background-Run-State mit Lease, Stale-Recovery und `WAITING_FOR_CAPACITY`
- 05:30-Morning-Run über den vorhandenen Fünfer-Review-Flow
- Patch-/Meilenstein-Backup-Kette mit echter Member-Hashprüfung
- statischer, secrets-reduzierter Offline-Snapshot unter `output/offline/`

## Optionaler Standalone-Betrieb

Die vorbereitete Runtime bleibt standardmäßig **nicht installiert**. Vorschau:

```powershell
.\scripts\install_runtime_tasks.ps1
```

Nach Owner-Prüfung können drei lokale Windows-Aufgaben (Autostart, Watchdog,
Scheduler) ausdrücklich mit `-Apply` installiert werden. Der Scheduler arbeitet
in einzelnen, begrenzten Läufen; der Watchdog besitzt Backoff und einen
Restart-Circuit. Der Publisher bleibt ohne konfigurierten Adapter fail-closed.

```powershell
.\scripts\install_runtime_tasks.ps1 -Apply
.\scripts\uninstall_runtime_tasks.ps1          # nur Vorschau
.\scripts\uninstall_runtime_tasks.ps1 -Apply   # tatsächlich entfernen
```
