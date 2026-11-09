# Report-Admin cases, retired votes and Discord stats — 2026-10-06

Deployed source: `1e5a4b6e20170c65299245ea8c0b4415d1597595`, branch
`codex/report-admin-mvp`. Hotfix only: public version remains **v0.9.2**.
No GitHub release, tag or push was made.

## Scope and behavior

The approved scope was **RCON3, RCON4 and the shared Discord report service**,
with backups. This deployment does not update the other RCON installations.

- Leadership voting is retired from chat, runtime and configuration UI. Startup
  recovery disables its old configuration and retires pending votes/messages;
  historical records remain available. Activation is rejected by the API.
- Report-Admin configuration is in the top setup wizard under
  **Apps → Discord-Report-Bot → KI & Report-Admin**, with a separate
  **Report-Regeln speichern** action. Optional Chat/Name AI remains separate.
- Teamkill reports use individual cases instead of the fixed five-in-five rule.
  There is a silent 60-second opportunity to apologize after the latest TK,
  with up to 15 minutes of context covering both reporter and accused.
  Automatic action requires a recorded TK and a narrowly recognized explicit
  first-person admission of intent. Apologies, reciprocal TK and ambiguous
  context go to human admins. Counts or a missing apology alone do not prove
  intent. See [the rule specification](../report-admin.md).
- Optional cheat review provides weapon/role context and 1/5/15-minute evidence
  windows for human review. **No automatic cheat kick or ban.** Discord's manual
  temporary-ban dialog can suggest 24 hours, but requires an admin's decision.
- Discord target validation preserves the fresh player-stat snapshot. Teamkills,
  combat and performance also appear for squad leaders, explicitly marked as
  the leader's stats rather than squad totals. Zero and unavailable values are
  distinguished; total embed size is bounded. This affects **new or updated
  reports**; existing cards were not bulk edited or backfilled.

This is a deterministic, rule-based Report Admin, not a new LLM integration.
The existing communication rule remains active and relies on the report;
RCON cannot establish whether someone spoke on voice chat.

## Live configuration

On both RCON3 and RCON4, Report Admin is enabled in `active` mode with
communication and teamkill rules enabled. Non-sanctioning cheat review was
enabled after both server checks. Existing `allow_self_reports=true` was
preserved: this remains a **real-kick test exception**, not a dry run.
Disable that option when self-report testing is finished.

All other settings were retained, including RCON3 reason templates 30
(communication) and 6 (teamkills); RCON4 still has no selected template IDs.
The selected template texts do not contain the obsolete fixed TK threshold.
SMTP and all container runtime environment values were verified unchanged.

## Backups and deployment

Host: `87.106.112.21`. Private deployment state:
`/root/hll_rcon_tool/.deploy-state/report-admin-cases-20261006/`.
Configuration snapshots contain credentials; **do not publish their contents**.

| Backup | Bytes | SHA-256 |
| --- | ---: | --- |
| `rcon-postgres.dump` | 2,350,867,865 | `a92d648e01be72a469b2b5e5efdac34c0445fee46a36108415d1ba78074d1eea` |
| `central-postgres.dump` | 337,481 | `b843bc9fcb06f193d0758c89fc6b4817ae4fa92935b4b8e25c8cd10af3127416` |
| `configuration-before.tar.gz` | — | `a53f879b5aeed77e584017390d0ef624619a001ac7169f8c6d69886b247bd297` |

Both custom-format database archives were fully read using `pg_restore`.
An isolated PostgreSQL test restored **schema only**, then used synthetic records
to check advisory locks, JSON fields, due scheduling, idempotency, recovery,
leadership retirement and server separation. It was not a full data restore.
The temporary test container and its volume were removed; backups are retained.

New image IDs (original base layers retained):

- Backend: `sha256:1ea60f4690d295670a651ced923f1df6e33844b02d6d2f2e5cbe2abbbbf22e01`
- Frontend: `sha256:bf68a2b11e9f517d42bc30888c701bbf745f106ef4b05e267bcac5130814b7af`
- Discord: `sha256:45b9dcc5eb72293f467ae1a7388f23b202e248efffcaa9fc965e1fa4a41ac4e8`

Images are labeled `gg.fln.hotfix=report-admin-cases` and
`gg.fln.hotfix.commit=1e5a4b6e20170c65299245ea8c0b4415d1597595`.
The frontend was built with API `/api/` and public version `v0.9.2`.

RCON4 was the canary, followed by RCON3. Backend, supervisor and frontend
containers were updated, along with this installation's background/webhook
consumers and the shared Discord service. Report/vote action advisory locks,
checks for pending actions and an Autobalancer execution lease protected the
cutover. Temporary leases were released after verification.

Protected containers retained their IDs and running states. RCON1/2 remain
stopped; HLL1, Ente1/2, Atomaresecho and other hosted RCON containers were not
changed. No game server, PostgreSQL or Redis restart; no schema migration.

## Verification and limits

- Source checks: 803 core backend regressions, 53 adjacent tests plus 11
  subtests, 107 Discord tests, 14 frontend/localization tests and four
  Playwright wizard tests passed. Localization and CSRF contracts passed.
- Production frontend rebuild and network-isolated candidate imports passed.
  The build retains its existing large-bundle warning.
- Each server passed HTTPS, CSRF/no-store checks, anonymous configuration
  denial, authenticated configuration reads and checksums of all 92 directly
  referenced frontend assets. Backend/Discord source checksums matched.
- Fresh RCON3 data contained 98 players and 581 parsed evidence-log lines at
  the final check. RCON4 was empty and returned a fresh empty roster.
- One Report-Admin worker owner per server and running routines were confirmed.
  No checked new report-related runtime errors; no pending leadership messages.
- A read-only Discord API call authenticated successfully and read an existing
  report message. **Zero messages posted and zero moderation actions** by the
  deployment checks.
- Historical successful kicks predate this rollout and are not evidence of a
  new TK/cheat pilot. No synthetic report, test kick or ban was generated. A
  natural end-to-end case under the new rules is still needed for live acceptance.

## Rollback

Retained rollback tags:

- `frontline/report-cases-rollback-backend:20261006`
- `frontline/report-cases-rollback-frontend:20261006`
- `frontline/report-cases-rollback-central:20261006`

They restore the preceding source
`8287643492cb1c95e8d839d570d66bf50359980b`. Private Compose models are
`hotfix.json` / `central-hotfix.json` and
`rollback.json` / `central-rollback.json` in the deployment-state directory.

Before rollback, stop new automatic actions and safely cancel pending work
under the shared execution lock. Save current configuration, then remove the
new `cheating` key or restore the scoped pre-change configuration: setting it
to false is insufficient for the older strict schema. Use original project
names and explicit service names with `up -d --no-deps --pull never`; do not
use `--remove-orphans`. Do not reactivate leadership voting or retired RCON
services. Do not restore the entire live database for a source-only rollback.
No rollback was needed during this deployment.
