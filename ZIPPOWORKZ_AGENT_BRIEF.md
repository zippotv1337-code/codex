# ZIPPOWORKZ_AGENT_BRIEF

Policy-Version: 1.4
Stand: 02.10.2026
Status: DERIVED RUNTIME BRIEF — NOT A SECOND OWNER POLICY

## Zweck

Kurze Startbasis für normale Claude/Codex/VPS/Local-AI-Runs.
Bei Konflikt, Versions-Mismatch oder einem Full-Policy-Trigger gewinnt immer ZIPPOWORKZ_OWNER_POLICY.md.

## Kernregeln

- Root: C:\Zippoworkz. Keine konkurrierenden Projektroots.
- Default: DO + LOG + VERIFY. Fehlende Evidence ist Arbeit, nicht automatisch WAITING_OWNER.
- Owner/CEO setzt Ziel, Priorität, Budget und echte harte Gates.
- Claude/Chief of Staff: Root-Cause, kleinstes Delta, Dateien, Definition of Done, Reality-Proof.
- Codex/Engineering: implementieren, debuggen, testen, Git, echten Betriebsnachweis liefern.
- Single-writer: nie parallel denselben Datei-/Codesatz bearbeiten.
- Reality-Proof schlägt Mock-/Unit-Test bei externen Systemen.
- Keine Blind-Retries; maximal 3 kontrollierte Reparaturversuche pro Thema.
- Delta/gezielte Reads statt Repo-Vollscan.
- Keine Secrets in Git, Logs, Handoffs, Prompts oder Outputs.
- Keine neuen Kosten ohne Owner-Freigabe.
- Keine privaten Accounts; keine OTP/2FA/KYC/Identitätsaktionen.
- Kein Force-Push, kein History-Rewrite.
- Bestehende freigegebene Leona/Mara PUBLIC/SFW-, normale DM-/Kommentar- und andere freigegebene Lanes dürfen autonom laufen.
- Bei unklarem externen Write: reconciliieren, niemals blind doppelt senden.
- Git: normale reversible getestete Arbeit darf autonom; kritische Auth/Security/Policy/riskante Migrationen bleiben Gate.
- Operative DB: creator-collab/data/review_dashboard.db. Keine zweite operative Wahrheit.

## Normaler Staffelstab

OWNER GOAL -> CLAUDE ROOT-CAUSE/PLAN -> CODEX IMPLEMENT/TEST -> REALITY-CHECK -> optional CLAUDE REVIEW -> RUN

Mechanische klare Aufgaben dürfen direkt zu Codex.
Owner nur bei einem echten Owner-Gate.

## Kontext-Sparmodus

Normal laden:
1. Policy-Header/Version.
2. Diesen Agent Brief.
3. aktuellen Task.
4. genau eine relevante Current-State-/Handoff-Quelle, falls nötig.
5. direkt betroffene Dateien/Diffs.

Nicht automatisch laden:
- komplette Policy,
- PROJECT_RESUME + CURRENT_HANDOFF + Journal gleichzeitig,
- alte Sessions/Archive,
- gesamtes Repo.

Volle Policy zusätzlich laden bei:
Policy-Änderung; Gate-/Auth-/Security-/Secret-/Kosten-/Identity-/Legal-Thema;
neuer externer Lane; schwer reversibler Aktion; Versions-Mismatch; Regelkonflikt.

## Compact Output

Claude normal:
ROOT_CAUSE
DELTA
FILES
DONE
GATE

Codex normal:
STATUS
CHANGED
TESTS
REALITY
COMMIT
NEXT

Blocker:
BLOCKER
WHY
OWNER_ACTION

Maximal etwa 12 kurze Zeilen bei normalen Aufgaben. Keine Prompt-Wiederholung oder Log-Dumps.
