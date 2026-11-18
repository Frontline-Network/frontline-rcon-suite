# Barricade cutover prototype (issue 404)

This is an offline review artifact for public Barricade commit
`de36456bb4aebbc253fe6d1839af7efac8bbbdf8`, not a Frontline feature and not an
instruction to modify an externally operated service. Apply
`barricade-peer-404-prototype.patch` only to a disposable checkout of that
commit. The accompanying contract tests execute methods extracted from that
checkout with synthetic data and, for database cases, disposable PostgreSQL.

The prototype selects outstanding repopulation responses by both player and
game, reports missing game IDs as failures, and commits known successful
references before propagating a later bulk error. A per-integration PostgreSQL
advisory transaction lock serializes synchronization, ban/unban operations,
and list creation across patched processes. Automatic replacement of an
existing remote list is refused rather than silently deleting its references.
Empty lists can still be created for a new integration.

The proposed CRCON synchronization keeps references missing from a scan and
does not expire unrecognized remote records. It requests inactive records as
well as active records. An explicitly inactive record with the exact existing
peer reference updates the corresponding community decisions for that game;
absence from a page is never treated as proof of an unban. It logs aggregate
discrepancy counts. A deleted record still needs separately verified resolution:
the peer cannot distinguish a real deletion from an incomplete scan. An
inactive observation can race a later reactivation; the existing API provides
no versioned, cross-service conditional update to make this atomic.

Use separate integration IDs and dedicated new HLL and HLLV lists. Keep the
historical Custom integration and its lists active during any proposed
transition. The peer's `/repopulate-integration` is an explicit backfill of
community decisions, not evidence that all historical data was migrated:
manual entries and unavailable IDs require separate reconciliation. Never
repoint or remove the historical integration merely because a repopulate
message reports completion.

This prototype is **not a complete solution to #404**. It needs review and
tests in the upstream application's full runtime before it could be proposed
to its operator. It does not implement a consistent remote pagination
snapshot; protect against an independently edited remote list; provide a
durable recovery journal for remote success followed by lost acknowledgement,
database commit failure, process death or cancellation; verify peer-side
references through a complete API; or prove the external deployment runs the
patched code. Advisory-lock disconnection, deployment with mixed old and new
workers, and all other code paths that mutate references require further
fault-injection and review. It also does not establish that the external peer
would accept, deploy or operate this patch.

In particular, non-destructive synchronization alone does not stop a later
repopulate from retrying a ban whose remote reply was lost. That requires a
durable intent written before sending, keyed at least by integration, game and
player, with a unique operation generation and an explicit uncertain outcome
that survives process restarts. The intent and reference confirmation must be
committed atomically after a confirmed result; recovery of uncertain operations
must not automatically submit a new ban. This needs a peer schema migration,
recovery workflow, and tests for partial bulk replies, process death, network
loss, concurrent retries and mixed games. No such journal is included here.

An exclusive empty list created for a **new** integration avoids adopting an
old manual record, but it is not proof that an existing integration's old
references belong to a particular community or game. Reconciliation of those
references requires a complete, authoritative peer-side mapping of
integration, game, peer player and Frontline record ID, including deletions
and changes during the snapshot, verified against the deployed service. That
evidence is currently unavailable. The published peer also declares a unique
constraint on `(player_id, integration_id)` and its bulk upsert uses the same
key. Supporting both HLL and HLLV bans for one player in the same integration
therefore additionally requires a reviewed peer schema migration and updates
to unqualified lookups/unbans; changing only the repopulation query is not
sufficient. Keep the historical Custom integration in place until those
conditions and the lost-reply journal have been validated.
