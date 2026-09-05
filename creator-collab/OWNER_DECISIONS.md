# Verbindliche Owner-Entscheidungen

Stand: 4. September 2026

Diese Datei hält dauerhafte Produkt- und Sicherheitsregeln fest. Status und
Zahlen stehen dagegen in `docs/CURRENT_STATE.json` und den Sitzungsjournalen.

## Personas und Transparenz

- Leona Voss und Mara Field sind fiktive, volljährige, KI-basierte Personas.
- Die Plattform-Kennzeichnung für KI-Inhalte wird beim Publishing geprüft.
- Normale Social-Captions erhalten keinen immer gleichen KI-Werbefooter.
- Keine erfundenen Kooperationen, Sponsoren oder persönlichen Erlebnisse.

## Content-Stufen

| Stufe | Safety | Sichtbarkeit | Öffentliche SFW-Plattformen |
|---|---|---|---|
| `ALLTAG` | `SFW` | `PUBLIC_SFW` oder `LOCAL_ONLY` | erlaubt nach Owner-Freigabe |
| `TEASER` | `SFW` | `PUBLIC_SFW` oder `LOCAL_ONLY` | erlaubt nach Owner-Freigabe |
| `ADULT_18` | `ADULT` | `ADULT_ONLY` | technisch gesperrt |

- Ein widersprüchlicher Datensatz wird bereits von SQLite abgewiesen.
- Adult-Material wird nicht in Git gespeichert und nicht über öffentliche
  Instagram-, Threads-, TikTok- oder YouTube-Pfade freigegeben.
- Reale Adult-Erzeugung oder -Veröffentlichung benötigt eine separate,
  ausdrückliche Owner-Freigabe. Dieser MVP erzeugt und veröffentlicht nichts
  davon automatisch.

## Content-Mix und Auswahl

- Planungsziel über 20 Slots: 40 % Alltag, 35 % Teaser, 25 % Adult 18+.
- Das Verhältnis ist eine Empfehlung, kein automatischer Generierungsauftrag.
- Jedes vollständige Paket hat fünf unterschiedliche Pose-Slots:
  `FRONTAL`, `LEFT_3Q`, `RIGHT_3Q`, `FULL_BODY_ACTION`, `CANDID`.
- Maximal zwei deutlich ähnliche Bilder je Paket.
- Top 3 werden gewichtet aus Qualität, Persona-Fit, Kohärenz, Stage-Fit und
  Neuheit gewählt und müssen mindestens drei Pose-Kategorien abdecken.

## Freigabe und externe Aktionen

- `READY_FOR_REVIEW` ist keine Veröffentlichungsfreigabe.
- Owner-Freigabe legt im MVP nur einen lokalen `mock-draft` an.
- Live-Publishing, Accountänderungen, Nachrichten und Follow-Aktionen brauchen
  einen eigenen, konkreten Auftrag.
- Keine Massen-Follow-/Unfollow-Automation.

## Medien, Rechte und Geheimnisse

- Nur eigene, lizenzierte oder nachweisbar KI-generierte Assets verwenden.
- Unklare Rechte blockieren kommerzielle und Website-Nutzung.
- Runtime-Medien liegen unter ignorierten `data/media/`-Pfaden; neue
  Creator-Bilder gehören nicht in Git.
- Passwörter, Tokens, Codes, Cookies und Tunnel-URLs werden nie committed.
- Das GitHub-Repository soll privat sein; die tatsächliche Sichtbarkeit wird im
  jeweils neuesten Journal mit sichtbarer Bestätigung dokumentiert.

## Rote Schranken

Diese Aktionen bleiben auch bei laufender Automatisierung manuell:

1. Live-Publishing und Profiländerungen.
2. Erzeugung oder Veröffentlichung von Adult-Material.
3. Änderung von Cloud-Zugriffsrechten oder Repository-Sichtbarkeit.
4. Löschen veröffentlichter Posts oder Originalmedien.
5. Kostenpflichtige Dienste, Verträge oder Käufe.
