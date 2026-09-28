# AI Branch Delta Report — 2026-09-28

## Scope and method

- Source branch: `codex/ai-ops-20260913`
- Exact source tip: `5b3298b45aa2fb7c27bece08cfd7f7de42340cf1`
- Source merge base: `7db1cb5d803d7cde6cc0c65b1cab5731a842f48f`
- Main baseline: `2337e6e2acfa495a29ae663546d1fe9bed84241e`
- Newer comparison: `codex/20260928-next-stack` at
  `91c00d4fe5cb65e3306abef88bbd8257c868fcc9`
- Integration branch: `codex/ai-delta-integration-20260928`

The old branch contains 29 commits and 106 changed paths relative to its merge
base. It was inspected as a source of deltas; it was not merged, rebased, or
cherry-picked. Current Owner Policy v1.2, the current Creator-Ops database, and
the current dashboard remain authoritative.

## PORTED — SAFE_TO_PORT

| Component | Old source | Result |
|---|---|---|
| Value-free secret scan | `creator_ops/secret_scan.py` | Ported and corrected. Findings contain only path, line, and kind; suspected values are never retained or printed. The old environment-assignment regex was fixed so names such as `SERVICE_PASSWORD` are actually detected. |
| Project scanner entry point | `scripts/check_secret_leaks.py` | Ported as a small wrapper around the current package. |
| Optional pre-push guard | `.githooks/pre-push` | Ported. It scans only Git-tracked `creator-collab` files and uses the existing Python runtime; it does not alter global Git configuration. |
| Focused regression coverage | old security tests | Reimplemented as `tests/test_secret_scan.py`; an existing authentication fixture was explicitly marked `test-only` so the repository-wide guard remains strict and usable. |

This port adds no provider, credential store, policy file, database, external
request, or paid dependency.

## Validation compatibility adopted from next-stack

The full-suite validation exposed an existing isolation defect: library and
test callers of `create_server()` inherited the checkout's live publishing
configuration, while Meta adapter tests inherited the production authority
root. The already-better, generic isolation pattern from
`codex/20260928-next-stack` was applied without porting any TikTok,
Short-Factory, schema, dashboard, or media-routing feature:

- omitted web configuration is now fail-closed with
  `UnconfiguredInstagramAdapter`;
- the production CLI still passes its explicit `config.toml` path;
- Meta publishing tests use their temporary directory as authority root.

This is validation support for the current architecture, not functionality
from the old AI branch.

## ALREADY_DONE / EXPANDED_BY_NEWER_IMPLEMENTATION

| Old component and paths | Current evidence | Classification |
|---|---|---|
| Local run state, pause/resume, lease and checkpoint logic: `creator_ops/ai_ops.py`, safe parts of `creator_ops/local_ai_runtime.py`, `tests/test_ai_ops.py` | `creator_ops/control_plane.py`, `background.py`, `checkpoint.py`, `operations_audit.py`, existing run leases and the canonical SQLite event ledger | EXPANDED_BY_NEWER_IMPLEMENTATION |
| Secret provider and value-free readiness: `creator_ops/secret_provider.py`, `security_status.py`, related dashboard status | `creator_ops/secrets.py`, node-local DPAPI broker, `external_readiness.py`; next-stack additionally has catalogued connector secrets and broker-only writes | EXPANDED_BY_NEWER_IMPLEMENTATION |
| TikTok read prototype: `creator_ops/tiktok_api.py`, read portions of `channel_operations.py`, `tests/test_channel_operations.py` | next-stack `creator_ops/tiktok.py` implements official OAuth state, broker-backed tokens, creator-info preflight, direct/draft video init, upload, status polling, idempotency, readiness and focused tests on the canonical DB | EXPANDED_BY_NEWER_IMPLEMENTATION |
| Meta single-package push: `creator_ops/meta_push.py`, related `web.py`, CLI and tests | current `creator_ops/publishing.py`, `external_readiness.py`, queue intent/receipt/reconciliation and proven controlled Meta publishing | EXPANDED_BY_NEWER_IMPLEMENTATION |
| Public media checks: `creator_ops/public_media.py`, `META_MEDIA_RUNBOOK.md` | current HTTPS manifest/probe enforcement in the Meta adapter; next-stack `media_routing.py` preserves provider routing without claiming public hosting | EXPANDED_BY_NEWER_IMPLEMENTATION |
| Backup and restore proof: `scripts/validate_scheduled_recovery.py`, `SCHEDULED_RECOVERY_PROOF_2026-09-14.md` | `creator_ops/recovery.py`, backup-chain tests, verified restore rules and secret-reduced archives | EXPANDED_BY_NEWER_IMPLEMENTATION |
| Read-only VPS status: `scripts/vps_readonly_check.ps1`, `VPS_NEXT_RUN_2026-09-14.md` | current publishing authority plus connector-secret replication/status scripts and the 2026-09-27 multi-node handoff | EXPANDED_BY_NEWER_IMPLEMENTATION |
| Analytics windows and learning drafts in old channel operations | current append-only `manual_analytics_events`, `AnalyticsService`, Operations Audit; next-stack links 24/72/168h evidence into pattern learning | EXPANDED_BY_NEWER_IMPLEMENTATION |
| Media research/creation placeholders | next-stack Virality / Trend Intelligence, Topic-to-Short Factory and current media routing | EXPANDED_BY_NEWER_IMPLEMENTATION |
| Changes to `cli.py`, `current_state.py`, `publishing.py`, `web.py`, dashboard app/control/studio files and their existing tests | later main implementations plus protected next-stack deltas | ALREADY_DONE / EXPANDED_BY_NEWER_IMPLEMENTATION |

## SUPERSEDED / HISTORICAL_ONLY / REJECT

| Old component and paths | Classification | Reason |
|---|---|---|
| Separate channel draft state: `creator_ops/channel_ops.py`, `config/channels.json`, `dashboard/channels.*`, `tests/test_channels.py` | REJECT | Writes `data/channel_ops.json`, creating a second status truth outside the canonical operational SQLite core. |
| Fixed Local-AI task catalogue and Qwen worker: remaining `local_ai_runtime.py`, AI-Ops page, `scripts/ai_ops/*` | SUPERSEDED / REJECT | Hard-coded September tasks, models, paths and role policy would revive stale work and a parallel control surface. Current control plane is capability-based and model-agnostic. |
| Duplicate security and handoff policy: `config/security/*`, `scripts/ai_ops/PERMISSIONS_POLICY.json`, `ZIPPOWORKZ_SECURITY_AND_HANDOFF_POLICY_v1.md`, `creator_ops/handoff.py` | REJECT | `ZIPPOWORKZ_OWNER_POLICY.md` v1.2 is the only canonical Owner policy; AGENTS + Current State + current journal/handoff are the one status chain. |
| Historical state snapshots: old changes to `AUTOPILOT_CHECKPOINT.md`, `CURRENT_HANDOFF.md`, `PROJECT_RESUME.md`, `ZIPPOWORKZ_MASTER_GOALS.md`, `docs/CURRENT_STATE.json`, `docs/HUMAN_HANDOFF.md`, `docs/OFFICIAL_META_PUBLISHING.md` | HISTORICAL_ONLY | They describe September 13–15 state and must not overwrite later verified facts or policy. |
| Historical content and posting documents: `CONTENT_KIT_2026-09-13*.md`, `README_POSTING_2026-09-1*.md`, `MARA_HOFLADEN_SONNTAG_2026-09-14.md`, `MILO_9X16_STARTER_2026-09-14.md`, image inventories and source notes | HISTORICAL_ONLY | Useful as archive evidence only; not current operational truth. |
| Generated/public Mara and Milo images and the Milo reference image under `assets/` | HISTORICAL_ONLY / REJECT FOR PORT | No current operational need was established and the task forbids copying generated/public media solely because it exists. The archival tag preserves provenance. |
| Cloud/media/password/Meta Business Suite/GitHub package handoffs | HISTORICAL_ONLY | Superseded by the current adapter, secret broker, media routing and runtime handoffs. |
| `releases/ZIPPOWORKZ_META_DASHBOARD_GITHUB_2026-09-15.zip` and checksum | REJECT | Large historical release archive; must not be reintroduced into the active release path. |
| September 13–15 session journals | HISTORICAL_ONLY | Preserved by the archival tag rather than copied into current status history. |
| Old `.env.example` and `START_CREATOR_OPS.ps1` deltas | SUPERSEDED | Current secret names, connector catalog, launcher and multi-node runtime are newer. |

## Safety conclusion

- No direct old-branch merge was performed.
- No old policy, current-state snapshot, database, release ZIP, generated asset,
  external receipt, or secret provider was copied.
- No second operational database or parallel JSON status store was introduced.
- Newer TikTok, dashboard, Creator-Ops, media-routing, Virality and
  Topic-to-Short work remains untouched on `codex/20260928-next-stack`.
- The old branch can be retired only after the port is tested, merged into
  main, read back from the remote, and its exact tip is preserved by
  `archive/ai-ops-20260913-final`.

## Validation result before main integration

- Python: `169 passed`
- Dashboard JavaScript: `5 passed`
- Python compile: passed
- Dashboard JavaScript syntax: passed
- SQLite `integrity_check`: `ok`
- SQLite `foreign_key_check`: `0` rows
- Git-tracked project secret scan: `OK (357 files checked)`
- `git diff --check`: passed

## Integration and retirement result

- Main merge commit: `b862f16c671e952e48c05cd7c83de65c0095caeb`
- Remote main readback matched the merge commit before retirement.
- Archive tag: `archive/ai-ops-20260913-final`
- Archive tag target: `5b3298b45aa2fb7c27bece08cfd7f7de42340cf1`
- Old remote branch `codex/ai-ops-20260913`: deleted and verified absent.
- No force push, history rewrite, external platform action, secret write, or
  paid action was performed.
