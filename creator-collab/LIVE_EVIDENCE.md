# Live Evidence

Stand: 2026-09-21T09:36:00+02:00 · Europe/Berlin

## Instagram

- **Offizielle API-Automation:** `PROVEN_LIVE` am 21.09.2026.
- **INSTAGRAM_AUTOMATION_PROOF:** 10/10 für je einen kontrollierten Leona- und
  Mara-Carousel-Pilot über `graph.instagram.com`; globale unbeaufsichtigte
  Live-Schalter bleiben absichtlich deaktiviert.

### Offiziell bestätigter Meta-Graph-Carousel-Pilot

- Persona: Leona Voss · `@leonavoss.ai`
- Content: ID `1` · „Rainy Berlin Afterwork“
- Publication: ID `1` · Provider `instagram-meta-graph`
- Permalink: https://www.instagram.com/p/DdilnXGEVdO/
- Instagram-Media-ID: `18028287917684160`
- Plattform-Zeitstempel: `2026-09-21T07:08:04+00:00`
  (`09:08:04 Europe/Berlin`)
- Format: `CAROUSEL_ALBUM`, drei eigenständige SFW-/PUBLIC_SFW-JPEGs.
- Account vor Publish read-only als `leonavoss.ai` / `MEDIA_CREATOR`
  bestätigt; Publishing-Limit 0/100.
- Vorab: drei öffentliche HTTPS-JPEGs mit HTTP 200, `image/jpeg` und gültiger
  JPEG-Magic; native AI-Kennzeichnung bestätigt.
- Nachweis: Queue genau ein Versuch, Status `PUBLISHED`, kein Fehler; Receipt
  `CONFIRMED`; DB-, Receipt- und Graph-ID/Permalink stimmen überein; alle drei
  Top-Picks als `PUBLISHED`; SQLite `integrity_check = ok`.
- Doppelpost-Schutz: derselbe Queue-Key besitzt nun ein bestätigtes Receipt;
  ein erneuter Dispatch liefert den vorhandenen Beleg statt erneut zu posten.
- Tokens bleiben ausschließlich im lokalen Windows-User-Environment. Weil sie
  zuvor im Chat offengelegt wurden, ist Rotation nach dem Proof empfohlen.

### Offiziell bestätigter Mara-Meta-Graph-Carousel

- Persona: Mara Field · `@mara.field.ai`
- Content: ID `4` · „Küchenfenster“
- Publication: ID `2` · Provider `instagram-meta-graph`
- Permalink: https://www.instagram.com/p/DdioXo1Ec9j/
- Instagram-Media-ID: `18090373508475307`
- Plattform-Zeitstempel: `2026-09-21T07:32:09+00:00`
  (`09:32:09 Europe/Berlin`)
- Format: `CAROUSEL_ALBUM`; Top 3 S4 Ganzkörper/Bewegung → S3 Fenster rechts
  3/4 → S5 candid am Tisch mit Notizbuch.
- Account vor Publish read-only als `mara.field.ai` / `BUSINESS` bestätigt;
  Publishing-Limit 0/100. Alle drei öffentlichen Medien bestanden HTTP 200,
  `image/jpeg` und JPEG-Magic.
- Queue genau ein Versuch, Status `PUBLISHED`, kein Fehler; Receipt
  `CONFIRMED`; DB-, Receipt- und Graph-ID/Permalink stimmen überein. Der
  anschließende Dispatch lieferte `due=0` und erzeugte keinen Doppelpost.

- **Konkreter Pilot:** `LIVE_NATIVE_OWNER_CONFIRMED`
- **Frühere native Piloten:** bleiben als historische Belege erhalten; sie sind
  nicht der neue Meta-Graph-Autopublish-Nachweis.
- **Live am 21. September:** 2 offizielle Meta-Carousels / 6 Bilder: Leona
  „Rainy Berlin Afterwork“ und Mara „Küchenfenster“.
- **Lokaler Modus:** globale unbeaufsichtigte Live-Schalter bleiben aus; die
  beiden exakt owner-freigegebenen Pakete liefen über den offiziellen Adapter.
- **Aktuelle kanonische Queue:** 2 × `PUBLISHED`, 0 × `LOCAL_SCHEDULED`.

### Neu sichtbar bestätigter Leona-Gym-Carousel

- Persona: Leona Voss · `@leonavoss.ai`
- Content: ID `1` · „Gym Reset, aber echt“
- Permalink: https://www.instagram.com/leonavoss.ai/p/Dc_GwljAKU_/
- Instagram-Shortcode: `Dc_GwljAKU_`
- Veröffentlichungszeit im lokalen Beleg:
  `2026-09-07T14:19:00+02:00`
- Reihenfolge: Asset `1` frontal → Asset `2` links 3/4 → Asset `5` candid.
- Sichtbar geprüft: Instagram meldete „Dein Beitrag wurde geteilt.“;
  Profilstand danach 8 Beiträge. Direkt am Post sind Caption, sechs Hashtags,
  `KI-Inhalte` und `Insights ansehen` sichtbar. Das KI-Label wurde vor dem
  Teilen aktiviert.
- Lokale Abstimmung: Publication `9`, Provider `instagram-native-manual`,
  Queuejob `4` und Content `1` jeweils `PUBLISHED`; der alte Mock-Draft
  Publication `8` ist als `PAUSED_DUPLICATE_RISK` gesperrt.

Caption:

> Kein perfekter Trainingsplan, kein Motivationsspruch. Schuhe zu, erster
> Satz, dann läuft’s meistens. Was bringt euch zuverlässig ins Training?
>
> #GymRoutine #BerlinFitness #WorkoutRealTalk #FitnessMotivationDE
> #Trainingsalltag #VirtualCreator

### Neu sichtbar bestätigter Leona-Carousel

- Persona: Leona Voss · `@leonavoss.ai`
- Content: ID `5` · „September Roofline“
- Permalink: https://www.instagram.com/p/Dc75xWsgEQo/
- Instagram-Shortcode: `Dc75xWsgEQo`
- Veröffentlichungszeit im lokalen Beleg:
  `2026-09-06T13:00:00+02:00`
- Reihenfolge: Asset `22` links 3/4 → Asset `25` candid → Asset `23`
  rechts 3/4.
- Sichtbar geprüft: Instagram meldete „Beitrag geteilt“, Profilstand 7 Posts,
  drei Slides, Caption, Alt-Texte und natives Label `KI-Inhalte`.
- Lokale Abstimmung: Publication `7`, Provider
  `instagram-native-manual:Dc75xWsgEQo`, Queuejob `2` und Content `5` jeweils
  `PUBLISHED`; der ältere Einzelpost bleibt unverändert erhalten.

Caption:

> September über den Dächern von Berlin. Noch ein bisschen Sommer in der
> Luft, aber abends merkt man schon, dass sich die Stadt verändert. Welchen
> Look würdet ihr für den nächsten Abend nehmen?
>
> #Berlin #CityStyle #SeptemberMood #Rooftop #EditorialStyle #VirtualCreator

### Frühere owner-bestätigte native Veröffentlichungen

- Mara Field · Content `4` ·
  https://www.instagram.com/mara.field.ai/p/Dc3d7CHgO3S/
- Leona Voss · Content `5` ·
  https://www.instagram.com/leonavoss.ai/p/Dc3elLhAC2-/

## Fiverr

- **Status:** `FIVERR_GIG1_CONTENT_COMPLETE_WAITING_FOR_OWNER_IDENTITY`
- Das eingeloggte Konto zeigt `Create your profile`; ein echtes
  Verkäuferprofil existiert noch nicht.
- Aktueller Gig 1: `AI Workflow Automation`; Titel, Beschreibung, neun FAQ,
  zehn Intake-Fragen, fünf Tags sowie die drei Pakete 149/349/699 USD sind
  lokal vollständig vorbereitet.
- Die früheren 45/95/175-USD-Social-Content-Packs bleiben ein separates
  Creator-Ops-Angebot und sind nicht der aktuelle Fiverr-Gig 1.
- Eigenes SFW-Gallery-Cover:
  `docs/assets/fiverr-gig-cover-ai-workflow-automation-v1.png`
  (`1619 × 971`, SHA256
  `3DB079745D6763248A360FFB093E7A5C7964DC0CA936A0F111AFB2700CE3EF9F`).
- Keine Identitäts-, Steuer-, Telefon- oder Businessangabe wurde erfunden oder
  eingetragen. Kein Gig wurde öffentlich erstellt oder veröffentlicht.

## Neues lokales Contentpaket

- Leona „Gym Reset, aber echt“ · Content `1` · fünf reale SFW-Bilder.
- Pose-Matrix vollständig; Top 3 `1 → 2 → 5`; alle Dashboard-Checks grün.
- Owner-Freigabe am 6. September um 18:39 Uhr; am 7. September um 14:19 Uhr
  nativ veröffentlicht und lokal reconciliiert. Publication `9`, Queuejob `4`
  und Content `1` sind jetzt `PUBLISHED`.
- Detailmanifest: `docs/CONTENT_PACKAGE_GYM_RESET_2026-09-06.md`.

## Lokale Review-Evidenz

- Mara „Fünf Minuten Maschinencheck“ · Content `4`: CHANGE um 18:39 Uhr mit
  Hinweis `ist nicht so`, danach REJECT um 18:40 Uhr; final `BLOCKED`.
- Beide Entscheidungen stammen aus `owner-dashboard`. Es wurde weder eine neue
  externe Veröffentlichung noch eine neue Mara-Queue erzeugt.

## Technische Belege

- Runtime: `http://127.0.0.1:4180/`, Health `ok`, Version `1.6.4-beta`.
- SQLite: `integrity_check = ok`, 7 Inhalte, 35 Assets, 9 Publikationen,
  4 Queuejobs.
- Assets: 26 reale Previews und 9 Mock-Slots.
- Tests: letzter vollständiger grüner Stand 133/133; nach dem heutigen
  Reconcile wurde SQLite erneut mit `integrity_check = ok` geprüft.
- `CURRENT_STATE`: offizieller Adapter korrekt als verfügbar beschrieben;
  Live-Zustand hängt von Owner-/Konfigurations-Gates ab.
- Recovery: `backups/Backup_Meilenstein_20260906-1852.zip`, SHA256
  `17df17d6c82fca6a7ca3d2b3c1df29c186c8d513ae694fda37f6695df6e03676`;
  233 Members, ZIP-Test und Sanitized-DB-Integrität grün.
- Kosten und neue Secrets: 0.
