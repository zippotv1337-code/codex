# Cloud-Bildpipeline für ZippoWorkz

Stand: 14. September 2026

## Verifizierter Zustand

Zwei bereits verbundene Cloud-Bilddienste sind in der Codex-Umgebung
erreichbar. Für das Mara-Paket `Hofladen am Sonntag` wurde ein Dienst mit
Referenzbild-Unterstützung verwendet. Fünf unterschiedliche 3:4-Bilder wurden
ohne Zukauf erzeugt, lokal gespeichert und anschließend visuell geprüft.

Damit muss Codex Bilder künftig nicht manuell retuschieren. Der sinnvolle
Workflow ist:

1. Persona-Avatar als Identitätsreferenz verwenden.
2. Pro Pose einen eigenen, klaren Shot-Auftrag senden.
3. Cloud-Ergebnisse in einen datierten lokalen Paketordner übernehmen.
4. Sichtprüfung auf Identität, Hände, Textartefakte, Logos, SFW und Dubletten.
5. Nur bestandene Dateien über den vorhandenen Importweg in ZippoWorkz laden.
6. Owner-Review im Dashboard; kein automatischer Live-Publish ohne echten
   Plattformbeleg.

## Grenzen

- Das kostenlose Bildkontingent ist begrenzt; keine endlosen Varianten.
- Video ist im aktuell verbundenen kostenlosen Workspace nicht verfügbar.
- Cloud-URLs sind Transportquellen, nicht die dauerhafte Asset Registry.
- Signierte Download-URLs, Kontodaten und sonstige Zugangsdaten werden weder
  in Git noch in Handoff-ZIPs gespeichert.
- Ein Cloud-Ergebnis gilt erst nach lokaler visueller QA als verwendbar.

## Empfehlung

Den bereits verbundenen Referenzbild-Workflow als primären Generator nutzen.
Der zweite verbundene Bilddienst bleibt Reserve. Ein zusätzliches Plugin ist
für normale Bildproduktion aktuell nicht nötig. Erst bei echtem Bedarf an
Video, Templates oder größerem Volumen neu bewerten; keine kostenpflichtige
Erweiterung ohne Owner-Freigabe.
