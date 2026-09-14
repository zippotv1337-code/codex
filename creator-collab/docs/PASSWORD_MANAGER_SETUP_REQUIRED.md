# Password Manager — einmalige Owner-Einrichtung

ZippoWorkz greift über einen provider-neutralen `SecretProvider` auf Zugangsdaten zu. Im Repository, Dashboard, Journal und Handoff werden ausschließlich Aliase wie `secret://meta/leona-voss/access-token` geführt; echte Werte werden weder angezeigt noch protokolliert.

## Unterstützte Wege

- Windows-Anmeldeinformationsverwaltung als primärer lokaler Store
- Runtime-Umgebungsvariablen als zeitweiliger Fallback
- deaktivierter Provider als fail-closed Betrieb

## Einzige offene Owner-Aktion

Einmalig einen primären Provider auswählen und die bereits vorhandenen Projekt-Zugangsdaten unter den im Dashboard genannten Aliasen hinterlegen. Keine Werte in diese Datei, Git, SQLite, Handoffs oder Chats kopieren.

Recovery-Codes bleiben getrennt in einem verschlüsselten Offline-Backup.
