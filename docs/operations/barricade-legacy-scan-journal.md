# Legacy Barricade scan delivery

Unregistered connections use a fresh random `unbound:` identifier for each
connection attempt. It identifies neither a credential nor a Barricade
integration. Each session selected by the legacy loop is committed as
`sending` before the batch is sent. A failed or lost reply is recorded for
review; a sender interrupted before recording its result remains visible as
`sending` and can be checked through the existing audited review API. Neither
the worker nor the review API retries an unbound scan.

If an earlier unbound attempt for the same server and player session is still
sending or has an uncertain result, a later unbound connection records a
separate `prior_unbound_uncertain` review without sending. A per-session
database advisory lock orders these checks across updated workers. This does
not mean the two connections are the same integration: they might be distinct
peers, in which case the later peer's scan is deferred for manual review. The
new review cannot be marked delivered because no send was made. Manual review
of the earlier uncertain attempt does not authorize a later automatic replay.
The same check applies when a subsequently registered integration tries to
scan that session: it records a "not sent" review without attributing the
earlier unbound attempt to that integration or allowing automatic retry. This
is conservative if the peers were actually different.

This change addresses only attempts selected by the existing legacy loop after
all senders run the new version. It does not recover attempts lost before
installation, identify unregistered or shared peers, prove delivery to Discord,
or repair the legacy timestamp cursor. Equal timestamps, late commits and
connections while the WebSocket is disconnected can still be missed. The two
corresponding legacy regression tests remain expected failures. Existing
unupdated workers can send without this journal, so mixed-version rollout is
not covered by the cross-connection guarantee. The registered durable scanner
has a separate identity and delivery model; unbound records are not attributed
to it or queued for that scanner.

Database/journal failures prevent a new send in this path. A `sending` record
may represent either a request in flight or a process interruption; the review
operation takes the same namespace lock as the sender before deciding which.
There is no claim of exactly-once delivery when the external peer can act
before its response is received.
