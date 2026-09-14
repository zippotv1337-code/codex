# Sitzungsjournal

- Datum/Zeit: 14.09.2026, 23:20 Europe/Berlin
- Agent: `Codex`
- Ziel der Sitzung: den vorhandenen Meta-/Instagram-Publish-Pfad bis zum
  sicheren Dashboard-Einzelversand fertig verdrahten, ohne Secrets oder einen
  Live-Post zu erzeugen.

## Ausgangslage

Der offizielle Meta-Adapter, die bestehende Queue-/Idempotenzlogik und die
lokale Content-Reserve waren vorhanden. Es gab noch keinen isolierten
Dashboard-Endpunkt für ein einzelnes Paket. Meta-User-Tokens, passende
Nutzer-IDs, öffentliche HTTPS-JPEGs und ein Tunnel waren nicht konfiguriert.

## Durchgeführt

- `MetaPushService` in die bestehende Dashboard-Runtime eingebunden.
- `GET /api/meta-push`, `POST /api/meta-push/preflight` und `POST
  /api/meta-push/push-one` ergänzt. POST-Aktionen bleiben passwort- und
  CSRF-geschützt.
- Einzel-Push auf eine positive Content-ID begrenzt; der globale Scheduler
  wird nicht aktiviert. Vor dem Versand erfolgt ein frischer Preflight.
- Dashboard `/channels` um Account-/Analytics-/Media-Status und die sichtbaren
  Aktionen „Einzelpaket prüfen“ / „Dieses Paket senden“ erweitert.
- Bereits veröffentlichte Channel-Inhalte bleiben read-only; TikTok-Milo wird
  nicht erneut gesendet.
- Sicherheits-Policy-Allowlist um den lokalen, nicht externen
  `milo_master_brief`-Task synchronisiert.
- TikTok-Response-Allowlisting gegen malformed `user`-/`videos`-Daten gehärtet.
- Loopback-only JPEG-Media-Origin und Runbook dokumentiert; kein Tunnel,
  Download oder Installer ausgeführt.
- `CURRENT_HANDOFF.md`, `PROJECT_RESUME.md`, `docs/CURRENT_STATE.json`,
  `docs/HUMAN_HANDOFF.md` und `docs/OFFICIAL_META_PUBLISHING.md` aktualisiert.

## Verifiziert

- Kanonische Runtime kontrolliert neu gestartet; Health:
  <http://192.168.188.131:4180/api/health> → `ok`.
- Dashboard ist auf Port 4180 erreichbar; geschützte Meta-Endpunkte antworten
  ohne Sitzung mit `401` statt einer ungeschützten Aktion.
- Python-Compile und JavaScript-Syntax grün.
- Neue/fokussierte Tests grün: `test_meta_push` (2),
  `test_channel_operations` (18), `test_public_media` (11),
  `test_meta_publishing` (10), `test_publishing_queue` (11) und
  `test_ai_ops` (21).
- SQLite `PRAGMA integrity_check` = `ok`.
- Keine Meta-/Instagram-/TikTok-/Fiverr-Aktion, kein Tunnel und kein Receipt
  in diesem Run.

## Entscheidungen

- App-ID und App-Geheimcode wurden weder gespeichert noch als User-Token
  behandelt. Ein echter Instagram-User-Token samt Konto-/Scope-Prüfung bleibt
  zwingend.
- Öffentliche Assets werden nicht aus lokalen PNGs erraten oder still
  konvertiert. Der Media-Origin verlangt drei eindeutige JPEG-Derivate und
  einen ausdrücklich konfigurierten HTTPS-Origin.
- Der vorhandene Scheduler bleibt `dispatch_live = false`; nur der explizite
  Einzelpaketweg kann nach bestandenen Gates dispatchen.

## Offen oder blockiert

- `META_GRAPH_AUTOMATION_PROOF` bleibt `NOT_PROVEN`: keine sicheren Meta-
  Nutzer-Credentials, keine verifizierte Account-Antwort und kein öffentlicher
  HTTPS-JPEG-Origin/Tunnel vorhanden.
- Die im Chat offengelegten Meta-/TikTok-Schlüssel sollten im jeweiligen
  Developer Portal rotiert werden. Keine Werte in Chat, Git, DB, Journal oder
  Logs übernehmen.

## GOAL UPDATES

| Goal ID | Before | After | Evidence | Next |
|---|---|---|---|---|
| M-03 | WAITING_SIGNAL / OWNER_GATE | WAITING_SIGNAL / OWNER_GATE | Einzelpaket-Preflight-/Push-Pfad verdrahtet und getestet; externer Proof fehlt | Owner-Credentials + HTTPS-Manifest |
| M-07 | ACTIVE | ACTIVE | bestehender SFW-Bestand unverändert; kein Doppelpost | erst nach Proof echten Output wählen |
| T-001 | ACTIVE | ACTIVE | Runtime-Neustart und `/api/health=ok` | kein weiterer Restart ohne Delta |
| T-002 | ACTIVE | ACTIVE | Analytics-Routen/Windows bleiben UNKNOWN ohne echte Messung | erste fällige reale Messung erfassen |

## Nächster Agent

1. Offengelegte App-Schlüssel rotieren und Nutzer-Token/IDs nur im sicheren
   Secret-Provider hinterlegen.
2. Drei eindeutige JPEG-Derivate eines freigegebenen Pakets über einen
   öffentlichen HTTPS-Origin bereitstellen; Manifestpfad konfigurieren.
3. Im Dashboard `/channels` den Preflight für genau ein Paket ausführen und
   nur bei `READY` den Einzelversand starten; danach Permalink/Receipt und
   24h-Analytics erfassen.
