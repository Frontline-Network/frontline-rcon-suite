# Experimental Barricade scan recovery

This implementation is not yet approved for production activation. It requires
an explicitly registered integration and API credential, the journal migration,
a fresh shared player roster, and session-journal observations. Both
`HLL_BARRICADE_DURABLE_SCANS` and `HLL_BARRICADE_JOURNAL_OBSERVATIONS` default
to off. This document describes safety constraints, not an activation recipe.

The game log's event times have second precision. The registration boundary
uses the application host's clock, and a successful log poll does not prove
that the game server has exposed all prior events. Clock skew, late events,
identity uncertainty and transitions from an older scanner must be resolved
before enabling automatic scans. Unconfirmed sends and ambiguous or recently
ended sessions require operator review; a retry can create a duplicate alert.

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

With the new consumer, an explicit `frontline_integration` connection is
rejected if durable scanning is disabled or the binding is invalid. A peer
without that parameter keeps the legacy path. **Older application versions do
not enforce this restriction**: do not reconnect an opted-in peer to an older
backend without first disabling the peer or blocking its credentials and
reviewing its pending and uncertain deliveries. Merely switching the image or
turning off the flag cannot guarantee that a previous scan was not processed.

The migration refuses to drop its tables when integration or scan history
exists. Rolling back application code does not require dropping those tables;
preserve them and the backups. Never delete this history to force downgrade,
because it is needed to distinguish confirmed, uncertain and reviewed work.
