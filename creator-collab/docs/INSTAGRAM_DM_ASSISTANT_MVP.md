# Instagram DM Assistant MVP

Status: P0 INBOUND IMPLEMENTED ON `codex/20260929-instagram-dm-p0`; P1+ BACKLOG
Owner intent: Instagram soll nicht nur posten, sondern eingehende DMs beantworten, Wünsche erkennen, passende Support-/Wishlist-/Merch-Flows anbieten und Sonderwünsche kontrolliert in Content-/Media-Jobs überführen.

## Ziel

Ein DM-System für Leona und Mara, das:
- normale Gespräche freundlich und persona-gerecht führt;
- FAQ und einfache Fragen selbst beantwortet;
- Wunschcontent erkennt;
- passende, nicht aufdringliche Support-/Wishlist-/Merch-Hinweise geben kann;
- bei geeigneten Wünschen einen Preview-/Custom-Content-Flow startet;
- unklare, riskante oder sensible Fälle an den Owner übergibt;
- alle wichtigen Schritte im bestehenden Dashboard sichtbar macht;
- keine zweite Datenbank und kein zweites Dashboard einführt.

## Grundprinzip

Conversation first, conversion second.

Der Bot soll nicht jede Nachricht monetarisieren. Erst Gespräch und Bedarf verstehen, dann nur bei echtem Anlass einen passenden CTA setzen.

Kein Druck, keine falsche Knappheit, keine falschen Versprechen, keine erfundene persönliche Beziehung.

Leona und Mara bleiben fiktionale erwachsene AI-basierte Personas. Der Bot darf persona-gerecht schreiben, aber keine reale menschliche Identität, echte Treffen, echte persönliche Erlebnisse oder reale Beziehungen vortäuschen.

## Intent-Klassen

Mindestens:
- SMALLTALK
- COMPLIMENT
- FAQ
- CONTENT_QUESTION
- CUSTOM_REQUEST
- SUPPORT_INTENT
- WISHLIST_INTENT
- PAYPAL_INTENT
- MERCH_INTENT
- COLLAB_OR_BUSINESS
- COMPLAINT
- SAFETY_OR_POLICY
- NEEDS_HUMAN

## Beispiel-Logik

### Kompliment / Smalltalk

User: "Hey, ich finde dich süß."

Leona-Stil:
"Danke dir 😘 Was gefällt dir bei mir eigentlich mehr – die entspannten Alltagsbilder oder eher die Gym-/Fashion-Vibes?"

Mara-Stil:
"Ach, das ist lieb 😄 Was magst du lieber – Hof-/Werkstatt-Vibes oder eher die ruhigeren Bilder?"

Ziel: Gespräch öffnen, nicht sofort verkaufen.

### Wunschcontent

User: "Kannst du mal ein Bild mit schwarzer Leggings und Spiegelselfie machen?"

Antwortlogik:
1. Wunsch erkennen.
2. Prüfen, ob der Wunsch in die erlaubte Content-Klasse passt.
3. Wenn passend:
   - Wunsch kurz bestätigen;
   - optional Preview/Idee anbieten;
   - bei personalisiertem Sonderwunsch dezent Support erwähnen.

Beispiel:
"Die Idee passt richtig gut 😘 Ich kann sowas als Wunschidee einplanen. Wenn du magst, kann ich dir vorher eine kleine Preview machen – und wenn du etwas ganz Persönliches willst, kannst du mich über meinen Support-Link unterstützen."

### Direkte Supportfrage

User: "Wie kann ich dich unterstützen?"

Antwort:
"Voll lieb von dir 💕 Wenn du möchtest, kannst du mich über meinen freigegebenen Support-/Wishlist-Link unterstützen. Wenn du dabei einen Wunsch hast, schreib ihn einfach direkt dazu."

Nur Owner-freigegebene Links verwenden.

## Preview-Flow

Preview ist optional und darf nur eingesetzt werden, wenn:
- der Wunsch technisch erzeugbar ist;
- keine zusätzlichen Kosten ohne Freigabe entstehen;
- der Inhalt in der zulässigen Lane liegt;
- der Bot keine Lieferung verspricht, die nicht zuverlässig erfüllt werden kann.

Mögliche Preview-Form:
- Wasserzeichen;
- kleinere Auflösung;
- Ausschnitt;
- Moodboard/Prompt-Konzept;
- ein allgemeiner Teaser statt personalisierter Vollversion.

Preview niemals als Täuschung verwenden.

## Paid / Support Flow

MVP unterstützt nur klar definierte Owner-freigegebene Ziele:
- PayPal.Me
- Amazon Wishlist
- Merch-Link
- später weitere freigegebene Plattformen

Regeln:
- Links ausschließlich aus zentraler Config/Secret-/Link-Registry;
- niemals Links aus einer User-DM ungeprüft übernehmen;
- nie behaupten, eine Zahlung sei angekommen, solange sie nicht verifiziert wurde;
- Custom-Content erst als PAID_CONFIRMED markieren, wenn Zahlungsstatus tatsächlich verifiziert ist;
- keine automatische Rückerstattung oder finanzielle Zusage ohne Owner-Gate;
- keine künstliche Verknappung oder Schuld-/Drucksprache.

## Custom-Request Pipeline

DM -> Intent -> Safety Check -> Persona Check -> Request Record -> Quote/Support Option -> optional Preview -> Payment/Support Evidence -> Media Job -> QA -> Delivery -> Conversion Event

Statusvorschlag:
- RECEIVED
- QUALIFIED
- PREVIEW_READY
- WAITING_SUPPORT
- SUPPORT_CONFIRMED
- MEDIA_PLANNED
- MEDIA_READY
- QA_READY
- DELIVERED
- CLOSED
- NEEDS_HUMAN

Die Umsetzung soll bestehende Creator-Ops-/Media-Routing-Strukturen erweitern, nicht daneben neu bauen.

## Safety / Human Handoff

Automatisch an NEEDS_HUMAN bei:
- unklarem Alter oder minderjährigenbezogenem sexualisiertem Kontext;
- expliziten oder riskanten Sonderwünschen außerhalb der freigegebenen Content-Lane;
- Zahlungsstreit, Chargeback, Betrugsverdacht;
- Drohungen, Erpressung, Stalking;
- rechtlichen/geschäftlichen Kooperationen;
- ungewöhnlich hohen Geldbeträgen;
- Identitäts-/KYC-/Accountfragen;
- Wunsch nach echten Treffen, Adresse, Telefonnummer oder privaten Realwelt-Daten;
- Unsicherheit des Modells.

Default Instagram-Lane bleibt platform-suitable / non-explicit.

## Conversation Memory

Pro Conversation nur notwendige Daten:
- IG conversation/user identifier;
- Persona;
- letzter Intent;
- letzter Bot-Schritt;
- bereits gesendete Links;
- aktiver Custom Request;
- Handoff-Status;
- Conversion-/Outcome-Events;
- Timestamps.

Keine unnötigen privaten Daten speichern.

## Anti-Spam / Anti-Duplicate

- keine ungefragten Massen-DMs;
- keine wiederholten Zahlungs-CTAs nach Ablehnung;
- idempotente Antwort-Events;
- keine identische Antwort mehrfach;
- Rate-Limit;
- bei API-Unsicherheit reconcile statt blind retry.

## Dashboard

Im bestehenden Dashboard ergänzen:
- offene DMs;
- NEEDS_HUMAN;
- Custom Requests;
- Preview Ready;
- Waiting Support;
- Support Confirmed;
- Delivered;
- häufige Intents;
- Links sent;
- Conversions;
- durchschnittliche Antwortzeit;
- Bot/Human Anteil.

Keine zweite Dashboard-App.

## Analytics / Learning

Messen:
- DM received
- DM replied
- conversation continued
- custom request detected
- support link sent
- preview sent
- support confirmed
- custom content delivered
- conversion
- handoff

Erfolg nicht nur an Umsatz messen:
- Antwortquote
- Gesprächslänge
- Handoff-Rate
- Block-/Complaint-Signale
- Conversion pro Intent
- Kosten pro Custom Request

Keine erfundenen Zahlen.

## 10 MVP-Antworttypen

1. Begrüßung
2. Kompliment
3. Smalltalk
4. Content-Frage
5. Wunschcontent
6. Support/Wishlist
7. Merch
8. Preview-Angebot
9. Human-Handoff
10. höfliches Ende / kein Interesse

## 5 Monetarisierungs-Flows

1. Custom Image Request -> optional Preview -> Support -> Lieferung
2. Wunsch für nächsten Post -> Support -> Priorisierung
3. Wishlist Intent -> freigegebener Wishlist-Link
4. PayPal Intent -> freigegebener PayPal.Me-Link
5. Merch Intent -> freigegebener Merch-Link

## Produktbeschreibung ZippoWorkz

"ZippoWorkz Instagram DM Assistant beantwortet eingehende Nachrichten, erkennt Fragen und Content-Wünsche, führt Interessenten durch freigegebene Support-, Wishlist- oder Merch-Flows und übergibt sensible Fälle an einen Menschen. Custom-Content kann vom Wunsch über Preview und Freigabe bis zur Auslieferung im bestehenden Creator-Ops-System verfolgt werden."

## Definition of Done für MVP

- Instagram DM inbound event wird sicher empfangen;
- Persona wird korrekt zugeordnet;
- Intent wird klassifiziert;
- 10 Antworttypen funktionieren;
- 5 Monetarisierungs-Flows sind konfigurierbar;
- nur freigegebene Links können gesendet werden;
- Custom Request kann als Media Job bis QA_READY übergeben werden;
- NEEDS_HUMAN ist im Dashboard sichtbar;
- Duplicate/Retry-Schutz vorhanden;
- Conversation/Conversion Events werden gespeichert;
- keine zweite DB / kein zweites Dashboard;
- keine externen Kosten ohne Owner-Gate;
- Tests für Routing, Safety, Links, Idempotenz und Handoff grün.

## Reihenfolge

Erst P0 / Runner / Insights stabilisieren.

Danach:
1. DM inbound + read-only logging
2. Intent + persona response
3. Handoff
4. approved links
5. custom request pipeline
6. preview flow
7. payment/support verification adapter
8. delivery + analytics

## Implementierungsgrenze P0 — 29. September 2026

Der Branch `codex/20260929-instagram-dm-p0` implementiert ausschließlich Schritt
1 bis zur lokalen Sichtbarkeit: Normalisierung, exakte Persona-Zuordnung,
deterministische Intent-Baseline, Safety-/Human-Handoff, Idempotenz und
Persistenz in der kanonischen Creator-Ops-Datenbank. Der bestehende
Nachrichtenbereich zeigt offene DMs und `NEEDS_HUMAN`.

Nicht enthalten und technisch nicht erreichbar sind Antworten/Senden,
freigegebene Links, Custom Requests, Preview, Payment/Support, Media-Jobs,
Delivery und echte Meta-Webhook-Registrierung. Diese bleiben P1+.
