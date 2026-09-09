# ZippoWorkz — sicherer lokaler Hintergrundbetrieb

Stand: 2026-09-09. Kein neuer Core, keine neue DB, kein zweites Dashboard.
Lane A abgeschlossen; Lane B WAITING_SIGNAL. Alle übrigen Lanes warten.

## Was unabhängig von Codex läuft

| Treiber | Aufgabe | Zeitpunkt / Grenze |
|---|---|---|
| Vorhandener Benutzer-Autostart | ein Supervisor + ein Backend | nach Windows-Anmeldung |
| Vorhandener Supervisor | Watchdog | alle 5 Minuten, 30 Sekunden Backoff, höchstens 3 Startversuche je 30 Minuten |
| Vorhandener Supervisor | lokaler Idle-Lauf | alle 5 Minuten, genau ein Durchlauf, danach Ende |
| Creator Ops - Daily Healthcheck | kompakter Healthcheck | täglich 02:45, verpassten Lauf nachholen |
| CreatorOps Weekly Recovery | Wochenbackup prüfen/bei Fälligkeit erstellen | täglich 03:00; höchstens ein valides Archiv pro ISO-Woche |
| CreatorOps Monthly Full Recovery | Monatsbackup prüfen/bei Fälligkeit erstellen | täglich 03:30; höchstens ein valides Archiv pro Kalendermonat |

Tasks verwenden den angemeldeten Benutzer mit begrenzten Rechten, kein gespeichertes
Passwort. PC muss an sein, Benutzer angemeldet; Schlaf/Ausgeschaltet ist kein
24/7-Betrieb. Kaltstart und wochen-/monatelanger Dauerlauf sind noch nicht beobachtet.
Kein zweiter Scheduler-/Watchdog-Windows-Task: deren einziger Treiber ist der
bestehende Supervisor. Gleichzeitige Wartungsaufrufe werden per Betriebssystem-Lock
ausgeschlossen; Windows-Tasks verwenden IgnoreNew.

Idle führt nur fällige Health-/Recovery-Arbeit aus. Er erzeugt keine neuen Inhalte,
keine synthetischen Analytics, Kommentare oder Nachrichten und sucht keine Arbeit.
Ohne Fälligkeit: IDLE_CLEAN und Ende. Fehlerzustände werden lokal mit Zeitpunkt
gemeldet. Keine automatische Meta-Verifizierung, kein Git, keine Plattformänderung.
Der Scheduler enthält keinen ausführbaren externen Dispatch-Pfad, auch nicht hinter
einem Konfigurationsschalter. Manuelle/gesondert autorisierte offizielle Adapter
bleiben getrennt davon fail-closed.

## Recovery

Bestehender RecoveryBackupService, kein zweites Backupsystem. Ziel: Projekt/backups.
SQLite online-backup statt ungesicherter Dateikopie; secret_reference wird in der
Kopie entfernt. Manifest, Member-SHA256, ZIP-Integrität und extrahierte DB werden
validiert. Keine VENV, Git-Daten, Schlüssel, Token-/Passwortdateien, DB-WAL/SHM,
Logs oder temporären Dateien. Meta-Sicherheitsreceipts bleiben schema-geprüft erhalten.
Historische defekte Backups werden nicht gelöscht und nur als Warnung gezählt;
aktive DB-Integritätsfehler liefern ERROR und verhindern neue Recovery-Archive.

Lokale Receipts: data/local_ops_status.json, data/watchdog_state.json,
data/runtime_tasks_status.json und sessions/runtime/local-ops-*.json.
Diese Dateien werden nicht nach Git synchronisiert. /control zeigt ihre Zeitpunkte.

## Stoppen und deaktivieren

- Dashboard /control → Pausieren: Wartung und Watchdog bleiben beim nächsten
  Aufruf PAUSED; ein bereits begonnener atomarer Backup-Schritt darf abschließen.
- STOP_STANDALONE_CREATOR_OPS.ps1: aktuellen Supervisor und Backend stoppen.
  Health-/Backup-Tasks starten keinen Backend-Ersatz.
- In Windows Aufgabenplanung die drei oben genannten Aufgaben deaktivieren.
- Vollständige Entfernung auf ausdrücklichen Owner-Wunsch:
  scripts/uninstall_runtime_tasks.ps1 zunächst Vorschau, dann -Apply.
  Entfernt nur benannte Creator-Ops-Aufgaben und den bekannten Benutzer-Autostart.
  Archivdateien/DB bleiben erhalten. Erneute Task-Aktivierung:
  scripts/install_runtime_tasks.ps1 Vorschau, danach -Apply.

## Aktuell verifizierte Grenzen

Python 3.14.7, VENV, tzdata 2026.3, SQLite-Modul 3.50.4 und SQLite CLI vorhanden.
Ein Listener 192.168.188.131:4180, passwortgeschützte API/Control-Seite erreichbar.
Aktive DB integrity_check=ok, foreign_key_check leer, Schema 5.
156 Tests bestanden, einschließlich 11 neuer Local-Ops-Tests und isolierter
Watchdog-Backoff/Circuit-Ausführung; keine echte Störung absichtlich am Live-Backend erzeugt.
Alle drei registrierten Windows-Tasks wurden am 09.09. direkt über Task Scheduler
gestartet, LastTaskResult=0. Weekly/Monthly prüften vorhandene Periodenarchive;
Neuanlage, Periodenwechsel und Restore-Integrität wurden auf isolierten DBs getestet.
Die erste Health-Inventur: 44 Archive/DB-Sicherungen, 43 gesund, 1 alte Warnung.
Ein abschließendes Meilensteinbackup ergänzt diesen Bestand.

Meta: ein gezielter Browsercheck /apps/ → öffentliche Developer-Startseite,
„Los geht’s“ statt sichtbarer App-Liste; einmaliger Einstieg lieferte keine bestätigte
Verifikation. Der genaue aktuelle SMS-Pending-Status ist nicht sichtbar belegt.
Keine OTP-/Identitätsaktion, App, Token oder offizielle Publikation erzeugt.
META=WAITING_SIGNAL, Analytics offiziell=WAITING_SIGNAL, Inbound=WAITING_SIGNAL.
Vorhanden sind zwei echte manuelle Leona-Messungen desselben Pakets, keine zwei
unabhängigen Gewinner. Fiverr: kein neuer Check, öffentliche Proof-Lücke bleibt.

## Begründete Autonomie-Schätzung

Dies ist ein Fähigkeits-/Betriebsreife-Schätzwert, keine gemessene Erfolgsquote.
Gewichte betonen den beauftragten Local-Ops-Ausbau (50 % Runtime/Recovery/Jobs),
ohne externe Lücken aus der Gesamtzahl herauszurechnen. Owner-Gates bewerten
korrekt erhaltene Grenzen, nicht deren Wegautomatisierung.

| Kategorie | Gewicht | Vorher | Nachher | Beleg / verbleibende Grenze |
|---|---:|---:|---:|---|
| Local Runtime | 15 % | 90 | 95 | ein gesunder Core; VENV nun vollständig; Kaltstart nicht neu beobachtet |
| Backup/Recovery | 15 % | 80 | 95 | bestehende validierte Archive; nun automatische Periodenprüfung, Ausschlüsse und echte Tasks |
| Background Jobs | 20 % | 35 | 95 | vorher vorbereitete Tasks/falscher Watchdog-Host; jetzt 3 reale Task-Runs, Idle/Circuit; Langzeitlauf offen |
| Content Ops | 15 % | 75 | 75 | Review/Stories/70:30 vorhanden; Produktions-/Qualitätsarbeit weiterhin nötig |
| Analytics | 10 % | 30 | 30 | echte manuelle Daten vorhanden, kein offizieller autonomer Abruf |
| Instagram Publishing | 10 % | 35 | 35 | native historische Belege und Adaptercode; offizieller End-to-End-Proof fehlt |
| Inbound Engagement | 5 % | 20 | 20 | sichere Text-Gates; keine offizielle verfügbare Inbox-Datenquelle |
| Fiverr | 5 % | 40 | 40 | Angebot und Owner-Identity-Meldung; öffentlicher Gig/API-Proof offen |
| Owner/Safety Gates | 5 % | 95 | 100 | sensible Gates erhalten, Scheduler hat nun harte externe Aktionssperre |

Gewichtete Summe: vorher 58,00 %, nachher 73,25 % (gerundet 58 → 73 %).
Reiner lokaler Betriebsblock: ca. 95 %. 85–90 % Gesamtbetrieb ist wegen der realen
Meta-/Analytics-/Inbound-/Fiverr-Lücken nicht belegt und wird nicht behauptet.

Owner bleibt nötig für Identität/OTP, Rechtliches, Geld, Käufe, Kontosicherheit,
riskante Gespräche, explizite Adult-Publikation, große Architekturänderungen,
irreversible externe Aktionen und ungewissen Veröffentlichungszustand.
