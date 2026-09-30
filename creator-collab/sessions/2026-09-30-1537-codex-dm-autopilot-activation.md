# Sitzungsjournal

- Datum/Zeit: 2026-09-30 15:37 Europe/Berlin
- Agent: `Codex`
- Ziel der Sitzung: Den bereits deployten Instagram-DM-P1-Pfad für Leona und Mara autonom aktivieren, beide Testdialoge über die offizielle Meta-API abgleichen und sichere Antworten genau einmal senden, sobald Meta einen Inbound liefert.

## Ausgangslage

- DM-P1 war kontrolliert deployed, aber `auto_reply_enabled=false` und noch ohne echte Inbound-Events.
- Konto-ID und Access Token waren für beide Personas im Windows-User-Environment vorhanden; der lokale Secret Broker enthielt noch keine Meta-Secrets.
- Beide Meta-Konten waren noch nicht für das App-Feld `messages` abonniert.
- Der Standalone-Scheduler synchronisierte Publishing und Insights, aber noch keine Instagram-DMs.

## Durchgeführt

- Beide offiziellen Konten read-only verifiziert: `leonavoss.ai` und `mara.field.ai`, jeweils richtige Persona und schreibbereiter Graph-Adapter.
- Secret Broker repariert: Der DPAPI-Pfad lädt nun die benötigte Windows-Assembly explizit. Konto-IDs, Access Tokens, Graph-Version und Host wurden ohne Klartextausgabe DPAPI-geschützt importiert und für `creator-ops-meta` freigegeben. Ein zufälliger Webhook-Verify-Token wurde ebenfalls nur im Broker erzeugt.
- Leona und Mara offiziell per Meta API für das Feld `messages` abonniert; Write und anschließender Readback waren für beide erfolgreich.
- Mehrfach kontrolliert synchronisiert. Die API meldete für beide Konten `SYNCED`, aber 0 gesehene und 0 importierte Inbound-Nachrichten. Die vom Owner beschriebenen manuellen Texte waren Outbound und lieferten daher keine Reply-fähige Empfänger-IGSID.
- `auto_reply_enabled=true` gesetzt.
- Neuen CLI-Schritt `instagram-dm-sync` hinzugefügt und in den vorhandenen 5-Minuten-Standalone-Scheduler integriert.
- Current-State-Erzeugung so angebunden, dass sie den echten konfigurierten Meta-DM-Provider read-only lädt statt irreführend `send_enabled=false` auszugeben.
- Runtime kontrolliert neu gestartet. Readback: `send_enabled=true`, Auto-Reply aktiv, beide Personas read/write-ready, Scheduler-DM-Sync erfolgreich.
- `docs/CURRENT_STATE.json` neu aus operativer DB und Runtime-Konfiguration erzeugt.

## Verifiziert

- Provider-Subscriptions: Leona 1 und Mara 1; jeweils Feld `messages` im API-Readback.
- Secret-Broker-Readback ohne Prozess-Environment: beide Personas vollständig konfiguriert und read/write-ready; Verify-Token vorhanden; keine Secretwerte ausgegeben.
- Fokussiert: 28 Tests plus 22 Subtests grün.
- Vollständig: 218 Tests plus 22 Subtests grün.
- Dashboard: 7/7 Node-Tests grün.
- Python-Compile grün.
- Secret-Scan: `OK (393 files checked)`.
- `git diff --check` grün.
- Operative SQLite: Schema 8, `integrity_check=ok`, Foreign Keys 0.
- Laufende Runtime: Health `ok`, Auth aktiv, DM-Modus `PROVIDER_VERIFIED_AUTONOMY_P1`, `send_enabled=true`.
- Keine echte DM gesendet, weil Meta noch keinen Inbound und keine Empfänger-IGSID lieferte. Kein Blind-Resend und kein erfundener Live-Erfolg.

## Entscheidungen

- Die kanonische Owner-Policy erlaubt normale projektbezogene Einzelantworten; deshalb ist Auto-Reply für sichere, provider-verifizierte Inbounds aktiviert.
- Scheduler-Polling ist ein funktionsfähiger offizieller Fallback, bis ein signierter öffentlicher Webhook vollständig eingerichtet ist.
- Outbound-Nachrichten werden nicht als Inbound-Test umgedeutet. Für den echten Sendbeleg wird ein nach der Subscription eingehender Dialog benötigt.

## Offen oder blockiert

- `META_APP_SECRET` fehlt weiterhin im Secret Broker; damit ist die Webhook-Signaturgrenze noch nicht live-ready.
- Es ist kein bestehender genehmigter öffentlicher HTTPS-Callback für `/webhooks/instagram` vorhanden.
- Für den echten Send-once-Livebeleg muss nach der Subscription eine neue externe DM an Leona oder Mara eingehen. Der aktive Scheduler übernimmt sie danach automatisch.

## Nächster Agent

1. Nach Eingang einer neuen externen Test-DM Scheduler-/Dashboard-Readback prüfen; keine manuelle Doppelverarbeitung starten.
2. Provider-Message-ID und `SENT`/`DELIVERED` oder `RECONCILE_REQUIRED` dokumentieren; bei Unsicherheit niemals erneut senden.
3. Meta-App-Secret und vorhandenen HTTPS-Callback später ergänzen, um zusätzlich den signierten Push-Webhook zu beweisen.
