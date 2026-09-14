# ZippoWorkz Rights Matrix v2

## Zentrale Rechte

- lokale Dateien: lesen, erstellen, ändern und verschieben; Löschen nur nach Backup
- GitHub: lesen, committen, pushen, Branches und Pull Requests; niemals Repository löschen
- Code: implementieren, reparieren, testen und dokumentieren
- APIs: lesen und schreiben, externe Aktionen nur nach Gates
- Social: ausschließlich Projektaccounts; Entwurf, Preview, Planung und `OWNER_APPROVED`es Publishing
- neue Plattformen: Recherche und Vorbereitung bis zur finalen menschlichen Bestätigung
- Kosten: jede Ausgabe benötigt Owner-Freigabe
- Secrets: Provider/Broker plus Leak-Check vor Push
- Local AI: eigene, strengere `LOCAL_SAFE_ONLY`-Rollenpolicy bleibt verbindlich

## Publishing-Gate

Publishing ist nur zulässig, wenn Inhalt oder Paket `OWNER_APPROVED` ist, der Zielaccount ein ZippoWorkz-Projektaccount ist, Assets und Metadaten zur Freigabe passen, keine Zahlung ausgelöst wird, kein Secret-Leak vorliegt und kein sensibler oder unklarer Fall markiert ist.

Andernfalls gilt `NEEDS_OWNER_ACTION`.

## Milo der Zug / TikTok P0

Milo ist lokal als fiktive KI-Creator-Marke definiert. Instagram und TikTok bleiben bis zu einer echten Verbindung `NOT_CONNECTED`. TikTok unterstützt lokal eine 9:16-Preview; `DRAFT_UPLOAD` und `DIRECT_POST` sind getrennte Zustände. Direct Post benötigt reales Asset, verbundenen Projektaccount und Owner-Freigabe. Es ist in diesem P0 kein Plattformtransport aktiviert.
