# End-of-match rankings

This is a server-scoped, opt-in feature. An administrator with the existing
automatic-broadcast permissions can configure it under Automation / Match
statistics. Settings are stored in the server's user configuration; the message
language is separate from the interface language. When no saved setting exists,
`FRONTLINE_END_MATCH_STATS_SERVERS` supplies the initial enabled state. It must
be identical in the affected backend and supervisor processes; a deployment
should persist the initial setting before removing this compatibility flag.

The normal match-end hook captures a live team snapshot, builds rankings for
currently connected players and selected squad types, and sends at most one
player and one squad admin message. When both contain results, the squad message
is scheduled through the existing server-specific RQ queue. The configurable
delay is 5–30 seconds. A queued message older than 90 seconds or disabled before
delivery is discarded. A Redis claim suppresses replayed match-end events and
automatic command retries are disabled to avoid repeating an uncertain send.

Teamplay is `combat + support * support_multiplier`; off/def is `offense +
defense * defense_multiplier`. K/D uses kills when deaths are zero. Kills/min
requires at least five minutes of recorded playtime. The squad figures aggregate
players currently in the squad. The type filter includes selected types together
in each ranking; it does not create separate rankings per type. These are not
personal summaries and exclude disconnected players. The RCON team snapshot can
also silently omit players missing from its detailed-player response.

The feature does not implement the reference plugin's VIP rewards, Discord
posting or chat commands. A console match test must still verify the end-screen
timing, actual display of both messages, long messages and the game's font support
for all eight languages. RCON acceptance is not evidence of client display.

As of the initial AFL deployment, its running custom v0.9.12 supervisor contains
only the earlier three-category, single-message implementation. The UI,
translations, extended rankings and delayed second message in this checkout
are staging changes and require a reviewed, update-safe release. Production
deployments must include both the backend/API and supervisor/worker code; do not
copy this entire checkout over a running instance.
