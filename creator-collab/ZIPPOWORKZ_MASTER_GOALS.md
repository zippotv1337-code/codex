# ZIPPOWORKZ — MASTER GOALS

Last consolidated: 2026-09-09 — AUTONOMY LIFT completed locally; Meta WAITING_SIGNAL.

Current execution authority: only Lane A LOCAL AUTONOMY and Lane B EXTERNAL PLATFORM PROOF.
Lane A COMPLETE / SKIP_DONE; Lane B WAITING_SIGNAL after one targeted check.
All other executable lanes WAITING_SIGNAL. Strategic goals below are not execution orders.
Evidence: docs/LOCAL_AUTONOMY.md and sessions/2026-09-09-local-autonomy.md.

## Purpose and precedence

This is the single active goals list for ZippoWorkz. Historical handoffs,
reports, backlogs and journals remain evidence only; they do not create a
second active backlog.

Priority on conflict:

1. Current explicit Owner instruction
2. Latest local session journal
3. This file
4. `docs/CURRENT_STATE.json`
5. `CURRENT_HANDOFF.md`
6. `OWNER_DECISIONS.md`
7. `AUTOPILOT_CHECKPOINT.md`
8. Older journals and reports

New ideas belong in the Idea Inbox. A completed item reopens only after a
reproducible defect, changed requirement, external signal, real data, or a
direct dependency. Otherwise it is `SKIP_DONE`.

## North stars

| ID | Goal | Status |
|---|---|---|
| NS-01 | ZippoWorkz is a real, later reusable creator/content/business operating system. | WAITING_SIGNAL |
| NS-02 | Creator learning loop: Content → Publish → Audience → Analytics → Learning. | WAITING_SIGNAL |
| NS-03 | Revenue learning loop: Offer → Customer → Intake → Fulfillment → Revenue → Learning. | WAITING_SIGNAL |
| NS-04 | Operations first: posts → analytics → leads → revenue before feature expansion. | WAITING_SIGNAL |

## Main goals

| ID | Goal | Status | Evidence / exit condition |
|---|---|---|---|
| M-01 | One canonical ZippoWorkz surface | DONE | One visible product, primary launcher, dashboard and operational DB; runtime contract verified 2026-09-08. |
| M-02 | Real Instagram analytics in ZippoWorkz | WAITING_SIGNAL — OBSERVING | Zwei echte Leona-Messungen sind gespeichert: Publication 7 (13 Aufrufe, 11 Betrachter, 1 Like; spät als 24h-Fenster erfasst) und Publication 4 (19 Aufrufe, 16 Betrachter, 2 Likes, 1 Profilbesuch; spät als 72h-Fenster erfasst). Beide gehören zum selben Contentpaket; die Learning-Logik zählt sie bewusst nur als einen unabhängigen Inhalt. Complete when real 24h/72h/168h snapshots create the first evidenced learning cycle. |
| M-03 | Official Meta/Instagram API proof | DEFERRED — EXTERNAL_SIGNAL_ONLY | Preserve the adapter; do not let Meta configuration block local content, analytics or revenue work. Resume only after a confirmed Developer-App/account-linkage signal; Leona read-only → one controlled publish → receipt/reconcile → Mara. |
| M-04 | Fiverr Gig 1 live: AI Workflow Automation | WAITING_SIGNAL | Die eingeloggte Verwaltung zeigte am 2026-09-08 `AKTIV 1`; Fiverr lieferte in der Tabelle einen Fehler und die öffentliche Ansicht war CAPTCHA-blockiert. Exit: öffentlicher Gig-Link störungsfrei sichtbar und dokumentiert. Basic $149, Standard $349, Premium $699. |
| M-05 | First real lead, order and revenue | BLOCKED_BY_M-04 | A genuine inquiry, order, fulfillment and revenue record; dry runs never count. |
| M-06 | Standardize fulfillment from first order | LATER | Learn recurring requests, revisions, integrations and boundaries. Gig 2 only after Gig 1 proof. |
| M-07 | Maintain real content cadence | WAITING_SIGNAL | Verbindliche öffentliche Richtung seit 2026-09-08: ca. 70 % glaubwürdiger Alltag/Setting/Handlung und 30 % glamourös/sexy angedeutet, stets `SFW + PUBLIC_SFW`. Leona bleibt urban/glamourös, Mara rural/sportlich; reale Analytics steuern Varianten, veröffentlichte Top-Picks werden nicht recycelt. |
| M-08 | Stories as a first-class lane | PARTIAL / LOCAL_IMPLEMENTED | Local preview/edit/approve/change/reject/pause/plan persistent and honest; official Story publishing waits for supported proof. |
| M-09 | Engagement from real comments | WAITING_SIGNAL | Use actual text only; manual suggestions, never mass engagement. |
| M-10 | Secure local/mobile operations | MOSTLY_DONE / LATER | Protected LAN, local dashboard and no router forwarding; no expansion without an actual need. |
| M-11 | Recovery, backup and journals | MAINTAINED_IN_LANE_A | Journal each meaningful run; pre-change backup for critical state; restore validation; no secrets. |
| M-12 | GitHub trustworthy mirror | DONE / SYNC_VERIFIED_2026_09_08 | main 3ac0cb8 externally confirmed; identical project tree, no secrets/DB/backups or force push. Evidence: sessions/2026-09-08-2255-github-sync.md. Visibility remains Owner-only; new changes may reopen normal sync. |
| M-13 | Simple model/runtime compatibility | MAINTAINED_IN_LANE_A | Stable current model/runtime is sufficient; stronger models are optional. |
| M-14 | Learn sellable product from demand | WAITING_REAL_SIGNALS | Learn from real inquiries, orders and fulfillment. |
| M-15 | Keep offers separate | LATER | Gig 1 automation (149/349/699) remains separate from historical SFW content packs (45/95/175). |
| M-16 | Expand channels after proof | LATER | TikTok, Threads, link page, video and remixes wait for stable operations plus real signals. |
| M-17 | Adult/Paid lane separate | LATER / OWNER_GATE | Public channels remain SFW; no adult work without explicit authorization. |
| M-18 | Long-term productization | LATER | No early multi-tenant SaaS or broad platform build. |

## Temporary execution goals — maximum two active lanes

| ID | Goal | Status | Evidence |
|---|---|---|---|
| LANE-A | Safe local autonomy | COMPLETE / SKIP_DONE | Three registered tasks executed with Result 0; one backend; idle, watchdog, integrity and recovery verified. |
| LANE-B | Official Meta / Instagram proof | WAITING_SIGNAL | Developer /apps/ redirected to public homepage; no verified app list. No further loop. |
| T-002 | Independent real analytics | WAITING_SIGNAL | Two manual Leona measurements, one independent package; official read unavailable. |
| T-003 | Fiverr public proof | WAITING_SIGNAL | Not retried in this run; no third lane. |

## Active experiments

### E-001 — GoFundMe: ZippoWorkz Support / Frühfinanzierung

- Status: **LIVE**; type: **EXPERIMENT**.
- Public campaign: <https://gofund.me/a5fafb44c>
- Purpose: test early willingness to support the next ZippoWorkz phase and learn which message earns meaningful shares/support.
- Track real values only: amount raised, donor count, shares, meaningful feedback, first-donation date, and optionally useful donation ranges.
- Donations are crowdfunding/support signals, **not** Fiverr or customer revenue. No invented traction, paid promotion, or constant copy rewrites.
- Review only after a meaningful donor/share signal or direct Owner request.

## Idea inbox

| ID | Idea | Status | Promotion trigger |
|---|---|---|---|
| I-001 | Separate ZippoWorkz Ops and Meta specialist lanes | IDEA | Clear time benefit and separate files/lanes. |
| I-002 | Dashboard layout refinement after Owner screenshot | IDEA | Concrete usability issue. |
| I-003 | Per-post 24h/72h/168h mini analytics card | PROMOTED_TO_M-02 | Current priority. |
| I-004 | Leona/Mara and 7/30-day leaderboard | PROMOTED_TO_M-02 | Real analytics. |
| I-005 | Video/Reels with suitable tools | LATER | Static loop stable and a video hypothesis. |
| I-006 | Polished remote access | LATER | Real offsite need. |
| I-007 | Link page / monetization funnel | LATER | Measurable destination needed. |
| I-008 | Winner remix / lightweight A/B | LATER | Enough real metrics. |
| I-009 | Additional personas | LATER | Leona/Mara economically useful. |
| I-010 | SaaS / multi-user packaging | LATER | Repeated external demand. |
| I-011 | Separate adult/paid lane | OWNER_GATE / LATER | Explicit Owner go. |
| I-012 | Revisit SFW content-pack offer | LATER | Automation Gig demand evidence. |
| I-013 | Kickstarter campaign | IDEA / ACCOUNT_CREATED | Product story, demo, rewards and realistic goal first. |
| I-014 | GoFundMe campaign | PROMOTED_TO_E-001 / LIVE | Campaign public at the E-001 URL. |

## Gates

| ID | Gate | Handling |
|---|---|---|
| GATE-META-01 | Meta developer/account verification | Wait; do not loop. |
| GATE-FIVERR-01 | Final public Fiverr state | Verify in a dedicated run. |
| GATE-GITHUB-01 | Repository visibility | Owner only. |
| GATE-PAID-01 | Paid services, ads or subscriptions | Owner approval. |
| GATE-ADULT-01 | Adult generation/publishing | Owner approval. |
| GATE-IDENTITY-01 | Selfie, ID, OTP, tax or phone identity | Owner only. |

## Permanent operating rules

- Codex local operations reference integrated on 2026-09-08: `AGENTS.md` routes
  local Python/operations work to `docs/CODEX_ZIPPOWORKZ_LOCAL_DESKTOP_OPS_SETUP.md`.
  Existing `.venv` (verified Python 3.14.7) and canonical `data/review_dashboard.db`
  are preserved. Historical setup deferral was superseded by the explicit 2026-09-09 autonomy task; current local jobs are documented in docs/LOCAL_AUTONOMY.md.
  Evidence: `sessions/2026-09-08-2251-codex-local-ops.md`.
- Preserve the existing core. Do not rebuild it because a new run begins.
- PUBLIC_SFW only for public creator channels; personas remain transparent as fictional AI creators.
- No secrets, passwords, tokens, cookies or identity material in code, DB, journals or Git.
- At run end update journal, current state, handoff and this file; mark completed temporary goals and stop when no active signal remains.

## Next operational sequence

1. Owner supplies visible successful Meta Developer access; then one Leona read/preflight.
2. Until that signal, only already enabled safe local background maintenance.
3. No content generation, Fiverr work, new dashboard, Git automation or onboarding retries.
