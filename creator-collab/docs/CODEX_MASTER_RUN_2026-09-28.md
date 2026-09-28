# CODEX MASTER RUN — 28.09.2026

Status: READY_FOR_CODEX
Ziel: Alle seit dem letzten Codex-Stand hinzugekommenen offenen Arbeiten in einem geordneten Run zusammenführen.

## 0. NICHTS VERWERFEN

Arbeitsbaum ist aktuell NICHT sauber. Vor irgendeinem Reset/Checkout/Stash zuerst prüfen und erhalten:
- creator-collab/config/connector_secret_catalog.json
- creator-collab/creator_ops/external_readiness.py
- creator-collab/creator_ops/secrets.py
- creator-collab/tests/test_external_readiness.py
- creator-collab/creator_ops/tiktok.py (untracked)
- creator-collab/tests/test_tiktok_adapter.py (untracked)

Diese Dateien enthalten begonnene TikTok/OAuth/Secret-Broker-Arbeit. NICHT löschen, überschreiben oder durch älteren main-Stand ersetzen.

Aktueller GitHub-main bei Erstellung dieses Auftrags: 94f62cb.

## 1. Verbindlicher Bootstrap

Vor Arbeit:
1. Repo-Root ZIPPOWORKZ_START_HERE.md lesen.
2. Repo-Root ZIPPOWORKZ_OWNER_POLICY.md vollständig lesen.
3. creator-collab/AGENTS.md lesen.
4. creator-collab/CURRENT_HANDOFF.md, docs/CURRENT_STATE.json, docs/BACKLOG.md und neuestes Journal lesen.
5. Chat-Memory/alte Owner-Decisions nicht gegen die aktuelle Policy stellen.

Wichtig: ZIPPOWORKZ_OWNER_POLICY v1.2 ist die einzige kanonische Owner-Policy.
## 2. Seit letztem Codex neu auf main

Folgende Änderungen sind bereits kanonisch und dürfen nicht zurückgedreht werden:
- 53646e2 — gemeinsame Owner-Policy eingeführt.
- d31cdc1 — kanonischer START_HERE / Agent-Bootstrap.
- 10eaf48 — Virality / Trend Intelligence als P1.
- 5e3d4a3 — Einfachheitsprinzip: Owner entscheidet, System arbeitet.
- 7464c46 — Topic-to-Short Factory als P1.
- 94f62cb — detaillierter MVP-Auftrag für Virality + Short Factory.

Zusätzlich wurde der aktive VPS lokal bereits so umgestellt, dass Dashboard/Worker/Bootstrap die zentrale Owner-Policy laden.
Keine neue konkurrierende Owner-Policy erzeugen.

## 3. Git-Strategie für diesen Run

Dieser Run berührt TikTok OAuth/Auth, Publishing-Core und wahrscheinlich DB-Schema.
Darum NICHT direkt nach main mergen.

- Erstelle/verwende einen Arbeitsbranch, z. B. codex/20260928-next-stack.
- Bestehende Dirty-Tree-Arbeit dabei erhalten.
- Sinnvolle Checkpoint-Commits erstellen und Branch pushen.
- Kein Force-Push, kein History-Rewrite.
- Merge nach main erst nach Owner-Gate für Auth/Security/DB-Schema/kritischen Publishing-Core.
- Reine Doku-/unkritische Ergänzungen können normal committed werden, aber nicht künstlich aufsplitten.

## 4. P0 — begonnene TikTok-Arbeit fertigstellen

Zuerst den vorhandenen TikTok-Diff fachlich prüfen und vervollständigen.
Ziel: offizieller, fail-closed TikTok-Adapter für das bestehende ZippoWorkz/Creator-Ops-System.

Vorhandene Arbeit umfasst bereits:
- OAuth Authorization URL / Code Exchange / Refresh,
- DPAPI Secret Broker,
- Creator-Info Preflight,
- Draft-Upload und Direct Post Init,
- FILE_UPLOAD / PULL_FROM_URL,
- Status-Fetch,
- Token Refresh,
- secret-free External Readiness,
- fokussierte Tests.

Nicht neu erfinden — vorhandene Implementierung reviewen, korrigieren und integrieren.
TikTok-Abschlusskriterien:
- kein Token/Secret in Logs, Git, Handoff oder Tests,
- OAuth state/redirect/scopes sauber validiert,
- Refresh-Rotation sicher und fail-closed,
- Creator-Info zwingend vor Direct Post,
- Privacy-/Comment-/Duet-/Stitch-Constraints aus Creator-Info respektieren,
- AIGC/AI-Kennzeichnung korrekt abbilden, soweit API unterstützt,
- kein Blind-Retry bei unbekanntem Publishstatus,
- Idempotenz/Reconcile-Konzept dokumentieren,
- External Readiness zeigt TikTok korrekt,
- Connector Secret Catalog passt,
- CLI/Service-Anbindung so weit ergänzen, dass der Adapter praktisch nutzbar ist,
- KEIN echter TikTok-Post ohne vorhandene sichere Credentials/Owner-Gates erzwingen.

Wenn TikTok Portal/URL-Verifikation/OTP/Consent erforderlich ist:
alles technisch bis 95 % vorbereiten und exakt EINEN gebündelten Owner-Handoff erzeugen.

## 5. P0 — Current Truth / Policy-Drift bereinigen

Aktuelle docs/CURRENT_STATE.json und Teile älterer Handoffs enthalten noch alte Owner-Gates.
Das ist Drift, keine neue Wahrheit.

Aufräumen:
- Current-State aus heutiger Policy/realem Runtime-Stand regenerieren/aktualisieren.
- Alte Sessions/Journals NICHT historisch umschreiben.
- Historische Aussagen klar als HISTORICAL/STALE behandeln.
- CURRENT_HANDOFF oben um einen neuen aktuellen Abschnitt ergänzen.
- Keine separate OWNER_DECISIONS-Policy reaktivieren.
- Aktuelle Regeln zu DMs, Kommentare, bestehende Gigs, SFW/Adult, TikTok, Kosten, Git und Owner-Fragen korrekt aus v1.2 übernehmen.
- Runtime-Zahlen nur behaupten, wenn aktuell belegt.

## 6. P1 — Virality / Trend Intelligence MVP

Führe creator-collab/docs/CODEX_NEXT_TASK_VIRALITY_SHORT_FACTORY.md als verbindlichen Teilauftrag aus.

Mindestens:
- strukturierter Trend-Brief mit Source/Evidence,
- Hook-/Visual-/Caption-/CTA-Pattern-Extraktion,
- Trennung Quelle vs. eigene Analyse,
- Speicherung wiederverwendbarer Patterns,
- Originalkonzept aus Thema + Zielgruppe + Persona/Kunde,
- keine Kopie fremder Texte/Inhalte,
- Status/Evidence pro Schritt.
## 7. P1 — Topic-to-Short Factory MVP

Auf Virality aufsetzen, keine zweite Architektur.

Zielpipeline:
Trend/Hook -> Originalkonzept -> Script -> Voice-Hinweise -> Shot/B-Roll-Plan ->
Media-Plan -> Captions/Subtitles -> QA -> Review/Gate -> später Publish ->
24/72/168h Insights -> Learning.

Für diesen Run mindestens intern testbar bis QA_READY.

Wichtig:
- bestehende Creator-Ops-DB als einzige operative Wahrheit,
- additive, migrationssichere DB-Änderungen,
- keine zweite App,
- kein Framework-Wechsel,
- keine Cloudkosten,
- keine echte Media-/Publish-Aktion als Voraussetzung für Tests.

## 8. Media-Routing vorbereiten

Die Factory muss an die vorhandene Media-Strategie anschließbar sein:
- Higgsfield = bevorzugter Cloud-Media-Worker.
- ComfyUI bleibt aus der Planung.
- Paid Higgsfield Calls benötigen Owner-Freigabe.
- OpenAI Image nur als Fallback gemäß Owner-Policy; keine Zusatzkosten ohne Freigabe.
- Local AI/Qwen plant/routet/bewertet, spezialisierter Worker generiert.

In diesem Run reicht eine saubere Adapter-/Job-Grenze und Statusmodell.
KEIN kostenpflichtiger Generierungsaufruf nötig.

## 9. Analytics-Learning-Loop

Bestehende echten 24/72/168h-Insights mit dem neuen Pattern-/Short-Modell verbinden.

Ziel:
- Hook/Format/Timing/CTA anhand echter Daten bewertbar,
- UNKNOWN/NULL wenn Daten fehlen,
- keine erfundenen Erfolgssignale,
- Views allein nicht als Gesamturteil,
- Learning darf nächste Planung beeinflussen, aber Persona-Grundidentität nicht autonom umschreiben.

Bestehende Instagram-Insights und Live-Proofs wiederverwenden.
## 10. Dashboard / Bedienung

Keine zweite Oberfläche bauen.

Im bestehenden Creator-Ops-/zentralen Dashboard nur den kleinsten sinnvollen Ausbau:
- Status für Trend Intelligence,
- Status für Topic-to-Short Pipeline,
- ggf. letzter Trendbrief / aktuelles Konzept / Pipeline-State,
- TikTok Readiness sichtbar, secret-free,
- Owner-Gate nur anzeigen, wenn wirklich erforderlich.

Das Einfachheitsprinzip aus Policy v1.2 gilt:
Wenn ein Schritt automatisierbar ist, den Owner nicht mit manuellen Kommandos belasten.

## 11. Bestehende offene Punkte mitziehen, aber nicht verzetteln

Nur wenn ohne großen Seitensprung sinnvoll:
- Fiverr Gig 1 Public-Readback des Owner-Saves vorbereiten/prüfen, keinen Gig duplizieren.
- Gig 2 als nächstes Produkt im Backlog belassen; nicht ohne notwendigen Gate live erstellen.
- Leona/Mara 24/72/168h Analytics sauber weiterführen.
- Leona×Mara Collab-Receipt/Current-State erhalten.
- Local-AI Multi-Node Secret-Replikation nicht als erledigt behaupten, solange Local-AI-Public-Key nicht live belegt ist.
- Higgsfield Broker-Key/paid calls nicht erfinden oder kaufen.

Nicht alles gleichzeitig extern ausführen. Erst stabile interne Grundlage.

## 12. Tests / Qualität

Mindestens:
- pytest für alle berührten Module,
- fokussierte TikTok/OAuth/Secret-Broker-Tests,
- Trend-/Pattern-/Short-Factory-Tests,
- Current-State-Tests,
- Dashboard-Tests falls UI geändert,
- Python compile,
- JS syntax check falls JS geändert,
- SQLite integrity_check + foreign_key_check nach DB-Migration,
- keine Secret-Leaks im git diff.

Bestehende Tests dürfen nicht still übersprungen werden.
## 13. Abschluss / Handoff

Am Ende:
1. CURRENT_HANDOFF.md aktualisieren.
2. docs/CURRENT_STATE.json aktualisieren.
3. docs/ARCHITECTURE.md nur bei echter Architekturänderung ergänzen.
4. docs/BACKLOG.md korrekt aktualisieren — nur wirklich fertige Teile als DONE.
5. neues Session-Journal schreiben.
6. Branch mit sinnvollen Checkpoint-Commits pushen.
7. Abschlussbericht liefern mit:
   - fertig,
   - teilweise fertig,
   - Tests,
   - DB-Migrationen,
   - externe Aktionen (sollten in diesem Run möglichst 0 sein),
   - Kosten (0, sofern Owner nichts neu freigibt),
   - Owner-Gates,
   - Commit-Hashes,
   - exakt nächster sinnvoller Schritt.

Owner-Fragen gebündelt stellen, nicht einzeln.
Nicht erneut nach Entscheidungen fragen, die bereits in ZIPPOWORKZ_OWNER_POLICY.md dokumentiert sind.

## Leitprinzip

Nicht mehr Arbeit für den Owner erzeugen.
Technische Komplexität intern lösen.
Der Owner entscheidet; ZippoWorkz arbeitet.
