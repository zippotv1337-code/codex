# Content Asset Inventory

Stand: 4. September 2026  
Zaehlweise: Nur eine tatsaechlich vorhandene, eindeutige Bilddatei gilt als
lokales Asset. Mock-Pfade, Screenshots und URLs werden separat ausgewiesen.

## Ergebnis in einem Satz

Je Persona existiert lokal genau **ein eindeutiges, hochaufloesendes und
wiederverwendbares Portraet**. Zusaetzlich sind je fuenf veroeffentlichte
Instagram-Posts belegt, deren Originaldateien aber nicht im Projekt liegen.

## Quellenpruefung

| Quelle | Ergebnis |
|---|---|
| Aktueller GitHub-/Repository-Stand | Geprueft; Content-Bruecke, Reports, Handoffs, Owner-Regeln und zehn Instagram-Belege vorhanden. |
| `data/*.db` | Geprueft; Review-DB enthaelt 2 echte lokale Imports und 8 Mock-Slots. Pipeline-DB/letzter JSON-Export enthalten 20 weitere Mock-Datensaetze. |
| `dashboard/assets/` | 2 echte PNG-Dateien: eine fuer Leona, eine fuer Mara. |
| `data/imported-assets/` | 2 byte-identische Importkopien der beiden Dashboard-Portraets; keine neuen Motive. |
| `assets/`, `generated/`, `final/`, `draft/` | Keine weiteren physischen Posting-Bilder gefunden. Die in SQLite genannten `.mock`-Pfade sind keine Dateien. |
| Backups/Exporte | 3 SQLite-Backups, 1 Restore-Pruefdatei und 2 secret-freie JSON-Exporte vorhanden. |
| Fruehere Content-Briefs | 4 Leona- und 4 Mara-Briefs in `CHATGPT_BRIDGE_TO_TUESDAY.md`; alle Texte vollstaendig, Bilder noch nicht produziert. |
| Zugaenglicher Projektchat `haupt` | Letzte Turns plus 10 Anhaenge geprueft: 8 System-/Dashboard-Screenshots, 2 Instagram-Profil-Screenshots. Keine hochaufloesenden Einzeldateien der Feed-Posts. |
| Character-Bibles | Regeln und Positionierung sind in Handoff/Owner-Dokumenten verteilt; keine eigenstaendige finale Character-Bible-Datei gefunden. |

## Eindeutige lokale Assets

| Persona | Asset | Motiv / Outfit / Szene | Qualitaet / Realismus | Pose / Blick | Bereits genutzt | Website | Instagram | Reserve | Empfehlung |
|---|---|---|---|---|---|---|---|---|---|
| Leona | [`dashboard/assets/leona-voss-avatar.png`](../dashboard/assets/leona-voss-avatar.png) | Nahportraet, cremefarbener Blazer, schwarzes Top, helles Fensterlicht | 8,8/10; natuerliche Haut, glaubwuerdiges Licht, leicht editorial | frontal, direkter Blick, freundliches Laecheln | Dashboard-Profil und Review-Slot; Social-Veroeffentlichung nicht bestaetigt | Profil, Close-up, About, Media Kit; Hero nur provisorisch | Profil, Story, Reel-Cover; nicht viermal als Feedmotiv wiederholen | Ja | **KEEP / PRIMARY PROFILE** |
| Leona | `data/imported-assets/leona-voss/2026-09-04/1d9f...png` | Exakte Kopie des vorigen Bildes | identisch | identisch | Review-Import | Nein, keine zweite Auswahl | Nein | Nein | **DUPLIKAT**; nicht als separates Asset zaehlen |
| Mara | [`dashboard/assets/mara-field-avatar.png`](../dashboard/assets/mara-field-avatar.png) | Nahportraet, Jeanshemd/Latzhosenriemen, deutsche Hofwerkstatt | 8,8/10; Hautstruktur, einzelne Haare und Werkstattlicht glaubwuerdig | frontal, direkter Blick, ruhiges Laecheln | Dashboard-Profil und Review-Slot; Social-Veroeffentlichung nicht bestaetigt | Profil, Close-up, About, Media Kit; Hero nur provisorisch | Profil, Story, Reel-Cover; nicht viermal als Feedmotiv wiederholen | Ja | **KEEP / PRIMARY PROFILE** |
| Mara | `data/imported-assets/mara-field/2026-09-04/0c31...png` | Exakte Kopie des vorigen Bildes | identisch | identisch | Review-Import | Nein, keine zweite Auswahl | Nein | Nein | **DUPLIKAT**; nicht als separates Asset zaehlen |

Sicherheits-/Rechtestatus laut Asset Registry: beide eindeutigen Dateien sind
`SFW`, `AI_GENERATED`, fuer Instagram/Threads/TikTok erlaubt und in der lokalen
Registry `UNPUBLISHED`. Eine spaetere Website-Nutzung sollte diese
Herkunftsinformation mitfuehren.

## Bereits veroeffentlichte, aber lokal nicht archivierte Assets

### Leona Voss

Die zugaengliche Profilansicht bestaetigt fuenf unterschiedliche SFW-Motive:
Spiegel/Abendlook, Cafe mit Blazer, langes Abendkleid auf Treppe, Gym und
Berlin-Rooftop/Anzug. Die eindeutige Zuordnung Motiv -> URL ist ohne
Einzeldateien nicht belastbar.

1. <https://www.instagram.com/leonavoss.ai/p/Dc0mbMAgE1M/>
2. <https://www.instagram.com/leonavoss.ai/p/Dc0oRg7APVa/>
3. <https://www.instagram.com/leonavoss.ai/p/Dc0pXtAgBJY/>
4. <https://www.instagram.com/leonavoss.ai/p/Dc0pc2sgDUd/>
5. <https://www.instagram.com/leonavoss.ai/p/Dc0pf8NAAnG/>

### Mara Field

Die zugaengliche Profilansicht bestaetigt mindestens drei unterschiedliche
SFW-Motive direkt: Feldrand mit kariertem Hemd, Kuechentisch/Kaffee in Latzhose
und Hof/Traktor in Latzhose. Fuenf Posts sind ueber Links bestaetigt; zwei
Motive konnten ohne Einzeldatei nicht verlaesslich klassifiziert werden.

1. <https://www.instagram.com/mara.field.ai/p/Dc0mATVAF2u/>
2. <https://www.instagram.com/mara.field.ai/p/Dc0oGuxgBWl/>
3. <https://www.instagram.com/mara.field.ai/p/Dc0pmnQAKHP/>
4. <https://www.instagram.com/mara.field.ai/p/Dc0ppmtAPJy/>
5. <https://www.instagram.com/mara.field.ai/p/Dc0pslwgH7R/>

Diese zehn Posts sind **bestehende Portfolio-Referenzen**, aber noch keine
lokalen Website-Master. Vor Wiederverwendung muessen die Originaldatei,
Generator-/Lizenzherkunft und der Rechtepfad gesichert werden. Ein Profil-
Screenshot ist kein Ersatz fuer das Masterbild.

## Mock- und Datenbankbestand

| Persona | Registry-Eintraege | Physische Datei | Verwendung |
|---|---:|---|---|
| Leona | 10 Pipeline-Mocks + 4 Review-Mocks | Nein | Tests, Layout, Top-3-Logik; nicht posten und nicht fuer Website zaehlen |
| Mara | 10 Pipeline-Mocks + 4 Review-Mocks | Nein | Tests, Layout, Top-3-Logik; nicht posten und nicht fuer Website zaehlen |

Die Scores der Mock-Eintraege bewerten nur deterministische Testdaten und sind
keine visuelle Qualitaetsbewertung realer Bilder.

## Doppelte und sehr aehnliche Bilder

- Exakt doppelt: je eine Importkopie pro Persona.
- Aehnlichkeit der zehn veroeffentlichten Posts kann ohne Masterdateien nicht
  per Hash geprueft werden. Die Profilansichten zeigen aber genuegend
  Szenenvariation fuer ein Portfolio.
- Fuer neue 5er-Sets bleibt die Regel: maximal zwei sehr aehnliche Bilder und
  die Pose-Matrix frontal / links 3/4 / rechts 3/4 / Ganzkoerper-Bewegung /
  candid verbindlich.

## Belastbare Zaehlung

- Leona: **1 lokales eindeutiges Asset**, plus **5 veroeffentlichte Referenzen**.
- Mara: **1 lokales eindeutiges Asset**, plus **5 veroeffentlichte Referenzen**.
- Insgesamt physisch lokal wiederverwendbar: **2**.
- Exakte Duplikate: **2**.
- Reine Mock-Datensaetze ohne Mediendatei: **28**.

Maschinenlesbare Kurzfassung: `docs/CONTENT_ASSET_INVENTORY.csv`.
