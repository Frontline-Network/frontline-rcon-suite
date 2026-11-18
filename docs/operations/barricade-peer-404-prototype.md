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

The proposed CRCON synchronization is non-destructive: missing or inactive
remote records do not delete existing Barricade references or change report
decisions, and unrecognized remote records are not expired. It logs aggregate
discrepancy counts. This preserves records through shifted or incomplete pages
but also means a genuine remote unban cannot be propagated automatically by
this reconciliation path; it requires a separately verified resolution.

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
