# CODEX RUN - Instagram DM Assistant P0

Stand: 2026-09-29
Branch: `codex/20260929-instagram-dm-p0`
Base: aktuelles `origin/main` ab `686b6a5`

## Owner-Auftrag

Der VPS-/Runner-Unterbau ist jetzt stabil verifiziert. Setze deshalb den in
`docs/INSTAGRAM_DM_ASSISTANT_MVP.md` vorgesehenen ersten Implementierungsschritt
um: sichere Instagram-DM-Inbound-Grundlage im bestehenden Creator-Ops-System.

Dieser Lauf ist read-only nach aussen. Er darf keine Instagram-DM senden,
keinen Support-/PayPal-/Wishlist-/Merch-Link verschicken, keinen Custom-Content
ausliefern und keine Plattform-/Account-Konfiguration veraendern.

## Vor dem Coden vollstaendig lesen

1. `../AGENTS.md` und `AGENTS.md`
2. `../ZIPPOWORKZ_START_HERE.md`
3. `../ZIPPOWORKZ_OWNER_POLICY.md`
4. `CURRENT_HANDOFF.md`
5. `docs/CURRENT_STATE.json`
6. `docs/INSTAGRAM_DM_ASSISTANT_MVP.md`
7. relevante bestehende DB-, Web-, Meta-, Engagement- und Media-Routing-Pfade

Keine historische Vollinventur. Nur aktuelle Pfade und notwendige Abhaengigkeiten.
## Zielbild dieses Laufs

Implementiere nur P0 der DM-Lane:

1. eingehendes DM-Ereignis sicher normalisieren und lokal erfassen;
2. Zielpersona Leona/Mara eindeutig bestimmen;
3. Intent aus den im MVP-Dokument definierten Klassen zuordnen;
4. Safety-/Human-Handoff-Regeln anwenden;
5. Idempotenz gegen doppelte Events sicherstellen;
6. minimal notwendige Conversation-/Event-Daten persistent halten;
7. offene DMs und `NEEDS_HUMAN` im bestehenden Dashboard/API sichtbar machen.

Noch nicht implementieren:
- automatisches Antworten/Senden;
- Preview-/Payment-/Support-/Merch-/Wishlist-Auslieferung;
- Media-Generierung;
- Custom-Content-Lieferung;
- echte Meta-Webhook-Registrierung;
- neue Accounts, neue Secrets oder neue bezahlte Dienste.

## Architekturregeln

- Eine DB: `data/review_dashboard.db`.
- Ein Dashboard: bestehende Creator-Ops-Weboberflaeche.
- Keine zweite Statuswahrheit und keine parallele Conversation-Datenbank.
- Bestehende Meta-/Media-/CurrentState-Komponenten erweitern statt duplizieren.
- Fehlende/unklare Werte bleiben `UNKNOWN`/null bzw. fuehren zu `NEEDS_HUMAN`.
- Keine unnoetigen privaten Daten speichern.
- Keine Secret-Werte in Code, DB, Logs, Tests, Docs oder Git.
## Funktionale Mindestanforderungen

### Inbound / Normalisierung
- Definiere einen provider-sicheren Normalizer fuer ein Instagram-DM-Inbound-Event.
- Externe Event-/Message-ID muss fuer Idempotenz verwendbar sein.
- Unvollstaendige oder nicht eindeutig zuordenbare Events werden fail-closed behandelt.
- Ein echter Netzwerk-Webhook darf in diesem Lauf nicht registriert oder aktiviert werden.
- Testfixtures duerfen ausschliesslich synthetische IDs/Texte enthalten.

### Persona
- Nur die bestehenden Personas `leona-voss` und `mara-field`.
- Zuordnung ueber bekannte Zielkonto-/Persona-Metadaten, nicht ueber freie Modellannahmen.
- Unbekanntes Konto oder Mehrdeutigkeit => `NEEDS_HUMAN`.

### Intent
Mindestens die Klassen aus dem MVP:
`SMALLTALK`, `COMPLIMENT`, `FAQ`, `CONTENT_QUESTION`,
`CUSTOM_REQUEST`, `SUPPORT_INTENT`, `WISHLIST_INTENT`,
`PAYPAL_INTENT`, `MERCH_INTENT`, `COLLAB_OR_BUSINESS`,
`COMPLAINT`, `SAFETY_OR_POLICY`, `NEEDS_HUMAN`.

Fuer P0 reicht eine testbare, deterministische Baseline plus klare Schnittstelle
fuer spaetere Modellklassifikation. Unsicherheit darf nie als sichere Klasse
ausgegeben werden.

### Safety / Handoff
Mindestens die im MVP genannten Human-Handoff-Faelle abdecken:
unklares Alter/minorbezogener sexualisierter Kontext, riskante Sonderwuensche,
Zahlungsstreit/Betrug, Drohung/Stalking, Business/Legal, hohe Geldbetraege,
KYC/Identitaet, Treffen/Adresse/Telefonnummer und Klassifikationsunsicherheit.

## Persistenz

Speichere nur, was fuer den MVP wirklich noetig ist:
- Conversation-/User-Referenz als Plattform-ID;
- Persona;
- letzter Intent;
- Handoff-Status und Grund;
- Event-/Message-ID fuer Idempotenz;
- Timestamps;
- optional notwendiger, begrenzter Nachrichtentext nur wenn die bestehende
  Daten-/Privacy-Architektur das vorsieht.

Bevorzugt bestehende Tabellen/Services erweitern. Falls eine additive
Schemaaenderung wirklich noetig ist:
- aktuelle Owner Policy beachten;
- Migration reversibel und getestet halten;
- keine zweite DB;
- Produktionsdatenbank vor Aenderung sichern;
- Integritaet/FKs danach pruefen.

## Dashboard / API
Im bestehenden Dashboard minimal ergaenzen:
- Anzahl offene DMs;
- Anzahl `NEEDS_HUMAN`;
- Liste der letzten Inbound-Events/Conversations mit Persona, Intent, Status,
  Zeit und Handoff-Grund;
- klar sichtbar: `SEND DISABLED / READ-ONLY P0`.

Keine zweite Seite/App erzwingen, wenn eine vorhandene Operations-/Engagement-
Ansicht sinnvoll erweitert werden kann.

## Tests / Akzeptanz

Mindestens testen:
- Leona- und Mara-Zuordnung;
- unbekannte Persona => Handoff;
- alle relevanten Intent-Klassen;
- Safety-Faelle => `NEEDS_HUMAN`;
- Duplicate Event => kein zweiter Datensatz/Side Effect;
- fehlende Event-ID / kaputtes Payload => fail-closed;
- keine Send-/Publish-/Payment-Aktion erreichbar;
- Dashboard/API zeigt gespeicherte P0-Daten;
- Current State bleibt konsistent;
- SQLite Integritaet und Foreign Keys gruen.

Zusaetzlich:
- relevante Python-Tests;
- Python-Compilecheck;
- Dashboard/Node-Tests falls UI beruehrt;
- JS-Syntaxcheck falls JS beruehrt;
- `git diff --check`;
- Secret-Scan;
- `CURRENT_STATE.json` validieren/aktualisieren, falls der neue P0-Status dort
  hingehoert;
- keine echten Meta-/Instagram-Aufrufe als Testersatz.

## Git-Regeln

Arbeite ausschliesslich auf `codex/20260929-instagram-dm-p0`.
Erhalte bestehende Next-Stack-/TikTok-/Fiverr-/Meta-Funktionalitaet.
Keine alten lokalen VPS-Diffs aus einem anderen Worktree uebernehmen.
Erzeuge sinnvolle Commits und pushe den Branch.
Nicht nach main mergen in diesem Lauf.

## Abschlussdokumentation

Aktualisiere nur die tatsaechlich betroffenen aktuellen Handoff-/State-/Backlog-
Dokumente. Historische Journale nicht umschreiben.

Abschlussbericht genau in dieser Reihenfolge:

### IMPLEMENTED
### DATA / SCHEMA
### SAFETY / FAIL-CLOSED
### DASHBOARD
### TESTS
### COMMITS
### OWNER GATES
### REMAINING DM MVP
### NEXT STEP
## Definition of Done

Der Lauf ist fertig, wenn ein synthetisches eingehendes Instagram-DM-Event
lokal deterministisch einer Persona und einem Intent zugeordnet, idempotent
gespeichert, bei riskantem/unklarem Inhalt an `NEEDS_HUMAN` uebergeben und im
bestehenden Dashboard sichtbar wird - ohne dass irgendeine Nachricht extern
gesendet werden kann.

Danach STOP. Kein automatischer Uebergang zu Reply-, Support-, Payment-,
Preview- oder Delivery-P1.
