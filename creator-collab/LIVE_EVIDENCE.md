# Live Evidence

Stand: 2026-09-06T13:34:00+02:00 · Europe/Berlin

## Instagram

- **Konkreter Pilot:** `LIVE_NATIVE_OWNER_CONFIRMED`
- **Offizielle API-Automation:** `LIVE_READY_WAITING_FOR_OWNER_CONFIG`
- **INSTAGRAM_AUTOMATION_PROOF:** 0/10; der Pilot lief nativ im Browser und
  ist kein Beweis für einen Meta-Graph-Autopublish.
- **Live in diesem Run:** 1 Carousel / 3 Bilder
- **Lokaler Modus:** `local-mock`; der offizielle Adapter ist vorhanden, aber
  Credentials, öffentliche HTTPS-Asset-URLs und globale Live-Gates bleiben aus.
- **Queue:** 2 × `LOCAL_SCHEDULED`, 1 × `PUBLISHED`.

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

- **Status:** `FIVERR_LAUNCH_READY_WAITING_FOR_OWNER`
- Das eingeloggte Konto zeigt `Create your profile`; ein echtes
  Verkäuferprofil existiert noch nicht.
- Texte, FAQ, Requirements, Tags, drei Pakete, Startpreise, Lieferzeiten,
  Revisionen und Nutzungsgrenzen sind lokal vollständig vorbereitet.
- Eigenes SFW-Gallery-Cover:
  `output/fiverr-gallery/fiverr-gig-cover-ai-social-content-pack.png`
  (`1618 × 972`, SHA256
  `3B3AAE177961792F7F24EF6A0A4A774E78BD6D24A0C5C26475B9E7FD66E5AD57`).
- Keine Identitäts-, Steuer-, Telefon- oder Businessangabe wurde erfunden oder
  eingetragen. Kein Gig wurde öffentlich erstellt oder veröffentlicht.

## Neues lokales Contentpaket

- Leona „Gym Reset, aber echt“ · Content `1` · fünf reale SFW-Bilder.
- Pose-Matrix vollständig; Top 3 `1 → 2 → 5`; alle Dashboard-Checks grün.
- Status `READY_FOR_REVIEW`; weder lokal freigegeben noch extern veröffentlicht.
- Detailmanifest: `docs/CONTENT_PACKAGE_GYM_RESET_2026-09-06.md`.

## Technische Belege

- Runtime: `http://127.0.0.1:4180/`, Health `ok`, Version `1.6.4-beta`.
- SQLite: `integrity_check = ok`, 6 Inhalte, 30 Assets, 7 Publikationen,
  3 Queuejobs.
- Assets: 26 reale Previews und 4 Mock-Slots.
- Tests: 117/117 grün; Python-Compilecheck grün.
- `CURRENT_STATE`: offizieller Adapter korrekt als verfügbar beschrieben;
  Live-Zustand hängt von Owner-/Konfigurations-Gates ab.
- Kosten und neue Secrets: 0.
