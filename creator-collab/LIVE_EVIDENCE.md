# Live Evidence

Stand: 2026-09-06T18:50:00+02:00 · Europe/Berlin

## Instagram

- **Konkreter Pilot:** `LIVE_NATIVE_OWNER_CONFIRMED`
- **Offizielle API-Automation:** `LIVE_READY_WAITING_FOR_OWNER_CONFIG`
- **INSTAGRAM_AUTOMATION_PROOF:** 0/10; der Pilot lief nativ im Browser und
  ist kein Beweis für einen Meta-Graph-Autopublish.
- **Live in diesem Run:** 1 Carousel / 3 Bilder
- **Lokaler Modus:** `local-mock`; der offizielle Adapter ist vorhanden, aber
  Credentials, öffentliche HTTPS-Asset-URLs und globale Live-Gates bleiben aus.
- **Queue:** 3 × `LOCAL_SCHEDULED`, 1 × `PUBLISHED`.

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
- Owner-Freigabe am 6. September um 18:39 Uhr: Publication `8`, Queuejob `4`,
  Status `LOCAL_SCHEDULED` für den 7. September 19:30 Uhr. Keine externe
  Veröffentlichung.
- Detailmanifest: `docs/CONTENT_PACKAGE_GYM_RESET_2026-09-06.md`.

## Lokale Review-Evidenz

- Mara „Fünf Minuten Maschinencheck“ · Content `4`: CHANGE um 18:39 Uhr mit
  Hinweis `ist nicht so`, danach REJECT um 18:40 Uhr; final `BLOCKED`.
- Beide Entscheidungen stammen aus `owner-dashboard`. Es wurde weder eine neue
  externe Veröffentlichung noch eine neue Mara-Queue erzeugt.

## Technische Belege

- Runtime: `http://127.0.0.1:4180/`, Health `ok`, Version `1.6.4-beta`.
- SQLite: `integrity_check = ok`, 6 Inhalte, 30 Assets, 8 Publikationen,
  4 Queuejobs.
- Assets: 26 reale Previews und 4 Mock-Slots.
- Tests: 119/119 grün; Python-Compilecheck grün.
- `CURRENT_STATE`: offizieller Adapter korrekt als verfügbar beschrieben;
  Live-Zustand hängt von Owner-/Konfigurations-Gates ab.
- Recovery: `backups/Backup_Meilenstein_20260906-1852.zip`, SHA256
  `17df17d6c82fca6a7ca3d2b3c1df29c186c8d513ae694fda37f6695df6e03676`;
  233 Members, ZIP-Test und Sanitized-DB-Integrität grün.
- Kosten und neue Secrets: 0.
