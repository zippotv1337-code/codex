# Codex Startauftrag

## Ziel dieses Laufs

Überführe den vorhandenen Repository-Stand inkrementell in einen sicheren, lokal nutzbaren MVP für Leona Voss und Mara Field. Der erste Meilenstein ist eine funktionierende Kette von Content-Idee bis menschlicher Freigabe und Publishing-Draft; echte Veröffentlichung bleibt deaktiviert.

## Reihenfolge

### 1. Bestand aufnehmen

- Lies `AGENTS.md`, `docs/MASTER_HANDOFF_VIRTUAL_CREATORS.md`, `docs/PROJECT_CONTEXT_VIRTUAL_CREATORS.md` und `docs/OWNER_DECISIONS.md` vollständig.
- Analysiere Verzeichnisstruktur, vorhandenen Code, Tests, Datenmodelle, Assets, Konfiguration und offene TODOs.
- Identifiziere, was bereits funktioniert. Ersetze nichts funktionierendes ohne klaren Grund.
- Suche nach fehlenden Secrets, externen API-Abhängigkeiten und produktiven Seiteneffekten, ohne diese selbst auszulösen.

### 2. Kurzen Ist-Stand dokumentieren

Erstelle oder aktualisiere eine knappe technische Bestandsaufnahme mit:

- vorhandenen Komponenten
- Lücken gegenüber dem Zielbild
- Risiken und Abhängigkeiten
- aktuellem Teststatus
- geschätzter Kostenwirkung
- Entscheidungen, die eine Freigabe brauchen

### 3. MVP bauen

Priorität:

1. Zentrales, versionierbares Persona-/Character-Schema für Leona und Mara.
2. Klare Asset-Ablage mit Trennung nach Persona, SFW/18+, final/draft/verworfen und Herkunft/Rechten.
3. Content-Datenmodell mit IDs, Persona, Serie, Plattformvarianten, Status, Kosten und Analytics-Feldern.
4. Idea-/Prompt-Pipeline, die persona-gerechte Vorschläge und plattformnative Varianten erzeugt.
5. Review-/Approval-Queue mit Freigeben, Überarbeiten, Neu generieren und Verwerfen.
6. Publishing-Adapter als sichere Schnittstelle; standardmäßig Mock/Draft, kein echter Post.
7. Analytics-Schema und Import-Schnittstellen für Messungen nach 24 h, 72 h und 7 Tagen.
8. Einfache Learning-Regeln auf Basis eigener Baselines und mehrerer Qualitätsmetriken.
9. Kostenprotokoll und harte 15-EUR-Grenze mit Stop-/Warnmechanismus vor externem Verbrauch.
10. Tests, Beispieldaten und eine kurze Betriebsanleitung.

### 4. Vertikalen Probelauf liefern

Erzeuge lokal mindestens je einen vollständigen SFW-Draft für Leona und Mara:

```text
Idee -> Persona-Prüfung -> Plattformvarianten -> Review-Eintrag -> Freigabe-Simulation
-> Publishing-Draft -> simulierte Analytics -> Learning-Entscheidung
```

Keine realen Veröffentlichungen, Käufe, Account-Erstellungen oder Nachrichten.

### 5. Abschlussbericht

Berichte knapp:

- was gebaut oder verbessert wurde
- welche Tests bestanden haben
- wie der lokale MVP gestartet wird
- welche externen Zugänge später erforderlich sind
- welche echten Aktionen auf Freigabe warten
- welche Kosten aktuell und im nächsten Schritt zu erwarten sind
- welche 3–5 nächsten Aufgaben den größten Nutzen bringen
- welche über-den-Tellerrand-Optionen du gefunden hast, jeweils mit Nutzen, Aufwand und Risiko

## Akzeptanzkriterien

- Leona und Mara haben getrennte, validierte Character-Daten.
- SFW und 18+ sind technisch und in der Ablage getrennt.
- Mindestens zwei SFW-Drafts durchlaufen die lokale Pipeline bis zur simulierten Freigabe.
- Kein Codepfad veröffentlicht standardmäßig real.
- Freigaben und Statuswechsel sind nachvollziehbar.
- Kosten lassen sich pro Vorgang zuordnen und vor Überschreitung stoppen.
- Analytics können pro Post und Messfenster gespeichert werden.
- Tests decken die wichtigsten Grenzen und Statuswechsel ab.
- Setup und Betrieb sind für einen neuen Codex-Lauf verständlich dokumentiert.
