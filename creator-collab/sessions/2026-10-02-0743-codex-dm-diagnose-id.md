# Sitzungsjournal — Instagram-DM-Diagnose-ID

- Datum/Zeit: 2026-10-02, 07:43 Europe/Berlin
- Agent: Codex
- Ziel der Sitzung: Ausschließlich den falsch positiven
  `account_id_match=false` im read-only DM-Diagnosepfad korrigieren.

## Ausgangslage

- `origin/main` und der Deployment-Checkout standen auf `93f3788`; der
  Working Tree war sauber.
- Die konfigurierte Konto-ID entspricht laut Owner-verifiziertem Meta-Readback
  dem Identity-Feld `id`, der Diagnosecode verglich jedoch `user_id`.
- Beide Provider-Conversations-Seiten waren gültig, aber leer. Ein echter
  DM-Inbound→Send→Delivery-Roundtrip war nicht nachgewiesen.

## Durchgeführt

- `creator_ops/instagram_dm_provider.py`: Identity-GET fragt
  `id,user_id,username` ab und vergleicht nur das vorhandene `id` mit der
  konfigurierten Konto-ID. Der Vergleich bleibt fail-closed.
- `tests/test_instagram_dm_diagnose.py`: passende/abweichende/fehlende `id`,
  unabhängiges `user_id`, exakt zwei GETs je Persona, kein POST und keine
  Ausgabe von IDs, Tokens, Nachrichtentext oder Paging-URL geprüft.
- Keine Credential-, Konfigurations-, Scheduler-, Runtime-, DB- oder
  Meta-Dashboard-Änderung; kein Nachrichtensend.

## Verifiziert

- Fokussierte DM-/Provider-/Diagnose-Tests: 59 bestanden plus 24 Subtests.
- Vollständige Python-Suite: 257 bestanden plus 24 Subtests.
- Python-Compile und `git diff --check` grün.
- Read-only CLI-Readback aus dem aktualisierten Checkout: Leona und Mara
  jeweils Identity-GET und Conversations-GET erfolgreich,
  `account_id_match=true`, Handle passend, gültige `data: []` mit Count 0.
- Diagnoseausgabe enthielt keine Konto-/Conversation-IDs, Tokens,
  Nachrichtentexte oder Paging-URLs. Kein POST.

## Entscheidungen

- `configured account ID == Meta identity.id` ist die einzige Vergleichsregel.
  `user_id` wird nicht ersatzweise als Match akzeptiert.
- Die historische falsche Diagnose-Evidence wurde nicht rückwirkend geändert;
  aktueller Handoff und Résumé zeigen den neuen Stand getrennt davon.

## Offen oder blockiert

- Ursache der leeren Conversations-Seiten bleibt ungeklärt. Der korrigierte
  ID-Abgleich allein beweist keine Inbox-Sichtbarkeit und keinen Bot-Betrieb:
  `BOT_WORKS=NO`.
- Kein Owner-Gate für diesen Codefix.

## Nächster Agent

1. Nur bei neuem API-sichtbarem Inbound die Nachricht und den Bot-Status
   kontrolliert reconciliieren; keinen Live-Erfolg aus Readiness ableiten.
2. Separat die Inbox-Visibility-Evidence prüfen, ohne den behobenen
   Diagnosevergleich wieder als Token-Mismatch zu behandeln.
3. Schema-9-Hardening nur als eigenen geprüften Integrationsauftrag angehen.
