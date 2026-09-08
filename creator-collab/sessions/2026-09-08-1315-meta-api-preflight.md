# Sitzungsjournal

- Datum/Zeit: 2026-09-08 13:15 Europe/Berlin
- Agent: `Codex`
- Ziel der Sitzung: Auf ausdrücklichen Owner-Wunsch prüfen, ob der vorhandene
  offizielle Meta-/Instagram-Adapter aktuell einen sicheren API-Start erlaubt.

## Ausgangslage

Der Meta-Adapter existiert lokal, die aktive Owner-Regel führte Meta bisher
als `DEFERRED_OWNER_VERIFICATION`. Der Owner verlangte einen erneuten Versuch.

## Durchgeführt

- `OWNER_DECISIONS.md`, `docs/OFFICIAL_META_PUBLISHING.md`, `config.toml`
  und `.env.example` gelesen.
- Den dokumentierten, read-only Meta-Preflight ausgeführt:
  `meta-preflight --publication-id 8 --content-id 1`.
- Nur das Vorhandensein, niemals die Inhalte, der sechs notwendigen
  Environment-Konfigurationswerte geprüft.

## Verifiziert

- Preflight-Ergebnis: `BLOCKED` mit
  `official_instagram_adapter_not_configured`.
- Provider: `instagram-official-unconfigured`.
- Fehlend: Leona-IG-User-ID, Leona-Token, Mara-IG-User-ID, Mara-Token,
  Graph-API-Version und öffentliches Medienmanifest.
- `config.toml`: `adapter = unconfigured`, `live_enabled = false`.
- Kein Graph-Read, kein Media-Container, kein Publish, keine Datenbank- oder
  Queue-Änderung. Keine Secrets ausgegeben, geloggt oder gespeichert.

## Entscheidungen

- Der Adapter bleibt fail-closed. Ohne echte Meta-Verbindung wird weder ein
  Dummy-Test noch Browser-Automation als API-Proof ausgegeben.
- Der nächste Schritt ist Owner-only: vorhandene Meta-App und beide
  professionellen Instagram-Personas verbinden und die echten Werte über
  einen sicheren lokalen Secret-Weg bereitstellen. Danach genau einen
  read-only Preflight, nicht mehrere Browser-Versuche.

## GOAL UPDATES

| Goal ID | Before | After | Evidence | Next |
|---|---|---|---|---|
| M-03 | WAITING_SIGNAL / OWNER_GATE | WAITING_SIGNAL / OWNER_GATE | Safe preflight found adapter unconfigured and all required config missing. | Owner completes Meta app/account linkage. |
| T-004 | WAITING_SIGNAL | WAITING_SIGNAL — CONFIG_MISSING | CLI `BLOCKED`, no external request. | One preflight after real configuration. |

## Offen oder blockiert

- Meta-App-/Developer- und Persona-Credential-Konfiguration ist noch nicht
  vorhanden. Tokens, OTPs und persönliche Verifizierung bleiben Owner-only.

## Nächster Agent

1. Erst nach Owner-Meldung über vollständige Meta-App-/Account-Verbindung denselben read-only Preflight ausführen.
2. Reale Instagram-Insights für Mara nach bewusstem Kontowechsel erfassen.
3. Fiverr-Gig bei CAPTCHA-freier öffentlicher Ansicht verifizieren.
