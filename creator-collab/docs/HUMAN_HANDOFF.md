# Human Handoff — ZippoWorkz

Stand: 14.09.2026, 12:48 Europe/Berlin

Das Security-/Handoff- und Milo/TikTok-Paket ist lokal vollständig umgesetzt,
getestet und in der laufenden ZippoWorkz-Runtime aktiviert.

## Genau eine Owner-Aktion

Einen primären Secret-Provider auswählen (empfohlen: Windows-
Anmeldeinformationsverwaltung) und die bereits vorhandenen Zugangsdaten der
ZippoWorkz-Projektkonten einmalig unter den im Dashboard angezeigten
`secret://...`-Aliasen hinterlegen.

Keine Secret-Werte in Chat, Git, Markdown, SQLite, Logs oder Handoffs kopieren.
Bis zur Einrichtung bleiben alle externen Adapter bewusst fail-closed.

## Bereits erledigt

- zentrale Policy v2.1 und gemeinsames Handoff-Schema installiert
- strengere Local-AI-Rollenpolicy erhalten und validiert
- SecretProvider/Broker und alias-only Audit implementiert
- Pre-Push-Secret-Check aktiviert
- Milo der Zug als fiktive KI-Marke lokal sichtbar
- Instagram/TikTok getrennt und ehrlich `NOT_CONNECTED`
- 9:16-Preview sowie lokales APPROVE/CHANGE/REJECT vorhanden
- Draft Upload und Direct Post getrennt; Direct Post dreifach gegated
- Analytics `UNKNOWN/NULL`, solange keine echten Werte existieren
- 178/178 Tests, Runtime-Health und SQLite-Integrität grün

- Dashboard: <http://192.168.188.131:4180/>
- Milo/TikTok: <http://192.168.188.131:4180/channels>
- Security: <http://192.168.188.131:4180/control>

Externe Aktionen dieses Runs: `NONE`.
