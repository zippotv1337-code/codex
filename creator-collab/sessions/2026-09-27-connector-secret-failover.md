# Connector Secret Failover — VPS + Local AI
Datum: 2026-09-27

## Ziel
Ein gemeinsamer Zippoworkz-Connector-/Secret-Layer soll auf VPS und Local AI
denselben Code verwenden, ohne Secret-Werte über Git, Logs, Prompts oder
Klartext-Netzfreigaben zu verteilen.

## Verifizierter VPS-Stand
- MACHINE_ID: ZIPPOWORKZ-VPS.
- Publishing Authority: VPS PRIMARY, Local AI STANDBY.
- Creator Ops Health: HTTP 200 auf 127.0.0.1:4180.
- Scheduled Tasks: Autostart, Watchdog, Scheduler und Connector Secret Replication
  zuletzt jeweils erfolgreich (LastResult 0).
- Meta/Instagram: beide Accounts live-ready aus DPAPI Broker.
- Creator-Ops-Web: Broker-Secret vorhanden.
- GitHub: managed auth, keine Secret-Replikation.

## Generische Secret-Replikation v2
- Katalog: config/connector_secret_catalog.json.
- secret_bundle_helper.py liest Scope, Worker und Secret-Namen aus dem Katalog.
- secret_replication.ps1 unterstützt ExportConnector/ImportConnector.
- RSA-3072/OAEP verschlüsselt jeden Secret-Wert für den Zielknoten.
- Private Replikationskeys bleiben DPAPI-geschützt auf dem jeweiligen Node.
- sync_connector_secrets_to_localai.ps1 exportiert automatisch nur READY-Connectoren.
- import_connector_bundles.ps1 läuft ausschließlich auf ZIPPOWORKZ-LOCALAI,
  importiert katalogisierte Bundles und löscht sie danach.
- install_runtime_tasks.ps1 ist node-aware:
  - VPS: Connector Secret Replication.
  - Local AI: Connector Secret Import.
- sync_meta_secrets_to_localai.ps1 bleibt als Legacy-Wrapper auf dem generischen Sync.

## Verifizierte Selftests
- meta-instagram: ExportConnector -> ImportConnector -> Delete bestanden.
- creator-ops-web: ExportConnector -> ImportConnector -> Delete bestanden.
- Test-Bundles nach Import nicht mehr vorhanden.
- Fokus-Regression: 22/22 Tests grün:
  - secret_resolution: 3
  - publish_authority: 3
  - meta_publishing: 11
  - external_readiness: 5

## Aktueller Connector-Status
- meta-instagram: READY_VPS / replizierbar.
- creator-ops-web: READY_VPS / replizierbar.
- github: MANAGED_AUTH / keine Secret-Kopie.
- higgsfield: Broker-Key fehlt noch; Owner-Gate ASK_BEFORE_EVERY_PAID_HIGGSFIELD_CALL bleibt.
- tiktok: PENDING_SECURE_ONBOARDING; kein echter Credential-Consumer im aktuellen Repo.
- fiverr: PENDING_API_CREDENTIALS; kein echter API-Credential-Consumer im aktuellen Repo.

## Local AI
Der Bootstrap unter Exchange/VPS_TO_LOCALAI/Current ist auf die generische
Connector-Replikation aktualisiert. Aktuell fehlt nur der Local-AI-Public-Key.
Sobald Local AI online ist, erzeugt der vorhandene Bootstrap den Schlüssel,
der VPS-Task erstellt die verschlüsselten Bundles und Local AI importiert sie
node-lokal in DPAPI. Bis dahin bleibt Local AI STANDBY.
