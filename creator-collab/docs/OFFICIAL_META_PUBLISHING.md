# Offizieller Instagram-/Meta-Publishing-Pfad

Stand: 5. September 2026 · standardmäßig vollständig deaktiviert

## Sicherheitszustand

Creator Ops veröffentlicht nur, wenn alle folgenden Gates gleichzeitig erfüllt
sind:

1. `config.toml`: `scheduler.dispatch_live = true`
2. `config.toml`: `publishing.adapter = "meta-graph"` und
   `publishing.live_enabled = true`
3. `config.toml`: `capabilities.official_instagram_publish = true` und
   `capabilities.live_external_actions = true`
4. `CREATOR_OPS_PASSWORD` ist gesetzt; Live-Modus startet auch auf Loopback
   niemals ohne Login- und CSRF-Schutz
5. Instagram-ID und Token sind persona-fest gesetzt:
   `META_IG_USER_ID_LEONA_VOSS` / `META_ACCESS_TOKEN_LEONA_VOSS` sowie
   `META_IG_USER_ID_MARA_FIELD` / `META_ACCESS_TOKEN_MARA_FIELD`
6. `META_GRAPH_API_VERSION` ist gesetzt
7. ein ignoriertes lokales Medienmanifest enthält für genau drei aktuelle
   Top-Picks öffentliche HTTPS-URLs und die ausdrückliche Bestätigung
   `native_ai_disclosure_confirmed = true`
8. der Owner hat das konkrete bereits lokal freigegebene Paket über den
   separaten Zweiklick-Button für Live-Versand autorisiert

Fehlt nur ein Gate, wird der unkonfigurierte Adapter verwendet. Secrets werden
weder in Git noch in SQLite, Logs, Exporten oder Backups gespeichert.

## Lokales Medienmanifest

`config/meta_media_manifest.example.json` nach
`data/meta_media_urls.json` kopieren und ausschließlich lokal ausfüllen. Die
Asset-IDs müssen zu den drei unveröffentlichten Top-Picks des Content-Items
gehören. Creator Ops lädt keine lokale Datei ungefragt auf einen externen Host.
Der Manifestwert ist ein zusätzlicher Owner-Gate. Der Adapter überträgt für
KI-Inhalte außerdem `is_ai_generated=true` ausschließlich am Carousel-Parent.

## Verifikations- und Doppelpostschutz

- Drei Child-Container und ein Carousel-Container werden über
  `/{ig_user_id}/media` angelegt.
- Vor dem Publish muss der Container `FINISHED` melden.
- Unmittelbar vor `/{ig_user_id}/media_publish` wird ein dauerhafter
  `PUBLISH_INTENT` gespeichert. Bleibt er nach Absturz oder unklarem Ergebnis
  zurück, ist jeder automatische Wiederholungsversuch gesperrt und eine
  manuelle Abstimmung nötig.
- `PUBLISHED` wird erst gesetzt, wenn Meta eine Medien-ID liefert und eine
  zweite Abfrage eine passende Instagram-HTTPS-Permalink-Bestätigung ergibt.
- Danach wird lokal ein geheimnisfreier Receipt unter `data/meta-receipts/`
  geschrieben. Derselbe Queue-Key liefert bei einem Neustart diesen Beleg
  zurück und sendet keinen zweiten Publish.
- Ist das Ergebnis des eigentlichen Publish-Aufrufs, der Bestätigung oder der
  Receipt-Speicherung
  unklar, wird die Queue blockiert und verlangt manuelle Verifikation. Es gibt
  keinen automatischen Blind-Retry.

## Aktueller Owner-Gate

In diesem Run waren weder Meta-Zugangsdaten noch ein Medienmanifest vorhanden;
außerdem wurde kein bestehendes Paket separat für Live-Versand autorisiert.
Deshalb wurde nur mit einem vollständig lokalen Fake-Transport getestet und
keine externe Anfrage gesendet. Das Aktivieren der drei Konfigurationswerte ist
eine separate Live-Freigabe, keine normale technische Voreinstellung.
