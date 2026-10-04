# Leadership votes and Discord action diagnostics

## A campaign message cancels a leadership vote

If a vote ends with `Manual action`, check the incident event actor and the
target's action history at the same time. A `Campaign:` or `VIP lifecycle:`
informational message is not an admin takeover. Previously, saving any message
in that history also invoked the manual-action guard, unintentionally cancelling
the target's vote before or during voting.

Information senders now use the internal `message_player_info` delivery path.
Delivery and its existing audit record remain unchanged. The public
`message_player` endpoint gains no new parameter or bypass: saved manual messages
still invoke the moderation guard, regardless of actor names or message text.
Punishments, kicks, bans and explicit Discord takeovers remain guarded.

Expired confirmations belong to the old workflow. Since the report-start hotfix,
eligible reports queue invitations without a second response. A sent message records
RCON acceptance, not proof that the player read it. Claiming the Discord report
intentionally stops the vote, including during invitation delivery.

## Other leaders have not received invitations

New procedures start as `inviting`, never `confirming`. The report immediately
queues invitations to all eligible leaders, including its reporter if eligible,
and freezes the electorate. Dispatch waits for durable delivery of the original Discord
report; a missing acknowledgement expires safely without a kick. It does not
block invitations belonging to the other team. There is no target warning or
additional player-confirmation phase. An eligible reporting leader's `!no` is a
negative ballot, not cancelling everyone's vote. An ordinary member's reply is
not a ballot or a veto. Admin takeover still cancels an unexecuted vote.
The target receives neither private warnings nor private results; legacy queued
target notices are rejected at dispatch as well as at enqueue time.
The target and the opposing team never receive ballot invitations.
Each eligible leader receives two separate invitations: German (`invite_de`),
then the approved English `LEADERSHIP VOTE` text (`invite`). Each has its own
durable receipt and language-specific dry-run notice. English is enqueued only
after the German attempt, so it cannot overtake it; after dismissing the English
message, the German message remains below it in the game UI. Other player notices
remain bilingual in one message.

Successful delivery in either language counts as one invited person, never two.
The first successful delivery allows a response; the voting deadline gives the
full voting duration after the final successful invitation delivery. Failed or
uncertain attempts are not retried, and both languages retain the same identity,
team, phase and manual-takeover checks.

Check the durable message purposes and recipients (`invite_de`, `invite`)
alongside the chat event timestamps, rather than assuming a report is an active
vote. RCON acceptance of a message still does not prove that a player read it.
The legacy `confirmation_seconds` setting no longer gates new procedures.
The report itself is not a YES vote. Existing votes keep their snapshotted rules;
change configuration only when no vote is open, because configuration changes
cancel open procedures. Do not replay historical reports or fabricate ballots.

## A squad member's report does not start a vote

Reporting and voting have separate eligibility checks. Any currently connected
squad member in the target's team may report, including someone from the target's
own squad. A commander may also report without a squad. Self-reports, missing or
ambiguous live identities, and unassigned non-commanders cannot start a vote.
These reports still go through the normal admin workflow.

The five-minute leadership tenure applies to voters, not reporters. Ordinary
members and recently appointed leaders do not count toward the minimum of three
eligible voters. An eligible reporting leader retains their ballot. The reported
leader and, for squad-leader targets, their squad remain excluded from voting.
The report itself never supplies a YES ballot.

Check the electorate at the report's timestamp: a later promotion does not admit
the reporter to an existing vote, and a report that failed the minimum electorate
does not automatically start later. After a round change or restart, the voters
still need five minutes of fresh observation. Team locks, cooldowns, Discord
delivery, private-chat and freshness checks still apply to every reporter.

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
