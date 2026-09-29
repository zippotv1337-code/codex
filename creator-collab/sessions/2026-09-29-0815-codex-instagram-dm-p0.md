# Sitzungsjournal

- Datum/Zeit: 2026-09-29, 08:15 Uhr (Europe/Berlin)
- Agent: `Codex`
- Ziel der Sitzung: Den Auftrag `docs/CODEX_INSTAGRAM_DM_P0_RUN.md` auf
  `codex/20260929-instagram-dm-p0` bis zur P0-Definition-of-Done umsetzen,
  ohne Merge nach `main` und ohne externe Nachrichten oder Plattformaktionen.

## Ausgangslage

Der Arbeitsbranch enthielt den bei Sitzungsbeginn aktuellen Main-Stand
`e289b7802aa360bf306773e24c4a7069610e9f7e`, aber noch keine produktive
Instagram-DM-Inbound-Lane. Der bestehende Engagement-Bereich hatte nur
Kommentarvorschläge. Die kanonische operative Datenbank war Schema 6; weder
ein DM-Sendepfad noch eine Meta-Webhook-Registrierung waren für diesen P0
zulässig.

## Durchgeführt

- Schema 7 additiv in derselben Datenbank eingeführt:
  `instagram_dm_conversations` und `instagram_dm_events` mit Foreign Keys,
  Provider-IDs, Zeitstempeln und idempotenten Unique-Indizes.
- `creator_ops/instagram_dm.py` ergänzt: begrenzte Inbound-Normalisierung,
  exakte Leona-/Mara-Zuordnung, 13 Intent-Klassen, deterministische
  Klassifikation, Safety-Policy und read-only Dashboard-Projektion.
- Unsichere Persona-Zuordnung, niedrige Klassifikationssicherheit und alle
  vorgegebenen Risikoarten gehen fail-closed nach `NEEDS_HUMAN`.
- Es werden weder Roh-Payload noch Nachrichtentext persistiert. Inbound-Text
  existiert nur vorübergehend während Klassifikation und Safety-Prüfung.
- Lokale API-Grenzen in den bestehenden Server integriert:
  `GET /api/instagram-dm` und authentifiziertes/CSRF-geschütztes
  `POST /api/instagram-dm/inbound`. Kein Send-/Reply-Endpunkt ergänzt.
- Bestehende Nachrichtenansicht erweitert: Persona, Intent, Status,
  Zeitpunkt und Handoff-Grund; sichtbarer Modus
  `SEND_DISABLED_READ_ONLY_P0`.
- Current-State-, Architektur-, MVP-, README-, Resume- und Handoff-Dokumente
  auf den belegten P0-Stand gebracht.

## Verifiziert

- Vollständige Python-Suite: `193 passed, 22 subtests passed`.
- Dashboard-JavaScript: `7 passed`.
- Python-Compilecheck, JavaScript-Syntaxcheck und JSON-Parsecheck: grün.
- Isolierte Kopie der operativen Schema-6-DB auf Schema 7 migriert und mit
  einem rein synthetischen Leona-Event geprüft: Persona `leona-voss`, Intent
  `SMALLTALK`, Status `OPEN`, `send_enabled=false`, `external_action=false`.
- Migrierte Kopie: `PRAGMA integrity_check=ok`, Foreign Keys 0.
- Originaldatenbank vor/nach Test unverändert, SHA-256 jeweils
  `6CDDEA5DADF45B3CFCC748E1C08AEF3B18C409F2AE27B09254A34A66E7924902`.
- Keine externe Nachricht, kein Webhook, kein Publish und keine sonstige
  Plattformaktion ausgeführt.

## Entscheidungen

- P0 bleibt absichtlich inbound-only und outbound-disabled. Eine lokale
  synthetische Inbound-Route beweist die Adaptergrenze, ohne einen echten
  Providerzugriff vorzutäuschen.
- Nur bekannte aktive Leona-/Mara-Konten werden automatisch zugeordnet.
  Unbekannte oder widersprüchliche Metadaten werden nicht erraten.
- Externe IDs und normalisierte Klassifikationsmetadaten genügen für
  Idempotenz und Dashboard-Triage; Nachrichtentext und Roh-Payload werden aus
  Datenschutz- und Sicherheitsgründen nicht gespeichert.
- Der Branch bleibt gemäß Owner-Auftrag getrennt von `main`.

## Offen oder blockiert

- Kein P0-Blocker. P0 ist lokal vollständig.
- P1+ bleibt bewusst offen: echter signierter Meta-Webhook, Provider-
  Berechtigungen, Antwortentwurf/Preview, Owner-Approval, Delivery-Tracking,
  Medienpfad sowie strikt getrennte Link-/Payment-Flows.
- Die spätere Integration nach `main` ist eine kritische, Owner-kontrollierte
  Entscheidung und wurde nicht vorgenommen.

## GOAL UPDATES

| Goal ID | Before | After | Evidence | Next |
|---|---|---|---|---|
| DM-P0-01 Inbound Normalisierung | OPEN | DONE | synthetische Leona-/Mara- und Provider-Events in Tests | später signierten Meta-Webhook separat planen |
| DM-P0-02 Persona und Intent | OPEN | DONE | 13 Intent-Klassen und exakte Persona-Auflösung getestet | keine P0-Arbeit mehr |
| DM-P0-03 Idempotenz | OPEN | DONE | Event-/Message-ID-Duplikate liefern dasselbe gespeicherte Ereignis | Provider-Reconciliation erst in P1+ |
| DM-P0-04 Safety | OPEN | DONE | Risiko- und Unsicherheitsfälle landen `NEEDS_HUMAN` | Owner-Triage später operationalisieren |
| DM-P0-05 Dashboard | OPEN | DONE | bestehende Nachrichtenansicht, API und JS-Test grün | kein zweites Dashboard bauen |
| DM-P0-06 Outbound-Schutz | OPEN | DONE | kein Send-Endpunkt; sichtbarer read-only Modus | Outbound bleibt außerhalb P0 |

## Nächster Agent

1. Branch und Testbelege reviewen; keine P0-Funktion erneut bauen.
2. Eine spätere Main-Integration nur nach expliziter Owner-Entscheidung und
   mit frischem DB-Backup/Restore-Nachweis ausführen.
3. Danach P1 als separaten Auftrag definieren; zuerst echten signierten
   Provider-Inbound beweisen, bevor Vorschläge oder Outbound erwogen werden.
