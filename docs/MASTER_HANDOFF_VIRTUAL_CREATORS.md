# Master Handoff – Virtual Creator System

Stand: 3. September 2026

## Auftrag in einem Satz

Baue das bestehende Repository inkrementell zu einem kostengünstigen, datengetriebenen Virtual-Creator-System für Leona Voss und Mara Field aus, das Content weitgehend automatisch vorbereitet und verbessert, aber Veröffentlichungen, Kosten und wesentliche externe Aktionen unter menschlicher Kontrolle hält.

## Unverrückbare Leitplanken

1. Leona Voss und Mara Field sind die etablierten Kernpersonas.
2. Trends bleiben opportunistisch und persona-gerecht.
3. Human-in-the-loop ist Pflicht: kein Live-Posting ohne konkrete Freigabe.
4. SFW und 18+ bleiben strikt getrennt.
5. Bis zu ersten Einnahmen gelten maximal 15 EUR laufende Kosten pro Monat; keine Ausgaben ohne Freigabe.
6. Fanvue ist die bevorzugte AI-freundliche Bezahlplattform, jedoch nur nach aktueller Regelprüfung und konformer AI-Kennzeichnung.
7. Das System misst, lernt und skaliert anhand mehrerer echter KPIs, nicht anhand einzelner Views.
8. Codex denkt über den bestehenden Plan hinaus, schlägt bessere Optionen vor und führt genehmigungspflichtige Neuerungen nicht eigenmächtig aus.

## Produktziel

Der gewünschte Alltagsbetrieb lautet:

```text
System beobachtet Signale und Performance
-> erstellt 3–5 passende Ideen je Persona
-> erzeugt Content-Drafts und Plattformvarianten
-> prüft Persona, Qualität, Rechte, Sicherheit und Kosten
-> Betreiber sieht Vorschauen und entscheidet
-> nur freigegebener Content wird terminiert/veröffentlicht
-> Ergebnisse werden nach 24 h / 72 h / 7 Tagen erfasst
-> System empfiehlt Skalieren, Variieren oder Stoppen
```

Der Betreiber soll hauptsächlich anschauen, auswählen und freigeben. Vollständig unbeaufsichtigtes Publizieren ist nicht das Ziel.

## Personas

### Leona Voss

Leona ist eine fiktive, volljährige, elegante und selbstbewusste Fashion-/Lifestyle-Creatorin. Ihre Welt umfasst deutsche City Nights, Fashion, Hotels, Rooftops, Reisen und filmische Alltagsszenen. Ihr Ton ist classy, charmant, leicht frech und etwas geheimnisvoll. Ihr Content braucht wiederkehrende Geschichten und Community-Entscheidungen statt bloßer Bildgalerien.

### Mara Field

Mara ist eine fiktive, volljährige, bodenständige und direkte Creatorin aus der modernen deutschen/europäischen Landwirtschaftswelt. Hof, Landmaschinen, Werkstatt, Felder und Arbeitsalltag sind ihr Kern. Sie ist keine amerikanische Cowgirl-/Ranch-Figur. Debatten, Praxisfragen, Maschinen-POVs und Community-Antworten eignen sich als wiederkehrende Formate.

Beide werden zunächst gleich getestet. Ressourcen werden erst nach wiederholbaren Ergebnissen umverteilt. Neue Personas kommen erst nach Validierung.

## Redaktions- und Freigabelogik

Statusmodell:

```text
IDEA -> GENERATED -> REVIEW -> APPROVED -> SCHEDULED -> PUBLISHED -> ANALYZED
```

Ohne Freigabe darf ein Inhalt `REVIEW` nicht verlassen. Externe Adapter starten in Mock-/Draft-Betrieb. Freigaben, Statuswechsel, Kosten und Veröffentlichungen müssen auditierbar sein.

## Content-Lernen

- Startwert: 70 % bewährte Formate, 30 % Experimente.
- Eigene Baselines und Medianwerte aufbauen.
- Gewinner nur bei mehreren Posts und mindestens zwei relevanten Qualitätskennzahlen skalieren.
- Gute Formate in 3–5 kontrollierten Varianten testen.
- Schwache Hypothesen nach 3–5 ernsthaften Varianten stoppen.
- Relevante Kennzahlen: Retention, Completion, Shares, Kommentare, Saves, Profilbesuche, Follow-Conversion, externe Klicks, Umsatz und Kosten.
- Ein einzelner viraler Post ist kein ausreichender Beweis.

## Monetarisierung und Plattformen

SFW-Reichweite und Monetarisierung werden parallel, aber getrennt getestet. Fanvue ist derzeit die bevorzugte Bezahlplattform für AI-Creators; diese Präferenz ist kein Ersatz für eine aktuelle Prüfung ihrer Bedingungen. Plattformen und Generatoren werden modular angebunden, damit Regeln, Preise oder Verfügbarkeit nicht das Gesamtsystem blockieren.

## Technische Zielarchitektur

```text
Character Memory + Asset Registry
            |
Trend/Idea Engine -> Prompt Builder -> Generator Adapter
            |               |
       Content Store <- Quality/Compliance Checks
            |
       Approval Dashboard
            |
      Publishing Adapters (default: mock/draft)
            |
       Analytics Collector -> Learning Engine
            |
       Recommendations + Cost Control
```

Wichtige Eigenschaften:

- providerunabhängige Adapter
- deterministische IDs und nachvollziehbare Metadaten
- sichere Wiederholbarkeit und Fehlerbehandlung
- klare Trennung von Persona, Plattform, SFW/18+ und Umgebungen
- keinerlei Secrets im Repository
- aktuelle Plattformregeln als konfigurierbare, überprüfbare Compliance-Schicht
- möglichst geringe laufende Kosten und transparente Kosten pro Asset/Post

## Umsetzungsvorgehen

1. Repository und vorhandene Komponenten vollständig verstehen.
2. Funktionierendes erhalten; nur begründet umbauen.
3. Character- und Asset-Daten zentralisieren.
4. Content-/Status-/Analytics-Datenmodell festlegen.
5. Review-Queue und sichere Draft-Pipeline als ersten vertikalen MVP bauen.
6. Mit je einem Leona- und Mara-Draft lokal testen.
7. Analytics und Learning zunächst mit importierten oder simulierten Daten validieren.
8. Externe Provider und Publisher erst modular anbinden, wenn Zugänge, Regeln, Kosten und Freigabe geklärt sind.
9. 18+-Pipeline separat vorbereiten und nur nach expliziter Freigabe aktivieren.
10. Nach jedem Schritt Tests, Dokumentation, Kostenwirkung und offene Entscheidungen aktualisieren.

## Was Codex selbstständig darf

Codex darf innerhalb des Repositorys analysieren, implementieren, refaktorieren, testen, dokumentieren, Mock-Daten erzeugen und Vorschläge vorbereiten. Codex soll nur bei echter Blockade fragen und ansonsten Annahmen transparent dokumentieren.

Codex darf ohne ausdrückliche Freigabe nicht live posten, Geld ausgeben, Konten oder Personas anlegen, Preise ändern, Kooperationen zusagen, Nutzer anschreiben, produktive Berechtigungen verändern oder Adult-Content veröffentlichen.

## Über den Tellerrand

Bei jeder größeren Entscheidung soll Codex kurz prüfen:

- Gibt es eine günstigere oder zuverlässigere Lösung?
- Kann eine zusätzliche Automatisierung sichere Routinearbeit sparen?
- Fehlt ein Risiko-, Compliance-, Rechte- oder Kostenbaustein?
- Gibt es ein stärkeres wiederholbares Format oder eine passendere Plattform?
- Lässt sich die Architektur vereinfachen, ohne Funktion oder Kontrolle zu verlieren?

Nur Vorschläge mit erkennbarem Mehrwert aufnehmen. Für jeden Vorschlag Nutzen, Aufwand, laufende Kosten, Risiken und erforderliche Freigabe nennen.

## Sofortiger nächster Schritt

Führe `docs/CODEX_STARTAUFTRAG.md` aus. Beginne mit einer Bestandsaufnahme, erstelle dann den lokalen vertikalen MVP und halte alle externen Wirkungen deaktiviert.
