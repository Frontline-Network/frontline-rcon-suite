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
