# ZIPPOWORKZ_COMMAND_LAYER

Stand: 02.10.2026
Policy-Version: 1.4
Status: ACTIVE / DERIVED WORKING SHORTHANDS

Diese Slash-Commands sind interne Arbeitskürzel, keine geheimen ChatGPT-Befehle.
Sie ändern keine Rechte und umgehen keine Owner-Gates.

## Core Commands

/rootcause — Ursache statt Symptom bestimmen; Evidence und Gegenhypothese nennen.
/assumptions — versteckte Annahmen offenlegen und unsichere markieren.
/verify — Behauptungen gegen Repo, Runtime, Provider oder Source of Truth prüfen.
/factcheck — externe/faktische Aussage mit belastbarer Quelle prüfen.
/critic — Plan/Diff aktiv auf Lücken, Scope-Drift und falsche Sicherheit prüfen.
/risks — konkrete Risiken + Mitigation, ohne daraus automatisch einen Stop zu machen.
/prioritize — nächsten höchsten P0/P1-Schritt auswählen.
/focus — Nebenthemen entfernen; genau einen aktuellen Scope halten.
/plan — kleinstes ausführbares Delta + Done-Kriterium.
/reverse — vom gewünschten Endzustand rückwärts zum nächsten Schritt planen.
/debug — reproduzieren -> isolieren -> Ursache -> kleinster Fix -> Test.
/solution — direkt umsetzbaren Lösungsweg liefern.
/alternative — maximal 2 sinnvolle Alternativen, wenn Primärweg blockiert ist.
/optimize — funktionierenden bestehenden Weg vereinfachen/beschleunigen.
/automate — wiederkehrende Owner-Handarbeit als Automationskandidat behandeln.
/implement — vorhandenen Plan ohne neue Architektur umsetzen.
/reality — echten Provider-/Runtime-/User-Proof statt Mock-Erfolg prüfen.
/compact — nur Ergebnis, Evidence, Blocker und Next; keine Wiederholung.
/json — nur wenn maschinenlesbare Übergabe technisch nützlich ist.
/status — STATUS / RESULT / BLOCKER / NEXT in maximal 6 kurzen Zeilen.

## Content / Growth Commands

/audience — Zielgruppe und konkreten Nutzen prüfen.
/customer — aus Kunden-/Käufersicht prüfen.
/market — Markt-/Nachfragefakten statt Ideen-Hype prüfen.
/competitor — relevante Konkurrenz/Muster sachlich vergleichen.
/growth — nächsten messbaren Reichweiten-/Conversion-Hebel wählen.
/hook — mehrere kurze Hooks mit klar unterschiedlichem Angle.
/headline — kurze starke Überschrift ohne Clickbait-Zwang.
/instagram — auf reale Instagram-Mechanik, Format und Insights ausrichten.
/reels — short-form Hook, Retention, Szenenfolge und CTA optimieren.

## Default Chains

Claude / Chief of Staff:
 /rootcause -> /assumptions -> /verify -> /prioritize -> /plan -> /compact

Codex / Engineering:
 /focus -> /implement -> /debug (nur bei Fehler) -> /verify -> /reality -> /compact

Blocker:
 /rootcause -> /alternative -> /verify -> falls wirklich Owner-only: /compact

Content:
 /audience -> /hook -> /instagram oder /reels -> /reality -> /optimize

## Regeln für Effizienz

- Nicht mehr als 3–5 Commands für eine normale Aufgabe aktiv kombinieren.
- /verify bedeutet gezielte Evidence, nicht Vollscan.
- /critic ist optional bei kritischen Änderungen, nicht Pflicht nach jedem Kleinschritt.
- /json nur für Maschinenübergaben; normale Owner-Kommunikation bleibt lesbar.
- /compact ist Default für Agent-zu-Agent und Agent-zu-Owner Statusmeldungen.
- Keine Command-Kette darf einen bereits bekannten Scope wieder aufblähen.
