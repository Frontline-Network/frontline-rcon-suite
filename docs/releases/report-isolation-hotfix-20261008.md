# Report Admin intervention isolation hotfix

Deployed on **2026-10-08** to **RCON3, RCON4 and the shared Discord report
service** on `87.106.112.21`. Final checks completed at **21:56 UTC / 23:56 CEST**.
Public version remains **v0.9.2**. No GitHub release, tag or push was made.

## Corrections

- `3bdddb94`: a moderation action against an unrelated player no longer cancels
  every report awaiting AI interpretation. A known target intervention still
  cancels immediately. If the final target is not yet known, interventions against
  original roster members are persisted and checked after independent resolution.
  Server-wide interventions, explicit report takeover and target protection remain.
- The worker supplies normalized leadership roles to the model. HLLV helicopter
  logistics officers, tank commanders and recon leaders are interpreted as leaders
  when the game-role resolver identifies them as such. Squad labels, alphabet
  aliases and the reviewed commander spelling `kommder` are clarified.
- `6d07bc38`: a player handle followed by `SL` is not a squad label, including a
  misspelled full handle. The backend still resolves and validates the player.
- `d16f7430`: prompt version `report-reason-3` requests short literal source
  excerpts, without grammatical corrections. Altered excerpts remain rejected.
- Codex report interpretation has a **35-second total budget**, including startup
  and admission waiting, within the worker's existing 45-second HTTP timeout.
  Per-operation waits do not renew that budget. Timeouts and uncertain attempts
  remain manual, without an automatic repeated analysis or kick. This bounds
  waiting; it does not guarantee provider availability or response time.
- Failed final role/seat checks retain bounded private diagnostics. Public
  incident summaries do not expose the intervention map or diagnostic seats.

Report Admin remains **active with previously authorized real kicks**. Provider,
model, rule flags, selected templates, the existing self-report test exception,
individual Teamkill policy and manual-only cheat sanctions were preserved.
Leadership voting stays disabled. SMTP remains `mail.fln.gg:587`, TLS,
`noreply@fln.gg`, with its existing password. No settings or schema migration.

## Verification

- **898 backend, incident, leadership and CSRF tests passed**, with two optional
  tests skipped and 11 subtests passed. **123 Discord service tests passed**.
- The backup schema was restored into a temporary network-isolated PostgreSQL
  container. Synthetic records confirmed advisory locks, intervention JSON
  persistence across sessions, target cancellation and server isolation.
  This was a schema restore, not a full-data restore. The temporary database and
  its anonymous volume were removed; all deployment backups were retained.
- The final real-model series contained **16 synthetic reports**. Fifteen matched
  the intended classification and target reference. One three-edit player name
  in a 100-player roster remained explicitly uncertain and manual. This safe
  fallback was retained, not converted into a forced match or retried until the
  model returned a kickable answer. Maximum response time in that series: 6.49 s.
- Independent target resolution passed all 16 outcomes, including the manual
  fallback, plus **32 rejection variants** for missing players, lost leadership,
  opponent-team targets and duplicated identities. Authentication and one-attempt
  deduplication were checked on the analysis endpoint.
- Earlier real-model checks exposed a handle incorrectly classified as a squad
  and a grammatically altered excerpt; the follow-up commits address these.
  Their private evaluation records remain available alongside the final series.
- Final installed source hashes, images and unchanged runtime environments matched.
  HTTPS, anonymous config denial, CSRF/no-store, authenticated config reads,
  single Report-Admin worker ownership, running routines and shared workers passed.
- RCON3 returned **98 players and 760 fresh evidence-log lines**; RCON4 was empty
  with two fresh log lines. No checked new Report-Admin or shared-worker errors.
  Discord diagnostics reported service, Discord binding and callback **online**.

No synthetic live incident, player message, test kick or ban was generated.
Model tests used synthetic inputs and the analysis-only endpoint, creating only
technical attempt receipts. Historical reports were not replayed. A naturally
submitted report remains necessary to confirm a new complete live kick workflow.
Voice silence is still an allegation, not something RCON can independently prove.

## Backups and deployment scope

Private directory: `/root/hll_rcon_tool/.deploy-state/report-isolation-20261008/`.
Configuration and state files contain credentials and must not be published.

| Backup | Bytes | SHA-256 |
| --- | ---: | --- |
| `rcon-postgres.dump` | 2,399,640,545 | `0d24acb79f904ae107a7c5ff7ac1187b5d3773ac0df1c877cbad3495a5c175b2` |
| `central-postgres.dump` | 372,133 | `10599962451f5eec1401efaaec739b830d040c1cbe9c11771ea2452b126f3464` |
| `configuration-before.tar.gz` | — | `2995c6e71f524aa80c50ff630a282cf658d1c632a234ceca245f7ac7a1120fe7` |

Both database archives were fully read by `pg_restore` before deployment.
Nine production Python files were overlaid on the existing images; all base
layers were preserved. Deployed source revision:
`d16f743089d2830380774d87d4f4a19a3ae65894`.

- Backend and shared consumers:
  `sha256:e964d6a1bc61f6ffdfa68465b95a266183578d62307693f9664d8191135e3d08`
- Shared Discord service:
  `sha256:69f0cd45aac5625f006e87b9d885f646bd0a4dd423d58ddaec5f3f38ae1d21e6`

The central service was updated and evaluated, then the shared consumers,
RCON4 as canary, and finally RCON3. Action locks and pending-case checks protected
the cutovers. Autobalancer execution leases protected each RCON restart and were
released afterward. Previously running supervisor processes remained running.

Frontends were neither rebuilt nor restarted. PostgreSQL, Redis and game servers
were not restarted. Protected containers retained their IDs and running states;
RCON1/2 remain stopped. HLL1, Ente1/2, Atomaresecho and other hosted RCON applications
and configurations were not changed. Original Compose files were not overwritten.

## Rollback

The private `rollback.json` and `central-rollback.json` preserve the previous
images; `hotfix.json` and `central-hotfix.json` describe the current deployment.
Baseline image tags are `frontline/report-isolation-base-backend:20261008` and
`frontline/report-isolation-base-central:20261008`.

Use the original project names and only the approved explicit services with
`up -d --no-deps --pull never`. Check and coordinate pending report actions under
the existing action lock before rollback; do not replay them. Preserve current
incident history and settings. No full-database restore or configuration conversion
is needed for this hotfix. Do not restart retired RCON1/2 or enable leadership votes.
