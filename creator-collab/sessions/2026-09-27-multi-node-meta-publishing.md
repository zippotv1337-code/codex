# Multi-Node Meta Publishing — VPS + Local AI

Datum: 2026-09-27
Status: VPS READY / LOCAL AI WAITING_FOR_PUBLIC_KEY

## Ziel
Instagram/Meta-Publishing soll nicht an einen einzelnen Rechner gebunden sein.
VPS und Local AI verwenden denselben Creator-Ops-Code, aber jeweils einen
eigenen lokal verschlüsselten Secret-Store. VPS ist PRIMARY, Local AI STANDBY.

## VPS — umgesetzt und verifiziert
- Die temporäre `.env.meta.local` wurde nach verifiziertem Import gelöscht.
- Sechs Meta-Konfigurationswerte liegen im node-lokalen DPAPI Secret Broker.
- Creator-Ops löst Meta-Werte über ENV-Override (Test/Notfall) und danach
  über den Zippoworkz Secret Broker auf.
- Read-only Meta-Check ohne ENV-Datei bestanden:
  - `leonavoss.ai`: Username-Match, Meta erreichbar.
  - `mara.field.ai`: Username-Match, Meta erreichbar.
- Keine Secret-Werte werden in Git, Logs, Handoffs oder Prompts geschrieben.

## Sichere Replikation
- Node-spezifisches RSA-3072-Schlüsselpaar.
- Private Replikationsschlüssel bleiben DPAPI-geschützt auf dem jeweiligen Node.
- Nur der öffentliche Schlüssel darf über `Exchange` übertragen werden.
- Meta-Secrets werden einzeln RSA-OAEP-verschlüsselt und nur als verschlüsseltes
  Bundle an den Zielknoten übergeben.
- VPS Self-Roundtrip (Export → Import → Bundle löschen) bestanden.
- Windows Task `Creator Ops - Meta Secret Replication` prüft alle 5 Minuten,
  ob der Local-AI-Public-Key vorliegt; bis dahin fail-safe `WAITING`.

## Publishing Authority / Doppelpost-Schutz
- `C:\Zippoworkz\Context\Owner\PUBLISHING_AUTHORITY.json`
- Aktiv: `ZIPPOWORKZ-VPS`
- Standby: `ZIPPOWORKZ-LOCALAI`
- Der Meta-Adapter blockiert Live-Publishing auf einem Standby-Knoten.
- Failover wird nur per Owner-Entscheidung oder verifiziertem Ausfall umgeschaltet.
- Read-only Preflight bleibt auf beiden Knoten möglich.

## Local AI — nächster automatischer Schritt
Beim nächsten Local-AI-Bootstrap:
1. Secret-Broker-Kompatibilität und Publishing-Authority prüfen.
2. Lokalen RSA-Key initialisieren.
3. Public-Key nach `Exchange\LOCALAI_TO_VPS\Current` ausgeben.
4. Verschlüsseltes VPS-Bundle empfangen und lokal in DPAPI importieren.
5. Bundle löschen.
6. `meta_node_status.py --live` ausführen.
7. Als STANDBY bleiben, solange VPS PRIMARY ist.

## Tests
- 26 fokussierte Tests grün.
- VPS DPAPI Roundtrip grün.
- RSA Secret-Replikations-Roundtrip grün.
- Meta read-only Username-/Quota-Check grün.
- Während dieser Infrastrukturarbeit wurde kein Instagram-Post veröffentlicht.
