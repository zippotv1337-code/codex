# ZippoWorkz — VPS Next Run

## Rolle

Der VPS ist ein leichter, read-only Beobachter. Er veröffentlicht nichts,
schreibt nicht in die operative SQLite-Datenbank und führt keine schwere
Bild-/Modellarbeit aus.

## Startvoraussetzungen

- Dieses Paket wurde bewusst ohne Zugangsdaten erzeugt.
- Host, Benutzer, Passwort/Schlüssel und Transport werden ausschließlich auf
  dem Zielsystem bzw. in einem sicheren Secret-Speicher gesetzt.
- Ein erreichbarer HTTPS-Health-Endpunkt muss ausdrücklich konfiguriert sein.
  Die private LAN-Adresse `192.168.188.131` ist vom Internet-VPS normalerweise
  nicht erreichbar.

## Begrenzte Aufgaben

1. Paket-Hashes prüfen.
2. Sanitisierten Current-State und Handoff lesen.
3. Falls `ZIPPOWORKZ_HEALTH_URL` gesetzt ist: genau einen HTTPS-Healthcheck mit
   kurzem Timeout ausführen.
4. Ergebnis als `VPS_RESULT.json` und `VPS_RESULT.md` lokal auf dem VPS
   schreiben.
5. Bei nicht erreichbarem Endpunkt `OFFLINE` melden; nicht loopen.
6. Keine `ONLINE`-Behauptung ohne echte erfolgreiche Antwort.

## Verboten

Keine Plattformaktionen, kein Instagram/Fiverr/Meta-Login, keine DMs oder
Kommentare, keine DB-Schreibzugriffe, keine Credentials in Ergebnisdateien,
keine Portfreigaben, keine Paid Services, kein Git-Push, kein Workspace-
Ersetzen und keine unbegrenzten Retries.

## Ergebnis

Der erste echte Lauf ist erfolgreich, wenn Paketprüfung und optionaler
Healthcheck mit Zeitstempel und Quell-URL ohne Secrets dokumentiert sind.
