# DM Auth-Diagnose — 2026-10-01

- Engineering nach Claude-Audit; Policy v1.3, Arbeitsbranch
  `codex/20261001-dm-auth-diagnose`; kein Merge/Deployment.
- Provider/Publishing-Transport/DM-Service/CLI/Secret-Auflösung geprüft.
  Änderungen ausschließlich Provider, CLI, fokussierte Tests und Übergabedokumente.
- Diagnose führt genau zwei GETs pro konfigurierter Persona aus: `/me` mit
  `user_id,username` und den bestehenden Conversations-GET. Keine Message-Details,
  Paging-Folgeaufrufe, DB-Initialisierung, Sync, Outbox, Sends oder Secret-Writes.
- Nur bereits vom Transport angebotene numerische Codes/HTTP-Status werden
  streng gefiltert ausgegeben, ohne Interpretation von Meta-Permission-Codes.
  Beliebige Exception-Texte und Payloads bleiben außerhalb der Ausgabe.
- Readiness-Kompatibilitätsfelder erhalten; neue explizite Credential-Basis.
  Fehlende/ungültige `data`-Listen und Nicht-Objekt-Einträge schlagen fail-closed
  fehl (Polling und Reconciliation); `data: []` bleibt gültig.

## Reale Diagnose

Aufruf: `python -m creator_ops.cli instagram-dm-diagnose`.
Bestehender DPAPI-Broker außerhalb der Sandbox verwendet. Im eingeschränkten
Prozess waren Credentials nicht auflösbar; das war lokale Zugriffsevidence,
kein Graph-Ergebnis. Keine Rotation/Neuerzeugung oder Accountänderung.

| Fakt | Leona | Mara |
|---|---|---|
| credentials_present | true | true |
| identity_call_ok | true | true |
| account_id_match | true | true |
| username | leonavoss.ai | mara.field.ai |
| expected_username_match | true | true |
| conversations_call_ok | true | true |
| response_has_data_list | true | true |
| conversation_count (erste Seite) | 0 | 0 |
| paging_present | false | false |

Dies beweist keinen realen Inbound-Zugriff. Der Owner bestätigt echte DMs an
beide Konten; die historische „nur Outbound“-Erklärung ist überholt. Offen ist
wirksamer Messaging-Zugriff der bestehenden App/Tokens auf diese Inbounds.
Eine fehlende Permission ist nicht bewiesen. Der Audit meldet HTTP 429 der
offiziellen Meta-Dokumentation; keine aktuellen Permission-/Fehlercode-Verträge
erfunden. Webhook bleibt außerhalb des Scopes. Falls später Token-/Consent-
Änderungen nötig werden, gilt das bestehende Credential-Owner-Gate.

## Verifikation

- Fokus: 51 Tests und 24 Subtests bestanden.
- Vorhandene Projekt-VENV enthält Pakete, ihr Basisinterpreter fehlt.
  Bestehender Runtime-Python 3.12.14 mit VENV-site-packages via prozesslokalem
  PYTHONPATH verwendet; nichts installiert oder dauerhaft umkonfiguriert.
- Full Python Suite: 243 Tests und 24 Subtests bestanden (243,64 Sekunden).
- Python compileall für creator_ops/tests grün; Secret-Scan über 406 getrackte
  Dateien einschließlich neuer Tests/Journal grün; Git-Diff-Check grün.
- Keine gesonderten Dashboard-/JavaScript-Tests, da kein Dashboard geändert.
