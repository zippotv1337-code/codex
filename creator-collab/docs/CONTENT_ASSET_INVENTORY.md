# Content Asset Inventory

Stand: 4. September 2026  
Zählweise: Nur tatsächlich vorhandene, eindeutige Bilddateien gelten als
Assets. Importkopien, Mock-Pfade und öffentliche URLs werden separat gezählt.

## Ergebnis

- Leona: **10 eindeutige lokale Content-Assets** in zwei fertigen Paketen.
- Mara: **10 eindeutige lokale Content-Assets** in zwei fertigen Paketen.
- Davon neu in diesem Run: **18**; gezielt wiederverwendete Profilanker: **2**.
- Dashboard: **20/20 echte Previews**, **12 Top-Picks**, **4 Pakete
  READY_FOR_REVIEW**.
- Öffentliche Portfolio-Referenzen ohne lokale Master: weiterhin 5 je Persona.

## Fertige lokale Pakete

| Persona | Paket/Pfad | Motive | Pose-Matrix | Qualität | Genutzt | Website | Instagram | Reserve | Empfehlung |
|---|---|---|---|---|---|---|---|---|---|
| Leona | `assets/generated/leona-voss/2026-09-05/l1-spaetsommer-berlin/` | Café, Altbau, City-Walk | 5/5 | 8,5–9 Ziel erreicht | unveröffentlicht; in Review | City, Candid, Full-body | Carousel | S1, S3 | **READY_FOR_REVIEW** |
| Leona | `assets/generated/leona-voss/2026-09-06/lv-btt-01-september-roofline/` | Rooftop, Skyline, Reflexion | 5/5 | 8,5–9 Ziel erreicht | unveröffentlicht; in Review | Hero, Editorial, Full-body | Carousel | S1, S3 | **READY_FOR_REVIEW / HERO-KANDIDAT** |
| Mara | `assets/generated/mara-field/2026-09-05/m1-maschinencheck/` | Hof, Reifen, Licht, Traktor | 5/5 | 8,5–9 Ziel erreicht | unveröffentlicht; in Review | Farm Hero, Technik, Full-body | Carousel | S1, S3 | **READY_FOR_REVIEW / FARM-HERO** |
| Mara | `assets/generated/mara-field/2026-09-06/mf-btt-02-kuechenfenster/` | Hofküche, Kaffee, Notizbuch | 5/5 | 8,5–9 Ziel erreicht | unveröffentlicht; in Review | Lifestyle, Candid, Full-body | Carousel | S1, S2 | **READY_FOR_REVIEW** |

Vollständige Einzeldateien, Hashes, Prompt-Deltas, QA und Top-3-Auswahl stehen
in `docs/CONTENT_PRODUCTION_RUN.md`.

## Profil-/Identitätsanker

| Persona | Datei | Rolle | Status |
|---|---|---|---|
| Leona | `dashboard/assets/leona-voss-avatar.png` | primäres Profil/Close-up; als S1 in L1 wiederverwendet | `AI_GENERATED`, SFW |
| Mara | `dashboard/assets/mara-field-avatar.png` | primäres Profil/Close-up; als S1 in M1 wiederverwendet | `AI_GENERATED`, SFW |

Die zugehörigen Dateien unter `data/imported-assets/` sind technische
Importkopien und werden nicht als zusätzliche Motive gezählt.

## Veröffentlichte Referenzen ohne lokale Master

### Leona

1. <https://www.instagram.com/leonavoss.ai/p/Dc0mbMAgE1M/>
2. <https://www.instagram.com/leonavoss.ai/p/Dc0oRg7APVa/>
3. <https://www.instagram.com/leonavoss.ai/p/Dc0pXtAgBJY/>
4. <https://www.instagram.com/leonavoss.ai/p/Dc0pc2sgDUd/>
5. <https://www.instagram.com/leonavoss.ai/p/Dc0pf8NAAnG/>

### Mara

1. <https://www.instagram.com/mara.field.ai/p/Dc0mATVAF2u/>
2. <https://www.instagram.com/mara.field.ai/p/Dc0oGuxgBWl/>
3. <https://www.instagram.com/mara.field.ai/p/Dc0pmnQAKHP/>
4. <https://www.instagram.com/mara.field.ai/p/Dc0ppmtAPJy/>
5. <https://www.instagram.com/mara.field.ai/p/Dc0pslwgH7R/>

Diese zehn URLs bleiben Portfolio-Belege, aber keine wiederverwendbaren
Masterdateien. Vor kommerzieller Wiederverwendung müssen Original und
Herkunft/Rechte gesichert werden.

## Mocks und Duplikate

- Die älteren Test-/Fallback-Mocks bleiben für Tests und leere Zustände
  erhalten, zählen aber nicht als Content.
- Technische Importkopien in `data/imported-assets/` sind Hash-Duplikate der
  20 registrierten Paketdateien.
- Innerhalb jedes finalen 5er-Sets sind höchstens zwei Bilder ähnlich; alle
  vier Sets erfüllen die verlangte Pose-Matrix.

Maschinenlesbare Kurzfassung: `docs/CONTENT_ASSET_INVENTORY.csv`.
