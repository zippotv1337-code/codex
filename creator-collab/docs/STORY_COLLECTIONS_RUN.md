# Story-Reserve und Collections

Stand: 5. September 2026 · ausschließlich lokal · kein Live-Publishing

## Story-Reserve

Aus den vier vorhandenen Feedpaketen werden vier Story-Pakete abgeleitet. Jedes
Paket besitzt drei klar getrennte Frames:

1. Teaser mit bestehendem Hook und erstem Top-Pick.
2. Poll mit einem unveröffentlichten alternativen Motiv außerhalb der Top 3.
3. Community-Frage mit CTA und einem weiteren Top-Pick.

Bereits veröffentlichte Assets werden ausgeschlossen. Story-Antworten bleiben
manuell; es findet kein automatisches Posten oder Engagement statt.

Dashboard: `http://127.0.0.1:4180/stories`

## Collections/Alben

Vier vorhandene Pakete erscheinen als read-only Collections mit:

- Coverbild
- Persona, Serie und Planungstag
- Tags für Stage, Safety, Sichtbarkeit und Plattform
- Asset-, Reserve- und Veröffentlichungsanzahl
- Top-3-Reihenfolge
- ehrlichem Top-Performer-Status

Solange keine echten Analytics existieren, bleibt Top Performer ausdrücklich
unbekannt.

Dashboard: `http://127.0.0.1:4180/collections`

## Verifikation

- Story-Pakete: 4
- Story-Frames: 12
- Collections: 4
- neue Bilder: 0
- externe Aktionen: 0
- Tests: 59/59 grün
- Python- und JavaScript-Syntax: grün
- SQLite `integrity_check`: ok
- Backup: `creator-ops-backup-post-stories-collections.db`
- SHA256: `3BF0A5CF67BF659C9D26BAF683223188ADDC8C966E12C63BDFE9FB46C7BA64A2`
