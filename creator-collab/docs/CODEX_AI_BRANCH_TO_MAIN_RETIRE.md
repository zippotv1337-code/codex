# CODEX TASK — AI BRANCH DELTA INTEGRATION + RETIRE

Status: OWNER-AUTHORIZED GOAL
Stand: 28.09.2026
Repository: zippotv1337-code/codex

## Owner intent

Integrate the useful, still-relevant content from `codex/ai-ops-20260913` into the current ZippoWorkz main in the form that best fits today's architecture. Do NOT blindly merge the old branch. After successful integration and verification, retire the old AI branch.

## Current verified Git facts

- main at task creation: `2337e6e2acfa495a29ae663546d1fe9bed84241e`
- old AI branch: `codex/ai-ops-20260913`
- AI tip: `5b3298b45aa2fb7c27bece08cfd7f7de42340cf1`
- merge base: `7db1cb5d803d7cde6cc0c65b1cab5731a842f48f`
- branch is diverged: 29 commits ahead / 37 commits behind current main

A direct merge is explicitly NOT the intended method.

## Mandatory bootstrap

Read first:
1. ZIPPOWORKZ_START_HERE.md
2. ZIPPOWORKZ_OWNER_POLICY.md
3. AGENTS.md
4. creator-collab/AGENTS.md
5. creator-collab/CURRENT_HANDOFF.md
6. creator-collab/docs/CURRENT_STATE.json

Newest confirmed owner policy and present runtime architecture override old branch assumptions.

## Integration method

Continue on the prepared branch:
`codex/ai-delta-integration-20260928`

Compare every meaningful AI-branch component against:
1. current main,
2. current active newer work, especially `codex/20260928-next-stack` where relevant,
3. current Owner Policy.

Classify each old-AI component as:
- ALREADY_DONE
- EXPANDED_BY_NEWER_IMPLEMENTATION
- SAFE_TO_PORT
- HISTORICAL_ONLY
- SUPERSEDED
- REJECT

Do not copy an older implementation when current main or next-stack already has a newer/better equivalent.
## Areas to inspect

The old AI branch includes, among other things:
- local_ai_runtime / ai_ops / handoff logic
- security / permissions / secret provider / secret scan
- channel operations
- TikTok API prototype
- Meta/public media helpers
- AI-Ops dashboard pages
- Local-AI startup scripts
- recovery / read-only VPS tooling
- older handoffs, current-state snapshots and historical session docs
- generated/public media and an old release ZIP

Treat old docs and session records as evidence, not automatically-current truth.

## Protect newer architecture

Do NOT regress or replace:
- ZIPPOWORKZ_START_HERE.md
- ZIPPOWORKZ_OWNER_POLICY.md
- current AGENTS bootstrap
- CurrentStateService
- current Creator-Ops DB architecture
- newer TikTok implementation from next-stack
- current Dashboard architecture
- current Meta/Instagram publishing and reconciliation
- current Fiverr state
- Virality / Trend Intelligence
- Topic-to-Short Factory
- current media routing
- current secret-broker approach

Do not reintroduce ComfyUI.
Do not reintroduce old duplicate owner policies.
Do not create a second operational database or second status truth.

## Port rules

For SAFE_TO_PORT items:
- port the smallest useful delta onto the integration branch;
- adapt it to current APIs/schema/policy instead of copying old files wholesale;
- add/update focused tests;
- no secret values;
- no blind external writes;
- no cost;
- no generated/public asset copied unless rights/provenance and current need are clear.

The old release ZIP must not be copied into the active release path merely because it exists.

## Validation

Before main integration:
- all relevant Python tests green;
- JS checks green where changed;
- compile checks green;
- SQLite integrity_check + foreign_key_check if DB code touched;
- secret scan green;
- no duplicate routes/modules competing with current implementations;
- no stale policy/current-state file becoming canonical;
- no unresolved merge conflict hidden by deletion/replacement.

Produce an AI-BRANCH-DELTA report containing every component and its classification.
## Main integration authorization

The owner explicitly authorizes this task goal:
when the integration branch is fully validated and there is no unresolved critical/security ambiguity, merge the approved AI delta into main.

Because the old branch touches Auth/Security/Publishing areas, STOP rather than merge if validation exposes an unresolved critical conflict, secret risk, destructive migration, or uncertain external state.

## Retire the old AI branch

Only AFTER:
1. useful deltas are either integrated or explicitly classified as SUPERSEDED/HISTORICAL/REJECT,
2. tests are green,
3. main contains the resulting verified integration,
4. a final readback proves the merge is present,

then retire `codex/ai-ops-20260913`.

Before deletion, preserve its exact final tip `5b3298b45aa2fb7c27bece08cfd7f7de42340cf1` as a clearly named archival Git tag if possible:
`archive/ai-ops-20260913-final`.

Then delete the active branch ref `codex/ai-ops-20260913` so it can no longer be mistaken for an active development line.

Do not delete the archival evidence/history.

## Final output

Return one compact report:
- PORTED
- ALREADY_DONE / EXPANDED
- SUPERSEDED / HISTORICAL / REJECTED
- TESTS
- MAIN MERGE COMMIT
- ARCHIVE TAG
- OLD AI BRANCH RETIRED: YES/NO
- remaining blockers, if any
- next smallest useful task

Leitsatz:
Use the old AI branch as a source of useful deltas, not as a replacement for today's ZippoWorkz.
