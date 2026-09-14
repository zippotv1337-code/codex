# Human Handoff — ZippoWorkz

Stand: 14.09.2026, 23:20 Europe/Berlin

## Meta-Dashboard-Pfad (fertig verdrahtet, noch nicht live bewiesen)

Unter `/channels` stehen jetzt pro Queue-Paket die Aktionen **Einzelpaket
prüfen** und **Dieses Paket senden**. Der Versand ist auf genau eine
Content-ID begrenzt, führt vorab einen frischen read-only Preflight aus und
schreibt nur nach bestätigter externer Media-ID plus Instagram-Permalink auf
`PUBLISHED`. Der globale Scheduler wird dabei nicht aktiviert.

Der lokale Media-Origin (`creator_ops.public_media`) kann drei explizit
ausgewählte JPEG-Derivate loopback-only und zeitbegrenzt bereitstellen. Für Meta
fehlen noch ein öffentlicher HTTPS-Origin und ein separater Tunnel; `cloudflared`
ist auf diesem Rechner nicht vorhanden und wurde nicht installiert.

### Noch nötige Owner-/Umgebungsaktionen für den echten Proof

1. Die im Chat offengelegten Meta-/TikTok-Schlüssel im jeweiligen Developer
   Portal rotieren. Werte nicht erneut im Chat senden.
2. Für Leona oder Mara einen echten Instagram-Nutzer-Token, die passende
   Nutzer-ID und die benötigten Content-Publishing-Berechtigungen über den
   sicheren Secret-Provider hinterlegen. Eine App-ID bzw. ein App-Geheimcode
   allein ist kein Nutzerzugang.
3. Drei eindeutige JPEG-Derivate eines freigegebenen `SFW`/`PUBLIC_SFW`-
   Pakets auf einem öffentlichen HTTPS-Origin bereitstellen und dessen
   Manifestpfad lokal konfigurieren.
4. Im Dashboard `Einzelpaket prüfen` ausführen. Nur bei `READY` den kontrollierten
   Einzelversand starten; bei Timeout zuerst Reconciliation, niemals blind
   erneut senden.

Meta wurde read-only geprüft und ist wegen fehlender sicher hinterlegter
Projekt-Credentials ehrlich blockiert. Der referenzgebundene Milo-9:16-
Fallback ist lokal vollständig umgesetzt, getestet und in der laufenden
ZippoWorkz-Runtime sichtbar.

## Genau eine dringende Owner-Aktion

Das im Chat offengelegte TikTok-Kundengeheimnis im TikTok Developer Portal
rotieren. Den neuen Wert nicht im Chat senden, sondern ausschließlich unter dem
vorhandenen `secret://tiktok/client_secret`-Alias im sicheren Secret-Provider
hinterlegen.

Keine Secret-Werte in Chat, Git, Markdown, SQLite, Logs oder Handoffs kopieren.
Bis zur Einrichtung bleiben alle externen Adapter bewusst fail-closed.

## Neuer Live-Beleg

- Milo TikTok-Fotopost:
  <https://www.tiktok.com/@miloderzug/photo/7685433578976709911>
- Medien-ID: `7685433578976709911`
- Sichtbar: Caption, Hashtags und natives KI-generiert-Label
- Veröffentlicht über: offizielle eingeloggte TikTok-Weboberfläche
- TikTok API: weiterhin nicht als User-Publish-Pfad bewiesen

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
- fokussierte Meta-/Channel-/Media-/Queue-/AI-Ops-Tests, Runtime-Health und
  SQLite-Integrität grün

- Dashboard: <http://192.168.188.131:4180/>
- Milo/TikTok: <http://192.168.188.131:4180/channels>
- Security: <http://192.168.188.131:4180/control>

Externe Aktionen dieses Runs: `NONE`.
