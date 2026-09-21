# Fiverr-Automation in ZippoWorkz

Stand: 21. September 2026

## Architektur

`Creator Ops -> FiverrAutomationService -> ReadProvider / WriteProvider -> SQLite -> /fiverr`

- Der kostenlose Read-Provider liest ausschließlich öffentliche Fiverr-Seiten.
- Der authentifizierte Read-/Write-Weg verwendet den normalen Seller-Webflow.
- Es werden keine privaten oder undokumentierten Fiverr-Endpunkte verwendet.
- Cookies, Sessiondaten, Passwörter, OTPs und KYC-Daten werden weder in SQLite
  noch in Git gespeichert.
- Das optionale PyPI-Paket `fiverr-api` ist kein Kernbestandteil und keine
  Schreibschnittstelle.
- Kostenpflichtige Scraper- oder Proxy-Dienste sind nicht aktiviert.

## Persistenz und Idempotenz

Die additiven Schema-5-Tabellen `fiverr_accounts`, `fiverr_gigs`,
`fiverr_operations` und `fiverr_human_gates` speichern ausschließlich
secret-freie Betriebsdaten. Gig-Slugs und Operation-Fingerprints verhindern
doppelte Gigs und identische Wiederholungsaktionen. Ein Write muss danach
erneut über den normalen Fiverr-Zustand verifiziert werden.

## Live verifizierter Stand

- Seller-Session: `AUTHENTICATED_SELLER`
- Adapterstatus: `WRITE_READY`
- Account: `zippoworkz`
- Aktive Gigs: `1`
- Öffentlicher Gig:
  https://www.fiverr.com/zippoworkz/build-custom-ai-workflow-automations-for-your-business-4-you
- Sichtbare 30-Tage-Werte: 13 Impressionen, 0 Klicks, 0 Orders,
  0 % Stornierungen.
- Die öffentliche Seite ist erreichbar, enthält aber noch Platzhalterdaten:
  Pakete `vgf / fgsg / ghfh`, Preise `50 / 150 / 355 USD`, Lieferzeiten
  `30 / 1 / 1 Tage`, jeweils `0` Revisionen, eine Galerie-Grafik und eine
  Platzhalter-Anforderung.

## Zielkorrektur für Gig 1

Der bestehende Gig wird aktualisiert; es wird kein zweiter Gig erzeugt.

- Basic: 149 USD, 4 Tage, 1 Revision, ein klar definierter Workflow,
  höchstens eine Integration.
- Standard: 349 USD, 7 Tage, 2 Revisionen, höchstens zwei Workflows bzw.
  Integrationen, Reporting oder Light Dashboard.
- Premium: 699 USD, 10 Tage, 3 Revisionen, höchstens drei Workflows,
  drei Integrationen, ein Dashboard und sieben Tage Support.

Die autoritative Copy liegt in `docs/FIVERR_GIG_DRAFT.md`, der Paketvertrag in
`docs/FIVERR_GIG1_PACKAGE_CATALOG.md` und das Intake in
`docs/FIVERR_GIG1_INTAKE.md`.

## Bedienung

- Dashboard: `/fiverr`
- CLI Status: `python -m creator_ops.cli --db data/review_dashboard.db fiverr-status --username zippoworkz`
- Kostenloser öffentlicher Versuch: `fiverr-sync-public`
- Secret-freier authentifizierter Import: `fiverr-sync-snapshot --file <json>`

Der öffentliche HTTP-Read wurde real geprüft und liefert derzeit eine Fiverr-
Challenge. Er bleibt deshalb ehrlich `LIMITED`; die authentifizierte Session
ist der funktionierende Read-/Write-Provider.
