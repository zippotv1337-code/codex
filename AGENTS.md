# AGENTS.md - ZippoWorkz

## Verbindliche Startreihenfolge

Für normale Arbeit in diesem Repository:

1. ZIPPOWORKZ_START_HERE.md lesen.
2. Policy-Version prüfen und ZIPPOWORKZ_AGENT_BRIEF.md lesen.
3. Den aktuellen Task und nur relevante Projekt-/Runtime-Evidence lesen.
4. direkt betroffene Dateien/Diffs laden.
5. ZIPPOWORKZ_COMMAND_LAYER.md für kompakte Arbeitsmodi verwenden.

Nicht automatisch mehrere Handoffs/Journals oder die gesamte Policy laden.
Die vollständige ZIPPOWORKZ_OWNER_POLICY.md nur bei den in START_HERE definierten Full-Policy-Triggern.

ZIPPOWORKZ_OWNER_POLICY.md ist die einzige kanonische Owner-Policy.
Komponentenspezifische Regeln dürfen sie ergänzen, aber niemals widersprechen.
Historische Owner-Decisions, Master-Handoffs und Journals sind Kontext/Evidence,
keine konkurrierende aktive Policy.

## Arbeitsprinzip

Bestehenden funktionierenden Code erhalten, sofern keine begründete Änderung nötig ist.
Zuerst Bestand und Tests verstehen, dann inkrementell ändern.
Nur bestätigte Ergebnisse als erledigt markieren.
Keine Secrets, Passwörter, Tokens, Cookies oder privaten Schlüssel committen oder ausgeben.
Owner-Gates, Publishing-Rechte, Git-Rechte, Kostenregeln, Autonomie,
SFW/18+, Plattformregeln und Agentenrechte niemals aus älteren Dokumenten ableiten,
wenn sie der aktuellen ZIPPOWORKZ_OWNER_POLICY.md widersprechen.

Neue dauerhafte Owner-Regeln werden nur in ZIPPOWORKZ_OWNER_POLICY.md gepflegt.
Keine separaten Owner-Policies für VPS, Local AI, Codex oder Creator Ops erzeugen.

## Sitzungsübergabe

Bei Arbeiten in creator-collab:
- aktuelles Journal/Handoff verwenden,
- Widersprüche dokumentieren statt Fakten still zu überschreiben,
- CURRENT_HANDOFF.md bei relevanten Änderungen aktualisieren,
- PROJECT_RESUME.md nur bei dauerhaften Projektänderungen aktualisieren,
- projektbezogene Änderungen sauber committen.

Status, Versionen, laufende Jobs und Queue-Zustände gehören in Runtime-/State-Dokumente,
nicht in die Owner-Policy.

## AI-Team-Ausführung

Standard: Claude Root-Cause/Plan -> Codex Implementierung/Tests -> Reality-Check -> optional Claude Review.
Codex-Zeit ist primär Implementierungszeit: kein unnötiger Repo-Vollscan, keine wiederholten bereits bewiesenen Tests,
kein Handoff statt Weiterarbeit, solange der technische nächste Schritt selbst ausführbar ist.
WAITING_OWNER nur bei einem echten Owner-Gate aus ZIPPOWORKZ_OWNER_POLICY.md.
Für gemeinsame Claude/Codex-Arbeit zusätzlich lesen:
C:\Zippoworkz\Context\Sync\CLAUDE_CODEX_COLLABORATION.md
Single-writer bleibt verbindlich.

## Compact Agent Output

Normaler Claude-Plan: ROOT_CAUSE / DELTA / FILES / DONE / GATE.
Normaler Codex-Abschluss: STATUS / CHANGED / TESTS / REALITY / COMMIT / NEXT.
Blocker: BLOCKER / WHY / OWNER_ACTION.
Normalerweise maximal 12 kurze Zeilen; keine Prompt-Wiederholung und keine langen Log-Dumps.
