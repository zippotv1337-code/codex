# Sitzungsjournal — Instagram-DM: IG_ID-Bindung, Single-Sender, Reconcile

- Datum/Zeit: 2026-10-02, 11:23–12:40 Europe/Berlin
- Agent: Claude Code (Opus 5.5). Codex-Implementierung scheiterte sofort am
  Codex-Usage-Limit (Kauf = Owner-Gate); Claude implementierte den Delta selbst,
  Codex reviewte danach.
- Ziel der Sitzung: Owner-Auftrag „Instagram-DM-Bot end-to-end fertigstellen“.

## Ausgangslage

- `origin/main` b84572f. Der VPS (`ZIPPOWORKZ-VPS`, laut
  `Context\Owner\PUBLISHING_AUTHORITY.json` aktiver Node) betreibt Creator Ops
  weiterhin aus `Workspace\deploy_dm_p1_b7ccbcad` (detached b785ce4 plus lokale,
  unversionierte Änderungen) mit der DB
  `Workspace\codex_ingest\creator-collab\data\review_dashboard.db` (Schema 8).
- `Workspace\codex_deploy` und `Handoff\VPS\ZIPPOWORKZ_CONSOLIDATION_FINAL.md`
  existieren auf dem VPS nicht; Scheduler/Watchdog liefen 06:00–07:45 ohne
  Neustart; es gibt keine Codex-Session vom 02.10. auf dem VPS. Der
  Single-Source-Cutover von 07:18 lief also auf einem anderen Host (vermutlich
  `ZIPPOWORKZ-LOCALAI`; dessen DB meldet 8 Publications, die VPS-DB 0).
- Read-only Meta auf dem VPS: Leona/Mara konfigurierte ID == `/me.user_id`
  (…9023/…3092), != `id`. `/conversations` per ID, per `/me`, mit
  Folder-Varianten und ohne `platform`: jeweils 0.
- Meta-Doku (Instagram Login, get-started): `id` = „app-scoped ID“; `user_id` =
  „Instagram professional account ID (IG_ID) … value of the `id` field received
  in webhook notifications“. Conversations API: das Business erscheint als IG_ID.
- b84572f hatte die Diagnose auf `id` umgestellt. Das ist für die kanonische
  VPS-Konfiguration falsch; der andere Host ist demnach mit app-scoped IDs
  konfiguriert, dort würde `poll()` eigene Nachrichten nicht als eigene erkennen.
- Zweiter DM-Poller auf dem VPS: Task „Zippoworkz Instagram DM Poll“
  (`_tmp\dm_readonly_sync.py`, alle 5 min) ist trotz Name nicht read-only
  (`sync_provider()` mit `auto_reply_enabled=true`).

## Durchgeführt

- f5f718b: `diagnose` vergleicht `user_id` und meldet `configured_id_kind`;
  `bind_identity()` prüft vor jedem `poll()` IG_ID und Handle (fail-closed, ein
  GET je Persona und Instanz); `dispatch_reply()` sendet nur auf dem aktiven Node
  (gleiche Authority wie Publishing) und erst nach Identity-Preflight, beides vor
  dem Claim.
- 5f7a561: read-only Reconcile-Pass im `instagram-dm-sync` (SENT → DELIVERED),
  `replies_delivered` je Persona, `external_action` nur bei echtem Send true.
- c89265c (nach Codex-Review): automatische Reconciles nur 1–15 min nach dem
  Send (≈ drei Syncs, Policy §4); Provider-Fehler → `RECONCILE_REQUIRED` mit
  sanitisiertem Code. Blockierte Antworten bleiben bewusst `APPROVED` und werden
  nie automatisch nachgesendet (kein Duplikat nach Failover).
- Deployment file-level wie am 01.10.: nur `creator_ops/instagram_dm.py` und
  `creator_ops/instagram_dm_provider.py` aus `origin/main` nach
  `deploy_dm_p1_b7ccbcad`; lokale VPS-Publishing-Änderungen unverändert.
  Backups: `C:\Zippoworkz\Backups\DM_IDENTITY_AUTHORITY_DEPLOY_20261002_115834`
  (Originalstand), `_120934`, `_122111`. Web über den Task
  „Creator Ops - Autostart“ neu gestartet.
- Task „Zippoworkz Instagram DM Poll“ deaktiviert (redundanter zweiter
  Writer/Sender), nicht gelöscht.
- Branch `vps/runtime-snapshot-20261002` (2af69e6) sichert den exakten
  VPS-Runtime-Code inklusive der unversionierten Publishing-Änderungen.
  Nicht mergen: kritischer Publishing-Kern, Owner-Gate.

## Verifiziert

- 269 Python-Tests plus 24 Subtests; DM/Authority fokussiert 74 plus 24;
  Dashboard 7/7; compileall; `git diff --check`; Secret-Scan 410 Dateien.
- Live auf dem VPS mit c89265c: Scheduler-Läufe `SYNCED` für beide Personas,
  `error: null` (inklusive neuer Identity-Bindung). Diagnose:
  `account_id_match=true`, `configured_id_kind=ig_professional_account_id`,
  Handles korrekt, 0 Conversations. `/api/health` ok, DB Schema 8,
  `integrity_check=ok`, Foreign Keys 0, alle DM-Tabellen 0.

## Entscheidungen

- Die konfigurierte Konto-ID muss die IG_ID (`user_id`) sein; die b84572f-Regel
  ist mit Meta-Doku-Beleg revidiert.
- DM-Sends nur auf dem aktiven Node. Kein Schema 9, keine Migration, kein Merge
  der VPS-lokalen Publishing-Änderungen.
- Kein App-Live-Schalten und keine Privacy-Veröffentlichung in diesem Lauf:
  Zwei Chrome-Browser sind verbunden, die Auswahl braucht den Owner. Außerdem
  erst nach sauberem Tester-Roundtrip und abgesichertem Zweit-Host.

## Offen oder blockiert

- `BOT_WORKS=NO`. Harter Blocker: kein frischer provider-sichtbarer Inbound. Die
  API kann keine DM initiieren, und Persona-Logins sind Owner-only. Owner: eine
  DM von `mara.field.ai` an `leonavoss.ai` (aktives Konto prüfen, nie erneut
  senden).
- Vorbedingung: Der `codex_deploy`-Host muss main ≥ c89265c deployen. Mit seinen
  app-scoped IDs schlägt sein DM-Sync dann fail-closed fehl (keine Sends), bis
  `META_IG_USER_ID_*` dort auf `user_id` gesetzt sind; als Standby blockiert die
  Authority Sends zusätzlich.
- Zwei operative DBs (VPS 0 Publications, anderer Host 8): Owner-/
  Architekturentscheid. Token-Refresh (Ablauf etwa Ende November) und Webhooks
  (brauchen Live und App-Secret) bleiben Backlog.

## Nächster Agent

1. Nach der Owner-DM nichts manuell senden. Nach höchstens 10 min read-only
   prüfen: 1 INBOUND (`provider_verified=1`), 1 Outbox SENT → DELIVERED
   (automatischer Reconcile), Mara-Seite `SKIPPED project_bot_reply_not_auto_answered`,
   kein Duplikat beim Folge-Sync.
2. Bleibt auch der Tester-Thread unsichtbar: Instagram-Einstellung „Zugriff auf
   Nachrichten erlauben“ beider Personas prüfen lassen, danach App-Live-Pfad.
3. Auf dem `codex_deploy`-Host main deployen und IDs korrigieren; erst danach
   App-Live-Modus.
