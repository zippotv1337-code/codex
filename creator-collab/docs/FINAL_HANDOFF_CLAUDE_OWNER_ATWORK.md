# Creator Ops – Finaler Handoff für Claude, Owner und @work

Stand: 4. September 2026 · Europe/Berlin

Dieses Dokument ist die kurze verbindliche Abschlussübergabe. Für den aktuellen
Fortsetzungspunkt gilt zusätzlich `AUTOPILOT_CHECKPOINT.md`. Historische Details
stehen in `sessions/CONSOLIDATED_JOURNAL.md` und den Einzeljournalen.

## Executive Summary

Creator Ops ist lokal betriebsfähig. Der Kernworkflow für Leona Voss und Mara
Field funktioniert mit echten Bildvorschauen, Review, lokalen Owner-
Entscheidungen, Archiv, Top 3, Engagement-Vorschlägen, Backups und einem
passwortgeschützten LAN-Zugang. Es gibt kein automatisches Live-Publishing.

Letzter verifizierter technischer Stand:

- 55/55 Tests grün
- SQLite `integrity_check = ok`
- 2 Creator-Personas
- je Persona 2 feedfähige Pakete
- je Persona 9 unveröffentlichte reale Assets
- 4 Reviewpakete über den 5. und 6. September
- 2 owner-bestätigte native Instagram-Posts
- 4 Vorschläge zu echten Posts in der Engagement Queue
- 0 echte Analytics-Events und keine verfügbaren Kommentartexte
- Kosten: 0 EUR
- keine externen Aktionen im Abschlussrun

## Übergabe an Claude – technischer Folgeagent

### Zuerst vollständig lesen

1. `AGENTS.md`
2. `creator-collab/AUTOPILOT_CHECKPOINT.md`
3. `creator-collab/PROJECT_RESUME.md`
4. `creator-collab/CURRENT_HANDOFF.md`
5. `creator-collab/sessions/CONSOLIDATED_JOURNAL.md`
6. neuestes Einzeljournal in `creator-collab/sessions/`

### Verbindliche Regeln

- Bestehenden funktionierenden Kern nicht neu bauen.
- Nur `creator-collab/` verändern.
- Keine Secrets in Dateien, Datenbank, Journal oder Chat schreiben.
- Keine neue Persona, keine Kosten und keine kostenpflichtigen Dienste.
- Keine Live-Posts, Kommentare, Likes, Follows oder DMs ohne ausdrückliche
  Owner-Freigabe.
- Fiktive KI-Personas transparent kennzeichnen; öffentliche Inhalte bleiben SFW.
- Keine KI-Selfies oder Umgehung von Plattform-Verifizierungen.
- Git/GitHub bleiben geparkt, bis der Owner dies ausdrücklich neu freigibt.

### Technischer Start

Lokal am PC:

```powershell
.\START_CREATOR_OPS.ps1
```

Beenden:

```powershell
.\STOP_CREATOR_OPS.ps1
```

Im Heimnetz:

```powershell
.\START_LAN_CREATOR_OPS.ps1
```

Die LAN-Adresse wird automatisch erkannt. Zuletzt war sie
`http://192.168.188.131:4180/`. Sie kann sich durch DHCP ändern. LAN-Betrieb
verlangt ein temporäres Passwort mit mindestens zwölf Zeichen. Keine
Routerfreigabe einrichten.

### Aktuelle technische Prioritäten

1. Keine neue Entwicklung starten, bevor der Owner die vier Pakete geprüft hat.
2. Nach Owner-Eingabe echte 24-/72-/168-h-Analytics erfassen und Top 3 sowie
   Prime Time kontrollieren.
3. Danach höchstens eine kleine Sidequest: Story-Pakete oder Collections/Alben.
4. Vor jedem längeren Run DB-Integrität und Backup prüfen.
5. Rechtzeitig `AUTOPILOT_CHECKPOINT.md`, Journal und Handoff aktualisieren.

### Bekannte Grenzen

- Kein offizieller Instagram-Publishing- oder Analytics-Adapter.
- Keine echten Analytics-Snapshots vorhanden.
- Keine echten Kommentartexte gespeichert; deshalb keine individuellen
  Antwortentwürfe erfinden.
- Mara Threads wartet auf eine offizielle persönliche Verifizierung.
- Eine optionale Windows-Firewallregel für LAN benötigt Owner-
  Administratorrechte und ist auf Private/LocalSubnet/TCP 4180 zu begrenzen.

## Übergabe an den Owner – was du jetzt machen musst

### 1. Creator Ops öffnen

Auf dem PC `START_CREATOR_OPS.ps1` starten. Für das Handy
`START_LAN_CREATOR_OPS.ps1` starten, ein temporäres Passwort festlegen und die
angezeigte LAN-Adresse in Safari öffnen. Handy und PC müssen im gleichen WLAN
sein.

### 2. Vier Pakete prüfen

Im Review stehen:

| Persona | Paket | Status | Hinweis |
|---|---|---|---|
| Leona | Spätsommer in Berlin | lokal `SCHEDULED` | fünf unveröffentlichte Assets |
| Mara | Fünf Minuten Maschinencheck | `READY_FOR_REVIEW` | veröffentlichtes S4 ausgeschlossen |
| Leona | September Roofline | `READY_FOR_REVIEW` | veröffentlichtes S4 ausgeschlossen |
| Mara | Küchenfenster | `READY_FOR_REVIEW` | fünf unveröffentlichte Assets |

Pro Paket:

- **APPROVE**: legt nur einen lokalen Mock-Draft an.
- **CHANGE**: Änderungswunsch kurz eintragen.
- **REJECT**: Paket lokal blockieren.

Keiner dieser Buttons veröffentlicht einen Live-Post.

### 3. Echte Daten nachtragen

Bei den zwei bereits veröffentlichten Instagram-Posts nach 24, 72 und 168
Stunden die sichtbaren Insights erfassen. Benötigt werden möglichst Reach oder
Views, Likes, Kommentare, Shares, Saves, Profilbesuche, Follows und Linkklicks.
Nur echte Werte verwenden.

### 4. Kommentare optional bereitstellen

Wenn individuelle Antwortvorschläge gewünscht sind, konkrete Kommentartexte
manuell bereitstellen. Eine reine Kommentaranzahl reicht nicht für eine
persönliche Antwort.

### 5. Spätere Entscheidung

Nach Review und Analytics genau eine nächste Produktion auswählen:

- Leona: „Gym Reset, aber echt“, oder
- Mara: „Werkstatt: Feierabend in drei Handgriffen“.

Nicht beide halb anfangen. Ein vollständiges Paket ist wertvoller.

## Übergabe an @work – benötigter gemeinsamer Kontext

### Projektziel

Zwei getrennte virtuelle Creator für den deutschen Markt betreiben:

- **Leona Voss**: Berlin, Fashion, Glamour, Lifestyle, gelegentlich Gym.
- **Mara Field**: deutscher Hofalltag, Landmaschinen, Werkstatt und Landleben.

Beide sind fiktive, erwachsen dargestellte KI-Personas. Inhalte für Instagram,
TikTok und Threads bleiben SFW. Sichtbare Marken dürfen nicht als Kooperation
dargestellt werden, wenn keine Partnerschaft besteht.

### Was @work als verifiziert behandeln darf

- Vier reale, vollständige Feedpakete existieren.
- Je Paket gibt es fünf Kandidaten und eine kuratierte Top 3.
- Veröffentlichte S4-Einzelbilder bei Mara Maschinencheck und Leona Roofline
  sind von späteren Carousel-Empfehlungen ausgeschlossen.
- Captions, Hooks, CTAs, Hashtags, Audio A/B/ohne und Prime Times sind vorhanden.
- Creator Ops zeigt echte Thumbnails und ist lokal sowie passwortgeschützt im
  Heimnetz erreichbar.
- Engagement ist nur ein Vorschlagsbereich und führt nichts extern aus.
- Reale Analytics fehlen noch. Keine Performance-Aussage erfinden.

### Was @work übernehmen soll

1. Owner beim Review der vier Pakete unterstützen.
2. CHANGE-Wünsche in klare, kleine Änderungsaufträge übersetzen.
3. Echte Analytics nach 24/72/168 Stunden gemeinsam auswerten.
4. Bei konkreten echten Kommentaren individuelle Antwortentwürfe formulieren.
5. Aus tatsächlichen Signalen höchstens drei Learnings für die nächste Woche
   ableiten.
6. Keine neue Architektur, Plattform oder Persona vorschlagen, solange Review
   und Analytics offen sind.

### Nicht behaupten

- keine Sponsoren oder Markenpartnerschaften
- keine erfundenen Follower-, Reichweiten- oder Umsatzwerte
- keine angeblich erfolgreichen Audio-Trends ohne aktuellen Plattformnachweis
- keine automatische Veröffentlichung
- keine erledigte Threads-Verifizierung für Mara

## Geparkte Punkte

Die folgenden Punkte sind kein technischer Betriebsblocker und bleiben beim
Owner geparkt:

- Repository-Sichtbarkeit
- `.git/index.lock`
- Commit und Push
- Branch-/Remote-Reparaturen
- GitHub-Synchronisation

## Verbindlicher nächster Startauftrag

> Lies `AUTOPILOT_CHECKPOINT.md` und diese Finalübergabe. Prüfe nur den lokalen
> Zustand. Unterstütze zuerst den Owner-Review der vier vorhandenen Pakete.
> Erfasse danach ausschließlich echte Analytics oder konkrete Owner-
> Änderungswünsche. Beginne keine neue große Arbeit, solange diese Owner-Gates
> offen sind. Git/GitHub und alle externen Aktionen bleiben geparkt.
