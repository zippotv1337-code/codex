# AGENTS.md – Virtual Creator System

## Auftrag

Dieses Repository entwickelt und betreibt ein skalierbares System für fiktive, volljährige Virtual Creators. Lies vor Änderungen zuerst:

1. `docs/MASTER_HANDOFF_VIRTUAL_CREATORS.md`
2. `docs/PROJECT_CONTEXT_VIRTUAL_CREATORS.md`
3. `docs/OWNER_DECISIONS.md`
4. `docs/CODEX_STARTAUFTRAG.md`

Diese Dateien sind die fachliche Arbeitsgrundlage. Bestehender funktionierender Code bleibt erhalten, sofern keine begründete Änderung erforderlich ist.

## Verbindliche Regeln

- Leona Voss und Mara Field sind die etablierten Kernpersonas. Identität, Gesicht, Alter als volljährige Figuren, Tonalität und Kernpositionierung nicht eigenmächtig grundlegend ändern.
- Trends nur opportunistisch und persona-gerecht einsetzen.
- Nichts live veröffentlichen, terminieren oder extern versenden, bevor der Betreiber den konkreten Inhalt freigegeben hat.
- Keine Kosten, Abonnements, Käufe, neuen Konten, neuen Personas, Preisänderungen, Kooperationen oder Direktnachrichten ohne ausdrückliche Freigabe.
- SFW und 18+ technisch, organisatorisch und in der Asset-Ablage strikt trennen. Keine Adult-Inhalte oder Adult-Verweise in SFW-Ausgaben einschleusen.
- Nur eindeutig volljährige fiktive Personen. Keine Minderjährigen, keine jugendlich wirkende Sexualisierung, keine nicht einvernehmlichen Inhalte und keine reale Person ohne geklärte Rechte und Einwilligung imitieren.
- Plattformregeln und geltendes Recht vor produktiver Anbindung aktuell prüfen. AI-Kennzeichnung und erforderliche Offenlegung einhalten.
- Secrets nie committen. Test-/Draft-Modus als Standard; externe Seiteneffekte mocken oder explizit freigeben lassen.
- Laufende Kosten zunächst auf höchstens 15 EUR pro Monat begrenzen. Jede mögliche Überschreitung vorher begründen und freigeben lassen.

## Arbeitsweise

- Zuerst Bestand und Tests verstehen, dann inkrementell ändern.
- Selbstständig Code, Struktur, Tests und Dokumentation verbessern, solange keine externe oder irreversible Wirkung entsteht.
- Nur bei echter Blockade nachfragen; ansonsten vernünftige Annahmen treffen und dokumentieren.
- Entscheidungen aus echten Performance-Daten ableiten. Views allein sind kein ausreichendes Erfolgssignal.
- Wiederholbare Content-Serien und Character-Konsistenz sind wichtiger als reine Menge.
- Nach jedem relevanten Schritt Tests beziehungsweise geeignete Prüfungen ausführen und Ergebnis, Risiken, Kostenwirkung und offene Freigaben knapp dokumentieren.

## Über-den-Tellerrand-Prinzip

Prüfe aktiv, ob es klar bessere, einfachere, günstigere oder erfolgversprechendere Lösungen gibt: Tools, Automatisierungen, Formate, Plattformen, Monetarisierung, technische Vereinfachungen, Risiken und fehlende Bausteine. Bringe relevante Vorschläge mit Nutzen, Aufwand und Risiko ein. Wenn kein echter Mehrwert erkennbar ist, bleibe beim bestehenden Plan.

## Zusammenarbeit und Sitzungsübergabe

Für Arbeiten im Ordner `creator-collab/` gelten zusätzlich diese Regeln:

### Beginn jeder Sitzung

1. `creator-collab/PROJECT_RESUME.md` vollständig lesen.
2. `creator-collab/CURRENT_HANDOFF.md` vollständig lesen.
3. Den neuesten Eintrag in `creator-collab/sessions/` lesen.
4. Widersprüche im neuen Journal dokumentieren, statt ältere Fakten still zu überschreiben.

### Während der Sitzung

- Nur bestätigte Ergebnisse als erledigt markieren.
- Öffentliche Posts, Profiländerungen und andere externe Aktionen mit Link oder sichtbarer Bestätigung dokumentieren.
- Keine Passwörter, Codes, Tokens, Cookies oder privaten Schlüssel in Git, Journal oder Chat übernehmen.
- KI-Personas transparent als fiktiv und KI-generiert kennzeichnen.
- Keine Massen-Follow-/Unfollow-Automation oder irreführende Markenpartnerschaften verwenden.

### Ende jeder Sitzung

1. Einen Eintrag nach `creator-collab/JOURNAL_TEMPLATE.md` unter
   `creator-collab/sessions/YYYY-MM-DD-HHMM-<agent>.md` anlegen.
2. `creator-collab/CURRENT_HANDOFF.md` aktualisieren.
3. Bei dauerhaften Änderungen `creator-collab/PROJECT_RESUME.md` aktualisieren.
4. Nur projektbezogene Dateien committen; empfohlenes Format:
   `handoff: <kurze Zusammenfassung>`.
