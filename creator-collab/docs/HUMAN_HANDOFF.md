# Human Handoff — Meta/Instagram Graph Live-Proof

Stand: 7. September 2026, Europe/Berlin

## Aktueller Status

`META_GRAPH_AUTOMATION_PROOF = not_yet_proven`.

Der offizielle Meta-Carousel-Adapter ist lokal implementiert und fail-closed.
Der Read-only-Preflight für Leona Content `1` / Publication `8` wurde ausgeführt
und meldet derzeit `official_instagram_adapter_not_configured`.

## Erledigt

- Instagram-Login-Graph-Host `graph.instagram.com` als Standard konfiguriert;
  Facebook-Login bleibt als dokumentierter Alternativpfad möglich.
- Öffentliche JPEG-URLs für den Testdatensatz vorbereitet und anonym erreichbar
  geprüft (temporärer Quick-Tunnel; nicht als Produktionshosting verwenden).
- Read-only-Preflight prüft Paket, exakt drei unveröffentlichte `PUBLIC_SFW`-
  Top-Picks, HTTPS/JPEG, Persona-Account, Username und Publishing-Quota.
- 17 fokussierte Meta-/Queue-Tests grün.
- Publish-Intent, Queue-Key, Receipt, bestätigte Medien-ID/Permalink und
  Unsicherheits-/Retry-Sperre sind lokal getestet.

## Owner-Gates (vom Owner selbst im Meta-UI bzw. in lokaler Umgebung)

1. Meta for Developers-Konto ist registriert. Im geöffneten Dialog steht als
   nächster Schritt `Verify account`: Der Owner muss seine Mobilnummer eingeben
   und den empfangenen SMS-Code selbst bestätigen.
2. Leona als professionelles Instagram-Konto (Creator oder Business) führen.
3. Eine Meta-App und den offiziellen Instagram-Login-Pfad mit den benötigten
   Berechtigungen einrichten: `instagram_business_basic` und
   `instagram_business_content_publish`.
4. Die echte Instagram User-ID und den kurzlebigen/langlaufenden Access-Token
   ausschließlich lokal als Umgebungsvariablen setzen. Niemals in Git, DB,
   Journal oder Chat eintragen.
5. Vor dem ersten echten Versand den lokalen Preflight ausführen und das
   Ergebnis `READY_FOR_OWNER_CONFIRMATION` bzw. `READY` prüfen.
6. Direkt vor dem öffentlichen Testpost die separate lokale
   `OWNER_LIVE_PUBLISH_APPROVED_UI`-Freigabe für genau Content `1` erteilen.

## Erwartete lokale Variablen

Siehe `.env.example`. Insbesondere werden benötigt:

- `META_IG_USER_ID_LEONA_VOSS`
- `META_ACCESS_TOKEN_LEONA_VOSS`
- `META_GRAPH_API_VERSION` (z. B. `v23.0`, passend zum Meta-Konto)
- optional `META_GRAPH_HOST=graph.instagram.com`
- optional `CREATOR_OPS_META_MEDIA_MANIFEST`

Keine Werte in dieses Dokument kopieren.

## Nach dem Owner-Gate

```text
python -m creator_ops.cli --db data/review_dashboard.db --config config.toml \
  meta-preflight --publication-id 8 --content-id 1
```

Erst bei einem positiven Preflight und einer frischen Owner-Live-Freigabe darf
der bestehende Queue-Dispatch genau dieses Pakets ausführen. Danach müssen
Media-ID, Instagram-Permalink und bestätigter Status in DB/Receipt sichtbar
sein. Bei Timeout oder unklarem Ergebnis nicht automatisch erneut senden;
zuerst über Receipt/Graph reconciliieren.

## Nicht erledigt / nicht behaupten

- Kein echter Meta-Graph-Publish wurde in diesem Lauf ausgeführt.
- Keine Credentials, Tokens oder OTPs wurden gespeichert.
- Kein zweites Paket und kein Creator-Ops-2.0-Feature wurde begonnen.

## Neuer Live-Post — 7. September 2026

- Leona `Gym Reset, aber echt` wurde nativ auf Instagram veröffentlicht:
  `https://www.instagram.com/leonavoss.ai/p/Dc_GwljAKU_/`
- Sichtbare Bestätigung: Instagram meldete `Dein Beitrag wurde geteilt.`;
  Profilstand danach 8 Beiträge.
- Creator Ops wurde lokal abgeglichen: Publication `9`, Content `1`,
  Queuejob `4`, Assets `1`, `2`, `5`.
- Nächste Owner-Aufgabe: sobald verfügbar, echte Insights für diesen Post
  erfassen und in Creator Ops eintragen. Fehlende Werte bleiben `UNKNOWN`.
