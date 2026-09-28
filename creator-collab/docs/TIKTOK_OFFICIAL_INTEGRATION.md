# Offizielle TikTok-Integration

Stand: 2026-09-28  
Status: technisch vorbereitet, kein Live-Proof und kein externer Post in diesem Run

## Umfang

ZippoWorkz verwendet ausschließlich TikToks offizielle OAuth-v2- und Content-
Posting-v2-Wege. Tokens liegen nur im node-lokalen DPAPI Secret Broker. DB,
Logs, API-Antworten, Handoffs und Git enthalten weder Token noch Client Secret.

Unterstützt sind:

- state-geschützter OAuth-Start, Code Exchange und Refresh-Rotation;
- Creator-Info als zwingender Preflight vor Draft oder Direct Post;
- `FILE_UPLOAD` und `PULL_FROM_URL`;
- Draft-Upload (`video.upload`) und Direct Post (`video.publish`);
- Creator-Constraints für Privacy, Kommentare, Duet, Stitch und Videolänge;
- AIGC-Kennzeichnung im Direct-Post-Payload;
- persistente Publish-Intents, Idempotenz und Status-Reconciliation;
- secret-free Readiness im bestehenden Dashboard.

## Sicherheits- und Retry-Vertrag

1. OAuth-State wird nur als SHA-256-Hash gespeichert und vor dem Token-
   Exchange atomar verbraucht.
2. Der Secret Broker schreibt Metadaten/Refresh-Token zuerst und den Access-
   Token zuletzt als lokalen Commit-Marker.
3. Vor einem Direct Post wird der verbundene Creator gelesen und mit dem
   erwarteten Account verglichen.
4. Ein Intent wird vor dem externen Initialisierungsaufruf geschrieben.
5. Bei unbekanntem Ergebnis bleibt er `RECONCILE_REQUIRED`; der gleiche
   Idempotency-Key sendet nicht blind erneut.
6. Nach einer erfolgreichen Initialisierung wird die `publish_id` vor dem
   Datei-Upload gespeichert. Ein abgebrochener Upload bleibt dadurch
   rekonstruierbar.
7. `PUBLISH_COMPLETE` wird ausschließlich aus TikToks Status-Endpunkt
   übernommen. ZippoWorkz erfindet keine externe Post-ID.

## Kosten- und Veröffentlichungsgrenze

Der Adapter selbst verursacht in diesem Run keine Kosten. Es wurden keine
Credentials angelegt, kein OAuth-Consent durchgeführt und kein TikTok-Inhalt
veröffentlicht. Direct Post wird erst nutzbar, wenn App-Konfiguration,
registrierter HTTPS-Redirect und die nötigen Scopes im Secret Broker vorhanden
sind. Nicht auditierte TikTok-Clients können plattformseitig auf private
Sichtbarkeit begrenzt sein; ZippoWorkz überschreibt die vom Creator-Info-
Endpunkt gelieferten Optionen nicht.

## Ein gebündeltes Owner-Gate

Wenn Readiness `READY_FOR_OWNER_OAUTH` meldet, ist genau eine persönliche
Aktion nötig: den von ZippoWorkz vorbereiteten TikTok-OAuth-Dialog öffnen und
die angezeigten Scopes für den richtigen Projektaccount bestätigen. Danach
speichert der Callback die Tokens im Secret Broker und der technische Lauf kann
ohne erneute Eingabe fortgesetzt werden. App-Freigabe, URL-Verifikation, OTP
oder KYC bleiben nur dann Owner-Gates, wenn TikTok sie tatsächlich verlangt.

## Operator-Schnittstellen

- `tiktok-oauth-begin`
- `tiktok-oauth-refresh`
- `tiktok-creator-info`
- `tiktok-video-init`
- `tiktok-reconcile`
- `external-readiness`

Alle Ausgaben sind secret-free. Ein echter Direct Post benötigt zusätzlich
einen stabilen Idempotency-Key, den erwarteten Account, expliziten Consent im
Auftrag und die von Creator Info erlaubten Optionen.

