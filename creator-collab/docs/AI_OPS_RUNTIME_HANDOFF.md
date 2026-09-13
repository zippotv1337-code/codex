# CODEX RUNTIME HANDOFF

generated_at: 2026-09-13T20:59:00+02:00
source_repo: https://github.com/zippotv1337-code/codex
source_commit: a6b2ef4b0738d9ce659c5a2947c2e39cf495b17c (implementation; pushed codex/ai-ops-20260913, main unchanged)
protocol_version: ai-ops-v1

## GLOBAL RULES

- Work only in C:/Zippoworkz; project Workspace/codex_ingest/creator-collab.
- Existing dashboard and canonical data/review_dashboard.db; schema 5. No second dashboard/DB architecture.
- Local AI allowed tasks: health, tests, triage, summary. No arbitrary model-generated commands or file writes.
- No platform actions, identity/OTP/secrets, payments, persona rewrites, Git push or workspace replacement from Local AI/VPS.
- Tasks/heartbeats/control stored in existing runtime_events. Exclusive local-AI lease prevents duplicate execution.
- Owner activity (<30s idle), UI Pause or Stop -> checkpoint; finish bounded atomic checks, release model. No forced normal kill.
- Each test command <=60s; model stream bounded (30s socket timeout / 90s overall checked between chunks); unload keep_alive=0; one model.
- Retries never indefinite. Maximum two attempts; BLOCKED is not auto-retried. DONE stays done.

## CURRENT SYSTEM STATE

- Dashboard: http://192.168.188.131:4180/ai-ops, password-protected; health/database ok.
- AI Ops navigation, agent states, task results, Start/Pause/Resume/Stop active.
- Four initial tasks finished with real evidence. Qwen3:8b produced LOCAL_AI_ANALYSIS_DRAFT.md; no model remained loaded.
- Original operational database absent from received GitHub archive/root. Current schema has 0 content/assets/publications/real analytics. No fake history restored.
- Git metadata safely recovered in the SAME workspace, baseline main fetched without replacing files. Local edits remain preserved; safe sync shows DEGRADED while dirty. Source fingerprint recorded with the run.
- VPS OFFLINE. No registered VPS or remote transport available; remote watcher implementation/deployment is not claimed complete.
- Existing creator, scheduling, publishing, rights and account logic preserved; no external platform actions.

## LOCAL AI — EXECUTABLE NEXT TASKS

mode: LOCAL_SAFE_ONLY
entry: C:/Zippoworkz/START_ZIPPOWORKZ.cmd or dashboard /ai-ops
queue_source: creator_ops/ai_ops.py TASKS + persisted runtime_events
pause_signal: aiops.control=PAUSED/STOPPED or local user activity

1. Read current persisted task status; skip the four DONE steps.
2. If no NEXT/PAUSED allowlisted task exists: write LOCAL_AI_RESULT.md, log IDLE_CLEAN, release lease and exit.
3. Do not restore/create content, synthesize analytics, scan other drives, reset attempts, or manufacture follow-up work.
4. New tasks only after a concrete new Codex/Owner delta and verified allowlist update.

Output: Handoff/LOCAL_AI_RESULT.md; optional Handoff/LOCAL_AI_ANALYSIS_DRAFT.md explicitly unverified draft; append Logs/local_ai_runtime.log.

## VPS — EXECUTABLE NEXT TASKS

mode: WAITING_FOR_OWNER_CONNECTION
1. Without an explicit configured VPS/transport: do not connect, do not claim ONLINE, do not run from the desktop as if remote.
2. Once supplied: configure/test a bounded read-only watcher against the existing health route and sanitized handoff; no heavy model or shared DB writes. This part is still gated, not implemented as a fake desktop VPS.
3. Confirm actual host execution and authenticated result transport before integrating remote heartbeat.
Output ownership: VPS alone writes Handoff/VPS_RESULT.md after a real run; currently no success file should be fabricated.

## OWNER ACTIONS

1. Provide the previous operational SQLite backup/exact original location for verified recovery.
2. If remote watcher is wanted, provide exact VPS and intended secure transport. No open public ports by default.

## NEXT CODEX INPUT

Read this file and newest project journal. Preserve current implementation. With no new Owner backup/VPS signal, STOP.
With a real backup: validate source read-only and integrity/schema; snapshot current canonical DB; plan controlled recovery and validate before switching. Never infer live receipts from docs.
With a VPS signal: deploy/test only the read-only watcher and verify remote provenance before showing ONLINE. Do not restart finished local tasks.
