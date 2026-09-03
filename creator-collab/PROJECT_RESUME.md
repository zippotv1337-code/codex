# Projekt-Résumé: Virtual Creators Germany

Stand: 3. September 2026

## Ziel

Zwei klar getrennte virtuelle Creator-Personas für den deutschen Markt
aufbauen, organische Reichweite testen und später über eine zentrale Linkseite
regelkonform monetarisieren. Alle Personas sind fiktiv, volljährig dargestellt
und KI-generiert.

## Personas

### Leona Voss

- Instagram: `@leonavoss.ai`
- Positionierung: Berlin, Fashion, Glamour, Lifestyle und gelegentlich Gym
- Ton: selbstbewusst, elegant, nahbar
- Sichtbarer Hinweis: fiktive, KI-generierte Persona

### Mara Field

- Instagram: `@mara.field.ai`
- Positionierung: deutscher Hofalltag, Landmaschinen, Werkstatt und Landleben
- Ton: bodenständig, humorvoll, fachlich interessiert
- Sichtbarer Hinweis: fiktive, KI-generierte Persona
- Bei sichtbaren Marken: keine Partnerschaft behaupten; zum Beispiel John Deere
  ausdrücklich als unabhängiges KI-Projekt kennzeichnen.

## Bestätigter Plattformstand

- Beide Instagram-Profile sind erstellt und über die Meta-Kontenübersicht erreichbar.
- Beide Instagram-Profile haben jeweils fünf veröffentlichte Feed-Beiträge.
- Jeder neue Beitrag wurde mit dem Instagram-KI-Label veröffentlicht.
- Facebook-Crossposting blieb deaktiviert.
- Jedes Profil folgt fünf manuell geprüften, thematisch passenden Startkonten.
- Es wurde keine Massen-Follow-/Unfollow-Automation eingesetzt.
- Die Creator-Instagram-Konten `@leonavoss.ai` und `@mara.field.ai` wurden aus
  der privaten Meta-Kontenübersicht in jeweils eigene Kontenübersichten
  verschoben.
- Das frühere private Threads-Profil wurde wieder auf `@zippo.rocco`
  zurückgestellt; seine 73 Follower blieben erhalten.
- Für Mara wurde ein neues Threads-Profil `@mara.field.ai` angelegt. Direkt
  nach dem Onboarding setzte Threads das Profil jedoch aus und verlangt eine
  echte Selfie-Verifizierung; das Profil ist daher noch nicht einsatzbereit.
- Die Instagram-Kontenwechselliste enthält wieder Mara, Leona und das private
  `zippo.rocco`; Leona ist nicht verloren.
- Threads-Bios und Startposts für beide Creator liegen freigabefertig in
  `creator-collab/THREADS_DRAFTS.md`.

## Instagram-Belege

### Leona

- https://www.instagram.com/leonavoss.ai/p/Dc0mbMAgE1M/
- https://www.instagram.com/leonavoss.ai/p/Dc0oRg7APVa/
- https://www.instagram.com/leonavoss.ai/p/Dc0pXtAgBJY/
- https://www.instagram.com/leonavoss.ai/p/Dc0pc2sgDUd/
- https://www.instagram.com/leonavoss.ai/p/Dc0pf8NAAnG/

### Mara

- https://www.instagram.com/mara.field.ai/p/Dc0mATVAF2u/
- https://www.instagram.com/mara.field.ai/p/Dc0oGuxgBWl/
- https://www.instagram.com/mara.field.ai/p/Dc0pmnQAKHP/
- https://www.instagram.com/mara.field.ai/p/Dc0ppmtAPJy/
- https://www.instagram.com/mara.field.ai/p/Dc0pslwgH7R/

## Starter-Netzwerk

- Mara: `landwirtschaft_mit_anna`, `landwirtschaft_knuf`,
  `stephan.landwirtschaft`, `landwirtschaft4you`, `agrarheute`
- Leona: `berlinfashionwe`, `voguegermany`, `glamourgermany`,
  `womenshealth.de`, `mitvergnuegen`

## Sicherheits- und Qualitätsregeln

- Keine reale Person imitieren oder eine echte Biografie vortäuschen.
- Keine expliziten Inhalte auf Instagram, TikTok oder Threads.
- KI-Herkunft in Profilen und realistisch wirkenden Beiträgen transparent machen.
- Nur eigene beziehungsweise rechtmäßig nutzbare Medien veröffentlichen.
- Keine Passwörter, OTPs oder Kontaktinformationen in dieses Repository schreiben.
- Reichweite über Content, Antworten und passende Themen aufbauen; keine Spam-Taktiken.

## Zusammenarbeit Codex und ChatGPT

- Gemeinsames Ziel-Repository: https://github.com/zippotv1337-code/codex
- Zielbranch: `main`
- Dauerhafter Projektstand: `creator-collab/PROJECT_RESUME.md`
- Aktuelle Übergabe: `creator-collab/CURRENT_HANDOFF.md`
- Pro abgeschlossener Sitzung wird ein datiertes Journal unter
  `creator-collab/sessions/` angelegt.
- Zugangsdaten, Bestätigungscodes und andere Geheimnisse werden niemals dort
  gespeichert.

## Creator-Ops-MVP

- Ein lokaler, modularer Python-/SQLite-MVP bildet den vertikalen Ablauf für
  Leona und Mara ab: Planung, Asset-Registrierung, Auswahl, Review,
  Freigabesimulation, Prime-Time-Terminierung, Mock-Veröffentlichung und
  Analytics-Lernen nach 24 Stunden, 72 Stunden und 7 Tagen.
- Der Publisher ist absichtlich ein `MockPublisher`; er veröffentlicht nichts
  auf echten Plattformen und verursacht keine externen Kosten.
- Der Ablauf ist über einen stabilen Run-Key idempotent. Wiederholungen am
  gleichen Tag erzeugen keine doppelten Inhalte oder Publikationen.
- Erholbare Fehler werden als `PARTIAL_READY` persistiert und können beim
  nächsten Lauf fortgesetzt werden.
- Plattform-Compliance verlangt KI-Transparenz und geklärte Medienrechte und
  blockiert Adult-Inhalte für Instagram, Threads, TikTok und YouTube.
- Der bestätigte Demo-Datenbestand enthält zwei Creators, zwei Content-Items,
  zehn Assets, zwei Mock-Publikationen und sechs Analytics-Snapshots.
- Schnellstart und Ergebnisbericht stehen in `docs/QUICKSTART.md` und
  `docs/LAST_RUN_REPORT.md`.
- Der tägliche Evening Run akzeptiert Starts nur zwischen 19:00 und 22:00 Uhr
  in `Europe/Berlin` und ist pro Datum idempotent.
- Prime Time beginnt konfigurationsbasiert, lernt anschließend aus
  7-Tage-Metriken und hält pro Creator mindestens 30 Minuten Slot-Abstand.
- Jeder neue Inhalt erhält einen Primary-/Alternate-/Reserve-Assetplan.
- Audio läuft über einen Adapter; nur bestätigte eigene oder lizenzierte
  Kandidaten werden gewählt, sonst greift sicher „ohne Musik“.
- Die Engagement Queue erzeugt ausschließlich manuell zu prüfende Vorschläge
  und führt keine Plattformaktion aus.
- Secret-freie JSON-Exporte und integritätsgeprüfte SQLite-Backups stehen über
  die CLI bereit.
- Eine lokale Freigabeoberfläche zeigt für morgen je eine Leona- und Mara-Karte
  mit fünf Assets, Top 3, Carousel, Caption, Audio-Fallback und Prime Time.
- Der Freigabe-Button protokolliert eine echte lokale Betreiberentscheidung,
  erstellt aber ausschließlich einen `mock-draft` ohne externe Veröffentlichung.

## Offene Projektbereiche

- Threads-Prüfung von Mara ausschließlich über den offiziellen Weg klären;
  keine KI-Selfies oder Umgehung der Identitätsprüfung verwenden.
- Separates Threads-Profil für Leona nach einmaliger Instagram-Anmeldung erstellen.
- Threads-Profile von Leona und Mara transparent als KI-Personas kennzeichnen
  und jeweils einen Start-Thread veröffentlichen.
- Regelmäßige Threads-Textformate und Antwortstrategie entwickeln.
- TikTok-Profile und native Kurzvideos aufbauen.
- Zentrale Linkseite und rechtssichere Monetarisierungsstrecke umsetzen.
- Performance nach 24 Stunden, 72 Stunden und 7 Tagen erfassen.
- MockPublisher nach separater Freigabe durch offizielle Plattformadapter
  ergänzen; echte Veröffentlichungen bleiben bis dahin deaktiviert.
- Die simulierten Analytics später durch erlaubte, offizielle API-Metriken
  ersetzen.
- Reale, rechtlich nutzbare Asset-Dateien in die Review-Kacheln importieren.
- Engagement Queue als zweite Ansicht in die lokale Oberfläche aufnehmen.
- Wiederherstellung aus einem SQLite-Backup als eigenen Disaster-Recovery-Lauf
  dokumentieren und testen.
