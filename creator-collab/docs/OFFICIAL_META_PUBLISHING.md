# Offizieller Instagram-/Meta-Publishing-Pfad

Stand: 6. September 2026 · standardmäßig vollständig deaktiviert

## Sicherheitszustand

Creator Ops veröffentlicht nur, wenn alle folgenden Gates gleichzeitig erfüllt
sind:

1. `config.toml`: `scheduler.dispatch_live = true`
2. `config.toml`: `publishing.adapter = "meta-graph"` und
   `publishing.live_enabled = true`
3. `config.toml`: `capabilities.official_instagram_publish = true` und
   `capabilities.live_external_actions = true`
4. `CREATOR_OPS_PASSWORD` enthält mindestens zwölf Zeichen. Live-Modus startet
   auch auf Loopback niemals ohne Login- und CSRF-Schutz.
5. Instagram-ID und Token sind persona-fest gesetzt:
   `META_IG_USER_ID_LEONA_VOSS` / `META_ACCESS_TOKEN_LEONA_VOSS` sowie
   `META_IG_USER_ID_MARA_FIELD` / `META_ACCESS_TOKEN_MARA_FIELD`.
6. `META_GRAPH_API_VERSION` ist bewusst gesetzt.
7. Ein ignoriertes lokales Medienmanifest enthält für genau drei aktuelle,
   unveröffentlichte Top-Picks öffentliche HTTPS-URLs und die Bestätigung
   `native_ai_disclosure_confirmed = true`.
8. Der Owner hat das konkrete bereits lokal freigegebene Paket über den
   separaten Zweiklick-Button für Live-Versand autorisiert.

Fehlt nur ein Gate, wird der unkonfigurierte Adapter verwendet. Der Scheduler
ruft den Live-Dispatch ebenfalls nur bei der vollständigen Gate-Kombination
auf. Secrets werden weder in Git noch in SQLite, Logs, Exporten oder Backups
gespeichert.

## Lokales Medienmanifest

`config/meta_media_manifest.example.json` nach
`data/meta_media_urls.json` kopieren und ausschließlich lokal ausfüllen. Die
Asset-IDs müssen zu den drei unveröffentlichten Top-Picks des Content-Items
gehören. Creator Ops lädt keine lokale Datei ungefragt auf einen externen Host.
Der Adapter überträgt für KI-Inhalte `is_ai_generated=true` ausschließlich am
Carousel-Parent.

## Verifikations- und Doppelpostschutz

- Drei Child-Container und ein Carousel-Container werden über
  `/{ig_user_id}/media` angelegt.
- Vor dem Publish muss der Carousel-Container `FINISHED` melden.
- Unmittelbar vor `/{ig_user_id}/media_publish` wird ein dauerhafter
  `PUBLISH_INTENT` mit Queue-Key, Container und Persona-Konto gespeichert.
- `PUBLISHED` wird erst gesetzt, wenn Meta eine Medien-ID liefert und eine
  zweite Abfrage dieselbe ID plus gültigen Instagram-HTTPS-Permalink bestätigt.
- Danach wird ein geheimnisfreier `CONFIRMED`-Receipt unter
  `data/meta-receipts/` atomar geschrieben.
- Neuplanung verändert den Queue-Key nicht. Ein alter Intent oder Receipt kann
  daher nicht durch einen neuen Termin umgangen werden.
- Ein nach Prozessabbruch zurückbleibender `PUBLISHING`-Claim wird dauerhaft
  `BLOCKED_EXTERNAL_PUBLISHING`; weder Scheduler noch Owner-Reschedule dürfen
  ihn blind erneut senden.
- Unsicheres Publish-Ergebnis, unbekannte Bestätigung oder fehlgeschlagener
  Receipt-Schreibvorgang verlangt immer manuelle Abstimmung.
- Patch-, Wochen- und Full-Recovery nehmen alle schema-validierten Intents und
  Receipts automatisch mit. Dadurch bleibt der Doppelpostschutz auch nach
  Restore erhalten.

## Manuelle Abstimmung

Bei einem blockierten unsicheren Ergebnis zuerst im offiziellen Instagram-
Konto prüfen, ob der Beitrag existiert. Nur eine sichtbar bestätigte native
Veröffentlichung darf anschließend mit `reconcile-instagram` und ihrem echten
Permalink lokal nachgetragen werden. Wenn kein Post existiert, muss ein späterer
neuer Versuch als bewusste Owner-Entscheidung dokumentiert werden; niemals den
Receipt löschen oder den Queue-Key per Hand ändern.

## Aktueller Owner-Gate

In diesem Run waren weder Meta-Zugangsdaten noch öffentliche Medien-URLs oder
eine Paket-Live-Autorisierung vorhanden. Alle Live-Konfigurationsschalter
blieben `false` beziehungsweise `unconfigured`. Es gab keinen externen Meta-
Aufruf und keinen neuen Instagram-Post.

Offizielle Referenzen:

- Meta Instagram Platform: <https://developers.facebook.com/docs/instagram-platform/content-publishing>
- Offizielle Meta-Instagram-API-Collection: <https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api>
