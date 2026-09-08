# Verbindliche Owner-Entscheidungen

## Aktueller Owner-Override — 8. September 2026: ZippoWorkz

- Kanonischer Produktname **ZippoWorkz**. Creator Ops bleibt der vorhandene Core, kein zweites Produkt.
- Ein operativer Workspace `creator-collab/`, ein Einstieg `/`, primärer Launcher `START_ZIPPOWORKZ.ps1`, DB `data/review_dashboard.db` mit Schema 5.
- `META_API = DEFERRED_OWNER_VERIFICATION`. Persönliche Verifizierung aktuell nicht möglich; keine Meta-/Auth-/Browser-Loops, keine Live-Schalter in diesem Run aktivieren. API-Code erhalten.
- Fiverr-Identität laut Owner erledigt. Historische Profil-Gates setzen dies nicht zurück. Öffentlicher Gig ohne echten Nachweis unbestätigt.
- Ansichten zusammenführen, Story-/Attention-Betriebsfehler gezielt beheben; kein Architektur-, Plattform- oder Persona-Neubau. Alte Mock-DBs nicht als echte Daten importieren.
- Git-Freigabe bleibt bestehen; tatsächliche Schreibrechte der Umgebung sind maßgeblich. Keine Umgehung von Windows-/Sandbox-Schutz.
- Lokale Story-Freigabe/Planung ist kein Live-Receipt. Keine künstlichen Posts/Analytics. Nach Prüfung, Übergabe und Journal STOP.

## Aktueller Owner-Override — 7. September 2026, 19:01 Uhr

- Git und GitHub sind nicht mehr geparkt oder zu ignorieren. Ältere
  gegenteilige Run-Regeln sind aufgehoben.
- Projektbezogene Commits, normale Branch-Pushes und sichere
  Fast-Forward-Synchronisierung sind wieder erlaubt.
- Bestehenden Credential Manager verwenden, nicht mit leerem Helper umgehen.
  Bei erneutem Fehler begrenzt diagnostizieren, keine Retry-Schleifen.
- Keine Secrets/DBs/Backups hochladen, kein Force-Push/History-Rewrite,
  keine destruktiven Änderungen oder Änderung der Repository-Sichtbarkeit.
- Die erfolgreiche Auth-Diagnose beweist noch keinen erfolgreichen Upload
  und garantiert nicht, dass künftig kein technischer Fehler auftreten kann.

Stand: 6. September 2026

Diese Datei hält dauerhafte Produkt- und Sicherheitsregeln fest. Status und
Zahlen stehen dagegen in `docs/CURRENT_STATE.json` und den Sitzungsjournalen.

## Personas und Transparenz

- Leona Voss und Mara Field sind fiktive, volljährige, KI-basierte Personas.
- Die Plattform-Kennzeichnung für KI-Inhalte wird beim Publishing geprüft.
- Normale Social-Captions erhalten keinen immer gleichen KI-Werbefooter.
- Keine erfundenen Kooperationen, Sponsoren oder persönlichen Erlebnisse.

## Content-Stufen

| Stufe | Safety | Sichtbarkeit | Öffentliche SFW-Plattformen |
|---|---|---|---|
| `ALLTAG` | `SFW` | `PUBLIC_SFW` oder `LOCAL_ONLY` | Inhalt braucht Review; Instagram-Ausführung danach vorab freigegeben |
| `TEASER` | `SFW` | `PUBLIC_SFW` oder `LOCAL_ONLY` | Inhalt braucht Review; Instagram-Ausführung danach vorab freigegeben |
| `ADULT_18` | `ADULT` | `ADULT_ONLY` | technisch gesperrt |

- Ein widersprüchlicher Datensatz wird bereits von SQLite abgewiesen.
- Adult-Material wird nicht in Git gespeichert und nicht über öffentliche
  Instagram-, Threads-, TikTok- oder YouTube-Pfade freigegeben.
- Reale Adult-Erzeugung oder -Veröffentlichung benötigt eine separate,
  ausdrückliche Owner-Freigabe. Dieser MVP erzeugt und veröffentlicht nichts
  davon automatisch.

## Content-Mix und Auswahl

- Öffentliche Instagram-Content-Richtung ab 8. September 2026: rund **70 %**
  glaubwürdiger Alltag, Setting, Handlung und Persönlichkeit sowie rund
  **30 %** glamourös/sexy angedeuteter Content. Beide Anteile bleiben strikt
  `SFW` und `PUBLIC_SFW`; „sexy“ entsteht durch Outfit, Haltung, Licht, Blick
  und nachvollziehbaren Kontext, nicht durch explizite Inhalte.
- Leona bleibt urban, stilvoll und glamourös: City/Café, Fashion, Zuhause,
  Abend und gelegentlich Gym. Mara bleibt ländlich, kräftig und bodenständig:
  Hof/Outdoor/Arbeit, Gym, Alltag und Freizeit. Die Personas und ihre
  Bildwelten werden nicht zusammengeführt oder neu gestaltet.
- Richtwerte für den Vier-Wochen-Plan: Leona City/urban 40 %, Fashion/Glamour
  25 %, Home/Alltag 20 %, Experimente 15 %; Mara Rural/Work/Outdoor 30 %, Gym
  25 %, Casual/Alltag 25 %, Experimente/Freizeit 20 %. Sie sind eine
  Planungsrichtung, kein automatischer Generierungsauftrag.
- Jede Szene braucht eine erkennbare Situation oder Handlung; künstlich
  wirkende Serien mit identischer Pose oder Blickrichtung sind zu vermeiden.
- `ADULT_18` bleibt außerhalb aller öffentlichen Pipelines und wird weder als
  Quote noch als Generierungsauftrag eingeplant.
- Jedes vollständige Paket hat fünf unterschiedliche Pose-Slots:
  `FRONTAL`, `LEFT_3Q`, `RIGHT_3Q`, `FULL_BODY_ACTION`, `CANDID`.
- Maximal zwei deutlich ähnliche Bilder je Paket.
- Top 3 werden gewichtet aus Qualität, Persona-Fit, Kohärenz, Stage-Fit und
  Neuheit gewählt und müssen mindestens drei Pose-Kategorien abdecken.

## Freigabe und externe Aktionen

### Output-first Owner-Override — 7. September 2026

- Projektbezogene, vollständige und SFW/PUBLIC_SFW-Instagram-Inhalte dürfen
  nach den bestehenden Safety-, Rechte-, Identitäts- und Idempotenz-Gates
  veröffentlicht, öffentlich geprüft und bei einem klaren Darstellungsfehler
  projektbezogen korrigiert oder archiviert werden.
- Ein zusätzlicher Einzel-Owner-Klick ist für solche Inhalte nicht erforderlich;
  persönliche Identität, OTP/Steuerdaten, Adult-Inhalte, Geld und neue Konten
  bleiben ausdrücklich Owner-only.
- Fiverr Gig 1 darf nach Abschluss des persönlichen Identity-Gates mit den
  bekannten echten Projektangaben veröffentlicht und öffentlich geprüft werden.
- Die Freigabe ändert nicht die Regel: Ohne echte Meta-Credentials darf kein
  API-Versand simuliert werden; native Instagram-Nutzung ist nur zulässig,
  wenn der eingeloggte projektbezogene Account und der konkrete SFW-Entwurf
  eindeutig verfügbar sind.

- `READY_FOR_REVIEW` ist keine Veröffentlichungsfreigabe.
- Owner-Freigabe legt im MVP nur einen lokalen `mock-draft` an.
- Für owner-freigegebene Inhalte ist echter offizieller Instagram-/Meta-
  Publish projektseitig `PRE_APPROVED_WITH_SAFETY_GATES`. Er braucht keine
  zusätzliche projektinterne Einzelgenehmigung, wenn Persona, `SFW`,
  `PUBLIC_SFW`, Rechte, KI-Disclosure, Idempotenz und technische Gates grün
  sind. Bei unklarem `media_publish` wird zuerst reconciliiert, niemals blind
  wiederholt.
- Der öffentliche Fiverr-Gig-Publish sowie vorbereitete Preise, Lieferzeiten,
  Revisionen, Kategorien, Tags, FAQ, Requirements, Gallery und Pakete sind
  projektseitig `PRE_APPROVED`, sobald das echte Verkäuferprofil vollständig
  ist. Persönliche Identität und Verifikation bleiben Owner-only.
- Echte vorhandene Meta-Credentials dürfen ausschließlich über Env-/Secret-
  Wege benutzt werden; erfundene Werte sowie Secrets in Git, DB, Logs oder
  Exporten sind verboten.
- Profiländerungen, Nachrichten, Kommentare, DMs sowie Follow-Aktionen bleiben
  eigene Owner-Aktionen und sind durch diese Vorabfreigabe nicht umfasst.
- Übergeordnete Sicherheits- und Bestätigungsregeln der jeweils ausführenden
  Oberfläche bleiben unberührt.
- Keine Massen-Follow-/Unfollow-Automation.

## Dauerhafter Arbeitsmodus

- Pro Run höchstens zwei Hauptquests; Sidequests erst nach Abschluss oder
  sauber dokumentiertem Blocker der P0-Lanes.
- Verifizierte Baseline wird als `SKIP_DONE` behandelt. Rework gibt es nur bei
  reproduzierbarem Fehler, geänderter Owner-Anforderung oder direkter
  Abhängigkeit eines echten Deltas.
- Ein kleiner Blocker erhält einen konzentrierten Lösungsversuch von ungefähr
  fünf Minuten. Danach: Ursache, Fallback und Fortsetzungspunkt dokumentieren
  und in einer unabhängigen Lane weiterarbeiten.
- Browser-/UI-Fehler: ein Fix und ein Retest; danach sicherer Fallback oder
  Human Handoff statt Schleife.
- Tests und Backups sind risikobasiert: Publishing, Auth, Datenbank,
  Idempotenz und Recovery erhalten Integrationstests; kleine Doku-/Content-
  Änderungen nur gezielte Prüfungen.
- HIGH/ULTRA ist für Meta-Publish, Secrets/Auth, externe Unsicherheit,
  Datenbank/Idempotenz und Recovery reserviert. Routine-Content und normale
  Dokumentation bleiben MEDIUM.
- Sichere Fast-Forward-Git-Synchronisierung ist erlaubt; Force-Push,
  History-Rewrite und Sichtbarkeitsänderungen bleiben verboten.
- Owner-Fragen werden gebündelt. Persönliche Identität, Ausweis-/Selfie-
  Verifikation, OTP, Passwörter, neue API-/OAuth-Schlüssel sowie fehlende
  persönliche Steuer- oder Identifikationsnummern bleiben beim Owner.
  Vorhandene echte Unternehmens-/Steuerangaben dürfen im vorab freigegebenen
  Fiverr-Formularlauf verwendet werden, aber niemals erfunden oder gespeichert.

## Medien, Rechte und Geheimnisse

- Nur eigene, lizenzierte oder nachweisbar KI-generierte Assets verwenden.
- Unklare Rechte blockieren kommerzielle und Website-Nutzung.
- Runtime-Medien liegen unter ignorierten `data/media/`-Pfaden; neue
  Creator-Bilder gehören nicht in Git.
- Passwörter, Tokens, Codes, Cookies und Tunnel-URLs werden nie committed.
- Das GitHub-Repository soll privat sein; die tatsächliche Sichtbarkeit wird im
  jeweils neuesten Journal mit sichtbarer Bestätigung dokumentiert.

## Rote Schranken

Diese Aktionen bleiben auch bei laufender Automatisierung gesperrt oder
benötigen eine neue ausdrückliche Einzelgenehmigung:

1. Geld ausgeben, Paid Ads, kostenpflichtige Dienste, Abos, Accounts, Verträge
   oder Käufe.
2. Erzeugung oder Veröffentlichung von Adult-Material.
3. Änderung von Cloud-Zugriffsrechten oder Repository-Sichtbarkeit.
4. Force-Push, Git-History-Rewrite oder destruktive Reset-/Löschaktionen.
5. Löschen veröffentlichter Posts oder Originalmedien.
6. Persönliche Identitäts-, Ausweis-, Selfie-, OTP- oder fehlende persönliche
   Steuer-/Identifikationsdaten.
7. Andere schwer rückgängig zu machende externe Verpflichtungen.

Offizieller Instagram-/Meta-Publish und öffentlicher Fiverr-Gig-Publish sind
keine pauschalen roten Schranken mehr; für sie gelten die oben dokumentierten
Safety-, Rechte-, Technik- und Identity-Gates.
