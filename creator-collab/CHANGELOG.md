# Changelog

## 1.6.4-beta — 2026-09-05

- Standalone-Betrieb läuft über einen einzelnen Supervisor mit Watchdog,
  Scheduler, Morning Run, read-only Offline-Snapshot und benutzereigenem
  Windows-Autostart; Live-Dispatch bleibt standardmäßig deaktiviert.
- Offizieller Meta-Graph-Adapter für Instagram-Carousels ergänzt: öffentliche
  HTTPS-Asset-URLs, persona-feste Kontozuordnung, `is_ai_generated=true` am
  Carousel-Parent, drei Top-Picks, Containerprüfung und echte ID-/Permalink-
  Bestätigung sind Pflicht.
- Lokales APPROVE ist keine Live-Freigabe: ein separater auditierter
  Zweiklick-Schritt autorisiert immer nur das konkrete Paket.
- Ein dauerhafter Publish-Intent wird vor `media_publish` geschrieben.
  Unsichere Ausgänge blockieren automatische Wiederholungen; bestätigte
  Receipts verhindern Doppelposts nach einem lokalen Neustart.
- Live-Konfiguration erzwingt selbst auf Loopback den Passwort-/CSRF-Schutz.
- Überfällige Queuejobs erhalten einen expliziten Owner-Button zum Übernehmen
  des vorgeschlagenen neuen Termins; die Aktion bleibt rein lokal.
- GPT-6 Astra HIGH ist als optionaler bevorzugter Capability-Pfad hinterlegt;
  GPT-5.6 Sol und der Runtime-Default bleiben funktionsfähige Fallbacks.
- Keine Live-Veröffentlichung, kein Fiverr-Formular und keine externe
  Accountaktion wurden in diesem lokalen Implementierungslauf ausgeführt.

## 1.4.1 — 2026-09-05

- Reviewkarten verwenden den autoritativen lokalen Queue-Termin; alte native
  Datumseinträge können keine falsche `00:00`-Prime-Time mehr erzeugen.
- Produktive Reviewpakete werden anhand realer, unveröffentlichter Assets
  ausgewählt statt durch ein globales Veröffentlichungsdatum ausgeblendet.
- Der Musikcheck akzeptiert nur geprüfte Lizenzzustände und repariert echte
  Ohne-Musik-Fallbacks additiv auf `SAFE_NO_AUDIO`.
- Publish-Queue und Publication bleiben bei Blockierung, Retry und notwendiger
  Neuplanung konsistent; Retry bleibt innerhalb des Terminfensters und
  DST-sichere Vorschläge liegen garantiert in der Zukunft.
- Top-3 vergibt ohne reale Analytics keine Scheinaränge mehr; betroffene
  Veröffentlichungen erscheinen ehrlich als `INSUFFICIENT_DATA`.
- Archivvorschauen bevorzugen das tatsächlich veröffentlichte Asset.
- Mobile Reviewstatus bleiben sichtbar; abgebrochene CHANGE/REJECT-Dialoge
  senden keine Entscheidung.
- CHANGE/REJECT verwenden einen eigenen responsiven Owner-Dialog statt des im
  eingebetteten Browser nicht unterstützten `window.prompt()`.
- Background-Leases werden während langer Tasks per Heartbeat erneuert;
  Kapazitäts-Wartezeiten und verlorene Ownership bleiben konsistent.
- Statischer read-only Offline-Snapshot und owner-gegatete Standalone-Skripte
  für Scheduler/Watchdog sind vorbereitet, aber nicht installiert.
- 96 Tests, Python-Compilecheck, 9 JavaScript-Syntaxchecks sowie echter
  SQLite-Backup-/Restore-Check grün.

## 1.4.0 — 2026-09-05

- Additive Schema-Version 5 mit dauerhafter lokaler Publish Queue sowie
  Background-Run-, Lease- und strukturierten Runtime-Events.
- Owner-Freigabe führt zu `LOCAL_SCHEDULED`; ohne offiziellen Instagram-
  Adapter wird niemals ein externer Termin oder Publish-Erfolg behauptet.
- Atomarer Queue-Claim, Idempotency-Key, Stale-Recovery, Retry-Metadaten und
  Review-Pfad für überfällige Slots.
- 05:30-Morning-Run über den bestehenden Fünfer-Review-Flow, idempotent und
  kapazitätsfähig.
- `WAITING_FOR_CAPACITY`, DB-Lease, Fehlerklassifikation und Mini-Journal für
  sichere Autopilot-Fortsetzung.
- Manifestierte Patch-Backups mit echter Member-Hashprüfung; Full nur noch bei
  begründetem Meilenstein.
- Leichte interne `mz_poke`-Experimentmarkierung mit SFW-/Persona-/Mix-Gates,
  ohne rückwirkende Markierung oder Kopieren fremder Inhalte.
- Human Handoff auf eine einzige kurze Owner-Inbox konsolidiert.

## 1.3.0 — 2026-09-05

- Revenue-first SFW-Pack-Katalog mit klaren Owner-Gates für Preis, Lieferung,
  Revisionen, Rechte und Veröffentlichung.
- Additive Schema-Version 4 für Product Packs, AdWorks-Kampagnen,
  Tracking-Links, Funnel-Events und Product Feedback.
- Idempotenter, vollständig lokaler AdWorks-Akzeptanztest von Pack bis
  synthetischem Revenue/Feedback; reale und Mock-Werte bleiben getrennt.
- Lokale Angebotsseite `/offer` und Revenue Board `/revenue`; Paid Spend ist
  nicht ausführbar.
- Modellagnostische Control Plane um AdWorks-Fähigkeiten ergänzt.
- Robuster, PID-/CommandLine-geprüfter Stop-/Restart-Pfad für Windows.
- Fiverr-, Intake-, Fulfillment-, Launch- und Produkt-Learning-Unterlagen als
  veröffentlichungsfertiger Entwurf ohne erfundene Preise.

## 1.2.0 — 2026-09-04

- Additive Schema-Version 3 für owner-bestätigte native Veröffentlichungen.
- Append-only manuelle Analytics für 24 h, 72 h und 7 Tage.
- Archiv- und Top-3-API sowie mobile Dashboard-Navigation.
- Gewichtetes Ranking: Saves 25, Shares 20, Comments 15, Profile Visits 15,
  Follows 10, Link Clicks 10, Likes 5; Raten haben Vorrang, sobald Reach oder
  Views vorliegen.
- Secret-freie Wochen- und Monats-Recovery-ZIPs mit Manifest, SHA256 und
  SQLite-Integritätsprüfung.
- LAN-Start mit automatischer Windows-Netzerkennung und verpflichtendem
  Passwort; optionale Firewall-Freigabe bleibt explizit.
- Zwei bereits owner-bestätigte Instagram-Posts lokal und idempotent als
  `instagram-native-manual` abgeglichen.

## 1.1.0 — 2026-09-04

- Safety-/Visibility-Trennung, Content-Mix, Pose-Matrix, diverse Top 3,
  geschützte Previews, dynamischer Status und optionaler Remote-Testmodus.
