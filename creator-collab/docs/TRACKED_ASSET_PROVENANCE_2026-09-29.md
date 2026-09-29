# Tracked Asset Provenance — 29.09.2026

Status: `DERIVED_AUDIT_EVIDENCE`

Scope: alle 44 von Git getrackten Dateien unter `assets/generated/` und
`assets/meta-public/` auf `origin/main` bei Beginn des WORK-001–005-Deltas.

Dieser Bericht macht vorhandene Evidenz auffindbar. Er erteilt keine neuen
Rechte, ändert keine Veröffentlichung und ersetzt weder die Asset Registry in
`data/review_dashboard.db` noch die Owner Policy. `NOT_VERIFIED` bedeutet
bewusst unbekannt und niemals automatisch freigegeben.

| Paketpfad | Dateien | Dokumentierte Herkunft | Rechte-/Safety-Evidence | Git-/Public-Status | Ergebnis |
|---|---:|---|---|---|---|
| `assets/generated/leona-voss/2026-09-05/l1-spaetsommer-berlin/` | 5 | Built-in ImageGen, Leona-Identitätsanker | `docs/CONTENT_PRODUCTION_RUN.md`: `AI_GENERATED`, `SFW`, `PUBLIC_SFW` | im öffentlichen Repository getrackt | `DOCUMENTED` |
| `assets/generated/leona-voss/2026-09-06/lv-btt-01-september-roofline/` | 5 | Built-in ImageGen | `docs/CONTENT_PRODUCTION_RUN.md`: `AI_GENERATED`, `SFW`, `PUBLIC_SFW` | im öffentlichen Repository getrackt | `DOCUMENTED` |
| `assets/generated/mara-field/2026-09-05/m1-maschinencheck/` | 5 | Built-in ImageGen, Mara-Identitätsanker | `docs/CONTENT_PRODUCTION_RUN.md`: `AI_GENERATED`, `SFW`, `PUBLIC_SFW` | im öffentlichen Repository getrackt | `DOCUMENTED` |
| `assets/generated/mara-field/2026-09-06/mf-btt-02-kuechenfenster/` | 5 | Built-in ImageGen | `docs/CONTENT_PRODUCTION_RUN.md`: `AI_GENERATED`, `SFW`, `PUBLIC_SFW` | im öffentlichen Repository getrackt | `DOCUMENTED` |
| `assets/meta-public/2026-09-20/leona-rainy-berlin-afterwork/` | 3 | öffentlich vorbereitete Leona-Paketkopien | `docs/LEONA_RAINY_BERLIN_AFTERWORK_2026-09-20.md`: `SFW/PUBLIC_SFW`; Rechteklasse dort nicht ausdrücklich genannt | absichtlich als Meta-HTTPS-Medien getrackt; später offiziell veröffentlicht | `RIGHTS_NOT_VERIFIED_IN_PACKAGE_DOC` |
| `assets/meta-public/2026-09-21/leona-spaetsommer-berlin/` | 3 | öffentliche Ableitungen aus dem dokumentierten Leona-ImageGen-Paket | Quellpaket in `docs/CONTENT_PRODUCTION_RUN.md`; Live-Evidence im Handoff vom 21.09. | absichtlich als Meta-HTTPS-Medien getrackt | `DOCUMENTED_BY_SOURCE_LINEAGE` |
| `assets/meta-public/2026-09-21/mara-kuechenfenster/` | 3 | öffentliche Ableitungen aus dem dokumentierten Mara-ImageGen-Paket | Quellpaket in `docs/CONTENT_PRODUCTION_RUN.md`; Live-Evidence im Handoff vom 21.09. | absichtlich als Meta-HTTPS-Medien getrackt | `DOCUMENTED_BY_SOURCE_LINEAGE` |
| `assets/meta-public/2026-09-22/leona-black-blazer-three-moods/` | 5 | Built-in OpenAI ImageGen mit Leona-Referenz | `docs/CONTENT_PACKAGE_LEONA_BLAZER_2026-09-22.md`: `AI_GENERATED`, `SFW/PUBLIC_SFW` | absichtlich als Meta-HTTPS-Medien getrackt und veröffentlicht | `DOCUMENTED` |
| `assets/meta-public/2026-09-22/mara-pause-am-feldrand/` | 5 | Built-in OpenAI ImageGen mit Mara-Referenz | `docs/CONTENT_PACKAGE_MARA_FIELD_PAUSE_2026-09-22.md`: `AI_GENERATED`, `SFW/PUBLIC_SFW` | im öffentlichen Repository getrackt | `DOCUMENTED` |
| `assets/meta-public/2026-09-22/mara-werkstattabend/` | 3 | neue Mara-Werkstattmotive laut Live-Journal | `sessions/2026-09-21-1955-codex-mara-workshop-live.md`; Rechteklasse nicht in einem Paketvertrag gebündelt | absichtlich als Meta-HTTPS-Medien getrackt und veröffentlicht | `RIGHTS_NOT_VERIFIED_IN_PACKAGE_DOC` |
| `assets/meta-public/2026-09-27/leona-mara-collab/` | 2 | mechanische JPEG-/Formatableitungen eines Library-Assets; Quell-SHA dokumentiert | `sessions/2026-09-27-leona-mara-collab-publish-handoff.md`; Eigentum/Lizenz des Library-Originals nicht ausdrücklich belegt | absichtlich als Meta-HTTPS-Medien getrackt und veröffentlicht | `SOURCE_RIGHTS_NOT_VERIFIED` |

## Kontrollsumme des Scopes

- `assets/generated/`: 20 Dateien
- `assets/meta-public/`: 24 Dateien
- Gesamt: 44 Dateien
- Getrackte ZIPs, Datenbanken oder ausführbare Release-Artefakte im aktuellen
  Baum: 0

## Sichere Folgerung

- Kein Asset wird in diesem Run gelöscht, verschoben oder neu veröffentlicht.
- Für Rainy Berlin, Werkstattabend und insbesondere das Collab-Library-Original
  bleibt eine spätere kommerzielle Wiederverwendung bis zur expliziten
  Rechteprüfung `NOT_VERIFIED`.
- Repository-Sichtbarkeit und History bleiben unverändert; jede Änderung daran
  ist Owner-Gate.
- Neue Medien müssen ihre Provenienz künftig im jeweiligen Paketdokument und in
  der operativen Asset Registry tragen, bevor sie als bewusst öffentliches
  Git-Asset gelten.
