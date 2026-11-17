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

At the same public Barricade revision, Custom integrations use the configured
WebSocket address directly and preserve its query string. Community RCON
integrations instead append `/ws/barricade` to the configured base URL. Adding
the integration query to that base URL therefore does not produce the intended
WebSocket path and query. An experimental path-scoped proxy route carries an
explicit peer ID for both the API and WebSocket, but the full integration is
not yet compatible: RCON3 reports Frontline `v0.9.12` and the published peer
rejects versions below v10. It also expires active records it does not know in
its selected blacklist. Do not advertise a compatibility version or activate
this route until the API contract and blacklist ownership behavior have been
validated and protected. Do not infer a unique peer from a potentially shared
API key. The isolated contract test exercises published peer code with
synthetic data, not the version in actual use.
The pinned public CRCON peer's `get_player_eos_ids` returns `None` for its
Hell Let Loose Vietnam EOS-ID slot even when a profile contains an EOS ID.
Its report-forwarding code explicitly treats the Vietnam game ID itself as
the EOS ID, so that lookup result does not establish a Vietnam scan or report
failure. The isolated contract tests exercise both code paths; the installed
peer and a live Vietnam connection have not been verified. The protective 403 for
automatic record expiry can interrupt synchronization when Barricade sees an
unrecognized active record; it protects the record but does not constitute a
successful synchronization. Do not enable this experimental route as a
production-ready integration while these conditions remain unresolved.

The legacy WebSocket handler can return an existing manual record's ID, which
can later permit its removal. The experimental explicitly bound path has an
additional, disabled-by-default ownership guard
(`HLL_BARRICADE_BLACKLIST_OWNERSHIP=1`). It records provenance atomically with
new records and the delivery journal, refuses to adopt unowned existing bans,
and requires the same integration and current credential for removal. Old
records are not automatically assigned to any integration. The legacy path is
unchanged, and the PostgreSQL test
`test_manual_record_must_not_be_claimed_as_barricade_owned` documents its gap
as a strict expected failure. Do not enable the guard on an existing connection
without first resolving existing records and the CRCON synchronization issue.
The feature flag and isolated tests do not certify the entire peer workflow.

The pinned public peer exposes `GET /communities/me/bans`, requiring its own
community ban-read scope, with an `integration_id` filter and per-item `game`
and `remote_id` fields. The Frontline Custom WebSocket credential is not
evidence of access to that API. Its query uses offset pagination without an
explicit ordering or snapshot; a live multi-page read can omit or duplicate
records when data changes. A complete, consistent, correctly scoped snapshot
is therefore a prerequisite for reconciliation, not something inferred from
an empty response or one successful page. Filtering existing Frontline rows
without proving the peer's complete state is unsafe: the peer deletes its
own local reference when its remote ID is absent. The read-only comparison
helper classifies overlaps and discrepancies, but does not establish record
ownership or authorize changes.
To repeat the optional offline contract test, obtain the four public files at
that revision (`integrations/custom/websocket.py`, `integrations/custom/integration.py`,
`integrations/crcon/integration.py`, and `integrations/websocket.py`). Set
`BARRICADE_PEER_SOURCE` to the first file and `BARRICADE_PEER_URL_SOURCES` to a
directory containing the latter three as `custom.py`, `crcon.py`, and
`websocket.py`. To check the Vietnam report path, also set
`BARRICADE_PEER_FORWARDING_SOURCE` to the pinned `barricade/forwarding.py`.
Run `pytest tests/test_barricade_public_peer_contract.py` in an
isolated test environment. The test checks the pinned Git blob hashes and
substitutes the alert callback; it does not contact Barricade or Discord.

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
