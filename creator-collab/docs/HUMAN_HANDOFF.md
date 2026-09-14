# Human Handoff — ZippoWorkz

Stand: 14.09.2026, 17:17 Europe/Berlin

Meta wurde read-only geprüft und ist wegen fehlender sicher hinterlegter
Projekt-Credentials ehrlich blockiert. Der referenzgebundene Milo-9:16-
Fallback ist lokal vollständig umgesetzt, getestet und in der laufenden
ZippoWorkz-Runtime sichtbar.

## Genau eine Owner-Aktion

Die bereits vorhandenen Meta-Zugangsdaten einmalig im sicheren Secret-Provider
(empfohlen: Windows-Anmeldeinformationsverwaltung) unter den im Dashboard
angezeigten `secret://meta/...`-Aliasen hinterlegen.

Keine Secret-Werte in Chat, Git, Markdown, SQLite, Logs oder Handoffs kopieren.
Bis zur Einrichtung bleiben alle externen Adapter bewusst fail-closed.

## Bereits erledigt

- zentrale Policy v2.1 und gemeinsames Handoff-Schema installiert
- strengere Local-AI-Rollenpolicy erhalten und validiert
- SecretProvider/Broker und alias-only Audit implementiert
- Pre-Push-Secret-Check aktiviert
- Milo der Zug an das echte Owner-Titelbild/Profilbild gebunden
- Instagram-Profil `miloderzug` öffentlich bestätigt; Transport weiterhin
  ehrlich nicht verbunden
- finales 9:16-PNG `Milos erste Fahrt am Morgen` ist `READY_FOR_REVIEW`
- echte 9:16-Preview sowie lokales APPROVE/CHANGE/REJECT vorhanden
- Draft Upload und Direct Post getrennt; Direct Post dreifach gegated
- Analytics `UNKNOWN/NULL`, solange keine echten Werte existieren
- Meta-Preflight reproduzierbar fail-closed; keine externe Anfrage
- 179/179 Tests, Runtime-Health und SQLite-Integrität grün

- Dashboard: <http://192.168.188.131:4180/>
- Milo/TikTok: <http://192.168.188.131:4180/channels>
- Security: <http://192.168.188.131:4180/control>

Externe Aktionen dieses Runs: `NONE`.
