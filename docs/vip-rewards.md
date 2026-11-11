# Additional VIP rewards

The **VIP-Belohnungen** page is at `/settings/others/vip-rewards`. Seed-VIP remains
at its existing location. Additional rewards ship disabled, with preview and the
seeding pause enabled. No game server changes are made by installing the code.

## Deployment

1. Back up the database and apply Alembic migration `c8e2a4f61009` through the
   existing maintenance-container workflow.
2. Deploy the backend and frontend together. Run the normal configuration seeding
   step. The new `vip_rewards` Supervisor program runs `manage.py vip_rewards`.
   If using a server-specific Supervisor file, copy that program stanza into it.
3. Give administrators the existing `can_view_seed_vip_config` /
   `can_change_seed_vip_config` permissions for configuration and
   `can_view_vip_ids` for status, progress and the journal.
4. Enable selected rules in preview first. Verify seeding pause, qualifying events,
   player exclusions and journal results on the target server before enabling live
   delivery. Preview progress and budgets are independent of live data.

## Rules and limits

The seeding gate uses Seed-VIP's `max_allies` and `max_axis`, even when Seed-VIP
awards are disabled. Both thresholds must hold for five minutes. Snapshots run
every 30 seconds; a detected drop or failed observation pauses rewards. A status
older than 60 seconds also pauses rewards, even if the seeding pause is disabled.
No paused or unobserved time is backfilled. Reconfiguration resets the attendance
baseline; a worker restart also resets the seeding release and balance signups.

The shared budget defaults to 24 hours per player/server in a rolling 24-hour
window. Seed-VIP and manual grants are excluded. Rewards are truncated to the
remaining budget; excess is discarded. Completed challenges and milestones are
consumed even if nothing can be awarded. Daily rule limits count positive grants.
Uncertain writes reserve their budget conservatively.

Only confirmed team membership at consecutive observations earns attendance time.
This is not an AFK detector. Round attendance is measured against observed,
unpaused round time. Daily and weekly rules use the configured time zone (default
Europe/Berlin, Monday week start). Event windows require explicit timezone offsets.

`!balance` signs up a player on the larger team, with at least four players'
difference by default. Signup lasts five minutes. A matching switch log and 15
minutes of confirmed presence on the target team are required. Ambiguous names,
unobserved transitions and RCON-triggered switches do not qualify. External admin
tools bypassing this RCON cannot be identified reliably; use the feature only when
team-switch commands are managed through this RCON. Returning or disconnecting
cancels the signup.

## Delivery and diagnostics

The database contains a durable event queue, separate preview/live progress, and
an immutable grant identity `(server, mode, player, rule, trigger)`. Processed queue
events are retained for 48 hours. The grant journal is retained for auditing.
PostgreSQL advisory locks serialize workers and player VIP writes across processes.
Manual changes, Seed-VIP, expiry cleanup and new rewards share the player lock.

A grant's absolute target expiry is committed before contacting HLL. After a
timeout the worker reads back that target without re-adding the duration. A match
is recorded as `awarded`; a mismatch becomes `review`. New grants for that player
are then withheld pending review. Notification failures never repeat a grant.

Monitor `vip_rewards_<server>.log` and the journal, especially `prepared` or `review`
entries and a stale/unknown status. For uncertain writes compare the stored target,
current VIP and intervening admin changes before making any manual correction.
Do not replay a reward or delete its journal record to retry it.
After inspecting/correcting the VIP manually, use **Als geprüft markieren** in the
journal (`can_add_vip` required). This acknowledges the conflict, allows future
rewards and records the administrator; it neither replays the write nor refunds
the reserved 24-hour budget.

Configuration API: `get_vip_rewards_config`, `validate_vip_rewards_config`,
`set_vip_rewards_config`. Read APIs: `get_vip_rewards_status`,
`get_vip_rewards_progress(player_id)`, and
`get_vip_rewards_journal(offset, limit, player_id, preview)` (maximum 100 rows).
Configuration revisions are server-generated; validation never writes settings.

## Offline validation

Run `python -m pytest tests/test_vip_rewards.py tests/test_logs.py
tests/test_seeding_rules_automod.py` with `SERVER_NUMBER=1` and
`HLL_MAINTENANCE_CONTAINER=1`. Delivery tests use SQLite journal transactions and
mock game-server calls. PostgreSQL locks and the game protocol still require a
staging smoke test; offline tests are not a production readiness claim.

Build the web application with `REACT_APP_API_URL=/api/` and `vite build`. The
existing fake/demo mode includes the new settings page for offline UI checks.

## Weekly support reward (local implementation)

The optional weekly_support rule counts observed increases in support score across
rounds, Monday–Sunday in the configured timezone. It is disabled by default;
5,000 points and 6 VIP hours are editable example defaults, not calibrated targets.
Settings and state are server-scoped, so HLL and HLLV may use different targets.
The rule shares the existing daily budget, preview mode, seeding pause, exclusions
and confirmed-delivery notification. One claim per player and local week.

Existing match totals are baselines, never retrospective credits. Round identity
is required in the worker. Round boundaries reset the score baseline but retain
weekly totals. A match high-water mark prevents duplicate credit after score
rebounds or reconnects. Unobserved gaps, configuration-change intervals, unknown
rounds, unhealthy snapshots and intervals crossing Monday are not estimated;
this conservatively can omit points. Weekly progress is stored in existing JSON
state; no additional database migration is needed.

The status_command setting defaults to !rewards, accepts a custom !command, and
can be empty to disable replies. Exact matching is case-insensitive; arguments
are not accepted. Replies are private, bilingual, limited to once per 30 seconds
per player, and suppressed in preview/disabled mode. The reply shows current-week
support progress and the configured reward, distinguishing goal completion from
confirmed credit. Conflicts with configured chat, map-vote and balance commands
are checked when saving and before replying. New conflicts introduced through
other configuration pages suppress this handler rather than overriding commands.

Local verification: 144 backend tests, 4 browser tests and production build passed.
No live deployment, real VIP grants or player messages were performed.
