# Semantic Report Admin hotfix — 2026-10-07

Deployed to **RCON3, RCON4 and the shared Discord report service** on
`87.106.112.21`. Public version remains **v0.9.2**; no release/tag/push was made.
Both server-local configurations were switched from `reason_mode=rules` to
`reason_mode=ai` after verification, completed at **15:18 UTC / 17:18 CEST**.

## Source and behavior

- `c3d941343088c5ebc1647ab2320105880e1fc0d1`: full-reason semantic routing,
  independent current-player resolution, protected worker and wizard selector.
- `fe879a84e1948bdce852d0cea9df3707299669d3`: fix Codex `thread/start` sandbox
  enum (`read-only`, not `readOnly`), with a wire-level regression test.
- `f4958ce18e4607adb949f90b1110d5978d423e27`: sanitized provider diagnostics.
- `cb33a6ac3a65314cf48a71a70ad19c00227243e2`: bounded admission waiting and
  live-report priority when the existing Codex account is busy.

The complete report is interpreted using the installation's existing Codex
connection and configured `gpt-5.6-luna` model. No account/model was substituted.
The model supplies neither executable commands nor a target player ID.
Original and fresh rosters, role/team/session continuity, literal source excerpts,
admin takeover and existing action guards remain authoritative.

Report Admin remains **active with the previously authorized real kicks**.
Communication/TK flags, non-sanctioning cheat review and selected templates were
preserved. RCON3 retains templates 30/6; RCON4 retains null selections.
`allow_self_reports=true` remains the previously authorized real-kick test
exception on both servers; it is not a dry run. Leadership voting stays retired.
SMTP remains `mail.fln.gg:587` with TLS and `noreply@fln.gg`; its password and all
runtime environment values were preserved, not logged in this document.

Settings: **Apps → Discord-Report-Bot → KI & Report-Admin → Einordnung des
Meldegrunds**. The source defaults still keep other installations in rule mode.

## Busy account handling

Real evaluation exposed an existing Codex startup enum error, then occasional
account contention with Chat/Name analysis. Connected-account status alone had
not proved inference worked. These findings were addressed before activation.

A waiting live report now takes priority over not-yet-started normal account
work. An already running analysis is not interrupted. Admission waits for up to
15 seconds; only the typed refusal raised **before account/runtime/model startup**
allows another admission request after two seconds. That refusal releases only
its pre-inference receipt. All actual/uncertain model attempts remain deduplicated;
generic 429/503 responses, timeouts and lost replies are not retried. RCON commits
its sending marker and checks cancellation/configuration/deadline again before
requeueing. The entire classification still expires 60 seconds after the report.
Prolonged overload therefore still becomes a manual case, never a delayed kick.

The priority is per installation in the existing service process. It does not
create additional accounts, parallel access to one account, or a new provider.
No automatic repetition of a kick was introduced.

## Backups and scope

Private state: `/root/hll_rcon_tool/.deploy-state/report-reason-20261007/`.
Its configuration/Compose files contain credentials: **do not publish them**.

| Backup | Bytes | SHA-256 |
| --- | ---: | --- |
| `rcon-postgres.dump` | 2,339,939,335 | `c541970f07745fc840d196d1602b7194776f1943833c8f00949b1348e55cb005` |
| `central-postgres.dump` | 338,851 | `aa5ef4e7507301ee8847b3eb85cadc1f74fcb909a0611c6cfde65b791b16c879` |
| `configuration-before.tar.gz` | — | `ca070544a418188fd0863901da36c0729240eab9a068fb217b2858ea0210a286` |

Both database archives were fully read by `pg_restore`. Schema was restored
into a network-isolated temporary PostgreSQL container and tested with synthetic
records (locks, JSON state, scheduling, recovery, server isolation). This was
not a full-data restore. The temporary container/volume was removed; all real
backups, including previous deployment backups, remain.

Final images:

- Backend/shared consumers: `sha256:528054b4e9362c21d06668623b14b78eccd30f9ea15f52a4e1187982df539e5d`
- Frontend: `sha256:60e28f7e4e09e87a1e0d744632ab95effb17d7f38169b301452034f3775d9787`
- Discord service: `sha256:21f752b2d327bea36f590c8ea44cf195f81973242b9d8e80130b4b804aff94db`

The frontend is the c3d94134 production build (later fixes changed no frontend
source), API `/api/`, version `v0.9.2`. Backend and Discord include cb33a6ac.
Original image layers were retained through scoped overlays.

The shared consumers were updated, then RCON4 as canary, followed by RCON3.
Report/vote action locks, pending-case checks and an Autobalancer execution lease
protected each RCON cutover. Leases were released. No PostgreSQL, Redis or game
server restart; no schema migration. Protected containers kept their IDs and
running states. RCON1/2 remain stopped. HLL1, Ente1/2, Atomaresecho and other
hosted RCON applications/configurations were not updated.

## Verification and limits

- Prior implementation checks: 860 backend/incident/leadership tests (2 skipped),
  115 Discord tests, four Node UI tests, four Playwright wizard tests, localization
  and CSRF checks and the production frontend build. Existing bundle-size warning.
- Follow-up checks after the deployment fixes: **169 backend/API tests** and
  **120 Discord tests**. These include priority ordering, no overlapping account
  runtimes, admission timeout cleanup, bounded requeue, takeover, generic failures,
  no inference before a typed busy refusal and no duplicate real attempt/kick.
- The last complete **19-case real-model series passed**, with unchanged prompt
  and semantic resolver: DE/EN complaints, spelling/spacing variants, paraphrases,
  squad/commander references, corrections, negations, quotations, spawns-only,
  missing-mic-with-chat, mixed/multiple targets, TK/cheat review and prompt injection.
  Replies took at most 11.38 seconds in that series. Independent target resolution
  also passed, including removed/nonleader/opponent/duplicate-player variants.
- After the priority fix, a real analysis with a **synthetic 100-player roster**
  and an exact player reference completed correctly in 5.48 seconds. No admission
  retry was needed in that particular request; contention is covered by the
  deterministic queue tests, not claimed as a natural live contention pilot.
- A separate 100-player typo case produced an explicit model uncertainty. The
  guard rejected it for automatic action, as intended. Spelling tolerance is
  therefore not a promise to auto-act on every two-letter typo. Earlier failed
  diagnostic calls and their sanitized/private receipts were retained, not erased.
- Both public frontends passed HTTPS, CSRF/no-store, anonymous config denial,
  authenticated config reads and hashes of **92 referenced assets each**. Installed
  backend/Discord source hashes, expected images and unchanged environments matched.
- RCON3 returned 98 players and 755 fresh evidence-log lines at the active check;
  RCON4 was empty with two fresh log lines. Each server had one Report-Admin owner
  and running routines. Previously running supervisor processes remained running;
  `log_stream`, `seed_vip` and `watch_killrate` retained their prior `EXITED` state.
- No checked new report/worker errors after cutover. Shared background/webhook
  services were healthy. Discord authentication and an existing report were verified
  with a read-only API request.

**No synthetic live incident, player message, test kick or ban was generated.**
Model evaluations used the analysis-only endpoint and synthetic rosters/text;
they created technical attempt receipts, not moderation cases. Historical kick
counts were unchanged in the final read and are not evidence of a new live kick.
A naturally submitted report remains necessary for live end-to-end acceptance.
RCON still cannot prove whether someone spoke on voice chat; the communication
rule relies on the report, with the documented false-report risk.

## Rollback

Before source rollback, safely stop new Report-Admin work and cancel pending
classification/actions under the shared action lock. Preserve current config,
remove `reason_mode` (unknown to the old strict schema), or restore only the
scoped pre-change Report-Admin configuration. Retain incident history. Never
restore the entire live database just to reverse this hotfix.

Private `rollback.json` / `central-rollback.json` restore the pre-hotfix images;
`hotfix.json` / `central-hotfix.json` are the final active models. Rollback tags:
`frontline/report-reason-rollback-{backend,frontend,central}:20261007`.
Use original project names, explicit approved services and
`up -d --no-deps --pull never`; never `--remove-orphans`. Do not restart retired
RCON1/2 or re-enable leadership votes. Backward/forward service updates must be
coordinated because the worker's safe busy-requeue code depends on the typed
pre-inference response from the updated central service.

Reference for the Codex protocol distinction:
[Codex App Server](https://learn.chatgpt.com/docs/app-server).
