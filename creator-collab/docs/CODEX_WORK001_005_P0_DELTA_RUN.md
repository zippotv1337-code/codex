# CODEX MASTER TASK — WORK 001–005 → CURRENT P0 DELTA

**Status:** READY_FOR_CODEX  
**Stand:** 28.09.2026  
**Baseline documents:** WORK 001, 002, 003, 004, 005 from 25.09.2026  
**Verified current remote main at task creation:** `9a774d50b135209e987b01ae8cde5facf14e0ca7`

## 0. Purpose

Use WORK 001–005 as the original P0 requirements/baseline, but implement against the **current consolidated ZippoWorkz state**.

Do **not** rebuild the 25.09 proposal literally when the project has since evolved further.

For every WORK requirement classify the present state as:

- `DONE`
- `EXPANDED`
- `SUPERSEDED_BY_BETTER_CURRENT_DESIGN`
- `OPEN`
- `BLOCKED_BY_OWNER_GATE`
- `HISTORICAL_ONLY`

Then implement only the remaining safe P0 delta.

## 1. Mandatory bootstrap and workspace safety

Read first:

1. `ZIPPOWORKZ_START_HERE.md`
2. `ZIPPOWORKZ_OWNER_POLICY.md`
3. `AGENTS.md`
4. `creator-collab/AGENTS.md`
5. `creator-collab/CURRENT_HANDOFF.md`
6. `creator-collab/docs/CURRENT_STATE.json`
7. latest relevant session journal

The current Owner Policy and current verified runtime/code state override old assumptions in WORK 001–005.

**Important local safety fact:** the long-lived checkout at `C:\Zippoworkz\Workspace\codex_ingest` may contain stale/uncommitted historical changes. Do not reset, clean, stash, or overwrite that tree as part of this task.

Create a **fresh worktree/branch from current `origin/main`**, for example:

`codex/work001-005-p0-delta-20260928`

No force push. No history rewrite.
## 2. WORK 001 baseline — P0 inventory / context consolidation

WORK 001 was a read-only inventory. Its central problem statement was:

- current knowledge was spread across multiple parallel context/handoff/status documents;
- older documents could contradict newer operational evidence;
- historical handoffs should become evidence/history rather than competing current truth;
- one clear responsibility should exist for durable context, decisions, current task, runtime state, evidence, current handoff and history.

WORK 001 proposed a future canonical structure, but that structure was a **proposal**, not a mandate to recreate it literally.

Current implementations such as `ZIPPOWORKZ_START_HERE.md`, central Owner Policy and current runtime state may supersede parts of that proposal.

### P0 delta question

Does the current system now give a new Chat/Work/Codex/VPS/Local-AI run one unambiguous load order and truth hierarchy without requiring old chats?

If yes, mark the old structural proposal `SUPERSEDED_BY_BETTER_CURRENT_DESIGN` where appropriate rather than moving files unnecessarily.

## 3. WORK 002 baseline — P0.1 implementation blueprint

WORK 002 converted WORK 001 into an implementation-ready plan.

Preserve these architectural principles:

- do not repeat the general repository audit;
- `creator-collab/creator_ops/current_state.py` / `CurrentStateService` is the existing secret-free runtime snapshot mechanism;
- do not silently introduce a second status generator or manually maintained competing status truth;
- the documented operational Creator-Ops DB is `creator-collab/data/review_dashboard.db`;
- migrations/renames require compatibility, backup, tests and rollback;
- old documents remain evidence unless safely replaced by pointers/archival classification;
- changes should be additive/minimal before destructive cleanup.

The old proposed `context/`, `state/`, `handoff/`, `archive/` tree is not itself a requirement if today's START_HERE/policy/handoff architecture already solves the same problem more cleanly.

## 4. WORK 003 baseline — P0.2 AI/Git/security integration

WORK 003 found the old AI branch strongly divergent and prohibited a blind merge.

That original P0.2 problem has materially changed:

- useful AI-branch deltas have now been selectively integrated;
- old branch `codex/ai-ops-20260913` has been retired;
- its history is preserved by `archive/ai-ops-20260913-final`;
- current main has a value-free secret scanner and publishing/test isolation.

Do not reopen the old AI branch integration as new work.

Instead verify current evidence and classify the old P0.2 requirements as DONE/EXPANDED/SUPERSEDED where proven.

Still inspect only genuinely remaining risks such as:
- tracked generated/public assets whose rights/public status are not established;
- active release/binary artifacts, if any remain outside archival history;
- any unresolved secret/history risk not already covered by current scanning/evidence.

Do not delete assets or rewrite history without an explicit current gate.
## 5. WORK 004 baseline — P0.3 data/state contracts

Keep the core contract:

- **GitHub:** versioned code, tests, schemas, docs, Owner Policy and deliberately public assets.
- **Creator Ops:** operational content, assets, queue, publishing, analytics, Fiverr and related operational state.
- **Canonical operational DB:** `creator-collab/data/review_dashboard.db`.
- **CurrentStateService:** derived secret-free runtime/status view.
- **Local AI:** jobs, results, checkpoints, handoffs/evidence — not a competing global operational DB.
- **VPS:** orchestration/control/read interfaces and evidence — not a second uncontrolled Creator-Ops truth.
- **Handoffs/Journals:** derived evidence/history, not an independent operational database.

Current main has already advanced to schema 6. Preserve that architecture.

Do **not** merge old databases merely because multiple historical DB names exist.

If an old DB/path appears:
1. identify whether it is active, historical, fixture, backup or stale;
2. do not migrate data without proven need;
3. require backup + mapping + dry-run + integrity + foreign-key check + rollback for any real migration.

Unknown remains `NOT_VERIFIED`.

## 6. WORK 005 baseline — final Codex package

WORK 005 required:

- P0.1 first: minimal context/agent consolidation;
- P0.2 next: selective AI/security integration, never blind branch merge;
- P0.3 next: single data/state contract, no second DB/status truth;
- small reversible changesets;
- protect Creator Ops, Meta/Instagram, Queue/Scheduler, Dashboard, Fiverr, Local AI and DB;
- tests and explicit rollback;
- do not turn proposals into claimed live state.

Treat WORK 005 as the execution ordering baseline, but collapse already-completed steps into evidence instead of redoing them.
## 7. Current consolidated state that must be protected

At task creation current remote main is `9a774d50b135209e987b01ae8cde5facf14e0ca7`.

Already integrated/protected architecture includes:

- canonical `ZIPPOWORKZ_START_HERE.md`;
- canonical `ZIPPOWORKZ_OWNER_POLICY.md` v1.2;
- AI-branch delta integration + retirement;
- value-free secret scanner and optional tracked-file pre-push guard;
- fail-closed test/library publishing isolation;
- Creator-Ops SQLite schema 6;
- official TikTok v2 adapter with OAuth, creator-info preflight, direct/draft paths, idempotency and reconciliation;
- TikTok credentials via local secret broker, not DB/Git/logs;
- Virality / Trend Intelligence;
- Topic-to-Short Factory through `QA_READY`;
- media routing with Higgsfield preference / OpenAI fallback and cost gate;
- 24/72/168h real-analytics learning hooks;
- current Dashboard extensions;
- Fiverr owner-save checkpoint;
- AI branch archived at `archive/ai-ops-20260913-final`;
- Next Stack archived at `archive/20260928-next-stack-final`.

Do not regress any of these to older WORK-era designs.

Do not reintroduce ComfyUI.
Do not recreate duplicate Owner policies.
Do not create another dashboard.
Do not create a second operational DB.
## 8. Phase A — produce the WORK 001–005 delta matrix

Before changing code, create a precise matrix:

| Requirement/source | Original intent | Current evidence/path | Classification | Remaining delta | Action |
|---|---|---|---|---|---|

Cover every material requirement from WORK 001–005, but group repetitive items.

The matrix must explicitly show where today's architecture is **better/newer** than the 25.09 proposal.

Do not treat an old filename/path as a goal by itself.

## 9. Phase B — implement remaining P0.1 delta

Only if still needed:

- remove ambiguity in load order through pointers/documentation, not new parallel truth;
- mark old/current documents clearly as canonical, derived, historical or superseded;
- ensure START_HERE leads to Owner Policy and current runtime/project evidence;
- ensure old OWNER_DECISIONS files cannot override central Owner Policy;
- ensure current handoff is derived from current evidence and does not silently revive old tasks;
- reduce repeated full-context scanning where safe.

Prefer compatibility pointers and archival markers over moves/deletes.

If P0.1 is already fully solved, document evidence and make no artificial change.

## 10. Phase C — implement remaining P0.2 delta

Do not redo the retired AI-branch integration.

Only close still-open security/provenance gaps that are safe and current.

Examples:
- classify tracked generated/public assets;
- produce manifest/provenance evidence if useful;
- verify no active old release ZIP is treated as current;
- verify secret scanner/pre-push guard behavior remains fail-closed for real secrets and does not expose values.

Asset deletion, public/private visibility changes, history rewriting or destructive cleanup remain owner-gated.

If no safe P0.2 delta remains, mark it DONE/EXPANDED with evidence.
## 11. Phase D — implement remaining P0.3 delta

Verify the data/state contract against actual current code and schema 6.

Required outcome:

- one operational Creator-Ops DB;
- no second manual/project JSON truth competing with CurrentStateService;
- every derived status has provenance/timestamp where appropriate;
- Local AI/VPS interfaces exchange explicit jobs/results/evidence, not uncontrolled DB replicas;
- stale/unknown states remain UNKNOWN/NOT_VERIFIED;
- DB backup/integrity rules remain intact.

If current implementation already satisfies the contract, document it and do not invent another abstraction.

Any real DB schema change in this phase requires the existing Owner gate and must not be merged automatically.

## 12. Simplicity / owner-friction requirement

Policy v1.2 principle applies:

**The Owner decides; the system works.**

Therefore identify manual steps that still exist only because of legacy architecture.

For each remaining recurring manual step ask:
- can an existing agent/API/dashboard perform it?
- can it be bundled?
- can it be removed permanently?
- does the Owner really need to touch it?

Do not create new manual maintenance burdens merely to satisfy an old WORK diagram.
## 13. Tests and acceptance

Run the tests required by actual changes.

Minimum verification before completion:

- relevant Python pytest suite;
- Python compilecheck;
- Dashboard/Node tests if touched;
- JS syntax check if touched;
- `git diff --check`;
- secret scan;
- `CURRENT_STATE.json` validation;
- SQLite `integrity_check`;
- SQLite `foreign_key_check`;
- verify no new second DB/status source was introduced;
- verify Owner Policy and START_HERE remain canonical.

No external platform post/message/action is required for this P0 run.
No purchase/cost.
No secret output.

## 14. Git and merge rules

Work on the isolated P0 branch.

Create meaningful checkpoint commits and push the branch.

Normal docs/compatibility improvements may be merged after green validation according to current Owner Policy.

STOP before main merge if the resulting delta touches a newly introduced critical:
- Owner Policy change,
- Auth/Security semantics,
- destructive DB/schema migration,
- critical publishing-core behavior,
- irreversible external action.

Do not ask the Owner questions already answered in current Owner Policy.

## 15. Completion format

Return exactly:

### WORK 001–005 DELTA MATRIX
Summary counts for DONE / EXPANDED / SUPERSEDED / OPEN / BLOCKED / HISTORICAL.

### IMPLEMENTED NOW
Only actual changes.

### ALREADY SOLVED BY NEWER ARCHITECTURE
Show evidence/current paths.

### REMAINING P0
Only genuine remaining work.

### TESTS
Exact results.

### COMMITS
Branch and commit hashes.

### OWNER GATES
Bundled; only gates that actually remain.

### MAIN STATUS
Merged/not merged and exact current main hash.

### NEXT STEP
Exactly one smallest useful next task.

Definition of Done:
WORK 001–005 have been reconciled against today's system; no old proposal has regressed newer architecture; all safe remaining P0 deltas are either implemented or explicitly gated; one current truth model remains.
