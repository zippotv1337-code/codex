# Creator Ops Architecture

## Bestehender Kern

`Content → Assets → QA/Top 3 → Review → Owner Gate → Mock/Manual Publication → Analytics → Learning`

Python-Standardbibliothek, SQLite, statisches Dashboard und lokale
PowerShell-Startskripte bleiben erhalten. Kein Framework-Wechsel.

## Revenue-first-Erweiterung

`ProductPack → AdWorksCampaign → TrackingLink → FunnelEvent → Revenue Board → ProductFeedback`

Schema 4 ist additiv. AdWorks liegt isoliert in `creator_ops/adworks.py`; der
Content-Statusautomat und Publisher wurden nicht verändert. Reale und
synthetische Funnel-Events werden über `is_mock` getrennt. Paid-Spend besitzt
keine ausführbare Methode.

## Background- und Publishing-Delta 1.4

`BackgroundCoordinator` hält Run-Key, Status, Schritt, Cursor,
Kapazitätswartezeit und Fehlerklasse dauerhaft in SQLite. Eine ablaufende
DB-Lease verhindert parallele Läufe und erlaubt Stale-Recovery; jeder Lauf
schreibt ein atomisches Mini-Journal.

Owner-Freigaben erzeugen eine idempotente lokale `publish_queue`. Der Zustand
`LOCAL_SCHEDULED` bedeutet nur, dass Creator Ops den Termin hält. Zur Fälligkeit
wird atomar geclaimt; ein externer Adapter muss den Queue-Key als Idempotency-
Token verwenden. Ohne konfigurierte offizielle Instagram-Schnittstelle endet
der Versuch ehrlich als `BLOCKED_EXTERNAL_PUBLISHING`. Überfällige Termine
werden niemals blind veröffentlicht, sondern `NEEDS_RESCHEDULE_REVIEW`.

## Oberflächen

- `/` Review und große Carousel-Vorschau
- `/control` sichere lokale Control Plane
- `/offer` lokaler Angebotsentwurf
- `/revenue` reales Revenue Board plus expliziter Dry Run
- `/archive`, `/top3`, `/engagement`, `/stories`, `/collections`

Nicht-Loopback-Zugriff nutzt unverändert Passwort, Session und CSRF. Externe
Credentials fehlen dem Kern nicht: Er bleibt im lokalen Dry Run vollständig
testbar.
