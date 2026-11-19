# Barricade scan recovery for a Custom integration

The durable scanner is opt-in for each server and integration. It needs the
journal migration, an authenticated API key, a fresh shared roster and
session-journal observations. An explicit registration enables the backend and
collector for that server when `HLL_BARRICADE_DURABLE_SCANS` and
`HLL_BARRICADE_JOURNAL_OBSERVATIONS` are unset. Setting either applicable flag
to `0` explicitly disables that service. Without a registered integration, the
collector neither publishes Barricade journal evidence nor records its CONNECT
observations. Database or registration lookup failures skip this optional
evidence and leave ordinary log processing running.

When switching from the legacy scanner, take and verify a paired backup and
stop the old consumer before registering the integration. Register its
dedicated key with the Django management command `barricade_scan_integration`.
Registration snapshots existing session IDs under a database lock. PostgreSQL
records the cutover time and the first observations of new connections.
Start the new consumer with the binding; the default configuration needs no
internal Compose override for these two switches.
Check for a fresh roster snapshot for the registered namespace. A WebSocket
connection alone does not establish which scanner handled it.

For automatic dispatch, Frontline checks that a roster taken after registration
showed the player absent before the matching CONNECT was observed. It then
checks current session and presence evidence. Existing sessions are excluded.
Under blacklist management, open **Review Barricade scans** to inspect a
missing connection observation, reconstructed session or missing response.
Ended and reconstructed sessions have no retry option. An authorized operator
can record a decision and reason for each entry.

The review page's status distinguishes disabled, unregistered, unavailable,
missing roster, missing log observation, pending events, and available evidence.
Available evidence only means the individual observations were readable and
fresh when checked. It does not establish their relative ordering, a current
Barricade connection, complete game logs, or successful scan delivery. A new
collector pass attempts to invalidate its prior success until that pass
completes. If the collector cannot reach Redis, the previous observation may
remain readable until it expires, so the status display may still report
individually available evidence. Before each automatic scan, a Redis-time
barrier now requires a collector poll to begin after the verification starts;
an older readable observation alone cannot pass that check. The barrier does
not prove complete game logs or prevent a disconnect immediately afterward.

The review list includes sends still marked `sending`, even when a peer has not
reconnected. An authorized operator can request a state check with a reason.
The check takes the same integration lock as the sender: if the send is still
active it waits for the sender to finish; if it remains interrupted, it moves
the entry to review without transmitting again. A completed send is not
overwritten. A later retry remains a separate, explicitly audited decision.

The public Barricade custom-integration handler at commit
`de36456bb4aebbc253fe6d1839af7efac8bbbdf8` runs its player-alert handler before
responding. That handler can return without an alert (for example, when no
alerts channel is configured); a successful response confirms completion of
the handler, not that a Discord message was delivered. A downstream failure
can occur after some side effects, and a repeated scan can invoke the alert
path again. Therefore a failed or missing response must not be replayed
automatically. This source inspection and isolated contract test do not prove
which Barricade version is running for a particular deployment.

At the same public Barricade revision, Custom integrations use the configured
WebSocket address directly and preserve its query string. Community RCON
integrations instead append `/ws/barricade` to the configured base URL. Adding
the integration query to that base URL therefore does not produce the intended
WebSocket path and query. For a **Custom** integration with an exclusive key,
registering the authenticated key ID allows its existing query-free URL to
remain in use. Keep the same integration UUID when rotating that key so its
delivery history survives. A shared key alone cannot identify a peer.
This binding does not establish ownership of pre-existing CRCON bans.
The isolated contract test
exercises both published URL adapters, not the version in actual use.
To repeat the optional offline contract test, obtain the four public files at
that revision (`integrations/custom/websocket.py`, `integrations/custom/integration.py`,
`integrations/crcon/integration.py`, and `integrations/websocket.py`). Set
`BARRICADE_PEER_SOURCE` to the first file and `BARRICADE_PEER_URL_SOURCES` to a
directory containing the latter three as `custom.py`, `crcon.py`, and
`websocket.py`. Run `pytest tests/test_barricade_public_peer_contract.py` in an
isolated test environment. The test checks the pinned Git blob hashes and
substitutes the alert callback; it does not contact Barricade or Discord.

The new consumer rejects an explicitly requested or registered connection
if durable scanning is disabled or its binding cannot be used. An unregistered
peer without the parameter uses the legacy path. On rollback, keep the
registered peer disconnected from any older backend until pending and
uncertain deliveries are reconciled. Older binaries do not know the binding.
Keep shared maintenance on an image that recognizes the migrated Alembic
revision, including after a host or Compose restart.

If maintenance on this shared database must preserve historical player IDs,
set `HLL_MAINTENANCE_LEGACY_PLAYER_IDS=0` in the host environment file and
verify the effective value on the maintenance service for each startup path.
This skips the two historical ID cleanup commands while continuing schema
and Redis migrations. The default value of `1` retains the legacy cleanup.

The migration refuses to drop its tables when integration or scan history
exists. Rolling back application code does not require dropping those tables;
preserve them and the backups. Never delete this history to force downgrade,
because it is needed to distinguish confirmed, uncertain and reviewed work.
After restoring a database backup, reconcile deliveries before reconnecting
the scanner. Barricade may have processed a scan after the backup snapshot.
