# Leadership votes and Discord action diagnostics

## Votes never start on busy servers

Inspect leadership presence age/tenure and the routines log before changing any
quorum or five-minute eligibility settings. Repeated `Incomplete live roster`
errors with all leaders' tenure resetting together can be caused by joining the
independently cached `get_players` and `get_detailed_players` UI responses.
Ordinary joins/disconnects make those responses temporarily disagree.

The vote context now uses every row from one timestamped bulk player snapshot,
through the existing HLL/HLLV adapter. It does not load a second roster or player
profiles. Missing/duplicate IDs, invalid packets, stale snapshots and unconfirmed
rounds still fail closed. Individual lifecycle/role changes still invalidate the
affected participant; the five-minute tenure and original majority remain intact.

After deployment, allow five minutes of real observation. Never backdate presence
records or replay old reports/ballots to make a production test succeed.

## Discord says the application did not respond in time

Incoming reports working does not prove that action callbacks work. Check the
central Discord integration's callback URL from inside the Discord service, using
the existing capability with `POST /api/discord/v1/diagnostics/ping` and the matching
installation ID. Do not log tokens. Compare latency, not just the HTTP status.

In a shared-database multi-server installation, an unavailable primary backend can
block actions for the whole installation. Back up the callback URL before moving
it to another verified public backend **of the same installation**. The diagnostic
response must confirm the installation ID. Existing incident action forwarding
must remain enabled so the incident's original server, not the callback backend,
receives the game action. Do not re-pair, change role permissions, or replay failed
moderation actions as part of a transport repair.

A callback ping is read-only; it is not evidence that a real kick occurred. Test
moderation execution with synthetic players in an isolated test environment, or
with separately agreed live participants. Keep existing reports and votes intact.
