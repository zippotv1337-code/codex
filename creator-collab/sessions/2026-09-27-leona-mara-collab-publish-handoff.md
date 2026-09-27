# Leona × Mara Collab — Publish Handoff 2026-09-27

## Owner decision
- Feed-Collab + passende Story sind ausdrücklich zur Veröffentlichung freigegeben.
- Vor **jedem** Higgsfield-Call muss separat Owner-Freigabe eingeholt werden.
- Für dieses Paket wurde **kein Higgsfield-Call** ausgeführt; Kosten: 0 €.

## Reused source asset
- Library title: `Gemeinsam stärker: Collab-Workout im Gym.png`
- Source SHA-256 after transfer: `DDF1F47BC9CA5FE134B81961FDDBC7A17E47ADB2D27B18D7F97043FB988592D2`
- No new motif/generation; only mechanical resizing/JPEG conversion.

## Public media prepared
Commit: `119179c`

Feed:
`https://raw.githubusercontent.com/zippotv1337-code/codex/main/creator-collab/assets/meta-public/2026-09-27/leona-mara-collab/feed.jpg`
- 1080×1350 JPEG
- HTTP 200 / image/jpeg
- SHA-256: `4CA01967FDC72B89538C550136A678F18D56DD7A3C47CE07A2AC15733534F3BB`

Story:
`https://raw.githubusercontent.com/zippotv1337-code/codex/main/creator-collab/assets/meta-public/2026-09-27/leona-mara-collab/story.jpg`
- 1080×1920 JPEG
- HTTP 200 / image/jpeg
- SHA-256: `480E497CD39C64F712BCB87D839B68C10563D45B379C5A23D5864B36FB47E5B7`

## Final feed copy
Two different vibes. Same energy. 🖤

Eigentlich ziemlich unterschiedlich — und vielleicht funktioniert es genau deshalb so gut. 👀

Leona × Mara ✨

Okay, wichtige Frage:
Wer von uns beiden würde bei einer spontanen Challenge zuerst einknicken? 😏

#LeonaXMara #Collab #GirlsDay #Lifestyle #GoodVibes

## Intended live flow
1. Read-only Meta preflight for `leonavoss.ai` and `mara.field.ai`.
2. Create exactly one feed media container on the primary account with native AI disclosure enabled and Mara as collaborator.
3. Publish exactly once; on unknown publish outcome do not retry blindly—reconcile first.
4. Confirm media ID + permalink.
5. Publish the prepared story asset on the approved account(s) after the feed is confirmed live.
6. Record receipt / current state.

## Current blocker — no publish attempt occurred
- On the currently connected ZiPPoWorkz Windows device, the former Meta variables are absent from Process and User environment.
- `.env.local` contains no Meta credentials.
- DPAPI Secret Broker currently has no registered secrets.
- The saved ChromeShot Instagram session is logged out.
- Therefore **no Meta container and no media_publish request were sent on 2026-09-27**.
- The older 2026-09-21 live tokens were documented as rotation-required; do not recover or reuse them from chat/logs.

## Next exact action
Securely reconnect current Meta/Instagram credentials or an authorized Instagram publishing connector. Then execute the intended live flow above without regenerating assets.


## RESOLVED LIVE — 2026-09-27
- Fresh local Meta credentials were supplied in `.env.meta.local`; values were never printed or committed.
- File is covered by `.gitignore` rule `.env.*` and is not tracked.
- Read-only preflight passed:
  - `leonavoss.ai` = MEDIA_CREATOR, quota before publish 0/100.
  - `mara.field.ai` = BUSINESS, quota before publish 0/100.
- Feed published exactly once from Leona with Mara passed as collaborator:
  - Media ID: `17918424729450608`
  - Permalink: `https://www.instagram.com/p/DdyhcL_EZzC/`
  - `media_product_type=FEED`
  - `is_ai_generated=true`
- Mara collaboration-invite read/accept endpoint is not available through the current Instagram Login token/host; Mara must accept the Collab invite in Instagram for the feed post to appear as co-authored on her profile.
- Prepared story image published to both accounts:
  - Mara story media ID `18137474008715760`
  - Leona story media ID `17869614849642694`
  - Both confirmed `media_product_type=STORY` and `is_ai_generated=true`.
- Quota after publish:
  - Leona: 2/100 (feed + story)
  - Mara: 1/100 (story)
- Higgsfield calls: 0
- Higgsfield cost: 0 EUR
- No blind retry occurred.
