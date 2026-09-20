# Sitzungsjournal

- Datum/Zeit: 20.09.2026, 23:27 Europe/Berlin
- Agent: `Codex`
- Ziel der Sitzung: Leona und Mara als Meta-/Instagram-Testkonten verifizieren
  und den offiziellen OAuth-Tokenweg bis zum persönlichen Login vorbereiten.

## Ausgangslage

Die Meta-App und die nötigen Instagram-Berechtigungen waren vorbereitet. Der
Owner hatte beide Tester-Einladungen manuell angenommen. Tokenwerte waren noch
nicht erzeugt oder lokal konfiguriert.

## Durchgeführt

- Meta-App-Rollen sichtbar geprüft: `leonavoss.ai` und `mara.field.ai` sind als
  Instagram-Tester eingetragen.
- In beiden Instagram-Konten die Autorisierung von `Zippoworkz-IG` mit Datum
  20.09.2026 sichtbar verifiziert.
- Meta-Tokenliste geöffnet; beide Konten werden dort getrennt angeboten.
- Für Mara und Leona jeweils `Token generieren` gestartet.
- Beide erzwungenen OAuth-Loginseiten als sicheren Owner-Handoff geöffnet
  gelassen.
- Nach der Owner-Rückmeldung den fertigen Mara-OAuth-Dialog übernommen, das
  Token ausschließlich im lokalen Windows-User-Environment gespeichert und
  die Zwischenablage anschließend geleert.
- Das von `/me` gelieferte tokengebundene Konto-Mapping für Mara lokal
  gespeichert. Die in der Meta-Setup-Tabelle angezeigte dauerhafte Instagram-
  Nutzer-ID blieb ein separates, read-only bestätigtes Feld; beide Werte wurden
  nicht in Projektdateien geschrieben.

## Verifiziert

- Beide Instagram-Konten sind auf Rollen- und Instagram-Seite eindeutig dem
  korrekten App-Namen zugeordnet.
- Kein Access-Token, Passwort, OTP, Cookie oder App-Geheimnis wurde in Chat,
  Git, Datenbank oder Journal geschrieben.
- Es wurde kein Feedpost, Carousel, Reel oder Story veröffentlicht.
- Read-only bestätigt: `mara.field.ai`, Kontotyp `BUSINESS`, korrektes
  tokengebundenes API-Konto und lesbarer `content_publishing_limit`-Endpunkt.

## Entscheidungen

- Persönliche Instagram-Anmeldedaten und mögliche 2FA-Codes werden
  ausschließlich durch den Owner eingegeben.
- Tokens werden nach erfolgreichem OAuth nur in lokaler Secret-/Env-Ablage
  gespeichert; aktuelle Source-of-Truth-Dateien enthalten nur Status, nie
  Secretwerte.
- Ein echter Testpost wird erst nach grünem Read-only-Preflight und einer
  unmittelbaren konkreten Bestätigung vor `media_publish` ausgelöst.

## Offen oder blockiert

- Für `leonavoss.ai` fehlt weiterhin ein separat erzeugter, lokal gespeicherter
  und read-only verifizierter Token.
- Danach Leona gegen Benutzername, Kontotyp und Publishing-Limit verifizieren.
- Erst danach einen einzelnen kontrollierten Leona-Testpost vorbereiten.

## GOAL UPDATES

| Goal ID | Before | After | Evidence | Next |
|---|---|---|---|---|
| M-03 | WAITING_SIGNAL | PARTIAL_CREDENTIAL_PROOF | Mara OAuth und Read-only-Limit verifiziert; kein Publish | Leona separat abschließen, dann Paket-Preflight |
| META-OAUTH-LEONA | NOT_STARTED | LOGIN_READY | Leona in Rollen-/Tokenliste, OAuth-Login offen | persönliche Anmeldung |
| META-OAUTH-MARA | LOGIN_READY | DONE | lokales Secret, korrekte API-Identität und Publishing-Limit read-only bestätigt | keine; nicht neu erzeugen |

## Nächster Agent

1. Leona-OAuth ausdrücklich als `leonavoss.ai` abschließen und Token nur lokal sichern.
2. Read-only Konto-/Publishing-Limit-Preflight für Leona ausführen.
3. Leona-Testpaket bis direkt vor `media_publish` vorbereiten und konkrete
   Aktionsbestätigung einholen.
