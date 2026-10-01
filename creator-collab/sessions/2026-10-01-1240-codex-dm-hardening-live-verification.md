# Sitzungsjournal

- Datum/Zeit: 2026-10-01 12:40 Europe/Berlin (lokaler Testblock; Commit- und Remote-Readback später ergänzt)
- Agent: `Codex`
- Ziel der Sitzung: Bestehenden Instagram-DM-P1-Bot gezielt härten, Schema 8→9 isoliert prüfen und den echten Leona-/Mara-Live-Roundtrip nachweisen, soweit ein kontrollierter Test-Inbound sichtbar wird.

## Ausgangslage

- Operative Runtime: `C:\Zippoworkz\Workspace\codex_ingest`, Schema 8; der neue Arbeitsbranch `codex/20261001-dm-bot-hardening` liegt in einem getrennten Worktree und ist nicht deployed.
- Leona und Mara waren beim Provider read-only erreichbar, aber es lagen keine API-sichtbaren Inbound-Konversationen vor. Ein echter Bot-Send/Receive-Roundtrip war nicht bewiesen.
- Der gemeldete Mara-Ausfall hatte noch keinen eindeutigen reproduzierbaren Job- oder Provider-Fehlerbeleg.

## Durchgeführt

- Bestehende Änderungen im Arbeitsbranch erhalten und die DM-P1-Lane gezielt um begrenzte Read-/Write-Retries, fail-closed Reconciliation, Persona-Isolation, secret-freies Eventlog, read-only Smokecheck und echten Bot-Status im bestehenden Dashboard erweitert.
- Im unabhängigen Review zwei zusätzliche Fehler erkannt und minimal behoben: ein veralteter `SEND_PENDING`-Claim konnte trotz konkurrierender Übernahme erneut dispatcht werden; Graph-400/403-Throttle-Antworten wurden ohne ihre relevanten Retry-Metadaten falsch klassifiziert. Beide Fälle sind jetzt fokussiert getestet.
- Die operative Schema-8-DB ausschließlich per Online-Backup in eine isolierte Kopie übernommen und diese zweimal auf das additive Schema 9 initialisiert. Live-DB und Laufzeit wurden dadurch nicht migriert.
- Meta-Accounts read-only über `id,username` geprüft: beide Account-IDs passen zu `leonavoss.ai` bzw. `mara.field.ai`. Die offizielle Konversationsliste (`platform=instagram`) antwortete für beide mit HTTP 200 und jeweils 0 Konversationen. Das Leerergebnis entsteht somit bereits beim Provider-Listing, vor Cursor-, Normalizer- und DB-Persistenzlogik.
- Ein einzelner kontrollierter Test-Inbound von einem externen, nicht automatisierten Owner-/Testkonto an Leona wurde angefragt; Eingang und Antwort waren zum Dokumentationszeitpunkt nicht bestätigt. Kein Fremdkontakt und kein Bot-Send nur für den Test.
- Direkte Claude-Integration war in diesem lokalen Codex-Lauf nicht verfügbar. Ein Claude-Review wird nicht behauptet; Branch, Diff und Testergebnisse sind dafür vorzubereiten.

## Verifiziert

- DB-Kopie: Quell-SHA256 vor/nach identisch; Schema 8→9; zweites `initialize()` idempotent; Creator-/Content-/Asset-/Publication-/DM-Basiscounts unverändert; `PRAGMA integrity_check=ok`, `PRAGMA foreign_key_check=0`; neue Operation-Event-Spalten vorhanden.
- Die operative DB blieb Schema 8 mit Integrity `ok` und Foreign Keys 0; im bisherigen Readback 0 DM-Conversations/Events/Outbox-Einträge.
- Provider-Identität und Konversationslisten: Leona und Mara jeweils HTTP 200; beide `conversation_count=0`.
- Ein abschließender erneuter read-only Provider-Poll nach den lokalen Fixes bestätigte weiterhin Leona 0 und Mara 0; es wurde dadurch weder eine Inbound-Row noch ein Bot-Send erzeugt.
- `META_DM_WEBHOOK_VERIFY_TOKEN` ist vorhanden; `META_APP_SECRET` ist im geprüften Runtime-Kontext nicht vorhanden. Signierter Push-Webhook ist daher nicht als bereit zu melden. Polling ist davon unabhängig.
- Finale vollständige Python-Suite nach den Review-Fixes: **258 passed, 36 subtests passed** in 97,94 Sekunden. Dashboard/Node: **8/8**. Python-Compile, JavaScript-Syntax und `git diff --check` grün. Erneuter Secret-Scan nach gezieltem Staging einschließlich Dokumentation: `SECRET LEAK CHECK: OK (411 files checked)`. Aus lokalen Tests folgt kein Live-DM-Proof.
- Code-Commit `d380cb4541ab8d010004ed26471cbf3a03615d6a` auf `codex/20261001-dm-bot-hardening` ist erstellt, gepusht und mit `git ls-remote` zurückgelesen. Main und operative Runtime blieben unverändert.
- `BOT_WORKS=NO`: kein echter provider-verifizierter Inbound, keine persistierte Test-Konversation und kein bestätigter Bot-Reply-Receipt.

## Entscheidungen

- Provider-Readiness und HTTP 200 gelten nicht als Live-DM-Proof. Null Inbounds werden nicht als Bot-Erfolg umgedeutet.
- Kein Test-DM-Versand von Mara an Leona: beide Accounts sind automatisiert; das könnte eine Antwortschleife auslösen. Ein freigegebenes nicht automatisiertes Testkonto ist der sichere Pfad.
- Keine Secrets, Roh-Webhooks oder Nachrichtentexte in Journal/Handoff.
- Kein Merge oder Deployment des kritischen Schema-/Messaging-Deltas allein aufgrund grüner Unit-Tests.

## Offen oder blockiert

- Der konkrete Grund für 0 Meta-sichtbare Konversationen ist noch nicht providerseitig bewiesen. Konto-Mapping ist korrekt; App-Zugriff/Rollen oder die Erzeugung eines neuen echten Inbounds sind als Hypothesen zu prüfen, nicht als Tatsachen auszugeben.
- Das kontrollierte Owner-/Test-Inbound-Signal fehlt noch. Ohne dieses gibt es keinen sicheren echten Provider-Send und keinen `BOT_WORKS=YES`-Beleg.
- Für diesen Branch steht nur der Live-Roundtrip und das separate Claude-Review aus; der lokale Test-/Secret-/Commit-Block ist abgeschlossen.

## GOAL UPDATES

| Goal ID | Before | After | Evidence | Next |
|---|---|---|---|---|
| Instagram DM P1 live | nicht bewiesen | nicht bewiesen | beide Graph-Listen HTTP 200, 0 Konversationen; kein Receipt | kontrollierten Test-Inbound lesen, einmal antworten, extern und lokal reconciliieren |
| Bot Hardening P1 | offen | Branch implementiert und geprüft, nicht deployed | Schema-9-Kopierprobe, 258 Python-Tests, 8 Node-Tests, Secret-Scan und Remote-Commit | Claude-Review und kontrolliertes Deployment nach Owner-Gate |

## Nächster Agent

1. Nach neuem Owner-/Test-Inbound Provider-Liste erneut read-only prüfen; nur den eindeutig zugeordneten Testfall einmal durch den vorhandenen Bot-Pfad senden und Receipt/DB-Lifecycle prüfen.
2. Bei weiter 0 Konversationen Meta-App-Zugriff/Tester-Rolle/Message-Permission und neuen Inbound gezielt mit Provider-Evidence klären; keine Blind-Sends.
3. Kritischen Schema-/Messaging-Branch separat durch Claude prüfen und erst nach nötiger Owner-Freigabe kontrolliert mergen/deployen.
